#!/usr/bin/env python3
"""Script pour tester les endpoints API."""

import os
import sys

# (placé en haut avant tout import applicatif)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
import json
from uuid import uuid4
from sqlalchemy.orm import sessionmaker
from app.config import settings
from sqlalchemy import create_engine
from app.models import User

BASE_URL = "http://localhost:8000"

print("=" * 70)
print("TEST API: FLUX COMPLET DE SCAN")
print("=" * 70)

# Créer un utilisateur (via la base de test)
print("\n[1] Créer un utilisateur de test en base...")

engine = create_engine(settings.DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

user = User(
    id=uuid4(),
    email=f"api_test_{uuid4().hex[:8]}@example.com",
    password_hash="test_password",
    full_name="API Test User",
)
session.add(user)
session.commit()

user_id = str(user.id)
print(f"✓ Utilisateur créé: {user_id}")
session.close()

# Créer un scan via l'API
print("\n[2] Créer un scan via POST /api/scans...")

payload = {
    "user_id": user_id,
    "repository_url": "https://github.com/test/vulnerable-repo.git",
    "upload_path": None,
}

response = requests.post(f"{BASE_URL}/api/scans", json=payload)
print(f"Status: {response.status_code}")

if response.status_code == 201:
    scan_data = response.json()
    scan_id = scan_data["id"]
    print(f"✓ Scan créé avec succès")
    print(f"  ID: {scan_id}")
    print(f"  Status: {scan_data['status']}")
    print(f"  Repository: {scan_data['repository_url']}")
else:
    print(f"✗ Erreur: {response.status_code}")
    print(response.text)
    exit(1)

# Récupération du scan
print(f"\n[3] Récupérer le scan via GET /api/scans/{scan_id}...")

response = requests.get(f"{BASE_URL}/api/scans/{scan_id}")
print(f"Status: {response.status_code}")

if response.status_code == 200:
    scan = response.json()
    print(f"✓ Scan récupéré")
    print(f"  Status: {scan['status']}")
    print(f"  Created: {scan['created_at']}")
else:
    print(f"✗ Erreur: {response.status_code}")
    print(response.text)

# Lancer l'analyse via POST /api/scans/{id}/run
print(f"\n[4] Lancer l'analyse via POST /api/scans/{scan_id}/run...")

response = requests.post(f"{BASE_URL}/api/scans/{scan_id}/run")
print(f"Status: {response.status_code}")

if response.status_code == 202:
    result = response.json()
    print(f"✓ Analyse lancée")
    print(f"  Status: {result['status']}")
    print(f"  Message: {result['message']}")
else:
    print(f"✗ Erreur: {response.status_code}")
    print(response.text)

# Lister les scans
print(f"\n[5] Lister les scans via GET /api/scans...")

response = requests.get(f"{BASE_URL}/api/scans", params={"user_id": user_id})
print(f"Status: {response.status_code}")

if response.status_code == 200:
    scans = response.json()
    print(f"✓ Scans trouvés: {len(scans)}")
    for s in scans:
        print(f"  - {s['id']}: {s['status']}")

print("\n" + "=" * 70)
print("✓ TESTS API TERMINÉS")
print("=" * 70)
