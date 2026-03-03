## Tâche 1: Intégration de Semgrep (SAST)

### Fichiers Principaux
- Service: `app/services/semgrep_service.py`
- API Implementation: `app/api/routes/scans.py` → endpoint POST /scans/{id}/run

### Fonctionnalités
- Lance Semgrep via CLI
- Parse les résultats JSON
- Détecte patterns vulnérables (SQL injection, XSS, etc.)
- Mappe les sévérités (ERROR→critical, WARNING→high, INFO→medium)

### Tests
- `test_imports.py` → valide l'import du service
- `test_database.py` → valide la BD des résultats
- `test_complete_scan.py` → teste les inserts

### Exécution
```bash
# Lancer Semgrep sur un projet
/Users/djidji/Documents/Projets/IPSSI/SecureScan/venv/bin/python3 test_imports.py
```
