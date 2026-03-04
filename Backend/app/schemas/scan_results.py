"""Schémas pour les résultats de scan (results, score, owasp-summary)."""

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class VulnerabilityResultItem(BaseModel):
    """Un finding dans GET /scans/{id}/results avec catégorie OWASP + sévérité."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    scan_id: UUID
    title: str
    description: str | None
    file_path: str | None
    line_start: int | None
    line_end: int | None
    severity: str
    confidence: str | None
    cve_id: str | None
    cwe_id: str | None
    owasp_category_id: str | None
    owasp_category_name: str | None
    status: str
    created_at: datetime


class ScanResultsResponse(BaseModel):
    """Réponse GET /scans/{scan_id}/results."""

    scan_id: UUID
    total: int
    items: list[VulnerabilityResultItem]


class ScanScoreResponse(BaseModel):
    """Réponse GET /scans/{scan_id}/score."""

    scan_id: UUID
    score: float
    grade: str
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    total_vulnerabilities: int


class OwaspSummaryItem(BaseModel):
    """Une catégorie OWASP avec son effectif pour le scan."""

    owasp_category_id: str
    owasp_category_name: str
    count: int


class ScanOwaspSummaryResponse(BaseModel):
    """Réponse GET /scans/{scan_id}/owasp-summary."""

    scan_id: UUID
    items: list[OwaspSummaryItem]
