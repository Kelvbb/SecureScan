"""Service pour lancer Semgrep (SAST) et parser les résultats."""

import asyncio
import json
import logging
import os
import subprocess
import shutil
import sys
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)


class SemgrepService:
    """Service pour l'analyse SAST avec Semgrep."""

    TOOL_NAME = "semgrep"

    @staticmethod
    async def run(project_path: str) -> dict:
        """
        Lance Semgrep et retourne les résultats parsés.
        
        Args:
            project_path: Chemin du projet à analyser
            
        Returns:
            Dict avec les résultats parsés
        """
        if not settings.SEMGREP_ENABLED:
            return {"status": "skipped", "reason": "Semgrep not enabled"}

        try:
            # Find semgrep binary path
            semgrep_path = shutil.which("semgrep")
            if not semgrep_path:
                error_msg = "Semgrep is not installed. Install with: pip install semgrep"
                logger.error(error_msg)
                return {
                    "status": "error",
                    "error": error_msg,
                    "tool": SemgrepService.TOOL_NAME,
                    "results": [],
                    "errors": [{"message": error_msg}],
                    "stats": {},
                    "analyzed_files": [],
                }
            
            # Construire la commande Semgrep avec plusieurs configs de sécurité
            # Utiliser plusieurs règles de sécurité pour détecter plus de vulnérabilités
            # Note: --config=auto active automatiquement les règles pour tous les langages détectés
            # Construire la commande Semgrep avec des règles adaptées aux technologies détectées
            # Utiliser les configs détectées par TechnologyDetector si disponibles
            if hasattr(SemgrepService, '_detected_configs') and SemgrepService._detected_configs:
                configs = SemgrepService._detected_configs
                logger.info(f"Utilisation des configs Semgrep détectées: {configs}")
            else:
                # Fallback: configs par défaut (toutes technologies)
                configs = [
                    "p/security-audit",
                    "p/owasp-top-ten",
                    "p/python",
                    "p/javascript",
                    "p/typescript",
                    "p/php",
                ]
                logger.info(f"Utilisation des configs Semgrep par défaut: {configs}")
            
            cmd = [
                semgrep_path,
                "--json",
                "--disable-nosem",  # Ne pas ignorer les commentaires nosem
                "--timeout=300",  # 300 secondes par fichier max (5 minutes)
                "--max-target-bytes=10000000",  # Limite la taille des fichiers (10MB)
                "--disable-version-check",  # Désactiver la vérification de version pour plus de rapidité
                "--no-git-ignore",  # Ne pas ignorer les fichiers selon .gitignore
            ]
            
            # Ajouter toutes les configs détectées
            for config in configs:
                cmd.extend(["-c", config])
            
            cmd.append(str(project_path))
            
            logger.info(f"Commande Semgrep: {' '.join(cmd[:10])}... (chemin tronqué)")

            try:
                # Exécuter Semgrep de manière asynchrone avec timeout
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                
                # Timeout global augmenté pour permettre l'analyse de tous les fichiers
                # Avec plusieurs configs, Semgrep peut prendre plus de temps
                logger.info(f"Lancement de Semgrep sur {project_path} avec {len([x for x in cmd if x == '-c'])} configs")
                try:
                    stdout, stderr = await asyncio.wait_for(
                        process.communicate(),
                        timeout=600.0  # 10 minutes pour analyser tous les fichiers avec toutes les règles
                    )
                except asyncio.TimeoutError:
                    process.kill()
                    logger.error("Semgrep execution timeout (>600s)")
                    return {
                        "status": "error",
                        "error": "Semgrep execution timeout (>600s)",
                    }

                # Parser la sortie même si le code de retour n'est pas 0
                # Semgrep peut retourner un code d'erreur même avec des résultats valides
                output = stdout.decode() if stdout else ""
                stderr_output = stderr.decode() if stderr else ""
                
                # Logger les erreurs stderr pour debug
                if stderr_output.strip():
                    logger.warning(f"Semgrep stderr: {stderr_output[:500]}")
                
                # Parser la sortie JSON
                try:
                    if not output.strip():
                        # Pas de sortie, vraie erreur
                        error_msg = f"Semgrep failed with return code {process.returncode}, no output"
                        if stderr_output:
                            error_msg += f": {stderr_output[:500]}"
                        logger.error(error_msg)
                        return {
                            "status": "error",
                            "error": error_msg,
                            "tool": SemgrepService.TOOL_NAME,
                            "results": [],
                            "errors": [{"message": error_msg}],
                            "stats": {},
                            "analyzed_files": [],
                        }
                    
                    data = json.loads(output)
                    # Si on a du JSON valide, continuer même avec un code d'erreur
                    if process.returncode != 0:
                        logger.warning(f"Semgrep a retourné un code d'erreur {process.returncode} mais la sortie JSON est valide")
                    
                    # Logger des statistiques pour déboguer
                    # Vérifier les résultats dans data.results et raw_output.results
                    results_count = len(data.get("results", []))
                    if results_count == 0 and "raw_output" in data:
                        raw_output = data.get("raw_output", {})
                        if isinstance(raw_output, dict):
                            results_count = len(raw_output.get("results", []))
                    
                    errors_count = len(data.get("errors", []))
                    stats = data.get("stats", {})
                    
                    # Extraire les fichiers analysés depuis stats ou raw_output
                    paths_scanned = []
                    if stats and "paths" in stats:
                        paths = stats.get("paths", {})
                        if isinstance(paths, dict):
                            paths_scanned = paths.get("scanned", [])
                        elif isinstance(paths, list):
                            paths_scanned = paths
                    elif "paths" in data:
                        # Semgrep peut aussi retourner paths directement dans data
                        paths_data = data.get("paths", {})
                        if isinstance(paths_data, dict):
                            paths_scanned = paths_data.get("scanned", [])
                        elif isinstance(paths_data, list):
                            paths_scanned = paths_data
                    
                    logger.info(f"Semgrep: {results_count} résultats, {errors_count} erreurs, {len(paths_scanned)} fichiers analysés")
                    
                    # Si aucun résultat, logger plus d'informations pour déboguer
                    if results_count == 0:
                        logger.warning(f"Semgrep n'a trouvé aucun résultat sur {len(paths_scanned)} fichiers analysés")
                        if stats:
                            logger.warning(f"Stats complètes: {json.dumps(stats, indent=2)[:500]}")
                        # Logger la structure de data pour debug
                        logger.info(f"data keys: {list(data.keys())}")
                        if "paths" in data:
                            logger.info(f"data.paths type: {type(data.get('paths'))}, content: {str(data.get('paths'))[:200]}")
                        # Logger quelques exemples de fichiers analysés
                        if paths_scanned:
                            logger.info(f"Exemples de fichiers analysés: {paths_scanned[:5]}")
                    
                except json.JSONDecodeError as e:
                    # Logger la sortie brute pour déboguer
                    logger.error(f"Erreur de parsing JSON Semgrep. Sortie (premiers 1000 chars): {output[:1000]}")
                    return {
                        "status": "error",
                        "error": f"Invalid JSON from Semgrep: {str(e)}",
                    }

                # Extraire les fichiers analysés depuis les stats
                analyzed_files = []
                stats = data.get("stats", {})
                
                # Semgrep peut retourner paths directement dans data (pas dans stats)
                if "paths" in data:
                    paths_data = data.get("paths", {})
                    if isinstance(paths_data, dict):
                        analyzed_files = paths_data.get("scanned", [])
                    elif isinstance(paths_data, list):
                        analyzed_files = paths_data
                
                # Semgrep retourne aussi les fichiers analysés dans stats.paths.scanned
                if not analyzed_files and "paths" in stats:
                    paths = stats.get("paths", {})
                    if isinstance(paths, dict):
                        if "scanned" in paths:
                            analyzed_files = paths.get("scanned", [])
                    elif isinstance(paths, list):
                        analyzed_files = paths
                
                # Fallback: utiliser stats.targets si disponible
                if not analyzed_files and "targets" in stats:
                    analyzed_files = stats.get("targets", [])
                
                # Extraire aussi les fichiers depuis les résultats (fichiers avec vulnérabilités)
                files_from_results = set()
                results_list = data.get("results", [])
                
                for result in results_list:
                    file_path = result.get("path")
                    if file_path:
                        files_from_results.add(file_path)
                
                # Combiner les fichiers analysés et ceux avec vulnérabilités
                all_analyzed = set(analyzed_files) | files_from_results
                analyzed_files = sorted(list(all_analyzed))
                
                # Si toujours pas de fichiers, utiliser _list_all_code_files comme fallback
                if not analyzed_files:
                    from app.services.scan_orchestrator import ScanOrchestrator
                    orchestrator = ScanOrchestrator(None)
                    analyzed_files = sorted(list(orchestrator._list_all_code_files(project_path)))
                    logger.info(f"Fallback: {len(analyzed_files)} fichiers trouvés via _list_all_code_files")
                
                # S'assurer que les résultats sont bien extraits
                results_list = data.get("results", [])
                
                return {
                    "status": "success",
                    "tool": SemgrepService.TOOL_NAME,
                    "results": results_list,  # Utiliser la liste extraite
                    "errors": data.get("errors", []),
                    "stats": stats if stats else {},  # Utiliser stats extrait
                    "analyzed_files": analyzed_files,  # Ajouter la liste des fichiers analysés
                    "raw_output": data,  # Garder les données brutes pour le parsing
                }

            except subprocess.TimeoutExpired:
                return {
                    "status": "error",
                    "error": "Semgrep process timeout",
                }
            except Exception as e:
                return {
                    "status": "error",
                    "error": str(e),
                }

        except FileNotFoundError:
            return {
                "status": "error",
                "error": "Semgrep is not installed. Install with: pip install semgrep",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }

    @staticmethod
    def parse_vulnerabilities(semgrep_results: dict) -> list[dict]:
        """
        Convertit les résultats Semgrep en format vulnérabilité standardisé.
        
        Args:
            semgrep_results: Résultats bruts de Semgrep
            
        Returns:
            Liste de vulnérabilités standardisées
        """
        vulnerabilities = []

        if semgrep_results.get("status") != "success":
            logger.warning(f"Semgrep status n'est pas 'success': {semgrep_results.get('status')}")
            return vulnerabilities

        # Semgrep peut retourner les résultats dans "results" ou dans "raw_output.results"
        results = semgrep_results.get("results", [])
        
        # Si pas de résultats dans "results", chercher dans "raw_output"
        if not results and "raw_output" in semgrep_results:
            raw_output = semgrep_results.get("raw_output", {})
            if isinstance(raw_output, dict):
                results = raw_output.get("results", [])
                if results:
                    logger.info(f"Résultats trouvés dans raw_output.results: {len(results)}")
                else:
                    logger.warning(f"raw_output.results est vide (type: {type(raw_output.get('results'))})")
                    # Logger la structure complète pour debug
                    logger.debug(f"raw_output keys: {list(raw_output.keys())}")
                    if "paths" in raw_output:
                        logger.debug(f"raw_output.paths: {raw_output.get('paths')}")
        
        # Si toujours pas de résultats, logger toutes les clés pour debug
        if not results:
            logger.warning(f"Aucun résultat trouvé. Clés disponibles: {list(semgrep_results.keys())}")
            if "raw_output" in semgrep_results:
                raw_output = semgrep_results.get("raw_output", {})
                if isinstance(raw_output, dict):
                    logger.warning(f"Clés dans raw_output: {list(raw_output.keys())}")
                    if "results" in raw_output:
                        logger.warning(f"Type de raw_output.results: {type(raw_output.get('results'))}")
        
        logger.info(f"Parsing de {len(results)} résultats Semgrep depuis semgrep_results")
        
        if not results:
            logger.warning("Aucun résultat trouvé dans la sortie Semgrep. Vérifiez la configuration des règles.")
            logger.warning(f"Keys disponibles dans semgrep_results: {list(semgrep_results.keys())}")
            
            # Logger les erreurs si présentes
            errors = semgrep_results.get("errors", [])
            if not errors and "raw_output" in semgrep_results:
                raw_output = semgrep_results.get("raw_output", {})
                if isinstance(raw_output, dict):
                    errors = raw_output.get("errors", [])
            
            if errors:
                logger.warning(f"Semgrep a retourné {len(errors)} erreurs:")
                for error in errors[:5]:  # Logger les 5 premières erreurs
                    logger.warning(f"  - {error}")
            
            # Logger les stats pour comprendre ce qui s'est passé
            stats = semgrep_results.get("stats", {})
            if not stats and "raw_output" in semgrep_results:
                raw_output = semgrep_results.get("raw_output", {})
                if isinstance(raw_output, dict):
                    stats = raw_output.get("stats", {})
            
            if stats:
                logger.info(f"Stats Semgrep: {json.dumps(stats, indent=2)[:1000]}")

        for result in results:
            try:
                # Extraire les informations de position précises
                start = result.get("start", {})
                end = result.get("end", {})
                
                # Extraire le numéro de ligne de début
                line_start = start.get("line") if isinstance(start, dict) else None
                if line_start is None:
                    # Fallback: utiliser line si disponible directement dans result
                    line_start = result.get("line")
                
                # Extraire le numéro de ligne de fin
                line_end = end.get("line") if isinstance(end, dict) else None
                if line_end is None:
                    line_end = line_start  # Si pas de fin, utiliser le début
                
                # Extraire le numéro de colonne pour plus de précision
                col_start = start.get("col") if isinstance(start, dict) else None
                col_end = end.get("col") if isinstance(end, dict) else None
                
                # Construire le titre avec plus de détails
                check_id = result.get("check_id", "Unknown")
                extra = result.get("extra", {})
                if not isinstance(extra, dict):
                    extra = {}
                
                message = extra.get("message", "Security issue detected")
                metadata = extra.get("metadata", {})
                if isinstance(metadata, dict):
                    rule_id = metadata.get("rule_id", check_id)
                else:
                    rule_id = check_id
                
                # Extraire le code source de la vulnérabilité si disponible
                source_code = extra.get("lines", "")
                if not source_code:
                    source_code = result.get("extra", {}).get("code", "")
                
                # Extraire la sévérité depuis metadata ou utiliser une valeur par défaut
                severity = SemgrepService._map_severity(extra.get("severity", "INFO"))
                
                # Extraire le chemin du fichier (relatif au projet)
                file_path = result.get("path", "")
                
                # Extraire CWE depuis metadata
                cwe_id = None
                if isinstance(metadata, dict):
                    cwe_list = metadata.get("cwe", [])
                    if cwe_list and isinstance(cwe_list, list) and len(cwe_list) > 0:
                        cwe_id = cwe_list[0] if isinstance(cwe_list[0], str) else None
                    elif isinstance(metadata.get("cwe"), str):
                        cwe_id = metadata.get("cwe")
                
                vuln = {
                    "title": f"{check_id}: {message}",
                    "description": message,
                    "file_path": file_path,
                    "line_start": line_start,
                    "line_end": line_end,
                    "col_start": col_start,
                    "col_end": col_end,
                    "severity": severity,
                    "rule_id": rule_id,  # Pour le mapping OWASP
                    "check_id": check_id,  # Pour le mapping OWASP aussi
                    "code_snippet": source_code,
                    "cwe_id": cwe_id,
                    "tool": "semgrep",
                }
                
                vulnerabilities.append(vuln)
                logger.debug(f"Vulnérabilité parsée: {check_id} dans {file_path}:{line_start}")
                
            except Exception as e:
                logger.error(f"Erreur lors du parsing d'un résultat Semgrep: {e}")
                logger.error(f"Résultat problématique: {json.dumps(result, indent=2)[:500]}")
                import traceback
                logger.error(traceback.format_exc())
                continue

        logger.info(f"Parsé {len(vulnerabilities)} vulnérabilités depuis Semgrep")
        return vulnerabilities

    @staticmethod
    def _map_severity(semgrep_severity: str) -> str:
        """Mappe la sévérité Semgrep vers un standard."""
        mapping = {
            "ERROR": "critical",
            "WARNING": "high",
            "INFO": "medium",
        }
        return mapping.get(semgrep_severity, "low")
