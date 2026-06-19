"""Detect impossible or fraudulent-looking candidate profiles."""
from datetime import date, datetime


def detect_honeypot(candidate: dict) -> tuple[bool, list[str]]:
    """Return whether the candidate should be treated as a honeypot."""
    reasons = []
    profile = candidate.get("profile", {})
    skills = candidate.get("skills", [])
    career = candidate.get("career_history", [])

    expert_zero_duration = [
        s.get("name", "")
        for s in skills
        if s.get("proficiency") == "expert"
        and s.get("duration_months", 1) == 0
        and s.get("endorsements", 0) == 0
    ]
    severe_expert_zero = len(expert_zero_duration) >= 3
    if severe_expert_zero:
        reasons.append(f"{len(expert_zero_duration)} expert skills with 0 months and 0 endorsements")

    expert_skills = [s for s in skills if s.get("proficiency") == "expert"]
    if len(expert_skills) > 12:
        reasons.append(f"claims expert proficiency in {len(expert_skills)} skills")

    total_career_months = sum(r.get("duration_months", 0) for r in career)
    claimed_years = float(profile.get("years_of_experience", 0) or 0)
    if total_career_months > 0:
        actual_years = total_career_months / 12
        severe_claimed_mismatch = claimed_years > actual_years + 4
        severe_actual_mismatch = actual_years > claimed_years + 5
        if severe_claimed_mismatch:
            reasons.append(f"claims {claimed_years:.1f} yrs but history shows {actual_years:.1f} yrs")
        if severe_actual_mismatch:
            reasons.append(f"career durations sum to {actual_years:.1f} yrs vs claimed {claimed_years:.1f} yrs")
    else:
        severe_claimed_mismatch = False
        severe_actual_mismatch = False

    parsed_ranges = []
    for role in career:
        try:
            start = datetime.strptime(role["start_date"], "%Y-%m-%d").date()
            end_str = role.get("end_date")
            end = datetime.strptime(end_str, "%Y-%m-%d").date() if end_str else date(2026, 6, 19)
            parsed_ranges.append((start, end, role.get("company", "")))
        except (KeyError, TypeError, ValueError):
            continue

    total_overlap_months = 0.0
    for i in range(len(parsed_ranges)):
        for j in range(i + 1, len(parsed_ranges)):
            s1, e1, c1 = parsed_ranges[i]
            s2, e2, c2 = parsed_ranges[j]
            if c1 and c1 == c2:
                continue
            overlap_start = max(s1, s2)
            overlap_end = min(e1, e2)
            if overlap_start < overlap_end:
                total_overlap_months += (overlap_end - overlap_start).days / 30
    if total_overlap_months > 18:
        reasons.append(f"{total_overlap_months:.0f} months of overlapping roles")

    severe_single_signal = severe_expert_zero or severe_claimed_mismatch or severe_actual_mismatch
    return len(reasons) >= 2 or severe_single_signal, reasons
