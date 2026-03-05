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
# Éditer .env avec vos paramètres :
# - DATABASE_URL=postgresql://user:password@localhost/securescan
# - SECRET_KEY=<clé-secrète-générée>
# - GIT_TOKEN=<token-github-optionnel>
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

Pour plus de détails sur l'architecture, les choix techniques, le schéma de base de données et le mapping OWASP, consulter :
- `ARCHITECTURE.md` - Schéma d'architecture
- `CHOIX_TECHNIQUES.md` - Justification des choix techniques
- `BASE_DE_DONNEES.md` - Schéma MCD/MLD
- `MAPPING_OWASP.md` - Mapping vers OWASP Top 10 2025
