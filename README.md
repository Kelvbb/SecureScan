# SecureScan

Plateforme web d'analyse de sécurité du code source qui orchestre des outils de sécurité open source (Semgrep, Bandit, ESLint, pip-audit, npm-audit, TruffleHog), agrège leurs résultats, les mappe sur l'**OWASP Top 10 2025**, et propose des corrections automatisées.

## Stack technique

| Couche                 | Technologie                                |
| ---------------------- | ------------------------------------------ |
| **Backend**            | Python 3.11+, FastAPI, SQLAlchemy, asyncio |
| **Frontend**           | React, TypeScript, Vite                    |
| **Base de données**    | PostgreSQL                                 |
| **Outils de sécurité** | Semgrep, Bandit, ESLint, pip-audit, npm-audit, TruffleHog |
| **Git**                | GitHub API / git CLI                       |

## Installation

### Prérequis

- **Python 3.11+**
- **Node.js 18+**
- **PostgreSQL 14+**
- **Git** (pour le clonage des dépôts)

### Installation complète

#### 1. Cloner le dépôt

```bash
git clone https://github.com/Kelvbb/SecureScan.git
cd SecureScan
```

#### 2. Configuration de la base de données

Créer une base de données PostgreSQL :

```bash
createdb securescan
# OU
psql -U postgres -c "CREATE DATABASE securescan;"
```

#### 3. Backend

```bash
cd Backend

# Créer l'environnement virtuel
python3 -m venv venv
source venv/bin/activate          # Linux/macOS
# OU
venv\Scripts\activate              # Windows

# Installer les dépendances
pip install -r requirements.txt

# Configurer les variables d'environnement
cp env.example .env
```

Initialiser la base de données :

```bash
psql -U <user> -d securescan -f securescanbdd.sql
```

Lancer le serveur backend :

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Le serveur sera accessible sur `http://localhost:8000`  
La documentation API (Swagger) sera disponible sur `http://localhost:8000/docs`

#### 4. Frontend

Dans un nouveau terminal :

```bash
cd Frontend
npm install
npm run dev
```

Le frontend sera accessible sur `http://localhost:5173`

## Lancement de l'application

1. **Démarrer le backend** (terminal 1) :
   ```bash
   cd Backend
   source venv/bin/activate  # Linux/macOS
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

2. **Démarrer le frontend** (terminal 2) :
   ```bash
   cd Frontend
   npm run dev
   ```

3. **Accéder à l'application** :
   - Frontend : http://localhost:5173
   - API Backend : http://localhost:8000
   - Documentation API : http://localhost:8000/docs

## Documentation technique

## Schéma d'architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                       FRONTEND (React)                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐            │
│  │  Dashboard   │  │  Scan Detail │  │   Results    │            │
│  └──────────────┘  └──────────────┘  └──────────────┘            │
│         │                  │                  │                  │
│         └──────────────────┼──────────────────┘                  │
│                            │                                     │
│                    ┌───────▼───────┐                             │
│                    │  API Client   │                             │
│                    └───────┬───────┘                             │
└────────────────────────────┼─────────────────────────────────────┘
                             │ HTTP/REST
┌────────────────────────────▼─────────────────────────────────────┐
│                    BACKEND (FastAPI)                             │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │              API Routes (FastAPI)                        │    │
│  │  - /api/auth/*      (authentification)                   │    │
│  │  - /api/scans/*     (gestion des scans)                  │    │
│  │  - /api/scans/{id}/results  (résultats)                  │    │
│  │  - /api/scans/{id}/fixes    (corrections)                │    │
│  └──────────────────────────────────────────────────────────┘    │
│                            │                                     │
│         ┌──────────────────┼──────────────────┐                  │
│         │                  │                  │                  │
│  ┌──────▼──────┐   ┌───────▼──────┐   ┌───────▼─────┐            │
│  │  Services   │   │   Models     │   │  Core       │            │
│  │  - Scan     │   │   (ORM)      │   │  - Auth     │            │
│  │  - Git      │   │   - User     │   │  - OWASP    │            │
│  │  - Remed.   │   │   - Scan     │   │  - Score    │            │
│  └──────┬──────┘   │   - Vuln     │   └─────────────┘            │
│         │          └───────┬──────┘                              │
│         │                  │                                     │
│         └──────────────────┼──────────────────┐                  │
│                            │                  │                  │
│                    ┌───────▼───────┐   ┌──────▼──────┐           │ 
│                    │   PostgreSQL  │   │ Scan        │           │
│                    │   Database    │   │ Orchestrator│           │
│                    └───────────────┘   └──────┬──────┘           │
└────────────────────────────────────────────────┼─────────────────┘
                                                 │
┌────────────────────────────────────────────────▼─────────────────┐
│                  OUTILS DE SÉCURITÉ (CLI)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐            │
│  │   Semgrep    │  │  pip-audit   │  │ TruffleHog   │            │
│  │   (SAST)     │  │  (deps)      │  │  (secrets)   │            │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘            │
│         │                 │                 │                    │
│  ┌──────▼───────┐  ┌──────▼────────┐  ┌─────▼────────┐           │ 
│  │   Bandit     │  │  npm-audit    │  │   ESLint     │           │
│  │  (Python)    │  │  (deps)       │  │  (JS/TS)     │           │
│  └──────────────┘  └───────────────┘  └──────────────┘           │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │         Projet cloné/téléversé (fichiers sources)        │    │
│  └──────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────┘
```

## Stratégie de mapping

Le mapping se fait en **2 étapes** :

1. **Mapping par règle** (prioritaire) : Analyse du `rule_id` ou `check_id` de l'outil
2. **Mapping par sévérité** (fallback) : Si aucun mapping spécifique, utilisation de la sévérité

## Tableau de mapping

| Mots-clés détectés | Catégorie OWASP | Exemples |
|-------------------|-----------------|----------|
| `sql`, `injection`, `xss` | **A05 - Injection** | SQL injection, XSS, command injection |
| `secret`, `password`, `key`, `trufflehog` | **A04 - Cryptographic Failures** | Secrets exposés, mots de passe en clair |
| `dependency`, `audit`, `cve`, `pip-audit`, `npm-audit` | **A03 - Software Supply Chain Failures** | Dépendances vulnérables (CVE) |
| `access`, `idor`, `cors` | **A01 - Broken Access Control** | IDOR, CORS mal configuré |
| `auth`, `session`, `login` | **A07 - Authentication Failures** | Brute force, sessions non invalidées |
| `config`, `header`, `debug` | **A02 - Security Misconfiguration** | Headers manquants, debug actif |
| `deserial`, `integrity` | **A08 - Software/Data Integrity Failures** | Désérialisation non sécurisée |
| `log`, `alert` | **A09 - Logging & Alerting Failures** | Logs absents, pas d'alertes |
| `exception`, `error`, `stack` | **A10 - Mishandling of Exceptional Conditions** | Erreurs non gérées, stack traces |

## Mapping par sévérité (fallback)

Si aucun mot-clé n'est trouvé dans le `rule_id`, le système utilise la sévérité :

- **Critical / High** → `A05` (Injection)
- **Medium** → `A02` (Security Misconfiguration)
- **Low** → `A09` (Logging & Alerting Failures)
- **Par défaut** → `A06` (Insecure Design)
