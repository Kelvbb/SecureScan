#!/usr/bin/env python3
"""Script pour tester l'analyse du dépôt SecureScan."""

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
from app.models.user import User
from app.services.scan_orchestrator import ScanOrchestrator
from app.config import settings

# URL du dépôt à analyser
REPO_URL = "https://github.com/Kelvbb/roubeyriesas.fr.git"

async def test_analyze_repo():
    """Test l'analyse complète du dépôt SecureScan."""
    print("=" * 80)
    print("ANALYSE DU DÉPÔT SECURESCAN")
    print("=" * 80)
    print(f"Dépôt: {REPO_URL}")
    print()
    
    # Créer la connexion à la base
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        # Récupérer un utilisateur
        user = db.query(User).first()
        if not user:
            print("❌ Aucun utilisateur trouvé en base")
            print("   Créez d'abord un utilisateur via l'interface web")
            return
        
        print(f"✅ Utilisateur trouvé: {user.email}")
        
        # Créer un scan
        scan = Scan(
            id=uuid4(),
            user_id=user.id,
            repository_url=REPO_URL,
            status="pending",
        )
        db.add(scan)
        db.commit()
        print(f"✅ Scan créé: {scan.id}")
        
        # Déterminer le chemin du projet
        project_path = f"{settings.PROJECT_ROOT}/{scan.id}"
        project_path_obj = Path(project_path)
        project_path_obj.mkdir(parents=True, exist_ok=True)
        
        print(f"📁 Chemin du projet: {project_path}")
        
        # Cloner le dépôt si nécessaire
        if not project_path_obj.exists() or not any(project_path_obj.iterdir()):
            print("\n📥 Clonage du dépôt...")
            try:
                from app.git.clone import clone_repository_with_auth
                
                git_token = settings.GIT_TOKEN if settings.GIT_TOKEN else None
                clone_repository_with_auth(
                    repo_url=REPO_URL,
                    target_path=project_path_obj,
                    token=git_token,
                    timeout=300,
                )
                print("✅ Dépôt cloné avec succès")
            except Exception as e:
                print(f"❌ Erreur lors du clonage: {e}")
                return
        else:
            print("✅ Dépôt déjà cloné")
        
        # Compter les fichiers
        code_files = list(project_path_obj.rglob("*.py")) + list(project_path_obj.rglob("*.ts")) + list(project_path_obj.rglob("*.tsx")) + list(project_path_obj.rglob("*.js")) + list(project_path_obj.rglob("*.jsx"))
        print(f"📊 Fichiers de code trouvés: {len(code_files)}")
        
        # Lancer l'orchestrateur
        print("\n" + "=" * 80)
        print("LANCEMENT DE L'ANALYSE")
        print("=" * 80)
        
        orchestrator = ScanOrchestrator(db)
        result = await orchestrator.run_scan(scan.id, str(project_path))
        
        print(f"\n✅ Analyse terminée!")
        print(f"   Status: {result.get('status')}")
        print(f"   Vulnérabilités trouvées: {result.get('vulnerabilities_count', 0)}")
        
        # Vérifier en base
        from app.models.vulnerability import Vulnerability
        vulns_in_db = db.query(Vulnerability).filter(
            Vulnerability.scan_id == scan.id
        ).all()
        
        print(f"\n📊 Vérification en base de données:")
        print(f"   Vulnérabilités en base: {len(vulns_in_db)}")
        
        if vulns_in_db:
            print(f"\n🔍 Exemples de vulnérabilités trouvées:")
            for i, vuln in enumerate(vulns_in_db[:10], 1):
                print(f"   {i}. {vuln.title[:60]}")
                print(f"      Fichier: {vuln.file_path}")
                print(f"      Ligne: {vuln.line_start}")
                print(f"      Sévérité: {vuln.severity}")
                print(f"      OWASP: {vuln.owasp_category_id}")
                print()
            
            # Statistiques par sévérité
            from collections import Counter
            severities = Counter(v.severity for v in vulns_in_db)
            print(f"\n📈 Répartition par sévérité:")
            for severity, count in severities.items():
                print(f"   {severity}: {count}")
            
            # Statistiques par OWASP
            owasp_counts = Counter(v.owasp_category_id for v in vulns_in_db if v.owasp_category_id)
            if owasp_counts:
                print(f"\n📈 Répartition par OWASP:")
                for owasp, count in owasp_counts.most_common():
                    print(f"   {owasp}: {count}")
        else:
            print(f"\n⚠️  Aucune vulnérabilité trouvée en base")
            print(f"   Vérifiez les logs pour comprendre pourquoi")
        
        # Afficher le scan final
        db.refresh(scan)
        print(f"\n📋 Statut final du scan:")
        print(f"   Status: {scan.status}")
        print(f"   Début: {scan.started_at}")
        print(f"   Fin: {scan.finished_at}")
        
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test_analyze_repo())
