## Tâche 2: Intégration npm-audit & pip-audit

### Fichiers Principaux
- Service: `app/services/pip_audit_service.py` (contient PipAuditService + NpmAuditService)
- API Implementation: `app/api/routes/scans.py` → endpoint POST /scans/{id}/run

### Fonctionnalités
- pip-audit: Audit des dépendances Python
- npm-audit: Audit des dépendances Node.js
- Parse les résultats JSON
- Détecte les CVE dans les dépendances
- Mappe les sévérités

### Tests
- `test_imports.py` → valide les imports
- `test_database.py` → valide la BD
- `test_complete_scan.py` → teste les inserts

### Exécution
```bash
# Tester les services d'audit
/Users/djidji/Documents/Projets/IPSSI/SecureScan/venv/bin/python3 test_imports.py
```
