"""Extract JD-aligned signals from each candidate profile."""
from datetime import date, datetime

from skill_matcher import match_groups_in_text, normalize_skill


DISQUALIFYING_TITLES_PRIMARY = {
    "marketing manager",
    "operations manager",
    "hr manager",
    "human resources",
    "sales executive",
    "sales manager",
    "content writer",
    "accountant",
    "graphic designer",
    "civil engineer",
    "mechanical engineer",
    "customer support",
    "supply chain",
    "procurement",
    "finance manager",
    "business development",
}

CONSULTING_FIRMS = {
    "tcs",
    "tata consultancy",
    "infosys",
    "wipro",
    "accenture",
    "cognizant",
    "capgemini",
    "hcl",
    "tech mahindra",
    "mphasis",
    "hexaware",
    "l&t infotech",
    "ltimindtree",
    "mindtree",
}

PRODUCT_INDUSTRY_HINTS = {
    "software",
    "saas",
    "internet",
    "e-commerce",
    "fintech",
    "healthtech",
    "edtech",
    "hr tech",
    "marketplace",
    "ai",
    "machine learning",
}

AI_ML_TITLES = {
    "ml engineer",
    "machine learning engineer",
    "ai engineer",
    "nlp engineer",
    "data scientist",
    "research engineer",
    "applied scientist",
    "applied ml",
    "search engineer",
    "retrieval engineer",
    "ranking engineer",
    "recommendation engineer",
    "mlops engineer",
}

ENGINEERING_TITLES = {
    "senior engineer",
    "staff engineer",
    "principal engineer",
    "founding engineer",
    "backend engineer",
    "software engineer",
    "platform engineer",
    "data engineer",
}

PRODUCTION_RETRIEVAL_PHRASES = [
    "embedding-based search",
    "semantic search",
    "vector search",
    "ranking system",
    "retrieval system",
    "recommendation system",
    "shipped",
    "production",
    "served",
    "deployed to",
    "30m",
    "35m",
    "50m",
    "100m",
    "million",
    "at scale",
    "migrated from keyword",
    "bm25",
    "hybrid search",
    "a/b test",
    "ndcg",
    "mrr",
    "offline evaluation",
    "reranker",
    "re-ranking",
    "two-stage",
    "candidate retrieval",
]


def score_career_descriptions(career_history: list[dict]) -> float:
    """Score career text for production retrieval and ranking systems work."""
    total_hits = 0.0
    for role in career_history:
        desc = role.get("description", "").lower()
        hits = sum(1 for phrase in PRODUCTION_RETRIEVAL_PHRASES if phrase in desc)
        weight = 1.3 if role.get("is_current", False) else 1.0
        total_hits += hits * weight
    return min(1.0, total_hits / 8.0)


def extract_candidate_skill_groups(skills: list[dict], text_groups: set[str] | None = None) -> dict[str, float]:
    """Compute trust-weighted canonical skill group scores."""
    proficiency_weights = {
        "beginner": 0.25,
        "intermediate": 0.60,
        "advanced": 0.85,
        "expert": 1.0,
    }
    group_scores: dict[str, float] = {}
    for skill in skills:
        proficiency = skill.get("proficiency", "beginner")
        endorsements = int(skill.get("endorsements", 0) or 0)
        duration_months = int(skill.get("duration_months", 0) or 0)
        proficiency_w = proficiency_weights.get(proficiency, 0.25)
        endorsement_bonus = min(1.0, 0.45 + endorsements / 18)
        duration_bonus = min(1.0, 0.25 + duration_months / 36)
        trust = 0.18 if proficiency == "expert" and endorsements == 0 and duration_months == 0 else (
            proficiency_w * endorsement_bonus * duration_bonus
        )
        for group in normalize_skill(skill.get("name", "")):
            group_scores[group] = max(group_scores.get(group, 0.0), trust)

    for group in text_groups or set():
        group_scores[group] = max(group_scores.get(group, 0.0), 0.35)
    return group_scores


