"""Service pour lancer Bandit (SAST spécialisé pour Python)."""

import asyncio
import json
import logging
import shutil
import subprocess
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)


class BanditService:
    """Service pour l'analyse SAST Python avec Bandit."""

    TOOL_NAME = "bandit"

    @staticmethod
    async def run(project_path: str) -> dict:
        """
        Lance Bandit et retourne les résultats parsés.
        
        Args:
            project_path: Chemin du projet à analyser
            
        Returns:
            Dict avec les résultats parsés
        """
        if not settings.BANDIT_ENABLED if hasattr(settings, 'BANDIT_ENABLED') else True:
            return {"status": "skipped", "reason": "Bandit not enabled"}

        try:
            # Find bandit binary path
            bandit_path = shutil.which("bandit")
            if not bandit_path:
                return {
                    "status": "error",
                    "error": "Bandit is not installed. Install with: pip install bandit[toml]",
                    "tool": BanditService.TOOL_NAME,
                    "results": [],
                    "errors": [],
                    "stats": {},
                    "analyzed_files": [],
                }
            
            # Construire la commande Bandit
            cmd = [
                bandit_path,
                "-r",  # Récursif
                "-f", "json",  # Format JSON
                "-ll",  # Niveau de sévérité : low et plus
                "--skip", "B101,B601",  # Ignorer certains tests si nécessaire
                str(project_path),
            ]
            
            logger.info(f"Commande Bandit: {' '.join(cmd)}")

            try:
                # Exécuter Bandit de manière asynchrone
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=300.0
                )
                
                output = stdout.decode() if stdout else ""
                stderr_output = stderr.decode() if stderr else ""
                
                if stderr_output.strip():
                    logger.warning(f"Bandit stderr: {stderr_output[:500]}")
                
                # Parser la sortie JSON
                try:
                    if not output.strip():
                        return {
                            "status": "error",
                            "error": "Bandit returned no output",
                            "tool": BanditService.TOOL_NAME,
                            "results": [],
                            "errors": [],
                            "stats": {},
                            "analyzed_files": [],
                        }
                    
                    data = json.loads(output)
                    
                    # Logger des statistiques
                    results_count = len(data.get("results", []))
                    metrics = data.get("metrics", {})
                    logger.info(f"Bandit: {results_count} résultats trouvés")
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Erreur de parsing JSON Bandit: {e}")
                    logger.error(f"Sortie: {output[:1000]}")
                    return {
                        "status": "error",
                        "error": f"Invalid JSON from Bandit: {str(e)}",
                        "tool": BanditService.TOOL_NAME,
                        "results": [],
                        "errors": [],
                        "stats": {},
                        "analyzed_files": [],
                    }

                # Extraire les fichiers analysés
                analyzed_files = []
                metrics = data.get("metrics", {})
                if "_totals" in metrics:
                    totals = metrics.get("_totals", {})
                    # Bandit ne retourne pas directement la liste des fichiers
                    # On extrait depuis les résultats
                    files_from_results = set()
                    for result in data.get("results", []):
                        file_path = result.get("filename")
                        if file_path:
                            files_from_results.add(file_path)
                    analyzed_files = sorted(list(files_from_results))
                
                return {
                    "status": "success",
                    "tool": BanditService.TOOL_NAME,
                    "results": data.get("results", []),
                    "errors": data.get("errors", []),
                    "stats": metrics,
                    "analyzed_files": analyzed_files,
                    "raw_output": data,
                }

            except asyncio.TimeoutError:
                return {
                    "status": "error",
                    "error": "Bandit execution timeout",
                    "tool": BanditService.TOOL_NAME,
                    "results": [],
                    "errors": [],
                    "stats": {},
                    "analyzed_files": [],
                }
            except Exception as e:
                return {
                    "status": "error",
                    "error": str(e),
                    "tool": BanditService.TOOL_NAME,
                    "results": [],
                    "errors": [],
                    "stats": {},
                    "analyzed_files": [],
                }

        except FileNotFoundError:
            return {
                "status": "error",
                "error": "Bandit is not installed. Install with: pip install bandit[toml]",
                "tool": BanditService.TOOL_NAME,
                "results": [],
                "errors": [],
                "stats": {},
                "analyzed_files": [],
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "tool": BanditService.TOOL_NAME,
                "results": [],
                "errors": [],
                "stats": {},
                "analyzed_files": [],
            }

    @staticmethod
    def parse_vulnerabilities(bandit_results: dict) -> list[dict]:
        """
        Convertit les résultats Bandit en format vulnérabilité standardisé.
        
        Args:
            bandit_results: Résultats bruts de Bandit
            
        Returns:
            Liste de vulnérabilités standardisées
        """
        vulnerabilities = []

        if bandit_results.get("status") != "success":
            logger.warning(f"Bandit status n'est pas 'success': {bandit_results.get('status')}")
            return vulnerabilities

        results = bandit_results.get("results", [])
        logger.info(f"Parsing de {len(results)} résultats Bandit")
        
        if not results:
            logger.warning("Aucun résultat trouvé dans la sortie Bandit")
            return vulnerabilities

        for result in results:
            try:
                # Bandit retourne : test_id, test_name, issue_severity, issue_confidence, issue_text, line_number, etc.
                test_id = result.get("test_id", "Unknown")
                test_name = result.get("test_name", "Security issue")
                issue_severity = result.get("issue_severity", "MEDIUM")
                issue_confidence = result.get("issue_confidence", "MEDIUM")
                issue_text = result.get("issue_text", "")
                line_number = result.get("line_number")
                filename = result.get("filename", "")
                
                # Mapper la sévérité Bandit vers notre standard
                severity_map = {
                    "HIGH": "high",
                    "MEDIUM": "medium",
                    "LOW": "low",
                }
                severity = severity_map.get(issue_severity.upper(), "medium")
                
                # Extraire CWE si disponible
                cwe_id = None
                if "CWE" in test_id or "CWE" in issue_text:
                    import re
                    cwe_match = re.search(r'CWE-?\d+', issue_text)
                    if cwe_match:
                        cwe_id = cwe_match.group(0)
                
                vuln = {
                    "title": f"{test_id}: {test_name}",
                    "description": issue_text,
                    "file_path": filename,
                    "line_start": line_number,
                    "line_end": line_number,
                    "severity": severity,
                    "cwe_id": cwe_id,
                    "rule_id": test_id,
                    "tool": "bandit",
                }
                
                vulnerabilities.append(vuln)
                logger.debug(f"Vulnérabilité parsée: {test_id} dans {filename}:{line_number}")
                
            except Exception as e:
                logger.error(f"Erreur lors du parsing d'un résultat Bandit: {e}")
                import traceback
                logger.error(traceback.format_exc())
                continue

        logger.info(f"Parsé {len(vulnerabilities)} vulnérabilités depuis Bandit")
        return vulnerabilities
