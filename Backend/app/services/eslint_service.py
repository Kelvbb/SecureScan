"""Service pour lancer ESLint avec règles de sécurité (JavaScript/TypeScript)."""

import asyncio
import json
import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)


class ESLintService:
    """Service pour l'analyse SAST JavaScript/TypeScript avec ESLint."""

    TOOL_NAME = "eslint"

    @staticmethod
    async def run(project_path: str) -> dict:
        """
        Lance ESLint avec règles de sécurité et retourne les résultats parsés.

        Args:
            project_path: Chemin du projet à analyser

        Returns:
            Dict avec les résultats parsés
        """
        if not settings.ESLINT_ENABLED if hasattr(settings, "ESLINT_ENABLED") else True:
            return {"status": "skipped", "reason": "ESLint not enabled"}

        try:
            project_path_obj = Path(project_path)

            # Vérifier si package.json existe (projet Node.js)
            package_json = project_path_obj / "package.json"
            if not package_json.exists():
                # Chercher dans les sous-dossiers
                for subdir in ["frontend", "Frontend", "src", "app"]:
                    candidate = project_path_obj / subdir / "package.json"
                    if candidate.exists():
                        package_json = candidate
                        break
                else:
                    return {
                        "status": "skipped",
                        "reason": "No package.json found",
                        "tool": ESLintService.TOOL_NAME,
                        "results": [],
                        "errors": [],
                        "stats": {},
                        "analyzed_files": [],
                    }

            # Vérifier si ESLint est installé localement ou globalement
            eslint_path = shutil.which("eslint")
            if not eslint_path:
                # Essayer npx eslint
                eslint_path = shutil.which("npx")
                if eslint_path:
                    # Utiliser npx pour exécuter eslint
                    cmd_base = ["npx", "--yes", "eslint"]
                else:
                    return {
                        "status": "error",
                        "error": "ESLint is not installed. Install with: npm install -g eslint eslint-plugin-security",
                        "tool": ESLintService.TOOL_NAME,
                        "results": [],
                        "errors": [],
                        "stats": {},
                        "analyzed_files": [],
                    }
            else:
                cmd_base = [eslint_path]

            # Essayer d'installer le plugin security si nécessaire
            # Vérifier si le plugin est déjà installé dans le projet
            node_modules_security = (
                project_path_obj / "node_modules" / "eslint-plugin-security"
            )
            if not node_modules_security.exists():
                # Chercher dans les sous-dossiers
                for subdir in ["frontend", "Frontend", "src", "app"]:
                    candidate = (
                        project_path_obj
                        / subdir
                        / "node_modules"
                        / "eslint-plugin-security"
                    )
                    if candidate.exists():
                        node_modules_security = candidate
                        break
                else:
                    # Le plugin n'est pas installé, essayer de l'installer
                    logger.info(
                        "Plugin eslint-plugin-security non trouvé, tentative d'installation..."
                    )
                    try:
                        # Installer le plugin dans le projet
                        install_cmd = [
                            "npm",
                            "install",
                            "--no-save",
                            "eslint-plugin-security",
                        ]
                        install_process = await asyncio.create_subprocess_exec(
                            *install_cmd,
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE,
                            cwd=str(project_path_obj),
                        )
                        await asyncio.wait_for(
                            install_process.communicate(), timeout=60.0
                        )
                        logger.info(
                            "Plugin eslint-plugin-security installé avec succès"
                        )
                    except Exception as e:
                        logger.warning(
                            f"Impossible d'installer eslint-plugin-security: {e}"
                        )
                        # Continuer sans le plugin, utiliser des règles de base

            # Créer un fichier de configuration temporaire
            # Utiliser le plugin security si disponible, sinon règles de base
            try:
                # Vérifier si le plugin est maintenant disponible
                node_modules_security = (
                    project_path_obj / "node_modules" / "eslint-plugin-security"
                )
                if not node_modules_security.exists():
                    for subdir in ["frontend", "Frontend", "src", "app"]:
                        candidate = (
                            project_path_obj
                            / subdir
                            / "node_modules"
                            / "eslint-plugin-security"
                        )
                        if candidate.exists():
                            node_modules_security = candidate
                            break

                if node_modules_security.exists():
                    # Utiliser le plugin security sans extends pour éviter les erreurs de configuration
                    # Activer les règles de sécurité manuellement
                    config_content = {
                        "plugins": ["security"],
                        "parserOptions": {"ecmaVersion": 2020, "sourceType": "module"},
                        "env": {"browser": True, "node": True, "es6": True},
                        "rules": {
                            # Règles de sécurité essentielles
                            "security/detect-buffer-noassert": "warn",
                            "security/detect-child-process": "warn",
                            "security/detect-disable-mustache-escape": "warn",
                            "security/detect-eval-with-expression": "error",
                            "security/detect-new-buffer": "warn",
                            "security/detect-no-csrf-before-method-override": "warn",
                            "security/detect-non-literal-fs-filename": "warn",
                            "security/detect-non-literal-regexp": "warn",
                            "security/detect-non-literal-require": "warn",
                            "security/detect-possible-timing-attacks": "warn",
                            "security/detect-pseudoRandomBytes": "warn",
                            # Règles ESLint de base pour la sécurité
                            "no-eval": "error",
                            "no-implied-eval": "error",
                            "no-new-func": "error",
                        },
                    }
                else:
                    # Utiliser des règles de base sans plugin
                    logger.warning(
                        "Utilisation d'ESLint sans plugin security (règles de base)"
                    )
                    config_content = {
                        "parserOptions": {"ecmaVersion": 2020, "sourceType": "module"},
                        "env": {"browser": True, "node": True, "es6": True},
                        "rules": {
                            "no-eval": "error",
                            "no-implied-eval": "error",
                            "no-new-func": "error",
                            "no-script-url": "error",
                            "no-proto": "error",
                        },
                    }
            except Exception:
                # En cas d'erreur, utiliser des règles de base
                config_content = {
                    "parserOptions": {"ecmaVersion": 2020, "sourceType": "module"},
                    "rules": {
                        "no-eval": "error",
                        "no-implied-eval": "error",
                    },
                }

            # Créer un fichier temporaire pour la config ESLint
            # S'assurer que le contenu ne contient que des propriétés valides pour ESLint
            # Supprimer toute propriété "name" ou autre qui pourrait être ajoutée par erreur
            valid_keys = [
                "extends",
                "plugins",
                "parserOptions",
                "rules",
                "env",
                "parser",
                "globals",
            ]
            clean_config = {k: v for k, v in config_content.items() if k in valid_keys}

            # Créer le fichier de configuration
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False
            ) as config_file:
                json.dump(clean_config, config_file, indent=2, ensure_ascii=False)
                config_path = config_file.name
                logger.debug(f"Fichier de configuration ESLint créé: {config_path}")
                logger.debug(
                    f"Contenu de la config: {json.dumps(clean_config, indent=2)}"
                )

            # Construire la commande ESLint
            # Utiliser le plugin security et le format JSON
            # Ne pas utiliser --no-eslintrc si on utilise des règles de base (sans plugin)
            cmd = cmd_base + [
                "--format",
                "json",
                "--ext",
                ".js,.jsx,.ts,.tsx",
            ]

            # Ajouter --no-eslintrc seulement si on utilise le plugin security
            if (
                "extends" in config_content
                and "plugin:security/recommended" in config_content.get("extends", [])
            ):
                cmd.append("--no-eslintrc")

            cmd.extend(
                [
                    "--config",
                    config_path,
                    str(project_path_obj),
                ]
            )

            logger.info(f"Commande ESLint: {' '.join(cmd[:5])}... (tronqué)")

            try:
                # Exécuter ESLint de manière asynchrone
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=str(
                        project_path_obj.parent
                        if package_json.parent != project_path_obj
                        else project_path_obj
                    ),
                )

                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=300.0
                )

                output = stdout.decode() if stdout else ""
                stderr_output = stderr.decode() if stderr else ""

                # Nettoyer le fichier de configuration temporaire
                try:
                    os.unlink(config_path)
                except Exception:
                    pass

                if stderr_output.strip():
                    logger.warning(f"ESLint stderr: {stderr_output[:500]}")

                # Parser la sortie JSON
                try:
                    if not output.strip():
                        return {
                            "status": "error",
                            "error": "ESLint returned no output",
                            "tool": ESLintService.TOOL_NAME,
                            "results": [],
                            "errors": [],
                            "stats": {},
                            "analyzed_files": [],
                        }

                    # ESLint retourne un tableau de résultats par fichier
                    data = json.loads(output)

                    # Flatten les résultats
                    all_results = []
                    analyzed_files = []
                    for file_result in data:
                        file_path = file_result.get("filePath", "")
                        if file_path:
                            analyzed_files.append(file_path)
                        messages = file_result.get("messages", [])
                        for message in messages:
                            # Ajouter le chemin du fichier à chaque message
                            message["filePath"] = file_path
                            all_results.append(message)

                    logger.info(
                        f"ESLint: {len(all_results)} résultats trouvés dans {len(analyzed_files)} fichiers"
                    )

                except json.JSONDecodeError as e:
                    logger.error(f"Erreur de parsing JSON ESLint: {e}")
                    logger.error(f"Sortie: {output[:1000]}")
                    return {
                        "status": "error",
                        "error": f"Invalid JSON from ESLint: {str(e)}",
                        "tool": ESLintService.TOOL_NAME,
                        "results": [],
                        "errors": [],
                        "stats": {},
                        "analyzed_files": [],
                    }

                return {
                    "status": "success",
                    "tool": ESLintService.TOOL_NAME,
                    "results": all_results,
                    "errors": [],
                    "stats": {
                        "files_analyzed": len(analyzed_files),
                        "issues_found": len(all_results),
                    },
                    "analyzed_files": analyzed_files,
                    "raw_output": data,
                }

            except asyncio.TimeoutError:
                # Nettoyer le fichier de configuration temporaire
                try:
                    os.unlink(config_path)
                except Exception:
                    pass
                return {
                    "status": "error",
                    "error": "ESLint execution timeout",
                    "tool": ESLintService.TOOL_NAME,
                    "results": [],
                    "errors": [],
                    "stats": {},
                    "analyzed_files": [],
                }
            except Exception as e:
                # Nettoyer le fichier de configuration temporaire
                try:
                    os.unlink(config_path)
                except Exception:
                    pass
                return {
                    "status": "error",
                    "error": str(e),
                    "tool": ESLintService.TOOL_NAME,
                    "results": [],
                    "errors": [],
                    "stats": {},
                    "analyzed_files": [],
                }
            finally:
                # S'assurer que le fichier temporaire est supprimé même en cas d'erreur
                try:
                    if "config_path" in locals():
                        os.unlink(config_path)
                except Exception:
                    pass

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "tool": ESLintService.TOOL_NAME,
                "results": [],
                "errors": [],
                "stats": {},
                "analyzed_files": [],
            }

    @staticmethod
    def parse_vulnerabilities(eslint_results: dict) -> list[dict]:
        """
        Convertit les résultats ESLint en format vulnérabilité standardisé.

        Args:
            eslint_results: Résultats bruts d'ESLint

        Returns:
            Liste de vulnérabilités standardisées
        """
        vulnerabilities = []

        if eslint_results.get("status") != "success":
            logger.warning(
                f"ESLint status n'est pas 'success': {eslint_results.get('status')}"
            )
            return vulnerabilities

        results = eslint_results.get("results", [])
        logger.info(f"Parsing de {len(results)} résultats ESLint")

        if not results:
            logger.warning("Aucun résultat trouvé dans la sortie ESLint")
            return vulnerabilities

        for result in results:
            try:
                rule_id = result.get("ruleId", "Unknown")
                message = result.get("message", "")
                severity = result.get("severity", 1)  # 1 = warning, 2 = error
                line = result.get("line")
                column = result.get("column")
                file_path = result.get("filePath", "")

                # Mapper la sévérité ESLint vers notre standard
                severity_map = {
                    2: "high",  # error
                    1: "medium",  # warning
                    0: "low",  # off (ne devrait pas arriver)
                }
                normalized_severity = severity_map.get(severity, "medium")

                vuln = {
                    "title": f"{rule_id}: {message}",
                    "description": message,
                    "file_path": file_path,
                    "line_start": line,
                    "line_end": line,
                    "col_start": column,
                    "col_end": column,
                    "severity": normalized_severity,
                    "rule_id": rule_id,
                    "tool": "eslint",
                }

                vulnerabilities.append(vuln)
                logger.debug(f"Vulnérabilité parsée: {rule_id} dans {file_path}:{line}")

            except Exception as e:
                logger.error(f"Erreur lors du parsing d'un résultat ESLint: {e}")
                import traceback

                logger.error(traceback.format_exc())
                continue

        logger.info(f"Parsé {len(vulnerabilities)} vulnérabilités depuis ESLint")
        return vulnerabilities
