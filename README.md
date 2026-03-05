# SecureScan

Plateforme web interne d'analyse de qualité et de sécurité du code source, développée pour **CyberSafe Solutions**.

## Contexte

**CyberSafe Solutions** est une startup française spécialisée en cybersécurité pour les PME (150 entreprises clientes, équipe de 35 développeurs). Suite à un audit de l'ANSSI, les problématiques suivantes ont été identifiées :

- Absence d'outil centralisé d'analyse de sécurité du code source
- Vulnérabilités d'injection (SQL, XSS) non détectées avant la mise en production
- Dépendances obsolètes avec des CVE connues dans les projets
- Manque d'intégration de tests de sécurité dans les pipelines CI/CD
- Absence de rapports de sécurité automatisés pour les clients
- Corrections de sécurité manuelles, lentes et sujettes aux erreurs

**SecureScan** orchestre des outils de sécurité open source, agrège leurs résultats, les mappe sur l'**OWASP Top 10 : 2025**, et propose des corrections automatisées.

---

## Fonctionnalités

### A. Soumission de projet

- Saisie d'une **URL de dépôt Git** (GitHub / GitLab) ou **téléversement d'une archive ZIP**
- Clonage automatique du dépôt côté serveur
- Détection automatique du **langage / framework** (PHP, JavaScript, Node.js, Python)

### B. Analyse de sécurité automatisée

| Type            | Outil intégré         | Description                                                 |
| --------------- | --------------------- | ----------------------------------------------------------- |
| **SAST**        | Semgrep               | Analyse statique, détection de patterns vulnérables         |
| **Dépendances** | pip-audit / npm-audit | Scan des CVE sur les dépendances Python et Node.js          |
| **Secrets**     | TruffleHog            | Détection de clés API, tokens et mots de passe dans le code |

Chaque outil est lancé via CLI en parallèle (`asyncio`), sa sortie JSON est parsée et stockée en base.

### C. Mapping OWASP Top 10 : 2025

Chaque vulnérabilité détectée est classée selon le référentiel **OWASP Top 10 : 2025** (couverture ≥ 5 catégories) :

| Catégorie                                     | Exemples de détection                                |
| --------------------------------------------- | ---------------------------------------------------- |
| **A01** Broken Access Control                 | IDOR, CORS mal configuré, escalade de privilèges     |
| **A02** Security Misconfiguration             | Headers manquants, debug actif, config par défaut    |
| **A03** Software Supply Chain Failures        | Dépendances vulnérables, packages malveillants       |
| **A04** Cryptographic Failures                | Mots de passe en clair, algorithmes obsolètes        |
| **A05** Injection                             | SQL injection, XSS, command injection                |
| **A06** Insecure Design                       | Absence de validation, flux non sécurisés            |
| **A07** Authentication Failures               | Brute force, sessions non invalidées                 |
| **A08** Software/Data Integrity Failures      | CI/CD non sécurisé, désérialisation                  |
| **A09** Logging & Alerting Failures           | Logs absents, pas d'alertes sur erreurs              |
| **A10** Mishandling of Exceptional Conditions | Erreurs non gérées, fail-open, stack traces exposées |

### D. Dashboard de visualisation

- **Score de sécurité global** (A / B / C / D / F ou score sur 100)
- **Répartition des vulnérabilités par sévérité** (critique, élevé, moyen, faible)
- **Distribution par catégorie OWASP Top 10** (graphiques)
- **Liste détaillée des findings** : fichier, ligne, description, sévérité, catégorie OWASP
- **Filtres et tri** : par sévérité, par outil source, par catégorie OWASP

### E. Système de correction automatisé

| Vulnérabilité           | Correction suggérée                                   |
| ----------------------- | ----------------------------------------------------- |
| Injection SQL           | Requêtes préparées / paramétrées                      |
| XSS                     | Échappement de sortie (`htmlspecialchars`, DOMPurify) |
| Dépendances vulnérables | Versions patchées suggérées                           |
| Secrets exposés         | Remplacement par variables d'environnement            |
| Mots de passe en clair  | Hachage argon2                                        |

