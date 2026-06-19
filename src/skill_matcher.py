"""Skill alias matching."""
import json
from pathlib import Path


def load_skill_groups() -> dict[str, list[str]]:
    path = Path(__file__).parent.parent / "data" / "skill_aliases.json"
    return json.loads(path.read_text(encoding="utf-8"))


SKILL_GROUPS = load_skill_groups()
ALIAS_LOOKUP: dict[str, str] = {}
for group_name, aliases in SKILL_GROUPS.items():
    for alias in aliases:
        ALIAS_LOOKUP[alias.lower()] = group_name


def normalize_skill(skill_name: str) -> set[str]:
    """Map a raw skill or text phrase to canonical JD skill groups."""
    name_lower = skill_name.lower().strip()
    groups_found = set()
    if not name_lower:
        return groups_found
    if name_lower in ALIAS_LOOKUP:
        groups_found.add(ALIAS_LOOKUP[name_lower])
    for alias, group in ALIAS_LOOKUP.items():
        if len(alias) >= 3 and (alias in name_lower or name_lower in alias):
            groups_found.add(group)
    return groups_found


def match_groups_in_text(text: str) -> set[str]:
    """Find canonical skill groups mentioned in free text."""
    text_lower = f" {text.lower()} "
    groups_found = set()
    for alias, group in ALIAS_LOOKUP.items():
        if alias in text_lower:
            groups_found.add(group)
    return groups_found