def score_career_for_role(career_history: list[dict]) -> dict:
    total_months = sum(r.get("duration_months", 0) for r in career_history)
    ai_ml_months = 0
    product_company_months = 0
    consulting_months = 0
    disqualifying_months = 0
    production_months = 0
    retrieval_months = 0
    management_only_months = 0

    for role in career_history:
        company = role.get("company", "").lower()
        title = role.get("title", "").lower()
        industry = role.get("industry", "").lower()
        description = role.get("description", "").lower()
        duration = int(role.get("duration_months", 0) or 0)
        text = f"{title} {industry} {description}"

        is_consulting = any(firm in company for firm in CONSULTING_FIRMS) or "it services" in industry
        consulting_months += duration if is_consulting else 0

        if any(t in title for t in DISQUALIFYING_TITLES_PRIMARY):
            disqualifying_months += duration
        if any(t in title for t in ["manager", "lead", "director", "head"]) and not any(
            t in text for t in ["engineer", "ml", "machine learning", "data scientist", "ai", "search"]
        ):
            management_only_months += duration

        groups = match_groups_in_text(text)
        is_ai_ml_title = any(t in title for t in AI_ML_TITLES)
        is_engineering_title = any(t in title for t in ENGINEERING_TITLES)
        ai_text_signal = len(groups & {"embeddings", "vector_db", "ranking_retrieval", "nlp_ir", "production_ml"}) >= 2
        if is_ai_ml_title or (is_engineering_title and ai_text_signal) or ai_text_signal:
            ai_ml_months += duration
            if not is_consulting or any(h in industry for h in PRODUCT_INDUSTRY_HINTS):
                product_company_months += duration

        prod_signals = ["deployed", "production", "serving", "online", "a/b", "monitoring", "model registry"]
        if "production_ml" in groups or sum(1 for s in prod_signals if s in text) >= 2:
            production_months += duration
        if groups & {"embeddings", "vector_db", "ranking_retrieval"}:
            retrieval_months += duration

    return {
        "total_months": total_months,
        "ai_ml_months": ai_ml_months,
        "product_company_months": product_company_months,
        "consulting_fraction": consulting_months / max(total_months, 1),
        "ai_ml_fraction": ai_ml_months / max(total_months, 1),
        "disqualifying_fraction": disqualifying_months / max(total_months, 1),
        "management_only_fraction": management_only_months / max(total_months, 1),
        "had_production_ml": production_months >= 12,
        "retrieval_months": retrieval_months,
        "is_consulting_only": consulting_months / max(total_months, 1) > 0.85,
    }


def score_education(education: list[dict]) -> float:
    if not education:
        return 0.45
    tier_scores = {"tier_1": 1.0, "tier_2": 0.8, "tier_3": 0.65, "tier_4": 0.5, "unknown": 0.55}
    fields = {
        "computer science",
        "cs",
        "information technology",
        "it",
        "electronics",
        "electrical",
        "mathematics",
        "statistics",
        "data science",
        "machine learning",
        "artificial intelligence",
        "software engineering",
    }
    best = 0.0
    for edu in education:
        field = edu.get("field_of_study", "").lower()
        degree = edu.get("degree", "").lower()
        score = tier_scores.get(edu.get("tier", "unknown"), 0.55)
        score += 0.1 if any(f in field for f in fields) else 0.0
        score += 0.1 if any(d in degree for d in ["m.tech", "m.s", "ms", "phd", "m.e", "master"]) else 0.0
        best = max(best, min(1.0, score))
    return best


def score_redrob_signals(signals: dict) -> dict:
    today = date(2026, 6, 19)
    try:
        last_active = datetime.strptime(signals.get("last_active_date", "2020-01-01"), "%Y-%m-%d").date()
        days_inactive = max(0, (today - last_active).days)
    except (TypeError, ValueError):
        days_inactive = 999

    if days_inactive <= 30:
        recency_score = 1.0
    elif days_inactive <= 60:
        recency_score = 0.85
    elif days_inactive <= 120:
        recency_score = 0.65
    elif days_inactive <= 180:
        recency_score = 0.45
    else:
        recency_score = 0.20

    response_rate = float(signals.get("recruiter_response_rate", 0.5) or 0)
    notice = int(signals.get("notice_period_days", 60) or 60)
    github = float(signals.get("github_activity_score", -1) or -1)
    interview_completion = float(signals.get("interview_completion_rate", 0.7) or 0.7)

    open_to_work = 1.0 if signals.get("open_to_work_flag", False) else 0.5
    notice_score = 1.0 if notice <= 30 else 0.8 if notice <= 60 else 0.65 if notice <= 90 else 0.5
    response_score = min(1.0, 0.25 + response_rate)
    interview_score = max(0.0, min(1.0, interview_completion))
    offer_rate = float(signals.get("offer_acceptance_rate", -1) or -1)
    if offer_rate == -1:
        offer_score = 0.60
    elif offer_rate >= 0.7:
        offer_score = 1.0
    elif offer_rate >= 0.4:
        offer_score = 0.75
    else:
        offer_score = 0.45
    if github == -1:
        github_score = 0.55
    elif github >= 50:
        github_score = 1.0
    elif github >= 20:
        github_score = 0.75
    elif github >= 5:
        github_score = 0.55
    else:
        github_score = 0.38
    saved = int(signals.get("saved_by_recruiters_30d", 0) or 0)
    market_signal = min(1.0, saved / 50)

    availability = (
        0.30 * recency_score
        + 0.20 * open_to_work
        + 0.18 * response_score
        + 0.12 * notice_score
        + 0.10 * interview_score
        + 0.10 * offer_score
    )
    engagement = (
        0.55 * github_score
        + 0.25 * market_signal
        + 0.20 * min(1.0, float(signals.get("profile_completeness_score", 50) or 50) / 100)
    )
    return {
        "availability": availability,
        "engagement": engagement,
        "recency_score": recency_score,
        "open_to_work": open_to_work,
        "notice_score": notice_score,
        "response_rate": response_rate,
        "github_score": github_score,
        "days_inactive": days_inactive,
        "notice_period_days": notice,
        "offer_score": offer_score,
        "interview_score": interview_score,
        "market_signal": market_signal,
    }


