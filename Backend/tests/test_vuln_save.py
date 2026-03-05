#!/usr/bin/env python3
"""Script pour tester la sauvegarde des vulnérabilités en base."""

import asyncio
import sys
from pathlib import Path
from uuid import uuid4

# Ajouter le chemin du backend
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.scan import Scan
from app.models.tool_execution import ToolExecution
from app.models.vulnerability import Vulnerability
from app.models.user import User
from app.services.semgrep_service import SemgrepService

# Configuration de la base de données (à adapter selon votre .env)
DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/securescan"


async def test_vuln_save(project_path: str):
    """Test la sauvegarde des vulnérabilités."""
    print("=" * 80)
    print("TEST DE SAUVEGARDE DES VULNÉRABILITÉS")
    print("=" * 80)

    # Créer la connexion à la base
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        # 1. Exécuter Semgrep
        print("\n" + "=" * 80)
        print("ÉTAPE 1: Exécution de Semgrep")
        print("=" * 80)

        result = await SemgrepService.run(project_path)

        print(f"Status: {result.get('status')}")
        print(f"Résultats bruts: {len(result.get('results', []))}")

        if result.get("status") != "success":
            print(f"❌ Semgrep a échoué: {result.get('error')}")
            return

        results = result.get("results", [])
        if not results:
            print(f"❌ Aucun résultat trouvé par Semgrep")
            print(f"   Vérifiez que Semgrep fonctionne sur ce projet")
            return

        print(f"✅ Semgrep a trouvé {len(results)} résultats")

        # 2. Parser les vulnérabilités
        print("\n" + "=" * 80)
        print("ÉTAPE 2: Parsing des vulnérabilités")
        print("=" * 80)

        vulns = SemgrepService.parse_vulnerabilities(result)
        print(f"Vulnérabilités parsées: {len(vulns)}")

        if not vulns:
            print(f"❌ Aucune vulnérabilité parsée")
            print(f"   Premier résultat brut:")
            import json

            print(json.dumps(results[0], indent=2)[:500])
            return

        print(f"✅ {len(vulns)} vulnérabilités parsées")
        print(f"\nExemple de vulnérabilité parsée:")
        print(f"  - Titre: {vulns[0].get('title', 'Unknown')[:60]}")
        print(f"  - Fichier: {vulns[0].get('file_path', 'Unknown')}")
        print(f"  - Ligne: {vulns[0].get('line_start')}")
        print(f"  - Sévérité: {vulns[0].get('severity', 'Unknown')}")

        # 3. Créer un scan de test
        print("\n" + "=" * 80)
        print("ÉTAPE 3: Création d'un scan de test")
        print("=" * 80)

        # Récupérer un utilisateur (ou créer un test)
        user = db.query(User).first()
        if not user:
            print("❌ Aucun utilisateur trouvé en base")
            print("   Créez d'abord un utilisateur via l'interface")
            return

        print(f"✅ Utilisateur trouvé: {user.email}")

        # Créer un scan
        scan = Scan(
            id=uuid4(),
            user_id=user.id,
            repository_url=project_path,
            status="running",
        )
        db.add(scan)
        db.flush()
        print(f"✅ Scan créé: {scan.id}")

        # 4. Créer une ToolExecution
        print("\n" + "=" * 80)
        print("ÉTAPE 4: Création d'une ToolExecution")
        print("=" * 80)

        tool_exec = ToolExecution(
            scan_id=scan.id,
            status="success",
            raw_output=result,
        )
        db.add(tool_exec)
        db.flush()
        print(f"✅ ToolExecution créée: {tool_exec.id}")

        # 5. Sauvegarder les vulnérabilités
        print("\n" + "=" * 80)
        print("ÉTAPE 5: Sauvegarde des vulnérabilités")
        print("=" * 80)

        saved_count = 0
        for i, vuln_data in enumerate(vulns[:10], 1):  # Limiter à 10 pour le test
            try:
                vuln = Vulnerability(
                    scan_id=scan.id,
                    tool_execution_id=tool_exec.id,
                    title=vuln_data["title"],
                    description=vuln_data.get("description"),
                    file_path=vuln_data.get("file_path"),
                    line_start=vuln_data.get("line_start"),
                    line_end=vuln_data.get("line_end"),
                    severity=vuln_data.get("severity", "medium"),
                    cve_id=vuln_data.get("cve_id"),
                    cwe_id=vuln_data.get("cwe_id"),
                )
                db.add(vuln)
                saved_count += 1
                print(f"  {i}. Ajouté: {vuln_data.get('title', 'Unknown')[:50]}")
            except Exception as e:
                print(f"  ❌ Erreur pour la vulnérabilité {i}: {e}")
                import traceback

                traceback.print_exc()

        # Flush pour vérifier qu'il n'y a pas d'erreur
        print(f"\nFlush de {saved_count} vulnérabilités...")
        try:
            db.flush()
            print(f"✅ Flush réussi")
        except Exception as e:
            print(f"❌ Erreur lors du flush: {e}")
            import traceback

            traceback.print_exc()
            db.rollback()
            return

        # Commit
        print(f"\nCommit des changements...")
        try:
            db.commit()
            print(f"✅ Commit réussi")
        except Exception as e:
            print(f"❌ Erreur lors du commit: {e}")
            import traceback

            traceback.print_exc()
            db.rollback()
            return

        # 6. Vérifier en base
        print("\n" + "=" * 80)
        print("ÉTAPE 6: Vérification en base de données")
        print("=" * 80)

        count = db.query(Vulnerability).filter(Vulnerability.scan_id == scan.id).count()
        print(f"Vulnérabilités en base pour ce scan: {count}")

        if count > 0:
            print(f"✅ SUCCÈS! {count} vulnérabilités sauvegardées")
            print(f"\nExemple de vulnérabilité en base:")
            vuln_example = (
                db.query(Vulnerability).filter(Vulnerability.scan_id == scan.id).first()
            )
            print(f"  - ID: {vuln_example.id}")
            print(f"  - Titre: {vuln_example.title[:60]}")
            print(f"  - Fichier: {vuln_example.file_path}")
            print(f"  - Ligne: {vuln_example.line_start}")
        else:
            print(f"❌ ÉCHEC! Aucune vulnérabilité en base")

        # Nettoyer (optionnel)
        print(f"\nNettoyage du scan de test...")
        db.delete(scan)
        db.commit()
        print(f"✅ Scan de test supprimé")

    except Exception as e:
        print(f"\n❌ Erreur générale: {e}")
        import traceback

        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 test_vuln_save.py <chemin_du_projet>")
        print("\nExemple:")
        print("  python3 test_vuln_save.py /tmp/securescan/projects/SCAN_ID")
        sys.exit(1)

    project_path = sys.argv[1]
    asyncio.run(test_vuln_save(project_path))
