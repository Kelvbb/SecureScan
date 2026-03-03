## Scripts Disponibles

### run_all_tests.sh
Exécute automatiquement TOUS les tests unitaires et d'intégration
```bash
bash run_all_tests.sh
```

**Qu'est-ce que ce script fait:**
1. ✓ Teste imports (pas d'erreur circulaire)
2. ✓ Teste structure BD (8 tables)
3. ✓ Lance LE VRAI SCAN avec tous les outils
4. ✓ Vérifie inserts en BD

**Sortie:**
- ✓ Pas d'erreur signifie tout fonctionne
- ✗ Une erreur signifie un problème

### Utilisation
```bash
cd /Users/djidji/Documents/Projets/IPSSI/SecureScan/backend
bash run_all_tests.sh
```

### Alternatives Manuelles
Si tu veux tester chaque partie séparément:
```bash
# 1. Imports only
./venv/bin/python3 test_imports.py

# 2. Database only
./venv/bin/python3 test_database.py

# 3. Scan complet
./venv/bin/python3 test_complete_scan.py

# 4. API (avec uvicorn running)
./venv/bin/python3 -m uvicorn app.main:app --port 8000  # Terminal 1
./venv/bin/python3 test_api_flow.py                     # Terminal 2

# 5. Vérification données
./venv/bin/python3 check_inserts.py
./venv/bin/python3 verify_inserts.py
```
