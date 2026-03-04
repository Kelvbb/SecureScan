"""Orchestrateur pour lancer tous les outils de sécurité en parallèle."""

import asyncio
from datetime import datetime
from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.scan import Scan
from app.models.tool_execution import ToolExecution
from app.models.vulnerability import Vulnerability
from app.services.semgrep_service import SemgrepService
from app.services.pip_audit_service import PipAuditService
from app.services.npm_audit_service import NpmAuditService
from app.services.trufflehog_service import TruffleHogService


class ScanOrchestrator:
    """Orchestrateur pour lancer tous les outils de sécurité."""

    def __init__(self, db: Session):
        """
        Initialise l'orchestrateur.
        
        Args:
            db: Sesion SQLAlchemy
        """
        self.db = db
        self.services = [
            (SemgrepService.TOOL_NAME, SemgrepService),
            (PipAuditService.TOOL_NAME, PipAuditService),
            (NpmAuditService.TOOL_NAME, NpmAuditService),
            (TruffleHogService.TOOL_NAME, TruffleHogService),
        ]

    async def run_scan(self, scan_id: UUID, project_path: str) -> dict:
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
            # Préparer les tâches asynchrones
            tasks = [
                self._run_tool(tool_name, service, scan_id, project_path)
                for tool_name, service in self.services
            ]

            # Exécuter tous les outils en parallèle
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Traiter les résultats
            all_vulns = []
            tool_executions = []

            for (tool_name, _), result in zip(self.services, results):
                if isinstance(result, Exception):
                    # Enregistrer l'erreur
                    tool_exec = ToolExecution(
                        scan_id=scan_id,
                        status="error",
                        raw_output={"error": str(result)},
                    )
                    self.db.add(tool_exec)
                    continue

                # Créer l'enregistrement ToolExecution
                tool_exec = ToolExecution(
                    scan_id=scan_id,
                    status=result.get("status", "error"),
                    raw_output=result,
                    started_at=datetime.utcnow(),
                    finished_at=datetime.utcnow(),
                )
                self.db.add(tool_exec)
                self.db.flush()

                # Parser les vulnérabilités
                vulns = self._parse_vulnerabilities(tool_name, result)
                for vuln_data in vulns:
                    vuln = Vulnerability(
                        scan_id=scan_id,
                        tool_execution_id=tool_exec.id,
                        title=vuln_data["title"],
                        description=vuln_data.get("description"),
                        file_path=vuln_data.get("file_path"),
                        line_start=vuln_data.get("line_start"),
                        line_end=vuln_data.get("line_end"),
                        severity=vuln_data.get("severity", "medium"),
                        cve_id=vuln_data.get("cve_id"),
                        cwe_id=vuln_data.get("cwe_id"),
                    )
                    self.db.add(vuln)
                    all_vulns.append(vuln_data)

            # Mettre à jour le statut du scan
            scan.status = "completed"
            scan.finished_at = datetime.utcnow()
            self.db.commit()

            return {
                "scan_id": str(scan_id),
                "status": "completed",
                "vulnerabilities_count": len(all_vulns),
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
        elif tool_name == "pip-audit":
            return await service.run(project_path)
        elif tool_name == "npm-audit":
            return await service.run(project_path)
        elif tool_name == "truffleHog":
            return await service.run(project_path)

    def _parse_vulnerabilities(self, tool_name: str, result: dict) -> list[dict]:
        """
        Parse les vulnérabilités à partir des résultats d'un outil.
        
        Args:
            tool_name: Nom de l'outil
            result: Résultats bruts de l'outil
            
        Returns:
            Liste des vulnérabilités parsées
        """
        if tool_name == "semgrep":
            return SemgrepService.parse_vulnerabilities(result)
        elif tool_name == "pip-audit":
            return PipAuditService.parse_vulnerabilities(result)
        elif tool_name == "npm-audit":
            return NpmAuditService.parse_vulnerabilities(result)
        elif tool_name == "truffleHog":
            return TruffleHogService.parse_vulnerabilities(result)
        return []
