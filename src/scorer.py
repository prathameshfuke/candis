"""JD-specific scoring engine."""

JD_SKILL_WEIGHTS = {
    "embeddings": 1.00,
    "vector_db": 0.95,
    "ranking_retrieval": 0.95,
    "python_strong": 0.85,
    "nlp_ir": 0.80,
    "production_ml": 0.80,
    "llm_finetuning": 0.45,
}
MAX_SKILL_SCORE = sum(JD_SKILL_WEIGHTS.values())


def compute_skill_score(skill_groups: dict[str, float]) -> float:
    raw = sum(JD_SKILL_WEIGHTS[group] * skill_groups.get(group, 0.0) for group in JD_SKILL_WEIGHTS)
    return min(1.0, raw / MAX_SKILL_SCORE)


def compute_must_have_bonus(skill_groups: dict[str, float], career: dict) -> float:
    must_groups = ["embeddings", "vector_db", "ranking_retrieval", "python_strong", "production_ml"]
    strong = sum(1 for g in must_groups if skill_groups.get(g, 0.0) >= 0.55)
    weak = sum(1 for g in must_groups if 0.25 <= skill_groups.get(g, 0.0) < 0.55)
    bonus = 0.018 * strong + 0.006 * weak
    if career["retrieval_months"] >= 24:
        bonus += 0.025
    return min(0.12, bonus)


def compute_career_multiplier(career: dict, current_title: str, notice_days: int = 60) -> float:
    title_lower = current_title.lower()
    hard_disqualifiers = {
        "marketing manager",
        "operations manager",
        "hr manager",
        "human resources",
        "sales executive",
        "content writer",
        "accountant",
        "graphic designer",
        "civil engineer",
        "mechanical engineer",
        "customer support",
        "supply chain",
    }
    if any(d in title_lower for d in hard_disqualifiers):
        multiplier = 0.14 if career["ai_ml_fraction"] < 0.2 else 0.45
        return multiplier

    base = 0.55 if career["is_consulting_only"] else 1.0
    ai_ml_bonus = min(0.28, career["ai_ml_fraction"] * 0.28)
    prod_bonus = 0.14 if career["had_production_ml"] else 0.0
    product_fraction = career["product_company_months"] / max(career["total_months"], 1)
    product_bonus = min(0.10, product_fraction * 0.10)
    retrieval_bonus = 0.08 if career["retrieval_months"] >= 24 else 0.03 if career["retrieval_months"] >= 12 else 0.0
    penalty = career["disqualifying_fraction"] * 0.45 + career["management_only_fraction"] * 0.20
    if notice_days <= 30:
        notice_modifier = 1.05
    elif notice_days <= 60:
        notice_modifier = 1.00
    elif notice_days <= 90:
        notice_modifier = 0.92
    else:
        notice_modifier = 0.82
    career_fit = min(1.2, base + ai_ml_bonus + prod_bonus + product_bonus + retrieval_bonus - penalty)
    multiplier = career_fit * notice_modifier
    return max(0.10, min(1.2, multiplier))


def compute_availability_multiplier(platform: dict) -> float:
    combined = 0.70 * platform["availability"] + 0.30 * platform["engagement"]
    return max(0.30, min(1.10, 0.3 + combined * 0.8))


def score_candidate(features: dict) -> dict:
    skill_score = compute_skill_score(features["skill_groups"])
    career_mult = compute_career_multiplier(features["career"], features["current_title"], features["notice_days"])
    availability_mult = compute_availability_multiplier(features["platform"])

    base = skill_score
    base += compute_must_have_bonus(features["skill_groups"], features["career"])
    base += (features["exp_score"] - 0.5) * 0.14
    base += (features["edu_score"] - 0.5) * 0.04
    base += (features["avg_assessment"] - 50) / 1200
    base += 0.025 if features["has_ai_certs"] else 0.0
    base += features["description_score"] * 0.15
    final = max(0.0, base * career_mult * availability_mult)
    return {
        "candidate_id": features["candidate_id"],
        "score": final,
        "skill_score": skill_score,
        "career_multiplier": career_mult,
        "availability_multiplier": availability_mult,
        "features": features,
    }


def generate_reasoning(scored: dict) -> str:
    f = scored["features"]
    career = f["career"]
    platform = f["platform"]
    profile = f["profile"]

    title = profile.get("current_title", "")
    company = profile.get("current_company", "")
    years = f["years"]
    notice = f["notice_days"]
    response = platform["response_rate"]
    github = platform.get("github_activity_raw", -1)
    last_active_days = platform["days_inactive"]
    desc_score = f.get("description_score", 0.0)

    skill_label = {
        "embeddings": "embedding retrieval",
        "vector_db": "vector DB",
        "ranking_retrieval": "ranking/IR systems",
        "python_strong": "Python",
        "nlp_ir": "NLP/IR",
        "production_ml": "production ML",
        "llm_finetuning": "LLM fine-tuning",
    }
    top_skills = sorted(f["skill_groups"].items(), key=lambda x: x[1], reverse=True)[:2]
    top_skill_str = " and ".join(
        skill_label.get(group, group) for group, score in top_skills if score > 0.3
    )
    if not top_skill_str:
        top_skill_str = "limited direct AI/IR skill evidence"

    prod_signal = "shipped production retrieval systems" if desc_score > 0.5 else "applied ML background"
    s1 = f"{title} at {company} with {years:.1f} yrs experience; {top_skill_str}; {prod_signal}."

    concerns = []
    positives = []

    if notice > 90:
        concerns.append(f"notice period {notice}d (JD prefers sub-30)")
    elif notice <= 30:
        positives.append(f"available in {notice}d")

    if last_active_days > 90:
        concerns.append(f"inactive {last_active_days}d")

    if response < 0.25:
        concerns.append(f"low recruiter response rate ({response:.0%})")
    elif response > 0.80:
        positives.append(f"high response rate ({response:.0%})")

    if github > 50:
        positives.append(f"strong GitHub activity ({github:.0f})")
    elif github == -1:
        concerns.append("no GitHub linked")

    if career["is_consulting_only"]:
        concerns.append("entire career in IT services")

    if career["disqualifying_fraction"] > 0.45:
        concerns.append("mostly non-ML roles")

    if concerns:
        s2 = "Concern: " + "; ".join(concerns[:2]) + "."
    elif positives:
        s2 = "Strong availability signals: " + "; ".join(positives[:2]) + "."
    else:
        s2 = "No major concerns; reasonable fit across skill and behavioral signals."

    return f"{s1} {s2}"
