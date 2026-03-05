"""
Moteur de classification des vulnérabilités & calcul du score.

- Chaque finding → catégorie OWASP (A01→A10)
- Règles de classification par sévérité (critique / haute / moyenne / basse)
- Algorithme de calcul du score global (/100 et grade A→F)
"""

from typing import Literal

# Sévérité normalisée (stockée en base après classification)
SeverityLevel = Literal["critical", "high", "medium", "low"]

# Mapping sortie outil → sévérité normalisée (insensible à la casse)
SEVERITY_ALIASES: dict[str, SeverityLevel] = {
    "critical": "critical",
    "critique": "critical",
    "error": "high",
    "high": "high",
    "haute": "high",
    "warning": "medium",
    "medium": "medium",
    "moyenne": "medium",
    "info": "low",
    "low": "low",
    "basse": "low",
    "note": "low",
}


def normalize_severity(raw: str) -> SeverityLevel:
    """
    Normalise la sévérité brute (outil) en une des 4 valeurs.
    Si non reconnu, défaut = medium.
    """
    key = (raw or "").strip().lower()
    return SEVERITY_ALIASES.get(key, "medium")


def map_severity_to_owasp_default(severity: SeverityLevel) -> str:
    """
    Mapping par défaut : sévérité → catégorie OWASP quand aucune règle spécifique.
    Permet de garantir qu'un finding a toujours une catégorie (A05 Injection par défaut
    pour les plus graves, A02 pour les plus faibles).
    """
    mapping: dict[SeverityLevel, str] = {
        "critical": "A05",  # Injection / critique
        "high": "A05",
        "medium": "A02",  # Misconfiguration
        "low": "A09",  # Logging
    }
    return mapping.get(severity, "A06")  # A06 Insecure Design par défaut


def map_rule_to_owasp(rule_id: str | None, tool_name: str | None) -> str | None:
    """
    Mapping règle / outil → catégorie OWASP (A01–A10).
    À étendre selon les règles Semgrep, ESLint, etc.
    """
    if not rule_id and not tool_name:
        return None
    rule = (rule_id or "").lower()
    tool = (tool_name or "").lower()
    # Exemples : règles d'injection → A05, dépendances → A03, secrets → A04
    if "sql" in rule or "injection" in rule or "xss" in rule:
        return "A05"
    if "secret" in rule or "password" in rule or "key" in rule or "trufflehog" in tool:
        return "A04"
    if "dependency" in rule or "audit" in tool or "cve" in rule:
        return "A03"
    if "access" in rule or "idor" in rule or "cors" in rule:
        return "A01"
    if "auth" in rule or "session" in rule or "login" in rule:
        return "A07"
    if "config" in rule or "header" in rule or "debug" in rule:
        return "A02"
    if "deserial" in rule or "integrity" in rule:
        return "A08"
    if "log" in rule or "alert" in rule:
        return "A09"
    if "exception" in rule or "error" in rule or "stack" in rule:
        return "A10"
    return None


def compute_score(
    critical: int,
    high: int,
    medium: int,
    low: int,
) -> tuple[float, str]:
    """
    Calcule le score de sécurité global à partir des comptages par sévérité.

    Formule : score sur 100 (pénalités par vulnérabilité).
    Puis conversion en grade A→F.

    Cas particulier : 0 vulnérabilité (critical=high=medium=low=0)
    → score = 100, grade = A (projet sans faille).

    Returns:
        (score_100, grade) avec grade in ("A", "B", "C", "D", "F")
    """
    # Pénalités par sévérité (arbitraires, à ajuster). 0 vuln → pénalité 0 → 100/ A
    penalty = critical * 25 + high * 10 + medium * 3 + low * 1
    # Score = max(0, 100 - pénalité), plafonné
    raw = 100.0 - penalty
    score_100 = max(0.0, min(100.0, raw))

    # Grade A→F
    if score_100 >= 90:
        grade = "A"
    elif score_100 >= 75:
        grade = "B"
    elif score_100 >= 50:
        grade = "C"
    elif score_100 >= 25:
        grade = "D"
    else:
        grade = "F"

    return round(score_100, 2), grade
