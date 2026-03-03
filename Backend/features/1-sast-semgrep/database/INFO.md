## Tâche 6: Stockage en Base de Données

### Modèles Principaux
- `app/models/tool_execution.py` → ToolExecution
- `app/models/vulnerability.py` → Vulnerability
- `app/models/scan.py` → Scan

### Structure BD

#### ToolExecution
```
id (UUID)
scan_id (FK → scans)
tool_id (FK → security_tools)
status (success/error/skipped)
raw_output (JSONB) ← Résultats bruts complets
started_at (TIMESTAMP)
finished_at (TIMESTAMP)
created_at (TIMESTAMP)
```

#### Vulnerability
```
id (UUID)
scan_id (FK → scans)
tool_execution_id (FK → tool_executions)
title (TEXT)
description (TEXT)
file_path (TEXT)
line_start (INTEGER)
line_end (INTEGER)
severity (critical/high/medium/low)
confidence (TEXT)
cve_id (VARCHAR 50)
cwe_id (VARCHAR 50)
owasp_category_id (FK → owasp_categories)
status (open/resolved)
created_at (TIMESTAMP)
```

### Tests
- `test_database.py` → valide tables & colonnes
- `test_complete_scan.py` → insère et récupère de vraies données
- `check_inserts.py` → compte rows par table
- `verify_inserts.py` → détails des inserts

### Exécution
```bash
# Vérifier les inserts en BD
./venv/bin/python3 check_inserts.py

# Voir données détaillées
./venv/bin/python3 verify_inserts.py

# Tester structure BD
./venv/bin/python3 test_database.py
```
