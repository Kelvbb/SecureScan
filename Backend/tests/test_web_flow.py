"""
Script de test qui reproduit exactement le processus de l'interface web :
1. Création d'un scan avec URL Git
2. Clonage du dépôt
3. Détection des technologies
4. Prévisualisation du projet
5. Lancement de l'analyse
6. Vérification des résultats et du score
"""

import asyncio
import sys
from pathlib import Path
from uuid import UUID

# Ajouter le répertoire parent au path pour les imports
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.scan import Scan
from app.models.user import User
from app.services.scan_orchestrator import ScanOrchestrator
from app.services.technology_detector import TechnologyDetector
from app.api.routes.scans import get_scan_preview, run_scan
from app.core.classification import compute_score, normalize_severity


def print_section(title: str):
    """Affiche une section avec un titre."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def print_step(step: int, description: str):
    """Affiche une étape."""
    print(f"📌 Étape {step}: {description}")


async def test_web_flow(repo_url: str):
    """
    Teste le flux complet de l'interface web.

    Args:
        repo_url: URL du dépôt Git à analyser
    """
    db: Session = SessionLocal()

    try:
        # =====================================================================
        # ÉTAPE 1: Création du scan (simule POST /api/scans)
        # =====================================================================
        print_section("ÉTAPE 1: CRÉATION DU SCAN")
        print_step(1, "Recherche de l'utilisateur...")

        # Trouver un utilisateur (ou créer un utilisateur de test)
        user = db.query(User).first()
        if not user:
            print("❌ Aucun utilisateur trouvé dans la base de données")
            print(
                "   Créez d'abord un utilisateur via l'interface web ou le script de test"
            )
            return

        print(f"✅ Utilisateur trouvé: {user.email}")

        print_step(2, "Création du scan...")
        scan = Scan(
            user_id=user.id,
            repository_url=repo_url,
            upload_path=None,
            status="pending",
        )
        db.add(scan)
        db.commit()
        db.refresh(scan)

        print(f"✅ Scan créé: {scan.id}")
        print(f"   URL: {repo_url}")
        print(f"   Status: {scan.status}")

        # =====================================================================
        # ÉTAPE 2: Clonage du dépôt (simule le clonage lors de la création)
        # =====================================================================
        print_section("ÉTAPE 2: CLONAGE DU DÉPÔT")
        print_step(1, "Clonage du dépôt Git...")

        from app.config import settings
        from app.git.clone import clone_repository_with_auth

        project_path = f"{settings.PROJECT_ROOT}/{scan.id}"
        project_root = Path(settings.PROJECT_ROOT)
        project_root.mkdir(parents=True, exist_ok=True)
        project_path_obj = Path(project_path)

        # Supprimer le dossier s'il existe déjà
        if project_path_obj.exists():
            import shutil

            shutil.rmtree(project_path_obj)
            print(f"   Suppression de l'ancien dossier: {project_path}")

        try:
            git_token = settings.GIT_TOKEN if settings.GIT_TOKEN else None
            clone_repository_with_auth(
                repo_url=repo_url,
                target_path=project_path_obj,
                token=git_token,
                timeout=300,
            )
            print(f"✅ Dépôt cloné avec succès")
            print(f"   Chemin: {project_path}")
        except Exception as e:
            print(f"❌ Erreur lors du clonage: {e}")
            return

        # =====================================================================
        # ÉTAPE 3: Détection des technologies (simule GET /api/scans/{id}/preview)
        # =====================================================================
        print_section("ÉTAPE 3: DÉTECTION DES TECHNOLOGIES")
        print_step(1, "Analyse du projet...")

        technologies = TechnologyDetector.detect(project_path)
        detected_techs = [tech for tech, detected in technologies.items() if detected]

        print(
            f"✅ Technologies détectées: {', '.join(detected_techs) if detected_techs else 'Aucune'}"
        )
        for tech, detected in technologies.items():
            status = "✓" if detected else "✗"
            print(f"   {status} {tech.capitalize()}")

        # Déterminer les outils à utiliser
        tools_to_run = TechnologyDetector.get_tools_to_run(technologies)
        print(f"\n📦 Outils sélectionnés: {', '.join(tools_to_run)}")

        # Configurations Semgrep
        semgrep_configs = TechnologyDetector.get_semgrep_configs(technologies)
        print(f"🔧 Configurations Semgrep: {', '.join(semgrep_configs)}")

        # Lister les fichiers
        orchestrator = ScanOrchestrator(db)
        all_files = orchestrator._list_all_code_files(project_path)
        print(f"\n📁 Fichiers à analyser: {len(all_files)} fichiers")

        # Organiser par type
        files_by_type = {
            "python": [f for f in all_files if f.endswith(".py")],
            "javascript": [f for f in all_files if f.endswith((".js", ".jsx"))],
            "typescript": [f for f in all_files if f.endswith((".ts", ".tsx"))],
            "php": [f for f in all_files if f.endswith(".php")],
            "java": [f for f in all_files if f.endswith(".java")],
            "go": [f for f in all_files if f.endswith(".go")],
            "ruby": [f for f in all_files if f.endswith(".rb")],
            "rust": [f for f in all_files if f.endswith(".rs")],
            "csharp": [f for f in all_files if f.endswith(".cs")],
        }

        for file_type, files in files_by_type.items():
            if files:
                print(f"   {file_type}: {len(files)} fichiers")

        # =====================================================================
        # ÉTAPE 4: Prévisualisation (simule GET /api/scans/{id}/preview)
        # =====================================================================
        print_section("ÉTAPE 4: PRÉVISUALISATION DU PROJET")

        # Simuler l'endpoint preview
        preview_data = {
            "scan_id": str(scan.id),
            "status": "ready",
            "technologies": technologies,
            "tools": tools_to_run,
            "files_by_type": {k: v for k, v in files_by_type.items() if v},
            "total_files": len(all_files),
            "semgrep_configs": semgrep_configs,
        }

        print("📊 Résumé de la prévisualisation:")
        print(f"   Status: {preview_data['status']}")
        print(f"   Technologies: {len(detected_techs)} détectées")
        print(f"   Outils: {len(tools_to_run)} sélectionnés")
        print(f"   Fichiers: {preview_data['total_files']} à analyser")

        # =====================================================================
        # ÉTAPE 5: Lancement de l'analyse (simule POST /api/scans/{id}/run)
        # =====================================================================
        print_section("ÉTAPE 5: LANCEMENT DE L'ANALYSE")
        print_step(1, "Démarrage de l'analyse de sécurité...")

        # Mettre à jour le statut du scan
        scan.status = "running"
        from datetime import datetime, timezone

        scan.started_at = datetime.now(timezone.utc)
        db.commit()

        print(f"✅ Scan mis à jour: status = 'running'")
        print(f"   Début: {scan.started_at}")

        # Lancer l'orchestrateur
        print_step(2, "Exécution des outils d'analyse...")
        print("   (Cela peut prendre plusieurs minutes selon la taille du projet)\n")

        result = await orchestrator.run_scan(scan.id, project_path)

        print(f"\n✅ Analyse terminée!")
        print(f"   Status: {result.get('status')}")
        print(f"   Vulnérabilités trouvées: {result.get('vulnerabilities_count', 0)}")

        # =====================================================================
        # ÉTAPE 6: Vérification des résultats (simule GET /api/scans/{id}/results)
        # =====================================================================
        print_section("ÉTAPE 6: VÉRIFICATION DES RÉSULTATS")

        from app.models.vulnerability import Vulnerability
        from app.models.tool_execution import ToolExecution

        # Compter les vulnérabilités en base
        vuln_count = (
            db.query(Vulnerability).filter(Vulnerability.scan_id == scan.id).count()
        )
        print(f"📊 Vulnérabilités en base de données: {vuln_count}")

        if vuln_count > 0:
            # Afficher quelques exemples
            vulns = (
                db.query(Vulnerability)
                .filter(Vulnerability.scan_id == scan.id)
                .order_by(Vulnerability.created_at.desc())
                .limit(10)
                .all()
            )

            print(f"\n📋 Exemples de vulnérabilités trouvées:")
            for i, vuln in enumerate(vulns, 1):
                print(f"   {i}. {vuln.title[:60]}...")
                print(f"      Fichier: {vuln.file_path}")
                print(f"      Ligne: {vuln.line_start}, Sévérité: {vuln.severity}")
                print(f"      OWASP: {vuln.owasp_category_id}")

        # Vérifier les exécutions d'outils
        tool_execs = (
            db.query(ToolExecution).filter(ToolExecution.scan_id == scan.id).all()
        )

        print(f"\n🔧 Exécutions d'outils: {len(tool_execs)}")
        for tool_exec in tool_execs:
            # Le nom de l'outil est stocké dans raw_output
            tool_name = "unknown"
            if tool_exec.raw_output and isinstance(tool_exec.raw_output, dict):
                tool_name = tool_exec.raw_output.get("tool", "unknown")

            print(f"   - {tool_name}: {tool_exec.status}")
            if tool_exec.finished_at and tool_exec.started_at:
                duration = (
                    tool_exec.finished_at - tool_exec.started_at
                ).total_seconds()
                print(f"     Durée: {duration:.2f}s")

        # =====================================================================
        # ÉTAPE 7: Calcul du score (simule GET /api/scans/{id}/score)
        # =====================================================================
        print_section("ÉTAPE 7: CALCUL DU SCORE")

        # Récupérer toutes les vulnérabilités pour le calcul du score
        all_vulns = (
            db.query(Vulnerability).filter(Vulnerability.scan_id == scan.id).all()
        )

        if all_vulns:
            # Compter les vulnérabilités par sévérité
            critical = high = medium = low = 0
            for v in all_vulns:
                level = normalize_severity(v.severity)
                if level == "critical":
                    critical += 1
                elif level == "high":
                    high += 1
                elif level == "medium":
                    medium += 1
                else:
                    low += 1

            # Calculer le score
            score_100, grade = compute_score(critical, high, medium, low)
            print(f"📊 Score de sécurité: {score_100}/100")
            print(f"   Grade: {grade}")
            print(f"   Vulnérabilités critiques: {critical}")
            print(f"   Vulnérabilités élevées: {high}")
            print(f"   Vulnérabilités moyennes: {medium}")
            print(f"   Vulnérabilités faibles: {low}")
        else:
            print("⚠️  Aucune vulnérabilité trouvée, score par défaut: 100/100")

        # =====================================================================
        # RÉSUMÉ FINAL
        # =====================================================================
        print_section("RÉSUMÉ FINAL")

        # Rafraîchir le scan pour avoir les dernières données
        db.refresh(scan)

        print(f"📋 Informations du scan:")
        print(f"   ID: {scan.id}")
        print(f"   URL: {scan.repository_url}")
        print(f"   Status: {scan.status}")
        print(f"   Créé le: {scan.created_at}")
        if scan.started_at:
            print(f"   Début: {scan.started_at}")
        if scan.finished_at:
            print(f"   Fin: {scan.finished_at}")
            if scan.started_at:
                duration = (scan.finished_at - scan.started_at).total_seconds()
                print(f"   Durée totale: {duration:.2f}s")

        print(f"\n📊 Statistiques:")
        print(f"   Technologies détectées: {len(detected_techs)}")
        print(f"   Outils utilisés: {len(tools_to_run)}")
        print(f"   Fichiers analysés: {len(all_files)}")
        print(f"   Vulnérabilités trouvées: {vuln_count}")

        if vuln_count > 0:
            print(
                f"\n✅ Test réussi: {vuln_count} vulnérabilités détectées et enregistrées"
            )
        else:
            print(f"\n⚠️  Test terminé mais aucune vulnérabilité détectée")
            print(f"   Vérifiez la configuration des outils et les règles de détection")

    except Exception as e:
        print(f"\n❌ Erreur lors du test: {e}")
        import traceback

        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    # URL du dépôt à tester
    REPO_URL = "https://github.com/Kelvbb/roubeyriesas.fr.git"

    # Permettre de passer l'URL en argument
    if len(sys.argv) > 1:
        REPO_URL = sys.argv[1]

    print("=" * 80)
    print("  TEST DU FLUX COMPLET DE L'INTERFACE WEB")
    print("=" * 80)
    print(f"\n📦 Dépôt à analyser: {REPO_URL}\n")

    # Lancer le test
    asyncio.run(test_web_flow(REPO_URL))

    print("\n" + "=" * 80)
    print("  FIN DU TEST")
    print("=" * 80)
