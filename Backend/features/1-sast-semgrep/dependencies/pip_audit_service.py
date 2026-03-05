"""Service pour lancer pip-audit ou npm audit et parser les résultats."""

import asyncio
import json
import subprocess
from pathlib import Path

from app.config import settings


class PipAuditService:
    """Service pour l'audit des dépendances Python avec pip-audit."""

    TOOL_NAME = "pip-audit"

    @staticmethod
    async def run(project_path: str) -> dict:
        """
        Lance pip-audit et retourne les résultats parsés.

        Args:
            project_path: Chemin du projet à analyser

        Returns:
            Dict avec les résultats parsés
        """
        if not settings.NPM_AUDIT_ENABLED:
            return {"status": "skipped", "reason": "Pip-audit not enabled"}

        try:
            # Vérifier si requirements.txt existe
            requirements_file = Path(project_path) / "requirements.txt"
            if not requirements_file.exists():
                return {
                    "status": "skipped",
                    "reason": "requirements.txt not found",
                }

            # Construire la commande pip-audit
            cmd = [
                "pip-audit",
                "--desc",
                f"--path={requirements_file}",
                "--format=json",
            ]

            # Exécuter pip-audit de manière asynchrone
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()

            # Parser la sortie JSON
            try:
                data = json.loads(stdout.decode())
            except json.JSONDecodeError:
                # pip-audit retourne parfois une sortie non-JSON quand tout est OK
                if "No known vulnerabilities" in stdout.decode():
                    data = {"vulnerabilities": []}
                else:
                    return {
                        "status": "error",
                        "error": "Failed to parse pip-audit JSON output",
                    }

            return {
                "status": "success",
                "tool": PipAuditService.TOOL_NAME,
                "vulnerabilities": data.get("vulnerabilities", []),
                "raw_output": data,
            }

        except FileNotFoundError:
            return {
                "status": "error",
                "error": "pip-audit is not installed",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }

    @staticmethod
    def parse_vulnerabilities(pip_audit_results: dict) -> list[dict]:
        """
        Convertit les résultats pip-audit en format vulnérabilité standardisé.

        Args:
            pip_audit_results: Résultats bruts de pip-audit

        Returns:
            Liste de vulnérabilités standardisées
        """
        vulnerabilities = []

        if pip_audit_results.get("status") != "success":
            return vulnerabilities

        for vuln in pip_audit_results.get("vulnerabilities", []):
            # Extraire les CVE IDs
            cve_ids = vuln.get("cve", [])
            cve_id = cve_ids[0] if cve_ids else None

            parsed_vuln = {
                "title": f"Vulnerable package: {vuln.get('name', 'Unknown')}",
                "description": vuln.get("description", ""),
                "file_path": "requirements.txt",
                "line_start": None,
                "line_end": None,
                "severity": "high",  # Les dépendances vulnérables sont considérées comme hautes
                "cve_id": cve_id,
                "cwe_id": None,
                "tool": "pip-audit",
            }
            vulnerabilities.append(parsed_vuln)

        return vulnerabilities


class NpmAuditService:
    """Service pour l'audit des dépendances Node.js avec npm audit."""

    TOOL_NAME = "npm-audit"

    @staticmethod
    async def run(project_path: str) -> dict:
        """
        Lance npm audit et retourne les résultats parsés.

        Args:
            project_path: Chemin du projet à analyser

        Returns:
            Dict avec les résultats parsés
        """
        if not settings.NPM_AUDIT_ENABLED:
            return {"status": "skipped", "reason": "npm-audit not enabled"}

        try:
            # Vérifier si package.json existe
            package_file = Path(project_path) / "package.json"
            if not package_file.exists():
                return {
                    "status": "skipped",
                    "reason": "package.json not found",
                }

            # Construire la commande npm audit
            cmd = [
                "npm",
                "audit",
                "--json",
                "--prefix",
                str(project_path),
            ]

            # Exécuter npm audit de manière asynchrone
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()

            # Parser la sortie JSON
            try:
                data = json.loads(stdout.decode())
            except json.JSONDecodeError:
                return {
                    "status": "error",
                    "error": "Failed to parse npm audit JSON output",
                }

            return {
                "status": "success",
                "tool": NpmAuditService.TOOL_NAME,
                "vulnerabilities": NpmAuditService._extract_vulnerabilities(data),
                "raw_output": data,
            }

        except FileNotFoundError:
            return {
                "status": "error",
                "error": "npm is not installed",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }

    @staticmethod
    def _extract_vulnerabilities(npm_audit_data: dict) -> list[dict]:
        """Extrait les vulnérabilités du format npm audit."""
        vulnerabilities = []

        for package_name, package_data in npm_audit_data.get(
            "vulnerabilities", {}
        ).items():
            if isinstance(package_data, dict) and "vulnerabilities" in package_data:
                for vuln_id, vuln_data in package_data["vulnerabilities"].items():
                    vulnerabilities.append(
                        {
                            "id": vuln_id,
                            "package": package_name,
                            "severity": vuln_data.get("severity", "unknown"),
                            "title": vuln_data.get("title", ""),
                            "description": vuln_data.get("description", ""),
                        }
                    )

        return vulnerabilities

    @staticmethod
    def parse_vulnerabilities(npm_audit_results: dict) -> list[dict]:
        """
        Convertit les résultats npm audit en format vulnérabilité standardisé.

        Args:
            npm_audit_results: Résultats bruts de npm audit

        Returns:
            Liste de vulnérabilités standardisées
        """
        vulnerabilities = []

        if npm_audit_results.get("status") != "success":
            return vulnerabilities

        for vuln in npm_audit_results.get("vulnerabilities", []):
            parsed_vuln = {
                "title": vuln.get("title", "Vulnerable dependency"),
                "description": vuln.get("description", ""),
                "file_path": "package.json",
                "line_start": None,
                "line_end": None,
                "severity": NpmAuditService._map_severity(
                    vuln.get("severity", "unknown")
                ),
                "cve_id": None,
                "cwe_id": None,
                "tool": "npm-audit",
            }
            vulnerabilities.append(parsed_vuln)

        return vulnerabilities

    @staticmethod
    def _map_severity(npm_severity: str) -> str:
        """Mappe la sévérité npm vers un standard."""
        mapping = {
            "critical": "critical",
            "high": "high",
            "moderate": "medium",
            "low": "low",
        }
        return mapping.get(npm_severity, "low")
