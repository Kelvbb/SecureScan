# Guide d'Installation et de Test des Outils CLI

## Vue d'ensemble

La plateforme SecureScan intègre quatre outils de sécurité qui s'exécutent via CLI (Command Line Interface) et produisent des résultats en JSON:

1. **Semgrep** - Analyse SAST (Static Application Security Testing)
2. **pip-audit** - Audit des dépendances Python
3. **npm-audit** - Audit des dépendances Node.js
4. **TruffleHog** - Détection de secrets dans le code

## Installation des Dépendances

### Étape 1: Activer le venv

```bash
cd /chemin/vers/SecureScan/backend
source venv/bin/activate
```

### Étape 2: Installer les requirements

```bash
pip install -r requirements.txt
```

Cela installe automatiquement tous les outils, y compris:
- `semgrep>=1.45.0`
- `pip-audit>=2.6.0`
- `truffleHog>=2.0.0`

### Étape 3: Vérifier l'installation

```bash
semgrep --version
trufflehog                # Affiche l'aide
pip-audit --version       # Pour vérifier pip-audit
npm -v                    # Pour npm (généralement déjà installé)
```

## Test des Outils

### Test automatisé complet

Pour tester tous les outils à la fois:

```bash
cd /Users/djidji/Documents/Projets/IPSSI/SecureScan/backend
python3 test_tools_cli.py
```

Ce script va:
1. ✓ Vérifier que tous les outils sont installés
2. ✓ Tester Semgrep sur du code vulnérable
3. ✓ Tester TruffleHog sur un projet avec secrets
4. ✓ Générer un rapport

**Résultat attendu:**
```
═══════════════════════════════════════════
RÉSUMÉ
═══════════════════════════════════════════
semgrep: ✓ Installed
trufflehog: ✓ Installed

✓ Tous les outils sont installés et fonctionnent!
```

### Test manuel par outil

#### Semgrep

```bash
# Créer un dossier de test
mkdir /tmp/test_semgrep
echo 'x = eval(input())' > /tmp/test_semgrep/test.py

# Lancer semgrep
semgrep --json --no-git-ignore /tmp/test_semgrep
```

**Résultat attendu:** JSON avec au moins 1 issue détectée

#### TruffleHog

```bash
# Créer un dossier de test avec secrets
mkdir /tmp/test_truffleHog
cd /tmp/test_truffleHog

# Initialiser un repo git
git init
echo 'API_KEY=sk-1234567890abcdefghijklmnop' > .env
git add .
git commit -m "initial"

# Lancer trufflehog
trufflehog --json --regex .
```

**Résultat attendu:** JSON avec au moins 1 secret détecté (high entropy ou pattern matching)

#### pip-audit

```bash
# Créer un project avec vulnérabilité
mkdir /tmp/test_pip_audit
cd /tmp/test_pip_audit
echo 'django==2.0' > requirements.txt

# Lancer pip-audit
pip-audit -r requirements.txt --desc
```

**Résultat attendu:** JSON ou rapport avec vulnérabilités trouvées

## Structure d'Exécution

### Flux de Scan Complet

```
POST /api/scans/{scan_id}/run
    ↓
ScanOrchestrator.run_scan()
    ↓
Exécution parallèle (asyncio.gather):
    ├─ SemgrepService.run()
    ├─ PipAuditService.run()
    ├─ NpmAuditService.run()
    └─ TruffleHogService.run()
    ↓
Chaque service:
    1. Lance la CLI de l'outil
    2. Capture stdout (JSON)
    3. Parse les résultats
    4. Sauvegarde dans la base de données
```

### Format JSON Standard

Chaque outil retourne un dictionnaire structuré:

```json
{
  "status": "success|error|skipped",
  "tool": "semgrep|pip-audit|npm-audit|truffleHog",
  "results": [...],           // Pour Semgrep
  "secrets": [...],           // Pour TruffleHog
  "dependencies": [...],      // Pour pip-audit/npm-audit
  "raw_output": {...},        // Réponse complète de l'outil
  "error": "message"          // Si status == "error"
}
```

## Guide de Dépannage

### ❌ "Command not found: semgrep"

**Solution:** Vérifier que le venv est activé
```bash
which semgrep    # Doit afficher le chemin du venv
source venv/bin/activate
pip install semgrep>=1.45.0
```

### ❌ "TruffleHog: error: the following arguments are required: git_url"

**Solution:** La version installée (2.x) a besoin d'un repo git. Le service le gère automatiquement en initialisant un repo local s'il n'existe pas.

### ❌ "No module named 'pydantic_settings'"

**Solution:** Réinstaller les dépendances
```bash
pip install --upgrade -r requirements.txt
```

### ❌ "JSON decode error"

**Solution:** Assurez-vous que l'outil a des droits de lecture/écriture sur le chemin du projet
```bash
chmod -R 755 /chemin/du/projet
```

## Tests d'Intégration

### Test 1: Import des services

```bash
python3 test_imports.py
```

Vérifie que tous les services Python s'importent correctement.

### Test 2: Connexion à la base de données

```bash
python3 test_database.py
```

Vérifie que la DB PostgreSQL est accessible.

### Test 3: Scan complet

```bash
python3 test_complete_scan.py
```

Lance un scan sur un projet test et vérifie l'insertion en DB.

### Test 4+: Tests API

```bash
python3 -m uvicorn app.main:app --port 8000 &
python3 test_api_flow.py
pkill -f uvicorn
```

Teste les endpoints API `/api/scans/*`.

## Configuration des Outils

Les outils peuvent être activés/désactivés via les variables d'environnement:

```bash
# Dans .env
SEMGREP_ENABLED=true
PIP_AUDIT_ENABLED=true
NPM_AUDIT_ENABLED=true
TRUFFLEHOG_ENABLED=true
```

Par défaut, tous les outils sont activés.

## Notes Importantes

### Performance
- **Semgrep** : Peut être lent sur les gros projets (>10k fichiers)
- **TruffleHog** : Plus rapide mais peut générer des faux positifs
- **pip-audit** : Très rapide, dépend de la taille du requirements.txt

### Sécurité
- Les secrets détectés par TruffleHog ne sont PAS stockés complets dans la DB
- Les chemins des fichiers vulnérables sont sanitizés
- Toute sortie CLI est capturée et loggée pour audit

### Limitation Connues
- TruffleHog 2.x fonctionne mieux sur des repos git (le service initialise un repo local si nécessaire)
- npm-audit nécessite Node.js et npm d'être installés
- Semgrep nécessite au minimum Python 3.9

## Contacts et Support

Pour signaler des problèmes:
1. Vérifier d'abord que tous les outils sont correctement installés
2. Générer un rapport de diagnostic avec `test_tools_cli.py`
3. Consulter les logs du serveur dans `/tmp/server.log`
4. Ouvrir un issue avec le rapport de diagnostic

---

**Dernière mise à jour:** 3 mars 2026
**API Version:** 1.0
