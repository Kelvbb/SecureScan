"""Service pour détecter les technologies utilisées dans un projet."""

import logging
from pathlib import Path
from typing import Dict, List, Set

logger = logging.getLogger(__name__)


class TechnologyDetector:
    """Détecte les technologies utilisées dans un projet."""

    @staticmethod
    def detect(project_path: str) -> Dict[str, bool]:
        """
        Détecte les technologies utilisées dans le projet.
        
        Args:
            project_path: Chemin du projet à analyser
            
        Returns:
            Dict avec les technologies détectées:
            {
                "python": True/False,
                "javascript": True/False,
                "typescript": True/False,
                "php": True/False,
                "java": True/False,
                "go": True/False,
                "ruby": True/False,
                "rust": True/False,
                "csharp": True/False,
            }
        """
        project = Path(project_path)
        if not project.exists():
            logger.warning(f"Le chemin du projet n'existe pas: {project_path}")
            return TechnologyDetector._default_detection()
        
        technologies = {
            "python": False,
            "javascript": False,
            "typescript": False,
            "php": False,
            "java": False,
            "go": False,
            "ruby": False,
            "rust": False,
            "csharp": False,
        }
        
        # Fichiers indicateurs pour chaque technologie
        indicators = {
            "python": [
                "requirements.txt",
                "setup.py",
                "pyproject.toml",
                "Pipfile",
                "poetry.lock",
                "manage.py",  # Django
                "app.py",  # Flask
                "main.py",
            ],
            "javascript": [
                "package.json",
                "yarn.lock",
                "package-lock.json",
                ".npmrc",
                "webpack.config.js",
                "vite.config.js",
                "rollup.config.js",
            ],
            "typescript": [
                "tsconfig.json",
                "tsconfig.base.json",
                ".ts",
            ],
            "php": [
                "composer.json",
                "composer.lock",
                "artisan",  # Laravel
                "symfony.lock",  # Symfony
                "index.php",
                ".php",
            ],
            "java": [
                "pom.xml",
                "build.gradle",
                "build.gradle.kts",
                ".gradle",
                ".java",
            ],
            "go": [
                "go.mod",
                "go.sum",
                "Gopkg.toml",
                ".go",
            ],
            "ruby": [
                "Gemfile",
                "Gemfile.lock",
                "Rakefile",
                ".rb",
            ],
            "rust": [
                "Cargo.toml",
                "Cargo.lock",
                ".rs",
            ],
            "csharp": [
                ".csproj",
                ".sln",
                "project.json",
                ".cs",
            ],
        }
        
        # Détecter par fichiers indicateurs
        for tech, files in indicators.items():
            for indicator in files:
                if indicator.startswith("."):
                    # Extension de fichier
                    if TechnologyDetector._has_extension(project, indicator):
                        technologies[tech] = True
                        logger.info(f"Technologie {tech} détectée via extension {indicator}")
                        break
                else:
                    # Fichier ou dossier
                    if TechnologyDetector._find_file(project, indicator):
                        technologies[tech] = True
                        logger.info(f"Technologie {tech} détectée via fichier {indicator}")
                        break
        
        # Détection TypeScript : vérifier si tsconfig existe ET si des fichiers .ts sont présents
        if technologies["typescript"]:
            if not TechnologyDetector._has_extension(project, ".ts"):
                # Si tsconfig existe mais pas de fichiers .ts, c'est peut-être juste une config
                # Vérifier dans node_modules ou autres
                technologies["typescript"] = TechnologyDetector._has_extension(project, ".ts", check_subdirs=True)
        
        # Détection JavaScript : si package.json existe, c'est très probablement du JS
        if TechnologyDetector._find_file(project, "package.json"):
            technologies["javascript"] = True
            # Vérifier aussi s'il y a des fichiers .js
            if not technologies["javascript"]:
                technologies["javascript"] = TechnologyDetector._has_extension(project, ".js")
        
        # Détection PHP : vérifier les fichiers .php
        if TechnologyDetector._find_file(project, "composer.json") or TechnologyDetector._has_extension(project, ".php"):
            technologies["php"] = True
        
        # Logger le résumé
        detected = [tech for tech, detected in technologies.items() if detected]
        if detected:
            logger.info(f"Technologies détectées: {', '.join(detected)}")
        else:
            logger.warning("Aucune technologie détectée, utilisation de la détection par défaut")
            return TechnologyDetector._default_detection()
        
        return technologies
    
    @staticmethod
    def _find_file(project: Path, filename: str, max_depth: int = 3) -> bool:
        """Recherche récursive d'un fichier."""
        try:
            # Chercher à la racine
            if (project / filename).exists():
                return True
            
            # Chercher dans les sous-dossiers (limité à max_depth)
            for depth in range(1, max_depth + 1):
                for path in project.rglob(filename):
                    # Ignorer node_modules et autres dossiers volumineux
                    if "node_modules" in str(path) or ".git" in str(path):
                        continue
                    # Vérifier la profondeur
                    relative = path.relative_to(project)
                    if len(relative.parts) <= depth + 1:
                        return True
        except Exception as e:
            logger.debug(f"Erreur lors de la recherche de {filename}: {e}")
        
        return False
    
    @staticmethod
    def _has_extension(project: Path, extension: str, check_subdirs: bool = True) -> bool:
        """Vérifie si des fichiers avec l'extension existent."""
        try:
            if not check_subdirs:
                # Vérifier seulement à la racine
                for file in project.iterdir():
                    if file.is_file() and file.suffix == extension:
                        return True
            else:
                # Vérifier récursivement (limité)
                for file in project.rglob(f"*{extension}"):
                    # Ignorer node_modules et autres
                    if "node_modules" in str(file) or ".git" in str(file):
                        continue
                    # Limiter la profondeur
                    relative = file.relative_to(project)
                    if len(relative.parts) <= 4:  # Max 4 niveaux
                        return True
        except Exception as e:
            logger.debug(f"Erreur lors de la vérification de l'extension {extension}: {e}")
        
        return False
    
    @staticmethod
    def _default_detection() -> Dict[str, bool]:
        """Retourne une détection par défaut (tout activé pour être sûr)."""
        logger.warning("Utilisation de la détection par défaut (toutes technologies activées)")
        return {
            "python": True,
            "javascript": True,
            "typescript": True,
            "php": True,
            "java": True,
            "go": True,
            "ruby": True,
            "rust": True,
            "csharp": True,
        }
    
    @staticmethod
    def get_semgrep_configs(technologies: Dict[str, bool]) -> List[str]:
        """
        Retourne les configurations Semgrep à utiliser selon les technologies détectées.
        
        Args:
            technologies: Dict des technologies détectées
            
        Returns:
            Liste des configs Semgrep à utiliser
        """
        configs = [
            "p/security-audit",  # Toujours inclure
            "p/owasp-top-ten",  # Toujours inclure
            # Note: p/security n'existe pas, retiré
        ]
        
        # Ajouter les configs spécifiques aux technologies détectées
        if technologies.get("python"):
            configs.append("p/python")
        
        if technologies.get("javascript"):
            configs.append("p/javascript")
        
        if technologies.get("typescript"):
            configs.append("p/typescript")
            configs.append("p/react")  # Souvent utilisé avec TypeScript
        
        if technologies.get("php"):
            configs.append("p/php")
            # Détecter les frameworks PHP
            # Note: On pourrait améliorer cela en détectant Symfony, Laravel, etc.
        
        if technologies.get("java"):
            configs.append("p/java")
        
        # Note: Certaines configs Semgrep n'existent pas ou ne sont pas disponibles
        # On les retire pour éviter les erreurs 404
        # if technologies.get("go"):
        #     configs.append("p/go")  # Non disponible (404)
        
        # if technologies.get("ruby"):
        #     configs.append("p/ruby")  # Vérifier disponibilité
        
        # if technologies.get("rust"):
        #     configs.append("p/rust")  # Vérifier disponibilité
        
        # if technologies.get("csharp"):
        #     configs.append("p/csharp")  # Vérifier disponibilité
        
        return configs
    
    @staticmethod
    def get_tools_to_run(technologies: Dict[str, bool]) -> List[str]:
        """
        Retourne la liste des outils à exécuter selon les technologies détectées.
        
        Args:
            technologies: Dict des technologies détectées
            
        Returns:
            Liste des noms d'outils à exécuter
        """
        tools = ["semgrep"]  # Toujours exécuter Semgrep
        
        # Outils spécifiques par technologie
        if technologies.get("python"):
            tools.append("bandit")
            tools.append("pip-audit")
        
        if technologies.get("javascript") or technologies.get("typescript"):
            tools.append("eslint")
            tools.append("npm-audit")
        
        # TruffleHog pour tous (détection de secrets)
        tools.append("truffleHog")
        
        return tools
