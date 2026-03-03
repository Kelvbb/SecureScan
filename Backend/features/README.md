# 🏗️ Architecture des Features - SecureScan

Ce dossier contient l'organisation des différents outils et features intégrés à SecureScan.

## 📂 Structure

```
features/
├── README.md                          # Ce fichier
├── CONTRIBUTING.md                    # Guide pour ajouter de nouvelles features
│
└── 1-sast-semgrep/                    # Feature 1: SAST avec Semgrep
    ├── README.md                      # Documentation de cette feature
    ├── services/                      # Code réutilisable
    │   ├── semgrep_service.py
    │   ├── pip_audit_service.py
    │   ├── trufflehog_service.py
    │   └── scan_orchestrator.py       # Orchestre tous les outils
    ├── tests/                         # Tests complets
    │   ├── test_imports.py
    │   ├── test_database.py
    │   ├── test_complete_scan.py
    │   ├── test_api_flow.py
    │   ├── check_inserts.py
    │   └── verify_inserts.py
    ├── docs/                          # Documentation détaillée
    │   ├── INTEGRATION.md             # Comment cette feature fonctionne
    │   ├── TEST_COMMANDS.md           # Commandes de test
    │   └── TESTS_SUMMARY.txt          # Résumé des résultats
    └── scripts/                       # Utilitaires
        └── run_all_tests.sh           # Script pour exécuter tous les tests
```

## 🎯 Chaque Feature Contient:

### 📄 `README.md`
Explique:
- Quels outils sont intégrés (Semgrep, pip-audit, npm-audit, TruffleHog)
- Comment fonctionnent les services
- Endpoints API disponibles
- Points clés à connaître

### 📂 `services/`
Code réutilisable:
- `*_service.py`: Chaque outil a son service
- `scan_orchestrator.py`: Lance tous les outils en parallèle

### 🧪 `tests/`
Suite de tests complète:
- `test_imports.py`: Valide les imports
- `test_database.py`: Vérifie connexion BD
- `test_complete_scan.py`: Tests inserts
- `test_api_flow.py`: Tests endpoints API
- Scripts additionnels pour vérification

### 📚 `docs/`
Documentation:
- Comment intégrer
- Commandes de test
- Résultats validés

### 🛠️ `scripts/`
Scripts utilitaires:
- `run_all_tests.sh`: Automatise les tests

## 🔄 Intégration dans l'App

Les services sont utilisés par:
- **API Routes**: `app/api/routes/scans.py` → endpoints `/api/scans/{id}/run`
- **Models**: `app/models/` → Scan, ToolExecution, Vulnerability
- **Config**: `app/config.py` → paramètres des outils

## 🚀 Comment Utiliser Cette Feature

```bash
# 1. Vérifier les imports
python3 features/1-sast-semgrep/tests/test_imports.py

# 2. Tester la BD
python3 features/1-sast-semgrep/tests/test_database.py

# 3. Tester les inserts
python3 features/1-sast-semgrep/tests/test_complete_scan.py

# 4. Lancer tous les tests
chmod +x features/1-sast-semgrep/scripts/run_all_tests.sh
./features/1-sast-semgrep/scripts/run_all_tests.sh
```

## ➕ Ajouter une Nouvelle Feature (pour vos collaborateurs)

Voir [CONTRIBUTING.md](CONTRIBUTING.md)

Structure à suivre:
```
features/
└── 2-dependency-audit/            # ou un autre numéro
    ├── README.md
    ├── services/
    │   └── votre_service.py
    ├── tests/
    │   ├── test_imports.py
    │   ├── test_*.py
    │   └── ...
    ├── docs/
    │   ├── INTEGRATION.md
    │   └── ...
    └── scripts/
        └── run_tests.sh
```

## 📋 État des Features

| # | Feature | Status | Services | Tests | Doc |
|---|---------|--------|----------|-------|-----|
| 1 | SAST (Semgrep) | ✅ Complète | ✓ | ✓ | ✓ |
| 2 | Dependency Audit | ⏳ À faire | - | - | - |
| 3 | Secrets Detection | ⏳ À faire | - | - | - |

## 💡 Conseils pour les Collaborateurs

1. **Suivre la structure** - Chaque feature = dossier `N-nom/`
2. **Documenter** - README + docs/ pour expliquer
3. **Tester** - tests/ doit être complète
4. **Services réutilisables** - Pas de code hardcodé
5. **API endpoints** - Ajouter dans `app/api/routes/`
6. **Base de données** - Créer les modèles SQLAlchemy
7. **Git branching** - Créer feature branch: `git checkout -b 2-dependency-audit`

## 📞 Contact / Questions

Voir le README principal du projet pour les contacts.

---

**Last Updated**: 3 mars 2026  
**Branch**: 10-backend-outil-1-sast-semgrep-cli-parsing-json
