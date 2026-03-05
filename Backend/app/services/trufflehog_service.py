"""Service pour lancer TruffleHog et détecter les secrets."""

import asyncio
import json
import shutil
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
        
        TruffleHog fonctionne mieux sur des repos git. Si le chemin ne contient
        pas un .git, on va initialiser un repo git local temporaire.
        
        Args:
            project_path: Chemin du projet à analyser
            
        Returns:
            Dict avec les résultats parsés
        """
        if not settings.TRUFFLEHOG_ENABLED:
            return {"status": "skipped", "reason": "TruffleHog not enabled"}

        try:
            project_path_obj = Path(project_path)
            
            # Initialiser un repo git temporaire si besoin
            git_dir = project_path_obj / ".git"
            needs_cleanup_git = False
            
            if not git_dir.exists():
                # Initialiser un repo git local
                try:
                    subprocess.run(
                        ["git", "init"],
                        cwd=str(project_path_obj),
                        capture_output=True,
                        timeout=10,
                    )
                    subprocess.run(
                        ["git", "add", "."],
                        cwd=str(project_path_obj),
                        capture_output=True,
                        timeout=10,
                    )
                    subprocess.run(
                        ["git", "commit", "-m", "initial", "--no-gpg-sign"],
                        cwd=str(project_path_obj),
                        capture_output=True,
                        timeout=10,
                    )
                    needs_cleanup_git = True
                except Exception as e:
                    return {
                        "status": "error",
                        "error": f"Failed to initialize git repo: {str(e)}",
                    }
            
            # Construire la commande TruffleHog
            # TruffleHog 2.x utilise: trufflehog [options] git_url
            # Pour un repo local, on peut passer file:// ou simplement le chemin
            trufflehog_path = shutil.which("trufflehog")
            if not trufflehog_path:
                return {
                    "status": "error",
                    "error": "TruffleHog is not installed. Install with: pip install truffleHog3",
                }
            
            # TruffleHog analyse récursivement tous les fichiers
            # Pour forcer l'analyse de tous les fichiers, on peut utiliser --no-verification
            cmd = [
                trufflehog_path,
                "--json",
                "--regex",  # Enable regex checks
                "--no-verification",  # Ne pas vérifier les secrets (analyse plus rapide)
                str(project_path_obj),
            ]

            try:
                # Exécuter TruffleHog de manière asynchrone
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                
                # Timeout de 60 secondes
                try:
                    stdout, stderr = await asyncio.wait_for(
                        process.communicate(),
                        timeout=60.0
                    )
                except asyncio.TimeoutError:
                    process.kill()
                    return {
                        "status": "error",
                        "error": "TruffleHog execution timeout (>60s)",
                    }

                # Parser la sortie JSON (TruffleHog retourne des résultats ligne par ligne)
                secrets = []
                if stdout:
                    try:
                        for line in stdout.decode().strip().split("\n"):
                            if line.strip():
                                try:
                                    data = json.loads(line)
                                    secrets.append(data)
                                except json.JSONDecodeError:
                                    # Certaines lignes peuvent ne pas être du JSON
                                    pass
                    except Exception as e:
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
                
            except subprocess.TimeoutExpired:
                return {
                    "status": "error",
                    "error": "TruffleHog execution timeout",
                }
            except Exception as e:
                return {
                    "status": "error",
                    "error": f"Error running TruffleHog: {str(e)}",
                }
            finally:
                # Nettoyer le repo git créé temporairement
                if needs_cleanup_git:
                    try:
                        shutil.rmtree(str(git_dir))
                    except Exception:
                        pass

        except FileNotFoundError:
            return {
                "status": "error",
                "error": "TruffleHog is not installed. Install with: pip install truffleHog",
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
            # TruffleHog retourne différentes structures selon le type de secret
            # Extraire les numéros de ligne si disponibles
            line_start = secret.get("line_number") or secret.get("line") or secret.get("lineNumber")
            line_end = line_start  # TruffleHog retourne généralement une seule ligne
            
            # Extraire le chemin du fichier
            file_path = secret.get("path") or secret.get("file_path") or secret.get("filePath")
            
            # Extraire le type de secret détecté
            secret_type = secret.get("reason") or secret.get("matched_type") or secret.get("type") or "Unknown"
            
            vuln = {
                "title": f"Secret detected: {secret_type}",
                "description": f"Found potential secret ({secret_type}) - {secret.get('reason', 'Secret detected')}",
                "file_path": file_path,
                "line_start": line_start,
                "line_end": line_end,
                "severity": "critical",
                "cve_id": None,
                "cwe_id": "CWE-798",
                "tool": "truffleHog",
                "confidence": "high",
            }
            vulnerabilities.append(vuln)

        return vulnerabilities

