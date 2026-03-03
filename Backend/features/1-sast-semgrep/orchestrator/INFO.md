## Tâche 4: Service Orchestrateur

### Fichiers Principaux
- Service: `app/services/scan_orchestrator.py`
- API Implementation: `app/api/routes/scans.py` → endpoint POST /scans/{id}/run

### Fonctionnalités
- Lance TOUS les outils en parallèle avec asyncio
- Gère l'orchestration et error handling
- Crée ToolExecution pour chaque outil
- Crée Vulnerability pour chaque résultat
- Gère les statuts: running → completed/error
- Timestamps: started_at, finished_at

### Architecture
```
ScanOrchestrator
├── run_scan(scan_id, project_path)
│   ├── _run_tool(Semgrep) → asyncio
│   ├── _run_tool(pip-audit) → asyncio
│   ├── _run_tool(npm-audit) → asyncio
│   └── _run_tool(TruffleHog) → asyncio
├── Parse résultats avec chaque service
└── Insère en BD (ToolExecution + Vulnerability)
```

### Tests
- `test_complete_scan.py` → teste l'orchestration complète

### Exécution
```bash
# Voir comment les outils tournent ensemble
/Users/djidji/Documents/Projets/IPSSI/SecureScan/venv/bin/python3 test_complete_scan.py
```
