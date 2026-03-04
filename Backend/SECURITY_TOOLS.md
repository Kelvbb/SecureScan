# Outils de Sécurité — SecureScan

## Vue d'ensemble

SecureScan orchestre 4 outils de sécurité open source exécutés en parallèle via CLI :

| Outil          | Type                | Sévérité détectée                               |
| -------------- | ------------------- | ----------------------------------------------- |
| **Semgrep**    | SAST                | ERROR → critical, WARNING → high, INFO → medium |
| **pip-audit**  | Dépendances Python  | high (CVE sur package)                          |
| **npm-audit**  | Dépendances Node.js | high (CVE sur package)                          |
| **TruffleHog** | Secrets             | critical (secret exposé)                        |

---

## Installation

### 1. Activer le venv et installer les dépendances

```bash
cd /chemin/vers/SecureScan/Backend
source venv/bin/activate
pip install -r requirements.txt
```

`requirements.txt` inclut déjà `semgrep>=1.45.0`, `pip-audit>=2.6.0` et `truffleHog>=2.0.0`.

### 2. Vérifier l'installation

```bash
semgrep --version
pip-audit --version
trufflehog          # Affiche l'aide
npm -v              # Doit être installé séparément avec Node.js
```

### 3. Installation manuelle si nécessaire

```bash
pip install semgrep          # Ou: brew install semgrep / apt-get install semgrep
pip install pip-audit
pip install truffleHog
npm install -g npm           # npm-audit est inclus avec Node.js
```

### 4. Configuration via `.env`

```env
SEMGREP_ENABLED=true
PIP_AUDIT_ENABLED=true
NPM_AUDIT_ENABLED=true
TRUFFLEHOG_ENABLED=true
PROJECT_ROOT=/tmp/securescan/projects
```

---

## Utilisation

### Via l'API

```bash
# 1. Créer un scan
curl -X POST http://localhost:8000/api/scans \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "repository_url": "https://github.com/example/repo.git",
    "upload_path": null
  }'

# 2. Lancer l'analyse
curl -X POST http://localhost:8000/api/scans/{scan_id}/run
# → 202 Accepted : {"scan_id": "...", "status": "running", "message": "Analysis started in background"}

# 3. Consulter le statut
curl http://localhost:8000/api/scans/{scan_id}

# 4. Récupérer les vulnérabilités
curl http://localhost:8000/api/vulnerabilities?scan_id={scan_id}
```

### Via les scripts de vérification

```bash
# Vérifier que les outils CLI sont installés et fonctionnels
python3 scripts/check_tools_cli.py

# Tester Semgrep seul sur un projet temporaire
python3 scripts/check_semgrep_quick.py

# Lancer toutes les vérifications d'un coup
bash scripts/run_all_checks.sh
```

> ⚠ Toujours lancer les tests via `pytest` et non `python tests/...` — 
> `conftest.py` n'est chargé que par pytest et est indispensable pour résoudre les imports `app.*`.

### Tests CLI manuels

```bash
# Semgrep
echo 'x = eval(input())' > /tmp/test.py
semgrep --json --no-git-ignore /tmp/

# TruffleHog (nécessite un repo git)
mkdir /tmp/test_th && cd /tmp/test_th
git init && echo 'API_KEY=sk-1234567890abcdefghijklmnop' > .env
git add . && git commit -m "initial"
trufflehog --json --regex .

# pip-audit
echo 'django==2.0' > /tmp/requirements.txt
pip-audit -r /tmp/requirements.txt --desc
```

---

## Architecture

### Structure des services

```
app/services/
├── semgrep_service.py       # Service SAST Semgrep
├── pip_audit_service.py     # Audit dépendances Python et Node.js
├── trufflehog_service.py    # Détection de secrets
└── scan_orchestrator.py     # Lance tous les outils en parallèle (asyncio)
```

### Flux d'exécution

```
POST /api/scans/{scan_id}/run
    ↓
ScanOrchestrator.run_scan()
    ↓
asyncio.gather() — exécution parallèle :
    ├─ SemgrepService.run()
    ├─ PipAuditService.run()
    ├─ NpmAuditService.run()
    └─ TruffleHogService.run()
    ↓
Chaque service :
    1. Exécute le CLI, capture stdout JSON
    2. Parse et normalise les résultats
    3. Insère en DB : ToolExecution + Vulnerability(ies)
```

### Format de retour standard (chaque service)

```json
{
  "status": "success|error|skipped",
  "tool": "semgrep|pip-audit|npm-audit|truffleHog",
  "results": [], // Semgrep
  "secrets": [], // TruffleHog
  "dependencies": [], // pip-audit / npm-audit
  "error": "..." // si status == "error"
}
```

---

## Structure en base de données

### ToolExecution

```python
{
  "id": UUID,
  "scan_id": UUID,
  "status": "success|error|skipped",
  "raw_output": { "results": [...], "errors": [...] },  # JSONB
  "started_at": datetime,
  "finished_at": datetime
}
```

### Vulnerability

```python
{
  "id": UUID,
  "scan_id": UUID,
  "tool_execution_id": UUID,
  "title": "SQL Injection found",
  "description": "...",
  "file_path": "src/app.py",
  "line_start": 42,
  "line_end": 45,
  "severity": "critical|high|medium|low",
  "cve_id": "CVE-2024-12345",  # dépendances uniquement
  "cwe_id": "CWE-89",
  "tool": "semgrep",
  "status": "open|resolved"
}
```

---

## Mapping OWASP Top 10

| Outil                 | Catégories OWASP                                                                                    |
| --------------------- | --------------------------------------------------------------------------------------------------- |
| Semgrep               | A01 Broken Access Control, A02 Security Misconfiguration, A04 Cryptographic Failures, A05 Injection |
| pip-audit / npm-audit | A03 Software Supply Chain Failures                                                                  |
| TruffleHog            | A02 Security Misconfiguration, A04 Cryptographic Failures                                           |

---

## Dépannage

**`Command not found: semgrep`**
→ Vérifier que le venv est activé : `source venv/bin/activate`

**`TruffleHog: error: git_url required`**
→ TruffleHog 2.x nécessite un repo git. Le service l'initialise automatiquement si besoin.

**`No module named 'pydantic_settings'`**
→ `pip install --upgrade -r requirements.txt`

**`JSON decode error`**
→ Vérifier les droits de lecture sur le chemin du projet : `chmod -R 755 /chemin/du/projet`

**Logs serveur**
→ `/tmp/server.log` lors d'un lancement via `run_all_checks.sh`

---

## Limitations

- **Semgrep** peut être lent sur les gros projets (>10k fichiers) et générer des faux positifs
- **TruffleHog** fonctionne mieux sur des repos git (le service gère l'init automatiquement)
- **npm-audit** nécessite Node.js installé séparément
- L'exécution sur du code non fiable est un risque — envisager un sandboxing pour la production
- Les secrets détectés par TruffleHog ne sont **pas** stockés en clair en DB
