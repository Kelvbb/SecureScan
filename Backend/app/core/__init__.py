"""Module core : classification, score, règles métier."""

from app.core.classification import (
    compute_score,
    normalize_severity,
    map_severity_to_owasp_default,
)

__all__ = [
    "normalize_severity",
    "map_severity_to_owasp_default",
    "compute_score",
]
