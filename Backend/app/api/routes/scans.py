"""Routes scans — créer, récupérer, lister, lancer analyse."""

import asyncio
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.core.classification import compute_score, normalize_severity
from app.models.scan import Scan
from app.models.user import User
from app.models.scan_metrics import ScanMetrics
from app.models.vulnerability import Vulnerability
from app.models.owasp_category import OwaspCategory
from app.schemas.scan import ScanCreate, ScanResponse, ScanList
from app.services.scan_orchestrator import ScanOrchestrator

router = APIRouter()


def _run_scan_background(scan_id: UUID, project_path: str, db: Session):
    """Fonction wrapper pour exécuter le scan en background."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(
            ScanOrchestrator(db).run_scan(scan_id, project_path)
        )
    finally:
        loop.close()


@router.post("", response_model=ScanResponse, status_code=status.HTTP_201_CREATED)
def create_scan(payload: ScanCreate, db: Session = Depends(get_db)) -> ScanResponse:
    """Crée un nouveau scan."""
    scan = Scan(
        user_id=payload.user_id,
        repository_url=payload.repository_url,
        upload_path=payload.upload_path,
        status="pending",
    )
    db.add(scan)
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


# --- Mes scans (utilisateur connecté) ---


@router.get("/me", response_model=list[ScanList])
def list_my_scans(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ScanList]:
    """Liste des scans de l'utilisateur connecté."""
    from sqlalchemy import select
    stmt = (
        select(Scan)
        .where(Scan.user_id == current_user.id)
        .order_by(Scan.created_at.desc())
    )
    scans = list(db.execute(stmt).scalars().all())
    return [ScanList.model_validate(s) for s in scans]


# --- Endpoints existants ---


@router.get("/{scan_id}", response_model=ScanResponse)
def get_scan(scan_id: UUID, db: Session = Depends(get_db)) -> ScanResponse:
    """Récupère les détails d'un scan."""
    scan = db.get(Scan, scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    return ScanResponse.model_validate(scan)


@router.get("", response_model=list[ScanList])
def list_scans(
    user_id: UUID | None = None,
    db: Session = Depends(get_db),
) -> list[ScanList]:
    """Liste les scans d'un utilisateur."""
    q = db.query(Scan)
    if user_id is not None:
        q = q.filter(Scan.user_id == user_id)
    scans = q.order_by(Scan.created_at.desc()).all()
    return [ScanList.model_validate(s) for s in scans]


@router.post("/{scan_id}/run", response_model=dict, status_code=status.HTTP_202_ACCEPTED)
def run_scan(
    scan_id: UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> dict:
    """
    Lance l'analyse de sécurité complète pour un scan.
    
    Exécute tous les outils (Semgrep, pip-audit, npm-audit, TruffleHog) en parallèle.
    Retourne immédiatement avec le statut "running", l'analyse continue en background.
    """
    scan = db.get(Scan, scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    if scan.status == "running":
        raise HTTPException(
            status_code=400,
            detail="Scan is already running",
        )

    # Déterminer le chemin du projet
    if scan.upload_path:
        project_path = scan.upload_path
    elif scan.repository_url:
        project_path = f"{settings.PROJECT_ROOT}/{scan_id}"
    else:
        raise HTTPException(
            status_code=400,
            detail="No repository URL or upload path provided",
        )

    # Lancer l'orchestrateur en background
    background_tasks.add_task(
        _run_scan_background,
        scan_id,
        project_path,
        db,
    )

    return {
        "scan_id": str(scan_id),
        "status": "running",
        "message": "Analysis started in background",
    }
