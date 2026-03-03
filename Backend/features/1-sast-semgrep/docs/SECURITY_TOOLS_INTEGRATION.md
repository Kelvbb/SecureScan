# Intégration des Outils de Sécurité - SecureScan

## Vue d'ensemble

Cette implémentation intègre 4 outils de sécurité majeurs pour analyser le code source:

| Outil | Type | Description |
|-------|------|-------------|
| **Semgrep** | SAST | Analyse statique pour détecter les patterns vulnérables |
| **pip-audit** | Dépendances | Audit des dépendances Python pour les CVE |
| **npm-audit** | Dépendances | Audit des dépendances Node.js pour les CVE |
| **TruffleHog** | Secrets | Détection des secrets hardcodés (API keys, tokens, etc.) |

## Architecture

### Structure des services

```
app/services/
├── __init__.py
├── semgrep_service.py       # Service SAST Semgrep
├── pip_audit_service.py     # Services d'audit des dépendances
├── trufflehog_service.py    # Service de détection de secrets
├── scan_orchestrator.py     # Exécute tous les outils en parallèle
└── tests.py                 # Exemples de test
```

### Flux d'exécution

```
1. User demande l'analyse: POST /api/scans/{scan_id}/run
2. Endpoint route crée un ScanOrchestrator
3. Orchestrateur lance tous les outils en parallèle avec asyncio
4. Chaque outil:
   - Exécute le CLI et récupère la sortie
   - Parse les résultats (généralement JSON)
   - Retourne les vulnérabilités standardisées
5. Les résultats sont stockés en base de données:
   - ToolExecution: enregistrement de l'outil lancé
   - Vulnerability: chaque vulnérabilité détectée
```

## Installation des dépendances

### 1. Mettre à jour Python packages

```bash
cd /Users/djidji/Documents/Projets/IPSSI/SecureScan/backend
pip install -r requirements.txt
```

### 2. Installer les CLI tools

#### Semgrep
```bash
# Installation via pip
pip install semgrep

# Ou via Homebrew (macOS)
brew install semgrep

# Ou via apt (Linux)
apt-get install semgrep
```

#### pip-audit
```bash
pip install pip-audit
```

#### npm-audit (inclus avec Node.js)
```bash
npm install -g npm  # S'assurer que npm est à jour
```

#### TruffleHog
```bash
pip install truffleHog
```

## Utilisation de l'API

### 1. Créer un scan

```bash
curl -X POST http://localhost:8000/api/scans \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "repository_url": "https://github.com/example/repo.git",
    "upload_path": null
  }'
```

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440001",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "created_at": "2026-03-03T10:00:00",
  ...
}
```

### 2. Lancer l'analyse

```bash
curl -X POST http://localhost:8000/api/scans/550e8400-e29b-41d4-a716-446655440001/run
```

**Response (202 Accepted):**
```json
{
  "scan_id": "550e8400-e29b-41d4-a716-446655440001",
  "status": "running",
  "message": "Analysis started in background"
}
```

### 3. Consulter le statut du scan

```bash
curl http://localhost:8000/api/scans/550e8400-e29b-41d4-a716-446655440001
```

### 4. Obtenir les vulnérabilités détectées

```bash
curl http://localhost:8000/api/vulnerabilities?scan_id=550e8400-e29b-41d4-a716-446655440001
```

## Configuration

Éditer le fichier `.env` pour configurer les outils:

```env
# Security Tools Configuration
SEMGREP_ENABLED=true
NPM_AUDIT_ENABLED=true
TRUFFLEHOG_ENABLED=true
PROJECT_ROOT=/tmp/securescan/projects
```

## Structure des données en base de données

### ToolExecution
Enregistrement de chaque lancement d'outil:

```python
{
  "id": UUID,
  "scan_id": UUID,
  "tool_id": UUID,
  "status": "success|error|skipped",
  "raw_output": {  # Résultat JSON brut complet
    "results": [...],
    "errors": [...]
  },
  "started_at": datetime,
  "finished_at": datetime,
  "created_at": datetime
}
```

### Vulnerability
Chaque vulnérabilité détectée:

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
  "cve_id": "CVE-2024-12345",
  "cwe_id": "CWE-89",
  "tool": "semgrep",
  "status": "open|resolved",
  "created_at": datetime
}
```

## Détails des services

### SemgrepService
- **Commande CLI:** `semgrep --json --output=file <path>`
- **Format sortie:** JSON structuré avec violations et erreurs
- **Mapping sévérité:** ERROR → critical, WARNING → high, INFO → medium

### PipAuditService / NpmAuditService
- **Commande:** `pip-audit --json` / `npm audit --json`
- **Format sortie:** JSON avec liste des vulnérabilités par package
- **Sévérité:** Considérée comme "high" (dépendance vulnérable)

### TruffleHogService
- **Commande:** `truffleHog filesystem <path> --json --only-verified`
- **Format sortie:** NDJSON (une ligne = un secret détecté)
- **Sévérité:** Toujours "critical" (secret exposé)

## Mapping vers l'OWASP Top 10

Les vulnérabilités détectées pueden être mappées automatiquement vers les catégories OWASP:

- **Semgrep results** → A01 (Broken Access Control), A02 (Security Misconfiguration), A04 (Cryptographic Failures)
- **Dépendances vulnérables** → A03 (Software Supply Chain Failures)
- **Secrets détectés** → A02 (Security Misconfiguration), A04 (Cryptographic Failures)

## Limitations et considérations

1. **Performances:**
   - Les analyses longues (gros projets) peuvent timeout
   - Exécution en parallèle avec asyncio pour optimiser le temps
   - Besoin de suffisamment de ressources (CPU, RAM, disque)

2. **Installation des outils:**
   - Les CLI tools doivent être installés sur le système d'exécution
   - Certains outils nécessitent des dépendances supplémentaires

3. **Sécurité:**
   - L'exécution d'outils sur un code non fiable peut être un risque
   - À considérer: sandboxing, isolation des ressources

4. **Faux positifs:**
   - Semgrep peut retourner des faux positifs
   - Vérifier manuellement les résultats avant action

## Prochaines étapes

1. **Intégration OWASP:** Mapping automatique des vulnérabilités vers OWASP Top 10
2. **UI de visualisation:** Afficher les résultats dans un dashboard
3. **Suggestions de fix:** Générer des corrections automatiques
4. **CI/CD integration:** Intégrer à GitHub Actions, GitLab CI, etc.
5. **Historique des scans:** Comparer les résultats au fil du temps
