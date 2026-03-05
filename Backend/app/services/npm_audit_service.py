"""Service pour lancer npm audit et détecter les vulnérabilités de dépendances Node.js."""

import asyncio
import json
import shutil
import subprocess
from pathlib import Path

from app.config import settings


class NpmAuditService:
    """Service pour l'analyse des dépendances Node.js avec npm audit."""

    TOOL_NAME = "npm-audit"

    @staticmethod
    async def run(project_path: str) -> dict:
        """
        Lance npm audit et retourne les vulnérabilités détectées.

        npm audit analyse les dépendances Node.js (package.json) pour
        détecter les vulnérabilités connues.

        Args:
            project_path: Chemin du projet à analyser

        Returns:
            Dict avec les résultats parsés
        """
        if not settings.NPM_AUDIT_ENABLED:
            return {"status": "skipped", "reason": "npm-audit not enabled"}

        try:
            # Découvrir le chemin de npm
            npm_path = shutil.which("npm")
            if not npm_path:
                return {
                    "status": "error",
                    "error": "npm is not installed. Install with: brew install node (macOS) or apt install npm (Linux)",
                }

            # Vérifier si package.json existe
            package_json = Path(project_path) / "package.json"
            if not package_json.exists():
                return {
                    "status": "skipped",
                    "reason": "package.json not found",
                }

            # Construire la commande npm audit
            cmd = [
                npm_path,
                "audit",
                "--json",  # Format JSON
                "--audit-level=low",  # Rapporte tous les niveaux
            ]

            try:
                # Exécuter npm audit de manière asynchrone avec timeout
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=str(project_path),  # Exécute dans le répertoire du projet
                )

                # Timeout global de 120 secondes (npm peut être plus lent)
                try:
                    stdout, stderr = await asyncio.wait_for(
                        process.communicate(), timeout=120.0
                    )
                except asyncio.TimeoutError:
                    process.kill()
                    return {
                        "status": "error",
                        "error": "npm audit execution timeout (>120s)",
                    }

                # Parser la sortie JSON
                try:
                    data = json.loads(stdout.decode())
                except json.JSONDecodeError as e:
                    return {
                        "status": "error",
                        "error": f"Invalid JSON from npm audit: {str(e)}",
                    }

                vulnerabilities = data.get("vulnerabilities", {})
                return {
                    "status": "success",
                    "tool": NpmAuditService.TOOL_NAME,
                    "results": vulnerabilities,
                    "metadata": {
                        "auditcount": data.get("auditcount", 0),
                        "vulnerabilities": data.get("vulnerabilities", {}),
                    },
                    "raw_output": data,
                }

            except subprocess.TimeoutExpired:
                return {
                    "status": "error",
                    "error": "npm audit process timeout",
                }
            except Exception as e:
                return {
                    "status": "error",
                    "error": str(e),
                }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }

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

        npm_vulns = npm_audit_results.get("results", {})

        for package_name, vuln_data in npm_vulns.items():
            if isinstance(vuln_data, dict):
                vuln = {
                    "package": package_name,
                    "severity": vuln_data.get("via", [{}])[0].get(
                        "severity", "unknown"
                    ),
                    "title": vuln_data.get("via", [{}])[0].get(
                        "title", "Unknown vulnerability"
                    ),
                    "description": vuln_data.get("via", [{}])[0].get("url", ""),
                    "cve": vuln_data.get("via", [{}])[0].get("cves", []),
                    "affected_versions": vuln_data.get("affected", ""),
                    "fixed_versions": vuln_data.get("range", ""),
                }
                vulnerabilities.append(vuln)

        return vulnerabilities
