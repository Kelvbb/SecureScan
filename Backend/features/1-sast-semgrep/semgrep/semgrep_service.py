"""Service pour lancer Semgrep (SAST) et parser les résultats."""

import asyncio
import json
import os
import subprocess
import shutil
import sys
from pathlib import Path

from app.config import settings


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
                return {
                    "status": "error",
                    "error": "Semgrep is not installed. Install with: pip install semgrep",
                }

            # Construire la commande Semgrep avec timeout strict
            # Utiliser une config disponible localement pour plus de vitesse
            cmd = [
                semgrep_path,
                "--json",
                "--no-git-ignore",
                "--timeout=60",  # 60 secondes par fichier max
                "--max-target-bytes=1000000",  # Limite la taille des fichiers
                "-c",
                "p/security-audit",  # Config pré-compilée pour l'audit de sécurité
                str(project_path),
            ]

            try:
                # Exécuter Semgrep de manière asynchrone avec timeout
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )

                # Timeout global de 120 secondes
                try:
                    stdout, stderr = await asyncio.wait_for(
                        process.communicate(), timeout=120.0
                    )
                except asyncio.TimeoutError:
                    process.kill()
                    return {
                        "status": "error",
                        "error": "Semgrep execution timeout (>120s)",
                    }

                # Parser la sortie JSON
                try:
                    data = json.loads(stdout.decode())
                except json.JSONDecodeError as e:
                    return {
                        "status": "error",
                        "error": f"Invalid JSON from Semgrep: {str(e)}",
                    }

                return {
                    "status": "success",
                    "tool": SemgrepService.TOOL_NAME,
                    "results": data.get("results", []),
                    "errors": data.get("errors", []),
                    "stats": data.get("stats", {}),
                    "raw_output": data,
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
            return vulnerabilities

        for result in semgrep_results.get("results", []):
            vuln = {
                "title": result.get("check_id", "Unknown"),
                "description": result.get("extra", {}).get("message", ""),
                "file_path": result.get("path", ""),
                "line_start": result.get("start", {}).get("line"),
                "line_end": result.get("end", {}).get("line"),
                "severity": SemgrepService._map_severity(
                    result.get("extra", {}).get("severity", "INFO")
                ),
                "cwe_id": result.get("extra", {}).get("cwe", [None])[0],
                "tool": "semgrep",
            }
            vulnerabilities.append(vuln)

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
            return vulnerabilities

        for result in semgrep_results.get("results", []):
            vuln = {
                "title": result.get("check_id", "Unknown"),
                "description": result.get("extra", {}).get("message", ""),
                "file_path": result.get("path", ""),
                "line_start": result.get("start", {}).get("line"),
                "line_end": result.get("end", {}).get("line"),
                "severity": SemgrepService._map_severity(
                    result.get("extra", {}).get("severity", "INFO")
                ),
                "cwe_id": result.get("extra", {}).get("cwe", [None])[0],
                "tool": "semgrep",
            }
            vulnerabilities.append(vuln)

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
