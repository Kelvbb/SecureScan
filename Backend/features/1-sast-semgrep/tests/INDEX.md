## Tests pour la Feature "1-sast-semgrep"

### Tests Disponibles

#### 1. test_imports.py
Valide que tous les services importent sans erreur circulaire
```bash
./venv/bin/python3 test_imports.py
```
✓ Import SemgrepService
✓ Import PipAuditService
✓ Import NpmAuditService
✓ Import TruffleHogService
✓ Import ScanOrchestrator

#### 2. test_database.py
Valide l'existence des tables et colonnes en BD
```bash
./venv/bin/python3 test_database.py
```
✓ Vérifie 8 tables
✓ Vérifie UUID primary keys
✓ Vérifie Foreign Keys

#### 3. test_complete_scan.py
Lance UN VRAI SCAN complet sur un répertoire test
```bash
./venv/bin/python3 test_complete_scan.py
```
✓ Crée Scan
✓ Lance Semgrep, pip-audit, npm-audit, TruffleHog en parallèle
✓ Insère résultats en BD
✓ Compte 2+ vulnerabilities trouvées

#### 4. test_api_flow.py
Teste l'endpoint API POST /scans/{id}/run (nécessite uvicorn running)
```bash
# Terminal 1:
cd backend
./venv/bin/python3 -m uvicorn app.main:app --port 8000

# Terminal 2:
./venv/bin/python3 test_api_flow.py
```
✓ POST /api/scans/{id}/run → 202 Accepted
✓ Background task exécutée
✓ Données insérées en BD

### Utilitaires de Vérification

#### check_inserts.py
Affiche le nombre de rows par table après un scan
```bash
./venv/bin/python3 check_inserts.py
```

#### verify_inserts.py
Affiche détails complets des inserts (colonnes sélectionnées)
```bash
./venv/bin/python3 verify_inserts.py
```

### Exécuter TOUS les Tests

```bash
# Test unitaires (sans API)
./venv/bin/python3 test_imports.py && \
./venv/bin/python3 test_database.py && \
./venv/bin/python3 test_complete_scan.py

# Test API (besoin d'une API running)
# Terminal 1: ./venv/bin/python3 -m uvicorn app.main:app --port 8000
# Terminal 2: ./venv/bin/python3 test_api_flow.py
```

Ou utiliser le script:
```bash
bash run_all_tests.sh
```
