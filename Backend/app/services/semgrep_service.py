"""Service pour lancer Semgrep (SAST) et parser les résultats."""

import asyncio
import json
import subprocess
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
            # Créer un fichier temporaire pour la sortie JSON
            output_file = Path(project_path) / ".semgrep-output.json"

            # Construire la commande Semgrep
            cmd = [
                "semgrep",
                "--json",
                f"--output={output_file}",
                "--no-git-ignore",
                str(project_path),
            ]

            # Exécuter Semgrep de manière asynchrone
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            stdout, stderr = await process.communicate()

            # Vérifier que le fichier de sortie a été créé
            if not output_file.exists():
                return {
                    "status": "failed",
                    "error": f"Semgrep output file not created",
                    "stderr": stderr.decode() if stderr else "",
                }

            # Parser le fichier JSON
            with open(output_file, "r") as f:
                data = json.load(f)

            # Nettoyer le fichier temporaire
            output_file.unlink()

            return {
                "status": "success",
                "tool": SemgrepService.TOOL_NAME,
                "results": data.get("results", []),
                "errors": data.get("errors", []),
                "stats": data.get("stats", {}),
                "raw_output": data,
            }

        except FileNotFoundError:
            return {
                "status": "error",
                "error": "Semgrep is not installed",
            }
        except json.JSONDecodeError as e:
            return {
                "status": "error",
                "error": f"Failed to parse Semgrep output: {str(e)}",
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
