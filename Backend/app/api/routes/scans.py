"""Routes scans — squelette + résultats, score, résumé OWASP."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_db
from app.core.classification import compute_score, normalize_severity
from app.models.scan import Scan
from app.models.scan_metrics import ScanMetrics
from app.models.vulnerability import Vulnerability
from app.models.owasp_category import OwaspCategory
from app.schemas.scan import ScanCreate, ScanResponse, ScanList
from app.schemas.scan_results import (
    ScanResultsResponse,
    VulnerabilityResultItem,
    ScanScoreResponse,
    ScanOwaspSummaryResponse,
    OwaspSummaryItem,
)

router = APIRouter()


def _get_scan_or_404(db: Session, scan_id: UUID) -> Scan:
    scan = db.get(Scan, scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    return scan


# --- Endpoints résultats / score / owasp-summary (avant /{scan_id}) ---


@router.get("/{scan_id}/results", response_model=ScanResultsResponse)
def get_scan_results(scan_id: UUID, db: Session = Depends(get_db)) -> ScanResultsResponse:
    """Liste des vulnérabilités du scan avec catégorie OWASP et sévérité."""
    _get_scan_or_404(db, scan_id)
    stmt = (
        select(Vulnerability)
        .where(Vulnerability.scan_id == scan_id)
        .options(joinedload(Vulnerability.owasp_category))
        .order_by(Vulnerability.created_at)
    )
    vulns = list(db.execute(stmt).unique().scalars().all())
    items = [
        VulnerabilityResultItem(
            id=v.id,
            scan_id=v.scan_id,
            title=v.title,
            description=v.description,
            file_path=v.file_path,
            line_start=v.line_start,
            line_end=v.line_end,
            severity=v.severity,
            confidence=v.confidence,
            cve_id=v.cve_id,
            cwe_id=v.cwe_id,
            owasp_category_id=v.owasp_category_id,
            owasp_category_name=v.owasp_category.name if v.owasp_category else None,
            status=v.status,
            created_at=v.created_at,
        )
        for v in vulns
    ]
    return ScanResultsResponse(scan_id=scan_id, total=len(items), items=items)


@router.get("/{scan_id}/score", response_model=ScanScoreResponse)
def get_scan_score(scan_id: UUID, db: Session = Depends(get_db)) -> ScanScoreResponse:
    """Score global du scan (/100 et grade A→F). 0 vulnérabilité → score 100, grade A."""
    _get_scan_or_404(db, scan_id)
    vulns = list(
        db.execute(
            select(Vulnerability).where(Vulnerability.scan_id == scan_id)
        ).scalars().all()
    )
    critical = high = medium = low = 0
    for v in vulns:
        level = normalize_severity(v.severity)
        if level == "critical":
            critical += 1
        elif level == "high":
            high += 1
        elif level == "medium":
            medium += 1
        else:
            low += 1
    total = len(vulns)
    score_100, grade = compute_score(critical, high, medium, low)
    metrics = db.get(ScanMetrics, scan_id)
    if metrics is None:
        metrics = ScanMetrics(
            scan_id=scan_id,
            total_vulnerabilities=total,
            critical_count=critical,
            high_count=high,
            medium_count=medium,
            low_count=low,
            score_global=score_100,
        )
        db.add(metrics)
    else:
        metrics.total_vulnerabilities = total
        metrics.critical_count = critical
        metrics.high_count = high
        metrics.medium_count = medium
        metrics.low_count = low
        metrics.score_global = score_100
    db.commit()
    return ScanScoreResponse(
        scan_id=scan_id,
        score=score_100,
        grade=grade,
        critical_count=critical,
        high_count=high,
        medium_count=medium,
        low_count=low,
        total_vulnerabilities=total,
    )


@router.get("/{scan_id}/owasp-summary", response_model=ScanOwaspSummaryResponse)
def get_scan_owasp_summary(
    scan_id: UUID, db: Session = Depends(get_db)
) -> ScanOwaspSummaryResponse:
    """Répartition des vulnérabilités par catégorie OWASP (A01–A10)."""
    _get_scan_or_404(db, scan_id)
    stmt = (
        select(
            Vulnerability.owasp_category_id,
            func.count(Vulnerability.id).label("count"),
        )
        .where(Vulnerability.scan_id == scan_id)
        .group_by(Vulnerability.owasp_category_id)
    )
    rows = db.execute(stmt).all()
    cat_ids = [r[0] for r in rows if r[0]]
    categories = {}
    if cat_ids:
        cats = db.execute(
            select(OwaspCategory).where(OwaspCategory.id.in_(cat_ids))
        ).scalars().all()
        categories = {c.id: c.name for c in cats}
    items = [
        OwaspSummaryItem(
            owasp_category_id=owasp_id or "unknown",
            owasp_category_name=categories.get(owasp_id, "Non classé"),
            count=count,
        )
        for owasp_id, count in rows
    ]
    items.sort(key=lambda x: (x.owasp_category_id == "unknown", x.owasp_category_id))
    return ScanOwaspSummaryResponse(scan_id=scan_id, items=items)


# --- Endpoints existants ---


@router.post("", status_code=201)
def create_scan(payload: ScanCreate, db: Session = Depends(get_db)):
    pass


@router.get("/{scan_id}")
def get_scan(scan_id: UUID, db: Session = Depends(get_db)):
    pass


@router.get("")
def list_scans(user_id: UUID | None = None, db: Session = Depends(get_db)):
    pass
