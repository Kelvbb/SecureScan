"""
Service de clonage Git pour récupérer les dépôts à analyser.
"""

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


class GitCloneError(RuntimeError):
    """Levée quand le clonage Git échoue."""


def clone_repository(repo_url: str, target_path: Path, timeout: int = 300) -> Path:
    """
    Clone un dépôt Git vers le chemin cible.
    
    Args:
        repo_url: URL du dépôt Git (HTTPS ou SSH)
        target_path: Chemin où cloner le dépôt
        timeout: Délai maximum en secondes (défaut: 300 = 5 minutes)
    
    Returns:
        Chemin du dépôt cloné
    
    Raises:
        GitCloneError: Si le clonage échoue
    """
    target_path = Path(target_path).resolve()
    
    # Vérifier que le répertoire parent existe
    target_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Si le répertoire existe déjà, le supprimer
    if target_path.exists():
        logger.warning(f"Le répertoire {target_path} existe déjà, suppression...")
        import shutil
        shutil.rmtree(target_path)
    
    logger.info(f"Clonage de {repo_url} vers {target_path}")
    
    try:
        subprocess.run(
            ["git", "clone", repo_url, str(target_path)],
            check=True,
            timeout=timeout,
            capture_output=True,
            text=True,
        )
        logger.info(f"Dépôt cloné avec succès dans {target_path}")
        return target_path
    except subprocess.CalledProcessError as exc:
        error_msg = f"Échec du clonage de {repo_url}: {exc.stderr or exc.stdout}"
        logger.error(error_msg)
        raise GitCloneError(error_msg) from exc
    except subprocess.TimeoutExpired as exc:
        error_msg = f"Timeout ({timeout}s) lors du clonage de {repo_url}"
        logger.error(error_msg)
        raise GitCloneError(error_msg) from exc
    except FileNotFoundError:
        error_msg = "Git n'est pas installé sur le système"
        logger.error(error_msg)
        raise GitCloneError(error_msg)


def clone_repository_with_auth(
    repo_url: str,
    target_path: Path,
    token: str | None = None,
    username: str | None = None,
    password: str | None = None,
    timeout: int = 300,
) -> Path:
    """
    Clone un dépôt Git avec authentification (token ou username/password).
    
    Args:
        repo_url: URL du dépôt Git
        target_path: Chemin où cloner le dépôt
        token: Token d'authentification (prioritaire)
        username: Nom d'utilisateur (si pas de token)
        password: Mot de passe (si pas de token)
        timeout: Délai maximum en secondes
    
    Returns:
        Chemin du dépôt cloné
    
    Raises:
        GitCloneError: Si le clonage échoue
    """
    # Injecter le token dans l'URL si fourni
    if token:
        if repo_url.startswith("https://"):
            # Format: https://token@github.com/user/repo.git
            repo_url = repo_url.replace("https://", f"https://{token}@")
        elif repo_url.startswith("http://"):
            repo_url = repo_url.replace("http://", f"http://{token}@")
        else:
            logger.warning("Token fourni mais URL n'est pas HTTPS/HTTP, utilisation directe")
    elif username and password:
        # Format: https://username:password@github.com/user/repo.git
        if repo_url.startswith("https://"):
            repo_url = repo_url.replace("https://", f"https://{username}:{password}@")
        elif repo_url.startswith("http://"):
            repo_url = repo_url.replace("http://", f"http://{username}:{password}@")
        else:
            logger.warning("Username/password fournis mais URL n'est pas HTTPS/HTTP, utilisation directe")
    
    return clone_repository(repo_url, target_path, timeout)
