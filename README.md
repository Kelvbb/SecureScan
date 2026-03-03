# SecureScan

Plateforme web interne d’analyse de qualité et de sécurité du code source, développée pour **CyberSafe Solutions**.

## Contexte

**CyberSafe Solutions** est une startup française spécialisée en cybersécurité pour les PME (150 entreprises clientes, équipe de 35 développeurs). Suite à un audit de l’ANSSI, les problématiques suivantes ont été identifiées :

- Absence d’outil centralisé d’analyse de sécurité du code source
- Vulnérabilités d’injection (SQL, XSS) non détectées avant la mise en production
- Dépendances obsolètes avec des CVE connues dans les projets
- Manque d’intégration de tests de sécurité dans les pipelines CI/CD
- Absence de rapports de sécurité automatisés pour les clients
- Corrections de sécurité manuelles, lentes et sujettes aux erreurs

**SecureScan** a pour objectif d’orchestrer des outils de sécurité open source existants, d’agréger leurs résultats, de les mapper sur l’**OWASP Top 10 : 2025**, et de proposer des corrections automatisées.

---

## Fonctionnalités

### A. Soumission de projet

- Saisie d’une **URL de dépôt Git** (GitHub / GitLab) ou **téléversement d’une archive ZIP**
- Clonage automatique du dépôt côté serveur
- Détection automatique du **langage / framework** (ex. : PHP, JavaScript, Node.js, Python)

### B. Analyse de sécurité automatisée

La plateforme intègre et orchestre **au minimum 3** des outils suivants :

| Type | Outils suggérés | Description |
|------|-----------------|-------------|
| **SAST** (Static Application Security Testing) | Semgrep, ESLint Security | Analyse statique du code pour détecter les modèles vulnérables |
| **Dépendances** | `npm audit`, `Composer audit` | Scan des dépendances pour identifier les CVE connues |
| **Secrets** | `git-secrets`, TruffleHog | Détection de clés API, mots de passe et tokens dans le code |
| **Qualité code** | ESLint, PHPStan | Analyse de qualité générale et bonnes pratiques |

**Exigence technique :** chaque outil est lancé via CLI ; sa sortie (JSON de préférence) est parsée et stockée.

### C. Mapping OWASP Top 10 : 2025

Chaque vulnérabilité détectée est classée selon le référentiel **OWASP Top 10 : 2025**. La plateforme doit couvrir **au moins 5** des catégories suivantes :

| Catégorie | Exemples de détection |
|-----------|------------------------|
| **A01** Broken Access Control | IDOR, CORS mal configuré, escalade de privilèges |
| **A02** Security Misconfiguration | Headers manquants, debug actif, config par défaut |
| **A03** Software Supply Chain Failures | Dépendances vulnérables, packages malveillants |
| **A04** Cryptographic Failures | Mots de passe en clair, algorithmes obsolètes |
| **A05** Injection | SQL injection, XSS, command injection |
| **A06** Insecure Design | Absence de validation, flux non sécurisés |
| **A07** Authentication Failures | Brute force, sessions non invalidées |
| **A08** Software/Data Integrity Failures | CI/CD non sécurisé, désérialisation |
| **A09** Logging & Alerting Failures | Logs absents, pas d’alertes sur erreurs |
| **A10** Mishandling of Exceptional Conditions | Erreurs non gérées, fail-open, stack traces exposées |

### D. Dashboard de visualisation

- **Score de sécurité global** (ex. : A / B / C / D / F ou score sur 100)
- **Répartition des vulnérabilités par sévérité** (critique, élevé, moyen, faible)
- **Distribution par catégorie OWASP Top 10** (graphiques)
- **Liste détaillée des findings** : fichier concerné, numéro de ligne, description, sévérité, catégorie OWASP
- **Filtres et tri** : par sévérité, par outil source, par catégorie OWASP

### E. Système de correction automatisé

Pour les vulnérabilités les plus courantes, la plateforme propose des **corrections prédéfinies** (basées sur des modèles) :

| Vulnérabilité | Correction suggérée |
|---------------|----------------------|
| Injection SQL | Requêtes préparées / paramétrées |
| XSS | Échappement de sortie (`htmlspecialchars`, DOMPurify) |
| Dépendances vulnérables | Versions patchées |
| Secrets exposés | Remplacement par variables d’environnement |
| Mots de passe en clair | Hachage (argon2) |

L’utilisateur **valide ou rejette** chaque correction proposée avant son application.

### F. Intégration Git automatisée

- **Création automatique d’une branche de correction** (ex. : `fix/securescan-2026-03-05`)
- **Application des corrections validées** sur cette branche
- **Push automatique** via l’API Git (GitHub API / Octokit ou git CLI)
- **Génération d’un rapport de sécurité** (HTML ou PDF) résumant l’analyse et les corrections appliquées

---

## Stack technique (suggestions)

- **Backend :** API pour orchestration des outils CLI, parsing JSON, stockage des résultats
- **Frontend :** Dashboard (score, graphiques, liste des findings, filtres)
- **Outils :** Exécution en CLI de Semgrep, ESLint, npm audit, Composer audit, git-secrets / TruffleHog, etc.
- **Git :** GitHub API / Octokit ou git CLI pour clonage, branches et push

---

## Installation et démarrage

*(À compléter selon l’architecture retenue : dépendances, variables d’environnement, commandes de lancement.)*

---

## Licence

Projet interne CyberSafe Solutions.
