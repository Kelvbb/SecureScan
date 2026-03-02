# Rôle de chaque fichier — SecureScan Backend

Une phrase par fichier pour comprendre la structure du projet.

---

## Racine Backend

| Fichier | Rôle |
|---------|------|
| **env.example** | Exemple de variables d'environnement à copier en `.env` (DATABASE_URL, CORS, etc.). |
| **requirements.txt** | Liste des dépendances Python (FastAPI, SQLAlchemy, psycopg2, pydantic, etc.). |
| **securescanbdd.sql** | Schéma SQL PostgreSQL (tables users, scans, vulnerabilities, owasp_categories, etc.). |

---

## `app/`

| Fichier | Rôle |
|---------|------|
| **app/__init__.py** | Marque le package Python `app` (pas de logique). |
| **app/main.py** | Point d'entrée FastAPI : création de l'app, CORS, montage des routers, route racine. |
| **app/config.py** | Chargement de la configuration depuis l'environnement (pydantic-settings). |

---

## `app/db/`

| Fichier | Rôle |
|---------|------|
| **app/db/__init__.py** | Expose `Base`, `get_db`, `engine`, `SessionLocal`, `init_db` pour le reste de l'app. |
| **app/db/base.py** | Déclare la base SQLAlchemy (`DeclarativeBase`) commune à tous les modèles. |
| **app/db/session.py** | Crée l'engine et la session SQLAlchemy, fournit `get_db` et `init_db`. |

---

## `app/models/`

| Fichier | Rôle |
|---------|------|
| **app/models/__init__.py** | Importe et réexporte tous les modèles SQLAlchemy du projet. |
| **app/models/user.py** | Modèle table `users` (email, password_hash, role, etc.). |
| **app/models/scan.py** | Modèle table `scans` (repository_url, language, status, lien vers user). |
| **app/models/security_tool.py** | Modèle table `security_tools` (nom, type, commande CLI). |
| **app/models/tool_execution.py** | Modèle table `tool_executions` (exécution d'un outil pour un scan, raw_output JSONB). |
| **app/models/owasp_category.py** | Modèle table `owasp_categories` (A01–A10, nom, description). |
| **app/models/vulnerability.py** | Modèle table `vulnerabilities` (titre, sévérité, fichier, ligne, owasp_category_id, etc.). |
| **app/models/suggested_fix.py** | Modèle table `suggested_fixes` (correctif proposé pour une vulnérabilité, patch_diff). |
| **app/models/scan_metrics.py** | Modèle table `scan_metrics` (score global, compteurs par sévérité pour un scan). |

---

## `app/schemas/`

| Fichier | Rôle |
|---------|------|
| **app/schemas/__init__.py** | Réexporte les schémas Pydantic utilisés par l'API. |
| **app/schemas/health.py** | Schéma de réponse du health check (`status: ok`). |
| **app/schemas/user.py** | Schémas `UserCreate` (création) et `UserResponse` (réponse API). |
| **app/schemas/scan.py** | Schémas `ScanCreate`, `ScanResponse`, `ScanList` pour les scans. |
| **app/schemas/vulnerability.py** | Schémas `VulnerabilityResponse` et `VulnerabilityList` pour les vulnérabilités. |
| **app/schemas/owasp.py** | Schéma `OwaspCategoryResponse` pour les catégories OWASP. |

---

## `app/api/`

| Fichier | Rôle |
|---------|------|
| **app/api/__init__.py** | Marque le package des routes et dépendances API. |
| **app/api/deps.py** | Dépendances injectables (ex. `get_db` pour la session SQLAlchemy). |
| **app/api/routes/__init__.py** | Marque le package des routers FastAPI. |
| **app/api/routes/health.py** | Route `GET /health` pour vérifier que l'API répond. |
| **app/api/routes/users.py** | Routes `POST /api/users` et `GET /api/users/{id}` (création et lecture utilisateur). |
| **app/api/routes/scans.py** | Routes `POST/GET /api/scans` et liste des scans (création, détail, liste par user). |
| **app/api/routes/vulnerabilities.py** | Routes liste des vulnérabilités d'un scan et détail d'une vulnérabilité. |
| **app/api/routes/owasp.py** | Route `GET /api/owasp` pour lister les catégories OWASP Top 10. |
