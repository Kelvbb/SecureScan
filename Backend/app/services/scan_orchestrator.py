"""
Backend\app\services\scan_orchestrator.py
Orchestrateur pour lancer tous les outils de sécurité en parallèle.
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.scan import Scan
from app.models.tool_execution import ToolExecution
from app.models.vulnerability import Vulnerability
from app.services.semgrep_service import SemgrepService
from app.services.bandit_service import BanditService
from app.services.eslint_service import ESLintService
from app.services.pip_audit_service import PipAuditService, NpmAuditService
from app.services.trufflehog_service import TruffleHogService
from app.services.technology_detector import TechnologyDetector
from app.core.classification import (
    map_rule_to_owasp,
    map_severity_to_owasp_default,
    normalize_severity,
)

logger = logging.getLogger(__name__)


class ScanOrchestrator:
    """Orchestrateur pour lancer tous les outils de sécurité."""

    def __init__(self, db: Session):
        """
        Initialise l'orchestrateur.

        Args:
            db: Sesion SQLAlchemy
        """
        self.db = db
        # Services disponibles (seront filtrés selon les technologies détectées)
        self.available_services = {
            SemgrepService.TOOL_NAME: SemgrepService,
            BanditService.TOOL_NAME: BanditService,  # SAST Python
            ESLintService.TOOL_NAME: ESLintService,  # SAST JavaScript/TypeScript
            PipAuditService.TOOL_NAME: PipAuditService,
            NpmAuditService.TOOL_NAME: NpmAuditService,
            TruffleHogService.TOOL_NAME: TruffleHogService,
        }
        self.services = []  # Sera rempli selon les technologies détectées

    async def run_scan(self, scan_id: UUID, project_path: str) -> dict:
        """
        Lance tous les outils de sécurité en parallèle.

        Détecte d'abord les technologies utilisées dans le projet,
        puis adapte les outils à exécuter en conséquence.
        """
        # Détecter les technologies utilisées
        logger.info("🔍 Détection des technologies utilisées dans le projet...")
        technologies = TechnologyDetector.detect(project_path)

        # Déterminer les outils à exécuter selon les technologies
        tools_to_run = TechnologyDetector.get_tools_to_run(technologies)
        logger.info(f"📦 Outils sélectionnés: {', '.join(tools_to_run)}")

        # Filtrer les services selon les outils sélectionnés
        self.services = [
            (tool_name, service_class)
            for tool_name, service_class in self.available_services.items()
            if tool_name in tools_to_run
        ]

        # Configurer Semgrep avec les règles adaptées aux technologies
        if SemgrepService.TOOL_NAME in tools_to_run:
            semgrep_configs = TechnologyDetector.get_semgrep_configs(technologies)
            logger.info(f"🔧 Configurations Semgrep: {', '.join(semgrep_configs)}")
            # Stocker les configs pour SemgrepService (sera utilisé lors de l'exécution)
            SemgrepService._detected_configs = semgrep_configs

        # Continuer avec l'exécution normale
        return await self._execute_scan(scan_id, project_path)

    async def _execute_scan(self, scan_id: UUID, project_path: str) -> dict:
        """
        Lance tous les outils de sécurité en parallèle.

        Args:
            scan_id: ID du scan
            project_path: Chemin du projet à analyser

        Returns:
            Dict avec les résultats agrégés
        """
        scan = self.db.get(Scan, scan_id)
        if not scan:
            raise ValueError(f"Scan {scan_id} not found")

        # Mettre à jour le statut du scan
        scan.status = "running"
        scan.started_at = datetime.utcnow()
        self.db.commit()

        try:
            # Préparer les tâches asynchrones avec suivi du temps de début
            tool_start_times = {}
            tasks = []
            for tool_name, service in self.services:
                tool_start_times[tool_name] = datetime.utcnow()
                tasks.append(self._run_tool(tool_name, service, scan_id, project_path))

            # Exécuter tous les outils en parallèle
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Traiter les résultats
            all_vulns = []
            tool_executions = []
            tool_end_time = datetime.utcnow()

            for (tool_name, _), result in zip(self.services, results):
                # Utiliser le temps de début enregistré avant l'exécution
                tool_start_time = tool_start_times.get(tool_name, tool_end_time)

                if isinstance(result, Exception):
                    # Enregistrer l'erreur
                    error_msg = str(result)
                    logger.error(f"Tool {tool_name} raised exception: {error_msg}")
                    tool_exec = ToolExecution(
                        scan_id=scan_id,
                        status="error",
                        raw_output={"error": error_msg, "tool": tool_name},
                        started_at=tool_start_time,
                        finished_at=tool_end_time,
                    )
                    self.db.add(tool_exec)
                    continue

                # Vérifier que result n'est pas None
                if result is None:
                    logger.error(
                        f"Tool {tool_name} returned None instead of a result dict"
                    )
                    tool_exec = ToolExecution(
                        scan_id=scan_id,
                        status="error",
                        raw_output={"error": "Tool returned None", "tool": tool_name},
                        started_at=tool_start_time,
                        finished_at=tool_end_time,
                    )
                    self.db.add(tool_exec)
                    continue

                # Logger le statut de chaque outil
                tool_status = result.get("status", "unknown")
                logger.info(f"Tool {tool_name} returned status: {tool_status}")

                if tool_status == "error":
                    error_msg = result.get("error", "Unknown error")
                    logger.error(f"Tool {tool_name} returned error: {error_msg}")
                elif tool_status == "skipped":
                    reason = result.get("reason", "Unknown reason")
                    logger.info(f"Tool {tool_name} was skipped: {reason}")

                # Extraire les fichiers analysés
                analyzed_files = self._extract_analyzed_files(
                    tool_name, result, project_path
                )
                result["analyzed_files"] = analyzed_files

                # Créer l'enregistrement ToolExecution
                tool_exec = ToolExecution(
                    scan_id=scan_id,
                    status=result.get("status", "error"),
                    raw_output=result,
                    started_at=tool_start_time,
                    finished_at=tool_end_time,
                )
                self.db.add(tool_exec)
                self.db.flush()

                # Parser les vulnérabilités
                vulns = self._parse_vulnerabilities(tool_name, result)
                logger.info(
                    f"Tool {tool_name} parsed {len(vulns)} vulnerabilities from result"
                )

                # Logger les détails si aucune vulnérabilité n'est trouvée
                if len(vulns) == 0 and result.get("status") == "success":
                    logger.warning(
                        f"Tool {tool_name} returned success but no vulnerabilities found"
                    )
                    logger.warning(f"Result keys: {list(result.keys())}")
                    if "results" in result:
                        logger.warning(
                            f"Number of results in raw_output: {len(result.get('results', []))}"
                        )
                    if "raw_output" in result and isinstance(
                        result["raw_output"], dict
                    ):
                        raw_results = result["raw_output"].get("results", [])
                        logger.warning(
                            f"Number of results in raw_output.results: {len(raw_results)}"
                        )
                        if raw_results:
                            logger.info(
                                f"First result example: {json.dumps(raw_results[0], indent=2)[:500]}"
                            )

                for vuln_data in vulns:
                    try:
                        # Normaliser la sévérité
                        normalized_severity = normalize_severity(
                            vuln_data.get("severity", "medium")
                        )

                        # Mapper vers OWASP
                        # Essayer rule_id, puis check_id, puis le titre pour extraire des indices
                        rule_id = vuln_data.get("rule_id") or vuln_data.get("check_id")
                        if not rule_id:
                            # Essayer d'extraire depuis le titre
                            title = vuln_data.get("title", "")
                            if ":" in title:
                                rule_id = title.split(":")[0]

                        owasp_category_id = map_rule_to_owasp(rule_id, tool_name)
                        if not owasp_category_id:
                            # Fallback: utiliser le mapping par défaut basé sur la sévérité
                            owasp_category_id = map_severity_to_owasp_default(
                                normalized_severity
                            )

                        logger.debug(
                            f"Mapping OWASP pour {rule_id} ({tool_name}): {owasp_category_id}"
                        )

                        # Tronquer cwe_id et cve_id si nécessaire (limite de 50 caractères en base)
                        cwe_id = vuln_data.get("cwe_id")
                        if cwe_id and len(cwe_id) > 50:
                            # Extraire juste le numéro CWE si c'est trop long
                            import re

                            cwe_match = re.search(r"CWE-?\d+", cwe_id)
                            if cwe_match:
                                cwe_id = cwe_match.group(0)
                            else:
                                cwe_id = cwe_id[:50]

                        cve_id = vuln_data.get("cve_id")
                        if cve_id and len(cve_id) > 50:
                            cve_id = cve_id[:50]

                        # Tronquer le titre si nécessaire (limite Text mais on limite quand même)
                        title = vuln_data["title"]
                        if len(title) > 500:
                            title = title[:497] + "..."

                        vuln = Vulnerability(
                            scan_id=scan_id,
                            tool_execution_id=tool_exec.id,
                            title=title,
                            description=vuln_data.get("description"),
                            file_path=vuln_data.get("file_path"),
                            line_start=vuln_data.get("line_start"),
                            line_end=vuln_data.get("line_end"),
                            severity=normalized_severity,  # Utiliser la sévérité normalisée
                            cve_id=cve_id,
                            cwe_id=cwe_id,
                            owasp_category_id=owasp_category_id,  # Ajouter le mapping OWASP
                        )
                        self.db.add(vuln)
                        all_vulns.append(vuln_data)
                        logger.debug(
                            f"Ajouté vulnérabilité: {vuln_data.get('title', 'Unknown')[:50]} dans {vuln_data.get('file_path', 'Unknown')} [OWASP: {owasp_category_id}]"
                        )
                    except Exception as e:
                        logger.error(
                            f"Erreur lors de l'ajout d'une vulnérabilité en base: {e}"
                        )
                        logger.error(
                            f"Données de la vulnérabilité: {json.dumps(vuln_data, indent=2)[:500]}"
                        )
                        import traceback

                        logger.error(traceback.format_exc())
                        continue

                # Flush et commit pour s'assurer que les vulnérabilités sont bien enregistrées
                try:
                    self.db.flush()
                    logger.info(
                        f"Flush réussi: {len(vulns)} vulnérabilités de {tool_name} ajoutées en base"
                    )

                    # Commit immédiatement après chaque outil pour garantir la persistance
                    self.db.commit()
                    logger.info(
                        f"Commit réussi: {len(vulns)} vulnérabilités de {tool_name} sauvegardées en base de données"
                    )

                    # Attendre un peu pour s'assurer que le commit est bien propagé
                    time.sleep(0.5)

                    # Vérifier que les vulnérabilités sont bien en base
                    count_in_db = (
                        self.db.query(Vulnerability)
                        .filter(
                            Vulnerability.scan_id == scan_id,
                            Vulnerability.tool_execution_id == tool_exec.id,
                        )
                        .count()
                    )
                    logger.info(
                        f"Vérification: {count_in_db} vulnérabilités de {tool_name} trouvées en base après commit"
                    )

                    if count_in_db != len(vulns):
                        logger.warning(
                            f"ATTENTION: {len(vulns)} vulnérabilités parsées mais seulement {count_in_db} en base!"
                        )
                        # Réessayer le commit si nécessaire
                        if count_in_db == 0 and len(vulns) > 0:
                            logger.warning(
                                f"Tentative de nouveau commit pour {tool_name}..."
                            )
                            self.db.commit()
                            time.sleep(0.5)
                            count_in_db = (
                                self.db.query(Vulnerability)
                                .filter(
                                    Vulnerability.scan_id == scan_id,
                                    Vulnerability.tool_execution_id == tool_exec.id,
                                )
                                .count()
                            )
                            logger.info(
                                f"Après nouveau commit: {count_in_db} vulnérabilités en base"
                            )
                except Exception as e:
                    logger.error(f"Erreur lors du flush/commit des vulnérabilités: {e}")
                    import traceback

                    logger.error(traceback.format_exc())
                    self.db.rollback()
                    # Continuer avec les autres outils même en cas d'erreur

                # Logger le nombre de vulnérabilités trouvées
                logger.info(
                    f"Tool {tool_name} found {len(vulns)} vulnerabilities and analyzed {len(analyzed_files)} files"
                )

            # Attendre un peu pour s'assurer que tous les commits sont bien propagés
            time.sleep(1)

            # Vérifier le nombre total de vulnérabilités en base avant de finaliser
            total_in_db = (
                self.db.query(Vulnerability)
                .filter(Vulnerability.scan_id == scan_id)
                .count()
            )
            logger.info(
                f"Total de vulnérabilités en base pour le scan {scan_id}: {total_in_db}"
            )

            if total_in_db == 0 and len(all_vulns) > 0:
                logger.error(
                    f"ERREUR CRITIQUE: {len(all_vulns)} vulnérabilités parsées mais aucune en base!"
                )
                logger.error("Tentative de réinsertion...")
                # Réessayer d'insérer les vulnérabilités
                for vuln_data in all_vulns[:10]:  # Limiter à 10 pour le test
                    try:
                        # Récupérer la tool_execution correspondante
                        tool_exec = (
                            self.db.query(ToolExecution)
                            .filter(ToolExecution.scan_id == scan_id)
                            .first()
                        )
                        if tool_exec:
                            normalized_severity = normalize_severity(
                                vuln_data.get("severity", "medium")
                            )
                            rule_id = vuln_data.get("rule_id") or vuln_data.get(
                                "check_id"
                            )
                            # Mapper selon l'outil
                            tool_for_mapping = (
                                tool_name
                                if tool_name in ["semgrep", "bandit", "eslint"]
                                else "semgrep"
                            )
                            owasp_category_id = map_rule_to_owasp(
                                rule_id, tool_for_mapping
                            )
                            if not owasp_category_id:
                                owasp_category_id = map_severity_to_owasp_default(
                                    normalized_severity
                                )

                            # Tronquer cwe_id et cve_id si nécessaire
                            cwe_id = vuln_data.get("cwe_id")
                            if cwe_id and len(cwe_id) > 50:
                                import re

                                cwe_match = re.search(r"CWE-?\d+", cwe_id)
                                if cwe_match:
                                    cwe_id = cwe_match.group(0)
                                else:
                                    cwe_id = cwe_id[:50]

                            cve_id = vuln_data.get("cve_id")
                            if cve_id and len(cve_id) > 50:
                                cve_id = cve_id[:50]

                            title = vuln_data["title"]
                            if len(title) > 500:
                                title = title[:497] + "..."

                            vuln = Vulnerability(
                                scan_id=scan_id,
                                tool_execution_id=tool_exec.id,
                                title=title,
                                description=vuln_data.get("description"),
                                file_path=vuln_data.get("file_path"),
                                line_start=vuln_data.get("line_start"),
                                line_end=vuln_data.get("line_end"),
                                severity=normalized_severity,
                                cve_id=cve_id,
                                cwe_id=cwe_id,
                                owasp_category_id=owasp_category_id,
                            )
                            self.db.add(vuln)
                    except Exception as e:
                        logger.error(f"Erreur lors de la réinsertion: {e}")

                try:
                    self.db.commit()
                    logger.info("Réinsertion réussie")
                except Exception as e:
                    logger.error(f"Erreur lors du commit de réinsertion: {e}")
                    self.db.rollback()

            # Mettre à jour le statut du scan
            scan.status = "completed"
            scan.finished_at = datetime.utcnow()

            # Commit final
            try:
                self.db.commit()
                logger.info(
                    f"Scan {scan_id} marqué comme terminé avec {total_in_db} vulnérabilités en base"
                )

                # Attendre un peu et vérifier une dernière fois
                time.sleep(1)
                final_check = (
                    self.db.query(Vulnerability)
                    .filter(Vulnerability.scan_id == scan_id)
                    .count()
                )
                logger.info(
                    f"Vérification finale: {final_check} vulnérabilités en base après commit final"
                )

                if final_check != total_in_db:
                    logger.warning(
                        f"Différence détectée: {total_in_db} avant commit, {final_check} après"
                    )
            except Exception as e:
                logger.error(f"Erreur lors du commit final: {e}")
                self.db.rollback()
                raise

            return {
                "scan_id": str(scan_id),
                "status": "completed",
                "vulnerabilities_count": total_in_db,  # Utiliser le count réel de la DB
                "vulnerabilities": all_vulns,
            }

        except Exception as e:
            scan.status = "error"
            scan.finished_at = datetime.utcnow()
            self.db.commit()
            raise ValueError(f"Scan failed: {str(e)}")

    async def _run_tool(
        self,
        tool_name: str,
        service,
        scan_id: UUID,
        project_path: str,
    ) -> dict:
        """
        Lance un outil de sécurité.

        Args:
            tool_name: Nom de l'outil
            service: Service de l'outil
            scan_id: ID du scan
            project_path: Chemin du projet

        Returns:
            Résultats du tool
        """
        if tool_name == "semgrep":
            return await service.run(project_path)
        elif tool_name == "bandit":
            return await service.run(project_path)
        elif tool_name == "eslint":
            return await service.run(project_path)
        elif tool_name == "pip-audit":
            return await service.run(project_path)
        elif tool_name == "npm-audit":
            return await service.run(project_path)
        elif tool_name == "truffleHog":
            return await service.run(project_path)
        else:
            logger.warning(f"Outil inconnu: {tool_name}")
            return {
                "status": "error",
                "error": f"Unknown tool: {tool_name}",
                "tool": tool_name,
                "results": [],
                "errors": [],
                "stats": {},
                "analyzed_files": [],
            }

    def _list_all_code_files(self, project_path: str) -> set[str]:
        """
        Liste tous les fichiers de code dans le projet (récursivement).

        Args:
            project_path: Chemin du projet

        Returns:
            Set des chemins de fichiers relatifs
        """
        files = set()
        project_path_obj = Path(project_path)

        if not project_path_obj.exists():
            return files

        # Extensions de fichiers de code à inclure
        code_extensions = {
            ".py",
            ".js",
            ".ts",
            ".jsx",
            ".tsx",
            ".php",
            ".java",
            ".go",
            ".rb",
            ".swift",
            ".kt",
            ".scala",
            ".c",
            ".cpp",
            ".cs",
            ".rs",
            ".sh",
            ".bash",
            ".yaml",
            ".yml",
            ".json",
            ".xml",
            ".html",
            ".css",
            ".scss",
            ".sass",
            ".vue",
            ".svelte",
            ".dart",
            ".lua",
            ".pl",
            ".pm",
            ".r",
            ".m",
            ".mm",
        }

        # Parcourir récursivement tous les fichiers
        for file_path in project_path_obj.rglob("*"):
            if file_path.is_file():
                # Ignorer les fichiers dans .git, node_modules, __pycache__, etc.
                parts = file_path.parts
                if any(part.startswith(".") and part != "." for part in parts):
                    continue
                if "node_modules" in parts or "__pycache__" in parts or ".git" in parts:
                    continue

                # Inclure si c'est un fichier de code
                if file_path.suffix.lower() in code_extensions or not file_path.suffix:
                    # Rendre le chemin relatif au projet
                    try:
                        rel_path = file_path.relative_to(project_path_obj)
                        files.add(str(rel_path))
                    except ValueError:
                        # Si le chemin ne peut pas être rendu relatif, utiliser le chemin absolu
                        files.add(str(file_path))

        return files

    def _extract_analyzed_files(
        self, tool_name: str, result: dict, project_path: str | None = None
    ) -> list[str]:
        """
        Extrait la liste des fichiers analysés depuis les résultats d'un outil.

        Args:
            tool_name: Nom de l'outil
            result: Résultats bruts de l'outil
            project_path: Chemin du projet (pour lister tous les fichiers si nécessaire)

        Returns:
            Liste des chemins de fichiers analysés
        """
        files = set()

        if tool_name == "semgrep":
            # Semgrep retourne les fichiers dans results[].path (fichiers avec vulnérabilités)
            for finding in result.get("results", []):
                file_path = finding.get("path")
                if file_path:
                    # Normaliser le chemin (enlever le préfixe du projet si présent)
                    if project_path and file_path.startswith(project_path):
                        try:
                            file_path = str(
                                Path(file_path).relative_to(Path(project_path))
                            )
                        except ValueError:
                            pass
                    files.add(file_path)

            # Semgrep retourne aussi tous les fichiers analysés dans analyzed_files
            analyzed_files = result.get("analyzed_files", [])
            if analyzed_files:
                for file_path in analyzed_files:
                    if isinstance(file_path, str):
                        # Normaliser le chemin
                        if project_path and file_path.startswith(project_path):
                            try:
                                file_path = str(
                                    Path(file_path).relative_to(Path(project_path))
                                )
                            except ValueError:
                                pass
                        files.add(file_path)
                    elif isinstance(file_path, dict) and "path" in file_path:
                        file_path_str = file_path["path"]
                        if project_path and file_path_str.startswith(project_path):
                            try:
                                file_path_str = str(
                                    Path(file_path_str).relative_to(Path(project_path))
                                )
                            except ValueError:
                                pass
                        files.add(file_path_str)

            # Fallback: utiliser stats.paths.scanned si analyzed_files n'est pas disponible
            if not analyzed_files:
                stats = result.get("stats", {})
                if "paths" in stats:
                    paths = stats.get("paths", {})
                    if isinstance(paths, dict) and "scanned" in paths:
                        for file_path in paths.get("scanned", []):
                            if isinstance(file_path, str):
                                if project_path and file_path.startswith(project_path):
                                    try:
                                        file_path = str(
                                            Path(file_path).relative_to(
                                                Path(project_path)
                                            )
                                        )
                                    except ValueError:
                                        pass
                                files.add(file_path)
                    elif isinstance(paths, list):
                        for file_path in paths:
                            if isinstance(file_path, str):
                                if project_path and file_path.startswith(project_path):
                                    try:
                                        file_path = str(
                                            Path(file_path).relative_to(
                                                Path(project_path)
                                            )
                                        )
                                    except ValueError:
                                        pass
                                files.add(file_path)
                elif "targets" in stats:
                    for target in stats.get("targets", []):
                        if isinstance(target, dict) and "path" in target:
                            file_path = target["path"]
                            if project_path and file_path.startswith(project_path):
                                try:
                                    file_path = str(
                                        Path(file_path).relative_to(Path(project_path))
                                    )
                                except ValueError:
                                    pass
                            files.add(file_path)
                        elif isinstance(target, str):
                            file_path = target
                            if project_path and file_path.startswith(project_path):
                                try:
                                    file_path = str(
                                        Path(file_path).relative_to(Path(project_path))
                                    )
                                except ValueError:
                                    pass
                            files.add(file_path)

            # Si on n'a toujours pas de fichiers, lister tous les fichiers du projet
            # (Semgrep analyse tous les fichiers mais ne les retourne que s'ils ont des vulnérabilités)
            if not files and project_path:
                all_files = self._list_all_code_files(project_path)
                files.update(all_files)

        elif tool_name == "truffleHog":
            # TruffleHog retourne les fichiers dans secrets[].path ou secrets[].file_path
            for secret in result.get("secrets", []):
                file_path = secret.get("path") or secret.get("file_path")
                if file_path:
                    files.add(file_path)

            # TruffleHog analyse tous les fichiers, donc on peut aussi lister tous les fichiers
            if project_path:
                all_files = self._list_all_code_files(project_path)
                files.update(all_files)
        elif tool_name == "pip-audit":
            # pip-audit analyse requirements.txt - chercher dans tout le projet
            if project_path:
                project_path_obj = Path(project_path)
                for req_file in project_path_obj.rglob("requirements.txt"):
                    try:
                        rel_path = req_file.relative_to(project_path_obj)
                        files.add(str(rel_path))
                    except ValueError:
                        files.add(str(req_file))
        elif tool_name == "npm-audit":
            # npm-audit analyse package.json - chercher dans tout le projet
            if project_path:
                project_path_obj = Path(project_path)
                for pkg_file in project_path_obj.rglob("package.json"):
                    try:
                        rel_path = pkg_file.relative_to(project_path_obj)
                        files.add(str(rel_path))
                    except ValueError:
                        files.add(str(pkg_file))

        return sorted(list(files))

    def _parse_vulnerabilities(self, tool_name: str, result: dict) -> list[dict]:
        """
        Parse les vulnérabilités à partir des résultats d'un outil.

        Args:
            tool_name: Nom de l'outil
            result: Résultats bruts de l'outil

        Returns:
            Liste des vulnérabilités parsées
        """
        logger.info(
            f"Parsing vulnérabilités pour {tool_name}, status: {result.get('status')}"
        )

        if tool_name == "semgrep":
            # Le résultat de Semgrep contient déjà les résultats dans "results"
            # Mais on doit s'assurer qu'on passe le bon format
            vulns = SemgrepService.parse_vulnerabilities(result)
            logger.info(f"Semgrep a retourné {len(vulns)} vulnérabilités après parsing")
            return vulns
        elif tool_name == "bandit":
            vulns = BanditService.parse_vulnerabilities(result)
            logger.info(f"Bandit a retourné {len(vulns)} vulnérabilités après parsing")
            return vulns
        elif tool_name == "eslint":
            vulns = ESLintService.parse_vulnerabilities(result)
            logger.info(f"ESLint a retourné {len(vulns)} vulnérabilités après parsing")
            return vulns
        elif tool_name == "pip-audit":
            return PipAuditService.parse_vulnerabilities(result)
        elif tool_name == "npm-audit":
            return NpmAuditService.parse_vulnerabilities(result)
        elif tool_name == "truffleHog":
            return TruffleHogService.parse_vulnerabilities(result)
        return []
