"""
Test et documentation pour l'intégration des outils de sécurité.

Ce fichier montre comment tester les services et l'orchestrateur.
"""

import asyncio
import json
from pathlib import Path
import sys

# Example pour tester les services individuellement


async def test_semgrep():
    """Test le service Semgrep."""
    from app.services.semgrep_service import SemgrepService

    project_path = "/path/to/your/project"
    result = await SemgrepService.run(project_path)
    print("Semgrep result:")
    print(json.dumps(result, indent=2, default=str))

    # Parser les vulnérabilités
    vulns = SemgrepService.parse_vulnerabilities(result)
    print(f"\nParsed vulnerabilities: {len(vulns)}")
    for vuln in vulns:
        print(f"- {vuln['title']} ({vuln['severity']})")


async def test_pip_audit():
    """Test le service pip-audit."""
    from app.services.pip_audit_service import PipAuditService

    project_path = "/path/to/your/project"
    result = await PipAuditService.run(project_path)
    print("pip-audit result:")
    print(json.dumps(result, indent=2, default=str))

    # Parser les vulnérabilités
    vulns = PipAuditService.parse_vulnerabilities(result)
    print(f"\nParsed vulnerabilities: {len(vulns)}")
    for vuln in vulns:
        print(f"- {vuln['title']} ({vuln['severity']})")


async def test_npm_audit():
    """Test le service npm-audit."""
    from app.services.pip_audit_service import NpmAuditService

    project_path = "/path/to/your/project"
    result = await NpmAuditService.run(project_path)
    print("npm-audit result:")
    print(json.dumps(result, indent=2, default=str))

    # Parser les vulnérabilités
    vulns = NpmAuditService.parse_vulnerabilities(result)
    print(f"\nParsed vulnerabilities: {len(vulns)}")
    for vuln in vulns:
        print(f"- {vuln['title']} ({vuln['severity']})")


async def test_trufflehog():
    """Test le service TruffleHog."""
    from app.services.trufflehog_service import TruffleHogService

    project_path = "/path/to/your/project"
    result = await TruffleHogService.run(project_path)
    print("TruffleHog result:")
    print(json.dumps(result, indent=2, default=str))

    # Parser les vulnérabilités
    vulns = TruffleHogService.parse_vulnerabilities(result)
    print(f"\nParsed vulnerabilities: {len(vulns)}")
    for vuln in vulns:
        print(f"- {vuln['title']} ({vuln['severity']})")


async def test_orchestrator():
    """Test l'orchestrateur complet."""
    from app.services.scan_orchestrator import ScanOrchestrator
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from uuid import uuid4

    # Créer une session de test
    DATABASE_URL = "postgresql://user:password@localhost/securescan"
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        project_path = "/path/to/your/project"
        scan_id = uuid4()

        orchestrator = ScanOrchestrator(db)
        result = await orchestrator.run_scan(scan_id, project_path)

        print("Orchestrator result:")
        print(json.dumps(result, indent=2, default=str))
    finally:
        db.close()


# ========== API ENDPOINT EXAMPLES ==========

"""
1. Créer un scan:
   POST /api/scans
   {
       "user_id": "550e8400-e29b-41d4-a716-446655440000",
       "repository_url": "https://github.com/example/repo.git",
       "upload_path": null
   }
   
   Response:
   {
       "id": "550e8400-e29b-41d4-a716-446655440001",
       "user_id": "550e8400-e29b-41d4-a716-446655440000",
       "status": "pending",
       "created_at": "2026-03-03T10:00:00"
   }

2. Lancer l'analyse:
   POST /api/scans/550e8400-e29b-41d4-a716-446655440001/run
   
   Response (202 Accepted):
   {
       "scan_id": "550e8400-e29b-41d4-a716-446655440001",
       "status": "running",
       "message": "Analysis started in background"
   }

3. Obtenir les détails du scan:
   GET /api/scans/550e8400-e29b-41d4-a716-446655440001
   
   Response:
   {
       "id": "550e8400-e29b-41d4-a716-446655440001",
       "user_id": "550e8400-e29b-41d4-a716-446655440000",
       "status": "completed",
       "started_at": "2026-03-03T10:00:01",
       "finished_at": "2026-03-03T10:05:00",
       "created_at": "2026-03-03T10:00:00"
   }

4. Obtenir les vulnérabilités:
   GET /api/vulnerabilities?scan_id=550e8400-e29b-41d4-a716-446655440001
"""


if __name__ == "__main__":
    # Pour tester, décommenter la fonction souhaitée
    # asyncio.run(test_semgrep())
    # asyncio.run(test_pip_audit())
    # asyncio.run(test_npm_audit())
    # asyncio.run(test_trufflehog())
    # asyncio.run(test_orchestrator())
    print("Les tests sont commentés. Décommenter la fonction souhaitée pour tester.")
