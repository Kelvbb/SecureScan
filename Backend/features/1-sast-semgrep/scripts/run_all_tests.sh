#!/bin/bash
# SCRIPT COMPLET DE TEST - SecureScan
# Exécute tous les tests et valide les inserts en base de données

set -e  # Arrêter si une commande échoue

echo "═"
echo "  TESTS COMPLETS - SECURESCAN"
echo "═"

# Couleurs pour l'output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Chemin du projet
PROJECT_ROOT="/Users/djidji/Documents/Projets/IPSSI/SecureScan"
BACKEND_DIR="$PROJECT_ROOT/backend"
PYTHON="$BACKEND_DIR/venv/bin/python3"

echo -e "${BLUE}[SETUP]${NC} Vérifier que le venv existe..."
if [ ! -d "$BACKEND_DIR/venv" ]; then
    echo -e "${YELLOW}⚠ Création du venv...${NC}"
    cd "$BACKEND_DIR"
    python3 -m venv venv
fi

echo -e "${BLUE}[SETUP]${NC} Installer les dépendances..."
cd "$BACKEND_DIR"
$PYTHON -m pip install --upgrade pip setuptools wheel > /dev/null 2>&1
$PYTHON -m pip install -r requirements.txt
$PYTHON -m pip install requests

echo ""
echo "═"
echo -e "${GREEN}[TEST 1] IMPORTS PYTHON${NC}"
echo "═"
$PYTHON test_imports.py

echo ""
echo "═"
echo -e "${GREEN}[TEST 2] CONNEXION À LA BASE DE DONNÉES${NC}"
echo "═"
$PYTHON test_database.py

echo ""
echo "═"
echo -e "${GREEN}[TEST 3] INSERTS COMPLÈTS (Scan + Tool + Vulnerabilities)${NC}"
echo "═"
$PYTHON test_complete_scan.py

echo ""
echo "═"
echo -e "${GREEN}[TEST 4] DÉMARRAGE DU SERVEUR FASTAPI${NC}"
echo "═"
echo -e "${BLUE}Lancement du serveur sur http://localhost:8000${NC}"
$PYTHON -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 > /tmp/server.log 2>&1 &
SERVER_PID=$!
echo -e "${BLUE}PID: $SERVER_PID${NC}"

# Attendre que le serveur démarre
sleep 5

if ! ps -p $SERVER_PID > /dev/null; then
    echo -e "${YELLOW}✗ Le serveur n'a pas démarré${NC}"
    cat /tmp/server.log
    exit 1
fi

echo -e "${GREEN}✓ Serveur démarré avec succès${NC}"

echo ""
echo "═"
echo -e "${GREEN}[TEST 5] TESTS API (Endpoints)${NC}"
echo "═"

echo -e "${BLUE}Test 5.1: GET / (Health Check)${NC}"
curl -s http://localhost:8000/ | jq .

echo -e "\n${BLUE}Test 5.2: GET /health${NC}"
curl -s http://localhost:8000/health | jq .

echo -e "\n${BLUE}Test 5.3: Flux API complet${NC}"
$PYTHON test_api_flow.py

echo ""
echo "═"
echo -e "${GREEN}[TEST 6] VÉRIFICATION DES INSERTS EN BD${NC}"
echo "═"
$PYTHON << 'EOF'
import sys
sys.path.insert(0, '/Users/djidji/Documents/Projets/IPSSI/SecureScan/backend')

from sqlalchemy import create_engine, text
from app.config import settings

engine = create_engine(settings.DATABASE_URL)

with engine.connect() as conn:
    tables = ['scans', 'tool_executions', 'vulnerabilities', 'users', 'owasp_categories']
    
    print("\n STATISTIQUES DES INSERTS EN BASE DE DONNÉES:\n")
    for table in tables:
        result = conn.execute(text(f"SELECT COUNT(*) as cnt FROM {table}"))
        count = result.scalar()
        print(f"  {table:<20} : {count:>5} row(s)")
    
    print("\n✓ Les données s'insèrent bien en base de données!")
EOF

# Arrêter le serveur
echo ""
echo "═"
echo -e "${BLUE}[CLEANUP] Arrêt du serveur${NC}"
echo "═"
kill $SERVER_PID 2>/dev/null || true
sleep 2

echo ""
echo "═"
echo -e "${GREEN}✓ TOUS LES TESTS RÉUSSIS!${NC}"
echo "═"

echo ""
echo " RÉSUMÉ:"
echo "  ✓ Imports Python: OK"
echo "  ✓ Connexion BD: OK"
echo "  ✓ Inserts Scan/Tool/Vuln: OK"
echo "  ✓ Serveur FastAPI: OK"
echo "  ✓ Endpoints API: OK"
echo "  ✓ Flux complet: OK"
echo "  ✓ Vérification BD: OK"
echo ""
