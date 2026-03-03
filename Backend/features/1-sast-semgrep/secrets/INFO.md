## Tâche 3: Intégration TruffleHog (Détection Secrets)

### Fichiers Principaux
- Service: `app/services/trufflehog_service.py`
- API Implementation: `app/api/routes/scans.py` → endpoint POST /scans/{id}/run

### Fonctionnalités
- Lance TruffleHog via CLI (filesystem mode)
- Détecte secrets hardcodés (API keys, tokens, etc.)
- Parse résultats NDJSON
- Classifie tous les secrets comme CRITICAL
- Maps vers CWE-798 (Hardcoded credentials)

### Tests
- `test_imports.py` → valide l'import
- `test_database.py` → valide la BD
- `test_complete_scan.py` → teste les inserts

### Exécution
```bash
# Tester le service de secrets
/Users/djidji/Documents/Projets/IPSSI/SecureScan/venv/bin/python3 test_imports.py
```
