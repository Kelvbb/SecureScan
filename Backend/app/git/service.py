"""
Automatisation du workflow Git post-correction.
Utilise le CLI git via subprocess — compatible GitHub, GitLab et dépôts auto-hébergés
sans dépendance SDK externe.
"""

from __future__ import annotations

import logging
import os
import subprocess
from datetime import date
from pathlib import Path

logger = logging.getLogger(__name__)


class GitServiceError(RuntimeError):
    """Levée quand une commande git retourne un code d'erreur ou dépasse le timeout."""


class GitService:
    """
    Encapsule les trois opérations Git du workflow SecureScan :
    création de branche, commit et push.

    Args:
        repo_path:    Chemin absolu vers le dépôt cloné.
        author_name:  Nom affiché dans les commits automatiques.
        author_email: Email affiché dans les commits automatiques.
        remote:       Nom du remote cible (défaut : "origin").
        timeout:      Délai max en secondes par commande git (défaut : 60).
    """

    def __init__(
        self,
        repo_path:    Path,
        author_name:  str = "SecureScan Bot",
        author_email: str = "securescan@cybersafe.local",
        remote:       str = "origin",
        timeout:      int = 60,
    ) -> None:
        self.repo_path    = repo_path.resolve()
        self.author_name  = author_name
        self.author_email = author_email
        self.remote       = remote
        self.timeout      = timeout
        self._check_repo()

    def create_fix_branch(self, base_branch: str | None = None) -> str:
        """
        Crée et checkout une branche fix/securescan-<YYYY-MM-DD>.
        Si le nom existe déjà, un suffixe numérique est ajouté (-2, -3, etc.).

        Args:
            base_branch: Branche de départ. Si None, part de la branche courante.

        Returns:
            Nom de la branche créée.
        """
        base_name   = f"fix/securescan-{date.today().isoformat()}"
        branch_name = self._unique_branch_name(base_name)

        if base_branch:
            self._run("checkout", base_branch)

        self._run("checkout", "-b", branch_name)
        logger.info("Branche créée : %s", branch_name)
        return branch_name

    def commit_fixes(
        self,
        message:       str  = "fix(securescan): corrections de sécurité automatiques",
        add_all_files: bool = True,
    ) -> str:
        """
        Stage les fichiers modifiés et crée un commit.

        Args:
            message:       Message de commit.
            add_all_files: Si True, lance git add -A avant le commit.

        Returns:
            SHA complet du commit créé.

        Raises:
            GitServiceError: si le working tree est propre (rien à committer).
        """
        if add_all_files:
            self._run("add", "-A")

        if not self._run_capture("status", "--porcelain").strip():
            raise GitServiceError(
                "Rien à committer — les corrections ont peut-être déjà été appliquées."
            )

        self._run("commit", "-m", message, env={
            "GIT_AUTHOR_NAME":     self.author_name,
            "GIT_AUTHOR_EMAIL":    self.author_email,
            "GIT_COMMITTER_NAME":  self.author_name,
            "GIT_COMMITTER_EMAIL": self.author_email,
        })

        sha = self._run_capture("rev-parse", "HEAD").strip()
        logger.info("Commit créé : %s — %s", sha[:10], message)
        return sha

    def push_branch(self, branch_name: str) -> None:
        """
        Pousse la branche sur le remote avec --force-with-lease.
        Plus sûr que --force : échoue si la branche distante a évolué entre-temps.

        Raises:
            GitServiceError: si le push échoue.
        """
        self._run("push", "--set-upstream", "--force-with-lease", self.remote, branch_name)
        logger.info("Branche '%s' poussée sur '%s'.", branch_name, self.remote)

    # ------------------------------------------------------------------
    # Helpers privés
    # ------------------------------------------------------------------

    def _check_repo(self) -> None:
        """Vérifie que repo_path pointe bien vers un dépôt Git valide."""
        if not self.repo_path.is_dir():
            raise GitServiceError(f"'{self.repo_path}' n'est pas un répertoire.")
        try:
            self._run("rev-parse", "--git-dir")
        except GitServiceError as exc:
            raise GitServiceError(f"'{self.repo_path}' n'est pas un dépôt Git : {exc}") from exc

    def _unique_branch_name(self, base: str) -> str:
        """Retourne base si disponible, sinon base-2, base-3, etc."""
        existing = {
            line.strip().lstrip("* ")
            for line in self._run_capture("branch", "--list").splitlines()
            if line.strip()
        }
        if base not in existing:
            return base
        counter = 2
        while f"{base}-{counter}" in existing:
            counter += 1
        return f"{base}-{counter}"

    def _run(self, *args: str, env: dict[str, str] | None = None) -> None:
        """Lance `git <args>` dans repo_path. Lève GitServiceError si code != 0."""
        cmd      = ["git", *args]
        full_env = {**os.environ, **(env or {})}
        logger.debug("$ %s", " ".join(cmd))
        try:
            subprocess.run(
                cmd, cwd=self.repo_path, env=full_env,
                capture_output=True, text=True,
                timeout=self.timeout, check=True,
            )
        except subprocess.CalledProcessError as exc:
            raise GitServiceError(
                f"Échec : {' '.join(cmd)}\nstdout : {exc.stdout}\nstderr : {exc.stderr}"
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise GitServiceError(f"Timeout ({self.timeout}s) : {' '.join(cmd)}") from exc

    def _run_capture(self, *args: str) -> str:
        """Comme _run mais retourne la sortie standard."""
        cmd = ["git", *args]
        logger.debug("$ %s (capture)", " ".join(cmd))
        try:
            result = subprocess.run(
                cmd, cwd=self.repo_path, env=os.environ.copy(),
                capture_output=True, text=True,
                timeout=self.timeout, check=True,
            )
            return result.stdout
        except subprocess.CalledProcessError as exc:
            raise GitServiceError(
                f"Échec : {' '.join(cmd)}\nstderr : {exc.stderr}"
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise GitServiceError(f"Timeout ({self.timeout}s) : {' '.join(cmd)}") from exc
