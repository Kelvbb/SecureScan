#!/usr/bin/env python3
"""Test d'intégration complet - Lancer un scan via API et vérifier les résultats."""

import asyncio
import sys
import tempfile
from pathlib import Path
from uuid import uuid4

import requests

sys.path.insert(0, '/Users/djidji/Documents/Projets/IPSSI/SecureScan/backend')

from sqlalchemy.orm import sessionmaker
from app.config import settings
from sqlalchemy import create_engine
from app.models import User, Scan

print("=" * 70)
print("TEST D'INTÉGRATION - SCAN COMPLET VIA API")
print("=" * 70)

# ============================================================================
# ÉTAPE 1: Créer un utilisateur
# ============================================================================
print("\n[ÉTAPE 1] Créer un utilisateur de test")
print("-" * 70)

engine = create_engine(settings.DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

try:
    user = User(
        id=uuid4(),
        email=f"test_integration_{uuid4().hex[:8]}@example.com",
        password_hash="test_password",
        full_name="Integration Test User"
    )
    session.add(user)
    session.commit()
    user_id = str(user.id)
    print(f"✓ Utilisateur créé: {user_id}")
except Exception as e:
    print(f"✗ Erreur: {e}")
    session.close()
    exit(1)

# ============================================================================
# ÉTAPE 2: Créer un projet de test avec du code vulnérable
# ============================================================================
print("\n[ÉTAPE 2] Créer un projet de test")
print("-" * 70)

with tempfile.TemporaryDirectory() as tmpdir:
    test_project = Path(tmpdir)
    
    # Créer des fichiers avec vulnérabilités
    # 1. Code vulnérable Python
    (test_project / "app.py").write_text('''
import subprocess
import os

# Command Injection
user_input = input()
os.system(f"echo {user_input}")

# Hardcoded credentials
DB_PASSWORD = "admin123456"
API_KEY = "sk-1234567890abcdefghijklmn"

# Use of eval
code = input()
result = eval(code)
''')
    
    # 2. Fichier .env avec secrets
    (test_project / ".env").write_text('''
DATABASE_URL=postgresql://admin:password123@localhost/mydb
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLE
API_SECRET=sk-1234567890abcdefghijklmnopqrstuvwxyz
''')
    
    # 3. requirements.txt avec dépendances vulnérables
    (test_project / "requirements.txt").write_text('''
django==2.0.0
requests==2.6.0
flask==0.10.0
''')
    
    print(f"✓ Projet de test créé dans {test_project}")
    print(f"  - app.py (code vulnérable)")
    print(f"  - .env (secrets)")
    print(f"  - requirements.txt (dépendances)")
    
    # ========================================================================
    # ÉTAPE 3: Créer un scan via API
    # ========================================================================
    print("\n[ÉTAPE 3] Créer un scan via API")
    print("-" * 70)
    
    try:
        response = requests.post(
            "http://localhost:8000/api/scans",
            json={
                "user_id": user_id,
                "repository_url": f"file://{test_project}",
                "language": "python"
            },
            timeout=10
        )
        
        if response.status_code != 201:
            print(f"✗ Erreur: {response.status_code}")
            print(f"  Response: {response.text}")
            session.close()
            exit(1)
        
        scan_data = response.json()
        scan_id = scan_data['id']
        print(f"✓ Scan créé: {scan_id}")
        print(f"  Status: {scan_data['status']}")
        
    except requests.exceptions.ConnectionError:
        print("✗ Erreur: Impossible de connecter au serveur API")
        print("  Assurez-vous que le serveur FastAPI est lancé sur http://localhost:8000")
        session.close()
        exit(1)
    except Exception as e:
        print(f"✗ Erreur: {e}")
        session.close()
        exit(1)
    
    # ========================================================================
    # ÉTAPE 4: Lancer le scan
    # ========================================================================
    print("\n[ÉTAPE 4] Lancer le scan complet")
    print("-" * 70)
    
    try:
        response = requests.post(
            f"http://localhost:8000/api/scans/{scan_id}/run",
            timeout=120
        )
        
        if response.status_code != 202:
            print(f"✗ Erreur: {response.status_code}")
            print(f"  Response: {response.text}")
            session.close()
            exit(1)
        
        result = response.json()
        print(f"✓ Scan lancé avec statut {response.status_code}")
        print(f"  Message: {result.get('message')}")
        
    except Exception as e:
        print(f"✗ Erreur: {e}")
        session.close()
        exit(1)
    
    # ========================================================================
    # ÉTAPE 5: Attendre et récupérer les résultats
    # ========================================================================
    print("\n[ÉTAPE 5] Attendre les résultats du scan")
    print("-" * 70)
    
    import time
    max_wait = 30  # Maximum 30 secondes
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        try:
            response = requests.get(
                f"http://localhost:8000/api/scans/{scan_id}",
                timeout=10
            )
            
            if response.status_code == 200:
                scan = response.json()
                status = scan.get('status')
                print(f"  Status: {status}")
                
                if status in ["completed", "failed"]:
                    print(f"✓ Scan terminé avec le statut: {status}")
                    break
                elif status == "running":
                    print(f"  Attente... ({int(time.time() - start_time)}s)")
                    time.sleep(2)
                else:
                    print(f"  Status: {status}")
                    time.sleep(1)
            else:
                print(f"✗ Erreur HTTP {response.status_code}")
                break
                
        except Exception as e:
            print(f"✗ Erreur lors de la récupération: {e}")
            break
        
        time.sleep(1)
    else:
        print(f"⚠ Timeout après {max_wait}s")
    
    # ========================================================================
    # ÉTAPE 6: Vérifier les résultats en base de données
    # ========================================================================
    print("\n[ÉTAPE 6] Vérifier les résultats en base de données")
    print("-" * 70)
    
    # Récupérer les données du scan depuis la DB
    session.expire_all()
    db_scan = session.query(Scan).filter(Scan.id == scan_id).first()
    
    if not db_scan:
        print(f"✗ Scan not found in database")
        session.close()
        exit(1)
    
    print(f"✓ Scan trouvé en DB")
    print(f"  ID: {db_scan.id}")
    print(f"  Status: {db_scan.status}")
    print(f"  Repository: {db_scan.repository_url}")
    print(f"  Language: {db_scan.language}")
    print(f"  Created: {db_scan.created_at}")
    
    # Vérifier les résultats
    from app.models.tool_execution import ToolExecution
    from app.models.vulnerability import Vulnerability
    
    tool_executions = session.query(ToolExecution).filter(
        ToolExecution.scan_id == scan_id
    ).all()
    
    vulnerabilities = session.query(Vulnerability).filter(
        Vulnerability.scan_id == scan_id
    ).all()
    
    print(f"\n  Exécutions d'outils: {len(tool_executions)}")
    for te in tool_executions:
        print(f"    - Tool: {te.id}")
        print(f"      Status: {te.status}")
        if te.raw_output:
            if te.raw_output.get('error'):
                print(f"      Error: {te.raw_output.get('error')}")
            print(f"      Tool Name: {te.raw_output.get('tool', 'N/A')}")
    
    print(f"\n  Vulnérabilités trouvées: {len(vulnerabilities)}")
    for v in vulnerabilities[:5]:  # Show first 5
        print(f"    - {v.title}")
        print(f"      Severity: {v.severity}")
        print(f"      File: {v.file_path}")
    
    # ========================================================================
    # RÉSUMÉ
    # ========================================================================
    print("\n" + "=" * 70)
    print("RÉSUMÉ")
    print("=" * 70)
    
    if tool_executions and vulnerabilities:
        print(f"✓ SUCCÈS complet")
        print(f"  - {len(tool_executions)} outil(s) exécuté(s)")
        print(f"  - {len(vulnerabilities)} vulnérabilité(s) trouvée(s)")
        print(f"\nLes outils CLI sont intégrés et fonctionnent correctement!")
    elif tool_executions:
        print(f"✓ Résultats partiels")
        print(f"  - {len(tool_executions)} outil(s) exécuté(s)")
        print(f"  - {len(vulnerabilities)} vulnérabilité(s) trouvée(s)")
    else:
        print(f"⚠ Aucun outil exécuté")
        print("\nVérifiez:")
        print(f"  1. Les outils CLI sont installés (test_tools_cli.py)")
        print(f"  2. Les permissions de fichiers")
        print(f"  3. La base de données PostgreSQL")

# Nettoyage
session.close()
