"""
Simulates the real-world messiness that makes entity resolution non-trivial:
the same person recorded slightly differently across FIRs filed at different
stations/years by different constables typing on different days.

This is intentionally injected so the entity-resolution module has a genuine
problem to solve, and so its precision/recall can be measured against a known
ground truth (see transactional_data.py -> entity_resolution_ground_truth.csv).
"""

import random

MUSLIM_FIRST_NAME_VARIANTS = {
    "Mohammed": ["Mohammed", "Mohd", "Md", "Muhammad", "Mohamed"],
    "Mohammed Ali": ["Mohammed Ali", "Mohd Ali", "Md. Ali"],
}

_SUBSTITUTIONS = [
    ("v", "w"), ("sh", "s"), ("ai", "ay"), ("ee", "i"), ("oo", "u"),
    ("th", "t"), ("kh", "k"), ("ph", "f"),
]


def _apply_random_substitution(name: str) -> str:
    name_l = name.lower()
    candidates = [(a, b) for a, b in _SUBSTITUTIONS if a in name_l]
    if not candidates:
        return name
    a, b = random.choice(candidates)
    idx = name_l.find(a)
    return name[:idx] + b + name[idx + len(a):]


def generate_name_variant(canonical_name: str) -> str:
    """Return a plausible mis-recorded variant of a canonical full name."""
    parts = canonical_name.split()
    strategy = random.choice([
        "abbreviate_first", "drop_middle", "substitution", "initials_surname", "as_is",
    ])

    if strategy == "abbreviate_first" and len(parts) >= 1:
        parts[0] = parts[0][0] + "."
        return " ".join(parts)

    if strategy == "drop_middle" and len(parts) >= 3:
        return f"{parts[0]} {parts[-1]}"

    if strategy == "substitution":
        return " ".join(_apply_random_substitution(p) for p in parts)

    if strategy == "initials_surname" and len(parts) >= 2:
        initials = "".join(p[0] for p in parts[:-1])
        return f"{initials} {parts[-1]}"

    return canonical_name


def maybe_age_drift(true_age_at_year: int) -> int:
    """Real DOB records sometimes get mis-entered; +/-1-2 year drift is common."""
    if random.random() < 0.25:
        return true_age_at_year + random.choice([-2, -1, 1, 2])
    return true_age_at_year
