"""
Endpoints de remédiation

GET  /scans/{scan_id}/fixes        → liste les corrections proposées
POST /scans/{scan_id}/fixes/apply  → applique les corrections validées + push Git

Contraintes métier :
  - Aucune modification n'est poussée sans au moins un fix_id validé (min_length=1).
  - Chaque fix expose son owasp_category (ex : "A05 – Injection").
  - Le message de commit est normalisé : "SECURESCAN: Automated security fixes applied".
  - Les credentials Git (token, auteur) proviennent exclusivement de config.py / .env.
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
    from app.api.deps import get_db
except ImportError:
    from app.db.session import get_db

from app.config import settings
from app.models.scan import Scan
from app.remediation.service import ApplyResult, FixProposalDTO, RemediationService
from app.git.service import GitService, GitServiceError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scans", tags=["Remediation"])

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

# Message de commit normalisé — ne pas modifier sans aligner les tests.
GIT_COMMIT_MESSAGE = "SECURESCAN: Automated security fixes applied"


# ---------------------------------------------------------------------------
# Schémas
# ---------------------------------------------------------------------------


class FixProposalOut(BaseModel):
    suggested_fix_id: uuid.UUID
    vuln_id: uuid.UUID
    file_path: str
    line_number: int
    original_line: str
    fixed_line: str
    patch_diff: str
    description: str
    owasp_category: str  # ex : "A05 – Injection"
    fix_type: str  # ex : "sql_injection"
    auto_applicable: bool

    model_config = {"from_attributes": True}


class FixesListOut(BaseModel):
    scan_id: uuid.UUID
    proposals: list[FixProposalOut]
    total: int


class ApplyFixesIn(BaseModel):
    """
    IDs des SuggestedFix que l'utilisateur a explicitement validés dans l'interface.

    Contrainte : au moins un ID requis — aucune correction ne peut être poussée
    sans validation explicite de l'utilisateur (min_length=1).
    """

    fix_ids: list[uuid.UUID] = Field(..., min_length=1)


class ApplyFixesOut(BaseModel):
    scan_id: uuid.UUID
    applied_fix_ids: list[uuid.UUID]
    skipped_fix_ids: list[uuid.UUID]
    errors: dict[str, str]  # str(fix_id) → message d'erreur
    git_branch: str | None = None
    git_commit: str | None = None
    git_pushed: bool = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_scan_or_404(scan_id: uuid.UUID, db: Session) -> Scan:
    scan = db.get(Scan, scan_id)
    if scan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scan {scan_id} introuvable.",
        )
    return scan


def _build_service(scan: Scan, db: Session) -> RemediationService:
    try:
        return RemediationService(
            project_root=Path(scan.project.clone_path),
            db_session=db,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


def _build_git_service(clone_path: str) -> GitService:
    """
    Instancie GitService avec les credentials issus de config.py / .env.

    Les valeurs GIT_TOKEN, GIT_AUTHOR_NAME, GIT_AUTHOR_EMAIL et GIT_TIMEOUT
    doivent être définies dans le fichier .env (jamais committées en dur).
    """
    return GitService(
        repo_path=Path(clone_path),
        author_name=settings.GIT_AUTHOR_NAME,
        author_email=settings.GIT_AUTHOR_EMAIL,
        timeout=settings.GIT_TIMEOUT,
        token=settings.GIT_TOKEN,  # injecté dans l'URL remote si non vide
    )


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

    Premier appel  → génère les SuggestedFix et les persiste en BDD.
    Appels suivants → charge les enregistrements existants (idempotent).

    Chaque proposition expose son `owasp_category` (ex : "A05 – Injection") et
    son `fix_type` (ex : "sql_injection") pour permettre le mapping côté frontend.
    Le `suggested_fix_id` est utilisé par le POST /apply pour valider les corrections.
    """
    scan = _get_scan_or_404(scan_id, db)
    service = _build_service(scan, db)

    try:
        proposals: list[FixProposalDTO] = service.get_or_create_fix_proposals(scan_id)
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.exception("Erreur génération proposals — scan %s", scan_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la génération des corrections : {exc}",
        ) from exc

    return FixesListOut(
        scan_id=scan_id,
        proposals=[FixProposalOut(**p.__dict__) for p in proposals],
        total=len(proposals),
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
    body: ApplyFixesIn,
    db: Annotated[Session, Depends(get_db)],
) -> ApplyFixesOut:
    """
    Workflow complet en deux étapes :

    **1. Application disque**
    Modifie les fichiers sources à la ligne exacte indiquée en BDD,
    uniquement pour les `fix_ids` présents dans le payload (validation explicite).
    Aucune modification n'est effectuée si la liste est vide — la contrainte
    `min_length=1` sur `ApplyFixesIn.fix_ids` garantit au moins un ID validé.

    **2. Push Git**
    - Crée une branche `fix/securescan-<YYYY-MM-DD>` (suffixe numérique si collision).
    - Commit avec le message normalisé `"SECURESCAN: Automated security fixes applied"`.
    - Push via `--force-with-lease` sur le remote configuré.

    Si aucun fix ne peut être appliqué, la réponse est retournée immédiatement
    sans tentative Git. En cas d'échec Git isolé, les fichiers corrigés sur disque
    restent valides — `git_pushed` indique le statut réel du push.
    """
    scan = _get_scan_or_404(scan_id, db)
    service = _build_service(scan, db)

    # --- 1. Application des corrections sur disque ---
    try:
        apply_result: ApplyResult = service.apply_fixes(validated_fix_ids=body.fix_ids)
    except Exception as exc:
        logger.exception("apply_fixes a échoué — scan %s", scan_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de l'application des corrections : {exc}",
        ) from exc

    # Rien à pousser si toutes les corrections ont été ignorées
    if not apply_result.applied:
        return ApplyFixesOut(
            scan_id=scan_id,
            applied_fix_ids=[],
            skipped_fix_ids=apply_result.skipped,
            errors=apply_result.errors,
        )

    # --- 2. Intégration Git ---
    git_branch: str | None = None
    git_commit: str | None = None
    git_pushed: bool = False

    try:
        git_svc = _build_git_service(scan.project.clone_path)
        git_branch = git_svc.create_fix_branch()
        git_commit = git_svc.commit_fixes(message=GIT_COMMIT_MESSAGE)
        git_svc.push_branch(git_branch)
        git_pushed = True
        logger.info(
            "Push réussi — scan=%s branche=%s commit=%s",
            scan_id,
            git_branch,
            git_commit,
        )
    except GitServiceError as exc:
        # Les fichiers sont corrigés sur disque, seul le push a échoué.
        # On remonte l'info sans bloquer la réponse HTTP.
        logger.error("GitService échoué — scan %s : %s", scan_id, exc)

    return ApplyFixesOut(
        scan_id=scan_id,
        applied_fix_ids=apply_result.applied,
        skipped_fix_ids=apply_result.skipped,
        errors=apply_result.errors,
        git_branch=git_branch,
        git_commit=git_commit,
        git_pushed=git_pushed,
    )