L'utilisateur **valide ou rejette** chaque correction avant son application.

### F. Intégration Git automatisée

- Création automatique d'une **branche de correction** (ex. : `fix/securescan-2026-03-05`)
- Application des corrections validées sur cette branche
- Push automatique via l'**API GitHub / git CLI**
- Génération d'un **rapport de sécurité** (HTML / PDF)

---

## Stack technique

| Couche                 | Technologie                                |
| ---------------------- | ------------------------------------------ |
| **Backend**            | Python 3.11+, FastAPI, SQLAlchemy, asyncio |
| **Frontend**           | React, TypeScript, Vite                    |
| **Base de données**    | PostgreSQL                                 |
| **Outils de sécurité** | Semgrep, pip-audit, npm-audit, TruffleHog  |
| **Git**                | GitHub API / git CLI                       |

---

## Installation

### Prérequis

- Python 3.11+
- Node.js 18+
- PostgreSQL
- Les outils CLI : `semgrep`, `pip-audit`, `truffleHog` (installés via `requirements.txt`)

### Backend

```bash
cd Backend
python3 -m venv venv
source venv/bin/activate          # Windows : venv\Scripts\activate
pip install -r requirements.txt
```

Copier et remplir le fichier d'environnement :

```bash
cp env.example .env
# Éditer .env : DATABASE_URL, SECRET_KEY, etc.
```

Initialiser la base de données :

```bash
psql -U <user> -d <database> -f securescanbdd.sql
```

Lancer le serveur :

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd Frontend
npm install
npm run dev
```

---

## Vérification

Des scripts de vérification sont disponibles dans `Backend/scripts/` :

```bash
cd Backend
source venv/bin/activate          # Linux/macOS
# OU
venv\Scripts\activate             # Windows

python scripts/check_imports.py        # Vérifie les imports Python
python scripts/check_database.py       # Vérifie la connexion et la structure BD
python scripts/check_tools_cli.py      # Vérifie que Semgrep, TruffleHog, etc. sont installés
python scripts/check_complete_scan.py  # Teste un cycle complet insert/retrieve en BD

bash scripts/run_all_checks.sh                                            # Linux/macOS
# OU
bash powershell -ExecutionPolicy Bypass -File scripts\run_all_checks.ps1  # Windows

# Vrais tests pytest
pytest tests/
```

Pour plus de détails sur les outils : [`Backend/SECURITY_TOOLS.md`](Backend/SECURITY_TOOLS.md)

---

## Structure du projet

```
SecureScan/
├── Backend/
│   ├── app/
│   │   ├── api/routes/         # Endpoints FastAPI
│   │   ├── core/               # Auth, classification OWASP
│   │   ├── db/                 # Session et base SQLAlchemy
│   │   ├── models/             # Modèles ORM (Scan, Vulnerability, User…)
│   │   ├── remediation/        # Système de correction automatisé
│   │   ├── schemas/            # Schémas Pydantic
│   │   ├── services/           # Semgrep, pip-audit, TruffleHog, orchestrateur
│   │   ├── git/                # Intégration Git (branches, push)
│   │   └── main.py             # Point d'entrée FastAPI
│   ├── scripts/                # Scripts de vérification manuelle
│   ├── tests/                  # Tests pytest
│   ├── EXPLICATIONS.md         # Rôle de chaque fichier Backend
│   ├── SECURITY_TOOLS.md       # Outils : installation, usage, dépannage
│   ├── securescanbdd.sql       # Schéma PostgreSQL
│   └── requirements.txt
├── Frontend/
│   └── src/
│       ├── api/                # Clients HTTP
│       ├── components/         # Composants React réutilisables
│       ├── views/              # Pages (Dashboard, Login, Register…)
│       └── main.tsx
├── .gitignore
└── README.md
```

---

## Licence

Projet interne CyberSafe Solutions.
