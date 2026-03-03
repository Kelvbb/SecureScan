"""
Endpoints de remédiation — SecureScan.

GET  /scans/{scan_id}/fixes        → liste les corrections proposées (générées ou chargées depuis la BDD)
POST /scans/{scan_id}/fixes/apply  → applique les corrections validées par l'utilisateur + push Git
"""

from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

try:
    from app.api.deps import get_db        # deps.py ré-exporte get_db
except ImportError:
    from app.db.session import get_db      # fallback : import direct

from app.models.scan import Scan
from app.remediation.service import ApplyResult, FixProposalDTO, RemediationService
from app.git.service import GitService, GitServiceError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scans", tags=["Remediation"])


# ---------------------------------------------------------------------------
# Schémas
# ---------------------------------------------------------------------------

class FixProposalOut(BaseModel):
    suggested_fix_id: uuid.UUID
    vuln_id:          uuid.UUID
    file_path:        str
    line_number:      int
    original_line:    str
    fixed_line:       str
    patch_diff:       str
    description:      str
    owasp_category:   str
    fix_type:         str
    auto_applicable:  bool

    model_config = {"from_attributes": True}


class FixesListOut(BaseModel):
    scan_id:   uuid.UUID
    proposals: list[FixProposalOut]
    total:     int


class ApplyFixesIn(BaseModel):
    """IDs des SuggestedFix que l'utilisateur a explicitement validés dans l'interface."""
    fix_ids: list[uuid.UUID] = Field(..., min_length=1)


class ApplyFixesOut(BaseModel):
    scan_id:         uuid.UUID
    applied_fix_ids: list[uuid.UUID]
    skipped_fix_ids: list[uuid.UUID]
    errors:          dict[str, str]   # str(fix_id) → message d'erreur
    git_branch:      str | None = None
    git_commit:      str | None = None
    git_pushed:      bool       = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_scan_or_404(scan_id: uuid.UUID, db: Session) -> Scan:
    scan = db.get(Scan, scan_id)
    if scan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Scan {scan_id} introuvable.")
    return scan


def _build_service(scan: Scan, db: Session) -> RemediationService:
    try:
        return RemediationService(project_root=Path(scan.project.clone_path), db_session=db)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# GET /scans/{scan_id}/fixes
# ---------------------------------------------------------------------------

@router.get(
    "/{scan_id}/fixes",
    response_model=FixesListOut,
    summary="Propositions de correction pour un scan",
)
def list_fix_proposals(
    scan_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
) -> FixesListOut:
    """
    Retourne les corrections proposées pour toutes les vulnérabilités supportées.

    Premier appel : génère les SuggestedFix et les persiste en BDD.
    Appels suivants : charge les enregistrements existants (idempotent).

    Le frontend utilise le `suggested_fix_id` de chaque proposition pour
    indiquer quelles corrections l'utilisateur valide ou rejette.
    """
    scan    = _get_scan_or_404(scan_id, db)
    service = _build_service(scan, db)

    try:
        proposals: list[FixProposalDTO] = service.get_or_create_fix_proposals(scan_id)
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.exception("Erreur génération proposals — scan %s", scan_id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Erreur lors de la génération des corrections : {exc}") from exc

    return FixesListOut(
        scan_id   = scan_id,
        proposals = [FixProposalOut(**p.__dict__) for p in proposals],
        total     = len(proposals),
    )


# ---------------------------------------------------------------------------
# POST /scans/{scan_id}/fixes/apply
# ---------------------------------------------------------------------------

@router.post(
    "/{scan_id}/fixes/apply",
    response_model=ApplyFixesOut,
    summary="Applique les corrections validées et pousse la branche Git",
)
def apply_fixes(
    scan_id: uuid.UUID,
    body:    ApplyFixesIn,
    db:      Annotated[Session, Depends(get_db)],
) -> ApplyFixesOut:
    """
    1. Modifie les fichiers sources sur disque à la ligne exacte indiquée en BDD.
    2. Crée une branche fix/securescan-<date>, commit et push.

    Si aucune correction ne peut être appliquée, la réponse est retournée
    sans tenter le push Git. En cas d'échec Git, les corrections disque
    restent valides — git_pushed indique le statut réel.
    """
    scan    = _get_scan_or_404(scan_id, db)
    service = _build_service(scan, db)

    try:
        apply_result: ApplyResult = service.apply_fixes(validated_fix_ids=body.fix_ids)
    except Exception as exc:
        logger.exception("apply_fixes a échoué — scan %s", scan_id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Erreur lors de l'application des corrections : {exc}") from exc

    if not apply_result.applied:
        return ApplyFixesOut(
            scan_id         = scan_id,
            applied_fix_ids = [],
            skipped_fix_ids = apply_result.skipped,
            errors          = apply_result.errors,
        )

    git_branch: str | None = None
    git_commit: str | None = None
    git_pushed: bool       = False

    try:
        git_svc    = GitService(repo_path=Path(scan.project.clone_path))
        git_branch = git_svc.create_fix_branch()
        git_commit = git_svc.commit_fixes(
            message=(
                f"fix(securescan): {len(apply_result.applied)} correction(s) "
                f"automatique(s) [scan {scan_id}]"
            )
        )
        git_svc.push_branch(git_branch)
        git_pushed = True
        logger.info("Push réussi — scan=%s branche=%s commit=%s", scan_id, git_branch, git_commit)
    except GitServiceError as exc:
        # Les fichiers sont corrigés sur disque, seul le push a échoué.
        # On remonte l'info sans bloquer la réponse.
        logger.error("GitService échoué — scan %s : %s", scan_id, exc)

    return ApplyFixesOut(
        scan_id         = scan_id,
        applied_fix_ids = apply_result.applied,
        skipped_fix_ids = apply_result.skipped,
        errors          = apply_result.errors,
        git_branch      = git_branch,
        git_commit      = git_commit,
        git_pushed      = git_pushed,
    )
