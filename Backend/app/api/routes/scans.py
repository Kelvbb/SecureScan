"""Routes scans — créer, récupérer, lister, lancer analyse."""

import asyncio
import logging
import os
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, File, status
from fastapi.responses import HTMLResponse, FileResponse, Response
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.core.classification import compute_score, normalize_severity
from app.config import settings
from app.models.scan import Scan
from app.models.user import User
from app.models.scan_metrics import ScanMetrics
from app.models.vulnerability import Vulnerability
from app.models.owasp_category import OwaspCategory
from app.models.tool_execution import ToolExecution
from app.schemas.scan import ScanCreate, ScanResponse, ScanList
from app.schemas.scan_results import (
    ScanOwaspSummaryResponse,
    OwaspSummaryItem,
    ScanResultsResponse,
    VulnerabilityResultItem,
    ScanScoreResponse,
)
from app.services.scan_orchestrator import ScanOrchestrator
from app.services.technology_detector import TechnologyDetector
from app.services.report_generator import ReportGenerator

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_scan_or_404(db: Session, scan_id: UUID) -> Scan:
    """Récupère un scan ou lève une 404."""
    scan = db.get(Scan, scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    return scan


def _run_scan_background(scan_id: UUID, project_path: str):
    """Fonction wrapper pour exécuter le scan en background."""
    # Créer une nouvelle session de base de données pour le thread background
    # La session passée en paramètre peut être fermée quand le thread s'exécute
    from app.db.session import SessionLocal
    db = SessionLocal()
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        logger.info(f"Démarrage du scan {scan_id} en background")
        result = loop.run_until_complete(
            ScanOrchestrator(db).run_scan(scan_id, project_path)
        )
        logger.info(f"Scan {scan_id} terminé: {result.get('vulnerabilities_count', 0)} vulnérabilités")
        
        # Vérification finale en base
        from app.models.vulnerability import Vulnerability
        final_count = db.query(Vulnerability).filter(Vulnerability.scan_id == scan_id).count()
        logger.info(f"Vérification finale: {final_count} vulnérabilités en base pour le scan {scan_id}")
        
        if final_count == 0:
            logger.warning(f"ATTENTION: Aucune vulnérabilité en base après la fin du scan {scan_id}")
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution du scan {scan_id}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        # Marquer le scan comme erreur
        try:
            scan = db.get(Scan, scan_id)
            if scan:
                scan.status = "error"
                scan.finished_at = datetime.utcnow()
                db.commit()
                logger.info(f"Scan {scan_id} marqué comme erreur")
        except Exception as db_error:
            logger.error(f"Erreur lors de la mise à jour du statut du scan: {db_error}")
            db.rollback()
    finally:
        # Attendre un peu avant de fermer pour s'assurer que tout est commité
        import time
        time.sleep(1)
        db.close()
        loop.close()
        logger.info(f"Session DB fermée pour le scan {scan_id}")


@router.post("/upload", response_model=ScanResponse, status_code=status.HTTP_201_CREATED)
def upload_scan(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ScanResponse:
    """
    Téléverse un fichier ZIP contenant le code à analyser.
    Le fichier est décompressé dans un dossier dédié au scan.
    """
    # Vérifier que c'est un fichier ZIP
    if not file.filename or not file.filename.endswith(('.zip', '.ZIP')):
        raise HTTPException(
            status_code=400,
            detail="Le fichier doit être une archive ZIP (.zip)"
        )
    
    # Créer le scan d'abord pour avoir un ID
    scan = Scan(
        user_id=current_user.id,
        repository_url=None,
        upload_path=None,
        status="pending",
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)
    
    # Créer le dossier de destination
    workspace_dir = Path(settings.PROJECT_ROOT)
    workspace_dir.mkdir(parents=True, exist_ok=True)
    scan_dir = workspace_dir / str(scan.id)
    scan_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Sauvegarder le fichier ZIP temporairement
        zip_path = scan_dir / file.filename
        with open(zip_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Décompresser le ZIP
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(scan_dir)
        
        # Supprimer le fichier ZIP après extraction
        zip_path.unlink()
        
        # Mettre à jour le scan avec le chemin
        scan.upload_path = str(scan_dir)
        db.commit()
        db.refresh(scan)
        
        return ScanResponse.model_validate(scan)
    
    except zipfile.BadZipFile:
        # Nettoyer en cas d'erreur
        shutil.rmtree(scan_dir, ignore_errors=True)
        db.delete(scan)
        db.commit()
        raise HTTPException(
            status_code=400,
            detail="Le fichier ZIP est corrompu ou invalide"
        )
    except Exception as e:
        # Nettoyer en cas d'erreur
        logger.error(f"Erreur lors du traitement du fichier: {e}")
        shutil.rmtree(scan_dir, ignore_errors=True)
        db.delete(scan)
        db.commit()
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors du traitement du fichier : {str(e)}"
        )


@router.post("", response_model=ScanResponse, status_code=status.HTTP_201_CREATED)
def create_scan(
    payload: ScanCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ScanResponse:
    """
    Crée un nouveau scan.
    Si une URL de dépôt Git est fournie, clone le dépôt et détecte les technologies.
    """
    # Créer le scan d'abord
    scan = Scan(
        user_id=current_user.id,
        repository_url=payload.repository_url,
        upload_path=payload.upload_path,
        status="pending",
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)
    
    # Si une URL Git est fournie, cloner le dépôt immédiatement
    if payload.repository_url:
        project_path = f"{settings.PROJECT_ROOT}/{scan.id}"
        project_root = Path(settings.PROJECT_ROOT)
        project_root.mkdir(parents=True, exist_ok=True)
        project_path_obj = Path(project_path)
        
        # Supprimer le dossier s'il existe déjà
        if project_path_obj.exists():
            shutil.rmtree(project_path_obj)
        
        try:
            logger.info(f"Clonage du dépôt {payload.repository_url} vers {project_path}")
            from app.git.clone import clone_repository_with_auth
            
            git_token = settings.GIT_TOKEN if settings.GIT_TOKEN else None
            clone_repository_with_auth(
                repo_url=payload.repository_url,
                target_path=project_path_obj,
                token=git_token,
                timeout=300,
            )
            logger.info(f"Dépôt cloné avec succès dans {project_path}")
        except Exception as e:
            logger.error(f"Erreur lors du clonage du dépôt: {e}")
            # Ne pas lever d'exception, le scan reste en "pending"
            # L'utilisateur pourra voir l'erreur dans la prévisualisation
    
    return ScanResponse.model_validate(scan)


@router.get("/{scan_id}/preview")
def get_scan_preview(
    scan_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retourne une prévisualisation du projet : technologies détectées et fichiers à analyser.
    """
    scan = _get_scan_or_404(db, scan_id)
    
    # Vérifier que l'utilisateur est propriétaire
    if scan.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Déterminer le chemin du projet
    project_path = None
    if scan.upload_path:
        project_path = scan.upload_path
    elif scan.repository_url:
        project_path = f"{settings.PROJECT_ROOT}/{scan_id}"
    
    if not project_path or not Path(project_path).exists():
        return {
            "scan_id": str(scan_id),
            "status": "not_ready",
            "message": "Le projet n'a pas encore été cloné ou téléversé",
            "technologies": {
                "python": False,
                "javascript": False,
                "typescript": False,
                "php": False,
                "java": False,
                "go": False,
                "ruby": False,
                "rust": False,
                "csharp": False,
            },
            "tools": [],
            "files_by_type": {},
            "total_files": 0,
            "semgrep_configs": [],
        }
    
    # Détecter les technologies
    technologies = TechnologyDetector.detect(project_path)
    
    # Déterminer les outils à utiliser
    tools_to_run = TechnologyDetector.get_tools_to_run(technologies)
    
    # Lister les fichiers à analyser
    from app.services.scan_orchestrator import ScanOrchestrator
    orchestrator = ScanOrchestrator(db)
    all_files = orchestrator._list_all_code_files(project_path)
    
    # Organiser les fichiers par type
    files_by_type = {
        "python": [],
        "javascript": [],
        "typescript": [],
        "php": [],
        "java": [],
        "go": [],
        "ruby": [],
        "rust": [],
        "csharp": [],
        "other": [],
    }
    
    for file_path in sorted(all_files):
        file_ext = Path(file_path).suffix.lower()
        if file_ext in [".py"]:
            files_by_type["python"].append(file_path)
        elif file_ext in [".js", ".jsx"]:
            files_by_type["javascript"].append(file_path)
        elif file_ext in [".ts", ".tsx"]:
            files_by_type["typescript"].append(file_path)
        elif file_ext in [".php"]:
            files_by_type["php"].append(file_path)
        elif file_ext in [".java"]:
            files_by_type["java"].append(file_path)
        elif file_ext in [".go"]:
            files_by_type["go"].append(file_path)
        elif file_ext in [".rb"]:
            files_by_type["ruby"].append(file_path)
        elif file_ext in [".rs"]:
            files_by_type["rust"].append(file_path)
        elif file_ext in [".cs"]:
            files_by_type["csharp"].append(file_path)
        else:
            files_by_type["other"].append(file_path)
    
    # Filtrer les types vides
    files_by_type = {k: v for k, v in files_by_type.items() if v}
    
    return {
        "scan_id": str(scan_id),
        "status": "ready",
        "technologies": technologies,
        "tools": tools_to_run,
        "files_by_type": files_by_type,
        "total_files": len(all_files),
        "semgrep_configs": TechnologyDetector.get_semgrep_configs(technologies),
    }


@router.get("/{scan_id}/results", response_model=ScanResultsResponse)
def get_scan_results(
    scan_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ScanResultsResponse:
    """Liste des vulnérabilités du scan avec catégorie OWASP et sévérité."""
    scan = _get_scan_or_404(db, scan_id)
    if scan.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Accès refusé")
    
    from sqlalchemy.orm import joinedload
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
def get_scan_score(
    scan_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ScanScoreResponse:
    """Score global du scan (/100 et grade A→F). 0 vulnérabilité → score 100, grade A."""
    scan = _get_scan_or_404(db, scan_id)
    if scan.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Accès refusé")
    
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


@router.get("/{scan_id}/files")
def get_scan_files(
    scan_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Retourne la liste des fichiers analysés par chaque outil en temps réel.
    """
    scan = _get_scan_or_404(db, scan_id)
    if scan.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Accès refusé")
    
    # Récupérer les exécutions d'outils
    tool_executions = list(
        db.execute(
            select(ToolExecution).where(ToolExecution.scan_id == scan_id)
        ).scalars().all()
    )
    
    # Extraire les fichiers analysés par outil
    files_by_tool = {}
    all_files = set()
    
    # Déterminer le chemin du projet pour lister tous les fichiers si nécessaire
    project_path = None
    if scan.upload_path:
        project_path = scan.upload_path
    elif scan.repository_url:
        project_path = f"{settings.PROJECT_ROOT}/{scan_id}"
    
    for exec in tool_executions:
        if exec.raw_output and isinstance(exec.raw_output, dict):
            # Essayer plusieurs façons d'identifier l'outil
            tool_name = (
                exec.raw_output.get("tool") or 
                exec.raw_output.get("tool_name") or
                # Essayer de deviner depuis le type de données
                ("semgrep" if "results" in exec.raw_output else None) or
                ("truffleHog" if "secrets" in exec.raw_output else None) or
                ("pip-audit" if "vulnerabilities" in exec.raw_output and "pip" in str(exec.raw_output).lower() else None) or
                ("npm-audit" if "vulnerabilities" in exec.raw_output and "npm" in str(exec.raw_output).lower() else None) or
                "unknown"
            )
            
            analyzed_files = exec.raw_output.get("analyzed_files", [])
            
            # Si aucun fichier n'est trouvé dans raw_output, essayer de les extraire
            if not analyzed_files and project_path:
                from app.services.scan_orchestrator import ScanOrchestrator
                orchestrator = ScanOrchestrator(db)
                analyzed_files = orchestrator._extract_analyzed_files(tool_name, exec.raw_output, project_path)
                # Mettre à jour raw_output avec les fichiers extraits
                exec.raw_output["analyzed_files"] = analyzed_files
                db.commit()
            
            if analyzed_files:
                files_by_tool[tool_name] = {
                    "files": analyzed_files,
                    "count": len(analyzed_files),
                    "status": exec.status,
                }
                all_files.update(analyzed_files)
    
    # Si aucun fichier n'est trouvé, essayer de lister tous les fichiers du projet
    if not all_files and project_path:
        from pathlib import Path
        project_path_obj = Path(project_path)
        if project_path_obj.exists():
            from app.services.scan_orchestrator import ScanOrchestrator
            orchestrator = ScanOrchestrator(db)
            all_project_files = orchestrator._list_all_code_files(project_path)
            if all_project_files:
                # Créer une entrée "all" pour tous les fichiers
                files_by_tool["all"] = {
                    "files": sorted(list(all_project_files)),
                    "count": len(all_project_files),
                    "status": "completed",
                }
                all_files = all_project_files
            else:
                logger.warning(f"Aucun fichier trouvé dans {project_path}")
        else:
            logger.warning(f"Le chemin du projet n'existe pas: {project_path}")
    
    return {
        "scan_id": str(scan_id),
        "total_files": len(all_files),
        "files_by_tool": files_by_tool,
        "all_files": sorted(list(all_files)),
    }


@router.get("/{scan_id}/owasp-summary", response_model=ScanOwaspSummaryResponse)
def get_scan_owasp_summary(
    scan_id: UUID, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ScanOwaspSummaryResponse:
    """Répartition des vulnérabilités par catégorie OWASP (A01–A10)."""
    scan = _get_scan_or_404(db, scan_id)
    if scan.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Accès refusé")
    
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
        
        # S'assurer que le dossier PROJECT_ROOT existe
        project_root = Path(settings.PROJECT_ROOT)
        project_root.mkdir(parents=True, exist_ok=True)
        
        # Cloner le dépôt Git si nécessaire
        project_path_obj = Path(project_path)
        if not project_path_obj.exists() or not any(project_path_obj.iterdir()):
            logger.info(f"Clonage du dépôt {scan.repository_url} vers {project_path}")
            try:
                from app.git.clone import clone_repository_with_auth
                
                # Cloner avec authentification si un token est disponible
                git_token = settings.GIT_TOKEN if settings.GIT_TOKEN else None
                clone_repository_with_auth(
                    repo_url=scan.repository_url,
                    target_path=project_path_obj,
                    token=git_token,
                    timeout=300,
                )
                logger.info(f"Dépôt cloné avec succès dans {project_path}")
            except Exception as e:
                logger.error(f"Erreur lors du clonage du dépôt: {e}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Erreur lors du clonage du dépôt: {str(e)}"
                )
    else:
        raise HTTPException(
            status_code=400,
            detail="No repository URL or upload path provided",
        )

    # Vérifier que le chemin du projet existe
    project_path_obj = Path(project_path)
    if not project_path_obj.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Le chemin du projet n'existe pas: {project_path}"
        )

    # Lancer l'orchestrateur en background
    # Ne pas passer db car on crée une nouvelle session dans le thread
    background_tasks.add_task(
        _run_scan_background,
        scan_id,
        project_path,
    )

    return {
        "scan_id": str(scan_id),
        "status": "running",
        "message": "Analysis started in background",
    }


@router.get("/{scan_id}/report/html", response_class=HTMLResponse)
def get_report_html(
    scan_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Récupère le rapport de sécurité au format HTML.
    """
    scan = _get_scan_or_404(db, scan_id)

    # Vérifier que l'utilisateur est propriétaire
    if scan.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Générer le rapport
    try:
        report_generator = ReportGenerator()
        html_content = report_generator.generate_html_report(db, scan_id)
        return html_content
    except Exception as e:
        logger.error(f"Erreur lors de la génération du rapport HTML: {e}")
        raise HTTPException(
            status_code=500,
            detail="Erreur lors de la génération du rapport"
        )


@router.get("/{scan_id}/report/pdf")
def get_report_pdf(
    scan_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Récupère le rapport de sécurité au format PDF.
    """
    scan = _get_scan_or_404(db, scan_id)

    # Vérifier que l'utilisateur est propriétaire
    if scan.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Générer le rapport
    try:
        report_generator = ReportGenerator()
        pdf_bytes = report_generator.generate_pdf_report(db, scan_id)
        
        pdf_filename = f"securescan_report_{scan_id}.pdf"
        
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={pdf_filename}"}
        )
    except Exception as e:
        logger.error(f"Erreur lors de la génération du rapport PDF: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la génération du rapport: {str(e)}"
        )

