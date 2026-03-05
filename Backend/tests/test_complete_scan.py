"""Script pour tester les inserts dans la base de données."""

import sys

sys.path.insert(0, "/Users/djidji/Documents/Projets/IPSSI/SecureScan/backend")

from uuid import uuid4
from datetime import datetime
from sqlalchemy.orm import sessionmaker
from app.config import settings
from sqlalchemy import create_engine
from app.models import Scan, ToolExecution, Vulnerability, User

print("=" * 70)
print("TEST COMPLET: INSERT & RETRIEVE DE DONNÉES")
print("=" * 70)

engine = create_engine(settings.DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

try:
    # TEST 1: Créer un utilisateur
    print("\n[TEST 1] Créer un utilisateur...")
    user = User(
        id=uuid4(),
        email=f"test_user_{uuid4().hex[:8]}@example.com",
        password_hash="test_hashed_password",
        full_name="Test User for Security Scans",
        role="user",
    )
    session.add(user)
    session.commit()
    print(f"✓ Utilisateur créé: {user.email} (ID: {user.id})")

    # TEST 2: Créer un scan
    print("\n[TEST 2] Créer un scan...")
    scan = Scan(
        id=uuid4(),
        user_id=user.id,
        repository_url="https://github.com/example/vulnerable-app.git",
        status="pending",
        created_at=datetime.utcnow(),
    )
    session.add(scan)
    session.commit()
    print(f"✓ Scan créé (ID: {scan.id})")
    print(f"  - Repository: {scan.repository_url}")
    print(f"  - Status: {scan.status}")

    # TEST 3: Créer une exécution d'outil
    print("\n[TEST 3] Créer une exécution d'outil (Semgrep)...")
    tool_exec = ToolExecution(
        id=uuid4(),
        scan_id=scan.id,
        status="success",
        raw_output={
            "tool": "semgrep",
            "results_count": 5,
            "errors": [],
            "execution_time_ms": 1234,
        },
        started_at=datetime.utcnow(),
        finished_at=datetime.utcnow(),
    )
    session.add(tool_exec)
    session.commit()
    print(f"✓ ToolExecution créée (ID: {tool_exec.id})")
    print(f"  - Status: {tool_exec.status}")
    print(f"  - Raw Output: {tool_exec.raw_output}")

    #  TEST 4: Créer des vulnérabilités
    print("\n[TEST 4] Créer des vulnérabilités...")

    vuln_data = [
        {
            "title": "SQL Injection in user input",
            "description": "User input is directly used in SQL query without parameterization",
            "file_path": "src/app/routes.py",
            "line_start": 42,
            "line_end": 45,
            "severity": "critical",
            "cwe_id": "CWE-89",
            "cve_id": None,
        },
        {
            "title": "Hardcoded API Key",
            "description": "API key found in source code",
            "file_path": ".env.example",
            "line_start": 3,
            "line_end": 3,
            "severity": "critical",
            "cwe_id": "CWE-798",
            "cve_id": None,
        },
        {
            "title": "XXE Vulnerability",
            "description": "XML parsing without disabling external entities",
            "file_path": "src/utils/xml_parser.py",
            "line_start": 18,
            "line_end": 22,
            "severity": "high",
            "cwe_id": "CWE-611",
            "cve_id": None,
        },
    ]

    vulnerabilities = []
    for v_data in vuln_data:
        vuln = Vulnerability(
            id=uuid4(),
            scan_id=scan.id,
            tool_execution_id=tool_exec.id,
            title=v_data["title"],
            description=v_data["description"],
            file_path=v_data["file_path"],
            line_start=v_data["line_start"],
            line_end=v_data["line_end"],
            severity=v_data["severity"],
            cwe_id=v_data["cwe_id"],
            cve_id=v_data["cve_id"],
        )
        vulnerabilities.append(vuln)
        session.add(vuln)

    session.commit()
    print(f"✓ {len(vulnerabilities)} vulnérabilités créées")
    for v in vulnerabilities:
        print(f"  - {v.title} ({v.severity})")

    #  TEST 5: Récup et vérifie les données
    print("\n[TEST 5] Récupérer les données...")

    # Récup le scan
    retrieved_scan = session.query(Scan).filter(Scan.id == scan.id).first()
    print(f"✓ Scan récupéré: {retrieved_scan.repository_url}")

    # Récup les tool_executions du scan
    tool_execs = (
        session.query(ToolExecution).filter(ToolExecution.scan_id == scan.id).all()
    )
    print(f"✓ {len(tool_execs)} ToolExecution(s) trouvée(s)")

    # Récup les vulnérabilités
    vulns = session.query(Vulnerability).filter(Vulnerability.scan_id == scan.id).all()
    print(f"✓ {len(vulns)} Vulnérabilité(s) trouvée(s)")
    for v in vulns:
        print(f"  - {v.title} ({v.severity}) at {v.file_path}:{v.line_start}")

    #  TEST 6: Statistiques globales
    print("\n[TEST 6] Statistiques de la base de données...")
    scans_count = session.query(Scan).count()
    tool_execs_count = session.query(ToolExecution).count()
    vulns_count = session.query(Vulnerability).count()

    print(f"✓ Scans total: {scans_count}")
    print(f"✓ ToolExecutions total: {tool_execs_count}")
    print(f"✓ Vulnerabilities total: {vulns_count}")

    #  CLEANUP
    print("\n[CLEANUP] Suppression des données de test...")
    session.delete(
        scan
    )  # Cascade delete automatique des tool_executions et vulnerabilities
    session.delete(user)
    session.commit()
    print("✓ Données de test supprimées")

except Exception as e:
    print(f"\n✗ ERREUR: {e}")
    import traceback

    traceback.print_exc()
    session.rollback()

finally:
    session.close()

print("\n" + "=" * 70)
print("✓ TOUS LES TESTS RÉUSSIS")
print("=" * 70)
