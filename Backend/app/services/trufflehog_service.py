"""Service pour lancer TruffleHog et détecter les secrets."""

import asyncio
import json
import subprocess
from pathlib import Path

from app.config import settings


class TruffleHogService:
    """Service pour la détection de secrets avec TruffleHog."""

    TOOL_NAME = "truffleHog"

    @staticmethod
    async def run(project_path: str) -> dict:
        """
        Lance TruffleHog et retourne les secrets détectés.
        
        Args:
            project_path: Chemin du projet à analyser
            
        Returns:
            Dict avec les résultats parsés
        """
        if not settings.TRUFFLEHOG_ENABLED:
            return {"status": "skipped", "reason": "TruffleHog not enabled"}

        try:
            # Créer un fichier temporaire pour la sortie JSON
            output_file = Path(project_path) / ".truffleHog-output.json"

            # Construire la commande TruffleHog filesystem
            cmd = [
                "truffleHog",
                "filesystem",
                str(project_path),
                "--json",
                f"--only-verified",
            ]

            # Exécuter TruffleHog de manière asynchrone
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            stdout, stderr = await process.communicate()

            # Parser la sortie JSON (TruffleHog retourne des résultats ligne par ligne)
            secrets = []
            if stdout:
                try:
                    for line in stdout.decode().strip().split("\n"):
                        if line:
                            data = json.loads(line)
                            secrets.append(data)
                except json.JSONDecodeError as e:
                    return {
                        "status": "error",
                        "error": f"Failed to parse TruffleHog output: {str(e)}",
                    }

            return {
                "status": "success",
                "tool": TruffleHogService.TOOL_NAME,
                "secrets": secrets,
                "raw_output": {"secrets": secrets},
            }

        except FileNotFoundError:
            return {
                "status": "error",
                "error": "TruffleHog is not installed",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }

    @staticmethod
    def parse_vulnerabilities(truffleHog_results: dict) -> list[dict]:
        """
        Convertit les résultats TruffleHog en format vulnérabilité standardisé.
        
        Args:
            truffleHog_results: Résultats bruts de TruffleHog
            
        Returns:
            Liste de vulnérabilités standardisées
        """
        vulnerabilities = []

        if truffleHog_results.get("status") != "success":
            return vulnerabilities

        for secret in truffleHog_results.get("secrets", []):
            vuln = {
                "title": f"Secret detected: {secret.get('type', 'Unknown')}",
                "description": f"Found credential of type {secret.get('type', 'Unknown')} in source code",
                "file_path": secret.get("file_path", ""),
                "line_start": secret.get("line_number"),
                "line_end": None,
                "severity": "critical",  # Les secrets sont toujours critiques
                "cve_id": None,
                "cwe_id": "CWE-798",  # Hardcoded credentials
                "tool": "truffleHog",
            }
            vulnerabilities.append(vuln)

        return vulnerabilities