def score_experience_fit(years: float) -> float:
    if 5 <= years <= 9:
        return 1.0
    if 4 <= years < 5:
        return 0.85
    if 9 < years <= 12:
        return 0.80
    if 3 <= years < 4:
        return 0.65
    if years > 12:
        return 0.68
    return 0.38


def extract_all_features(candidate: dict) -> dict:
    profile = candidate.get("profile", {})
    skills = candidate.get("skills", [])
    career = candidate.get("career_history", [])
    education = candidate.get("education", [])
    signals = candidate.get("redrob_signals", {})

    free_text = " ".join(
        [
            profile.get("headline", ""),
            profile.get("summary", ""),
            " ".join(r.get("description", "") for r in career),
            " ".join(r.get("title", "") for r in career),
        ]
    )
    text_groups = match_groups_in_text(free_text)
    skill_groups = extract_candidate_skill_groups(skills, text_groups)
    career_analysis = score_career_for_role(career)

    assessment_scores = signals.get("skill_assessment_scores", {})
    jd_relevant_assessment_keys = [
        "python",
        "machine learning",
        "ml",
        "nlp",
        "data science",
        "deep learning",
        "ai",
        "information retrieval",
        "vector",
        "embedding",
        "sentence transformer",
        "faiss",
        "elasticsearch",
        "recommendation",
        "ranking",
        "search",
    ]
    framework_noise_keys = [
        "haystack",
        "langchain",
        "llamaindex",
        "airflow",
        "hadoop",
        "excel",
        "illustrator",
        "opencv",
        "javascript",
    ]
    ai_assessments = [
        v
        for k, v in assessment_scores.items()
        if any(keyword in k.lower() for keyword in jd_relevant_assessment_keys)
        and not any(noise in k.lower() for noise in framework_noise_keys)
    ]
    avg_assessment = sum(ai_assessments) / len(ai_assessments) if ai_assessments else 50.0
    certifications = candidate.get("certifications", [])
    has_ai_certs = any(
        any(
            k in f"{c.get('name', '')} {c.get('issuer', '')}".lower()
            for k in ["aws", "gcp", "azure", "tensorflow", "pytorch", "databricks", "mlflow", "hugging face", "google ml"]
        )
        for c in certifications
    )

    return {
        "candidate_id": candidate["candidate_id"],
        "years": float(profile.get("years_of_experience", 0) or 0),
        "current_title": profile.get("current_title", ""),
        "headline": profile.get("headline", ""),
        "skill_groups": skill_groups,
        "text_groups": text_groups,
        "career": career_analysis,
        "description_score": score_career_descriptions(career),
        "edu_score": score_education(education),
        "exp_score": score_experience_fit(float(profile.get("years_of_experience", 0) or 0)),
        "platform": score_redrob_signals(signals),
        "has_ai_certs": has_ai_certs,
        "avg_assessment": avg_assessment,
        "notice_days": int(signals.get("notice_period_days", 60) or 60),
        "country": profile.get("country", ""),
        "location": profile.get("location", ""),
        "profile": profile,
        "signals": signals,
    }
