## Tâche 5: Endpoint API POST /scans/{scan_id}/run

### Fichiers Principaux
- Route: `app/api/routes/scans.py` → fonction `run_scan()`
- Orchestre tout le workflow

### Fonctionnalités
- POST /api/scans/{scan_id}/run
- Lance l'analyse en background (BackgroundTasks)
- Retourne 202 Accepted immédiatement
- Exécute ScanOrchestrator().run_scan()
- Stoppe après résultat (completed/error)

### HTTP Response
```
Status: 202 Accepted
Body: {
  "scan_id": "uuid",
  "status": "running",
  "message": "Analysis started in background"
}
```

### Tests
- `test_api_flow.py` → teste cet endpoint spécifiquement

### Exécution
```bash
# Tester l'endpoint API complet
cd backend
./venv/bin/python3 -m uvicorn app.main:app --port 8000
# Dans une autre terminal:
./venv/bin/python3 test_api_flow.py
```
