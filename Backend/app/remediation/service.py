"""
Couche métier du système de correction.
Génère les propositions depuis les templates, les persiste dans suggested_fixes,
puis les applique sur les fichiers sources à la ligne exacte indiquée en BDD.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Sequence
import uuid

from sqlalchemy.orm import Session

from app.models.scan import Scan
from app.models.vulnerability import Vulnerability
from app.models.suggested_fix import SuggestedFix
from app.remediation.templates import FixResult, VulnerabilityType, generate_fix

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Mapping fix_type → catégorie OWASP Top 10 : 2025
# Utilisé pour reconstruire owasp_category quand le SuggestedFix
# est chargé depuis la BDD (qui ne stocke pas ce champ).
# ---------------------------------------------------------------------------
OWASP_CATEGORY_BY_FIX_TYPE: dict[str, str] = {
    "sql_injection": "A05 – Injection",
    "xss": "A05 – Injection",
    "command_injection": "A05 – Injection",
    "exposed_secret": "A02 – Security Misconfiguration",
    "hardcoded_password": "A04 – Cryptographic Failures",
    "weak_hash": "A04 – Cryptographic Failures",
    "broken_access_control": "A01 – Broken Access Control",
    "insecure_deserialization": "A08 – Software/Data Integrity Failures",
    "missing_auth": "A07 – Authentication Failures",
    "outdated_dependency": "A03 – Software Supply Chain Failures",
    "missing_logging": "A09 – Logging & Alerting Failures",
    "unhandled_exception": "A10 – Mishandling of Exceptional Conditions",
}


def _owasp_for(fix_type: str) -> str:
    """Retourne la catégorie OWASP 2025 correspondant au fix_type, ou une valeur par défaut."""
    return OWASP_CATEGORY_BY_FIX_TYPE.get(fix_type, "A06 – Insecure Design")


# ---------------------------------------------------------------------------
# DTOs
# ---------------------------------------------------------------------------


@dataclass
class FixProposalDTO:
    """Données de correction sérialisables retournées à l'API."""

    suggested_fix_id: uuid.UUID
    vuln_id: uuid.UUID
    file_path: str
    line_number: int
    original_line: str
    fixed_line: str
    patch_diff: str
    description: str
    owasp_category: str  # ex : "A05 – Injection"
    fix_type: str  # ex : "sql_injection"
    auto_applicable: bool


@dataclass
class ApplyResult:
    applied: list[uuid.UUID] = field(default_factory=list)
    skipped: list[uuid.UUID] = field(default_factory=list)
    errors: dict[str, str] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class RemediationService:
    """
    Orchestre la génération et l'application des corrections template-based.

    Args:
        project_root: Chemin absolu vers les sources clonés du projet analysé.
        db_session:   Session SQLAlchemy active.
    """

    def __init__(self, project_root: Path, db_session: Session) -> None:
        if not project_root.is_dir():
            raise ValueError(f"project_root invalide : {project_root}")
        self.project_root = project_root
        self.db = db_session

    def get_or_create_fix_proposals(self, scan_id: uuid.UUID) -> list[FixProposalDTO]:
        """
        Retourne les propositions de correction pour un scan.

        Idempotent : si les SuggestedFix existent déjà en BDD, ils sont retournés
        directement sans regénération. Sinon, ils sont créés et persistés.
        """
        supported_types = [t.value for t in VulnerabilityType]
        vulns: list[Vulnerability] = (
            self.db.query(Vulnerability)
            .filter(
                Vulnerability.scan_id == scan_id,
                Vulnerability.vuln_type.in_(supported_types),
            )
            .all()
        )

        proposals: list[FixProposalDTO] = []
        for vuln in vulns:
            existing: SuggestedFix | None = (
                self.db.query(SuggestedFix)
                .filter(SuggestedFix.vulnerability_id == vuln.id)
                .first()
            )
            if existing:
                dto = self._suggested_fix_to_dto(existing, vuln)
                if dto:
                    proposals.append(dto)
                continue

            dto = self._generate_and_persist(vuln)
            if dto:
                proposals.append(dto)

        return proposals

    def apply_fixes(self, validated_fix_ids: Sequence[uuid.UUID]) -> ApplyResult:
        """
        Applique sur disque les corrections dont les IDs ont été validés par l'utilisateur.

        Seuls les fix_ids présents dans validated_fix_ids sont traités — aucune
        modification ne peut être appliquée sans validation explicite.

        Les fichiers sont traités un par un. Au sein d'un même fichier, les lignes
        sont modifiées en ordre décroissant pour que les indices restent valides
        après chaque substitution. L'écriture est atomique (tmp → rename).
        """
        result = ApplyResult()
        if not validated_fix_ids:
            return result

        fixes: list[SuggestedFix] = (
            self.db.query(SuggestedFix)
            .filter(SuggestedFix.id.in_(validated_fix_ids))
            .all()
        )

        # Grouper par fichier pour minimiser les lectures/écritures disque
        by_file: dict[str, list[tuple[SuggestedFix, Vulnerability]]] = {}
        for sf in fixes:
            vuln: Vulnerability = sf.vulnerability
            by_file.setdefault(vuln.file_path, []).append((sf, vuln))

        for rel_path, pairs in by_file.items():
            abs_path = self._resolve_path(rel_path)

            try:
                lines = self._read_file_lines(abs_path)
            except OSError as exc:
                msg = f"Lecture impossible : {exc}"
                logger.error("%s — %s", abs_path, msg)
                for sf, _ in pairs:
                    result.skipped.append(sf.id)
                    result.errors[str(sf.id)] = msg
                continue

            # Ordre décroissant : modifier la ligne 20 avant la ligne 5
            # évite que les insertions multi-lignes décalent les indices suivants.
            sorted_pairs = sorted(pairs, key=lambda p: p[1].line_number, reverse=True)

            for sf, vuln in sorted_pairs:
                idx = vuln.line_number - 1  # conversion 1-indexed → 0-indexed

                if idx < 0 or idx >= len(lines):
                    msg = (
                        f"Ligne {vuln.line_number} hors limites "
                        f"({len(lines)} lignes dans {rel_path})."
                    )
                    logger.warning("SuggestedFix %s — %s", sf.id, msg)
                    result.skipped.append(sf.id)
                    result.errors[str(sf.id)] = msg
                    continue

                if not sf.patch_diff:
                    try:
                        fix = generate_fix(
                            VulnerabilityType(vuln.vuln_type), lines[idx]
                        )
                        fixed_content = fix.fixed_line
                    except KeyError as exc:
                        msg = f"Template absent pour {vuln.vuln_type} : {exc}"
                        result.skipped.append(sf.id)
                        result.errors[str(sf.id)] = msg
                        continue
                else:
                    fixed_content = self._extract_fixed_lines_from_diff(sf.patch_diff)

                replacement = fixed_content.splitlines(keepends=True)
                if replacement and not replacement[-1].endswith("\n"):
                    replacement[-1] += "\n"

                lines[idx : idx + 1] = replacement
                result.applied.append(sf.id)
                logger.info(
                    "Correction appliquée — fix_id=%s fichier=%s ligne=%d",
                    sf.id,
                    rel_path,
                    vuln.line_number,
                )

            try:
                self._write_file_lines_atomic(abs_path, lines)
            except OSError as exc:
                msg = f"Écriture impossible : {exc}"
                logger.error("%s — %s", abs_path, msg)
                for sf, _ in pairs:
                    if sf.id in result.applied:
                        result.applied.remove(sf.id)
                        result.skipped.append(sf.id)
                        result.errors[str(sf.id)] = msg

        return result

    # ------------------------------------------------------------------
    # Helpers privés
    # ------------------------------------------------------------------

    def _generate_and_persist(self, vuln: Vulnerability) -> FixProposalDTO | None:
        """Génère la correction via le template, crée le SuggestedFix en BDD."""
        try:
            original_line = self._read_line(vuln.file_path, vuln.line_number)
            fix: FixResult = generate_fix(
                VulnerabilityType(vuln.vuln_type), original_line
            )
        except (KeyError, OSError) as exc:
            logger.warning("Génération impossible pour vuln %s : %s", vuln.id, exc)
            return None

        patch_diff = self._make_unified_diff(
            vuln.file_path, vuln.line_number, fix.original_line, fix.fixed_line
        )
        sf = SuggestedFix(
            vulnerability_id=vuln.id,
            fix_type=vuln.vuln_type,
            description=fix.explanation,
            patch_diff=patch_diff,
            auto_applicable=True,
            created_at=datetime.utcnow(),
        )
        self.db.add(sf)
        self.db.flush()  # récupère sf.id sans commit définitif

        return FixProposalDTO(
            suggested_fix_id=sf.id,
            vuln_id=vuln.id,
            file_path=vuln.file_path,
            line_number=vuln.line_number,
            original_line=fix.original_line,
            fixed_line=fix.fixed_line,
            patch_diff=patch_diff,
            description=fix.explanation,
            owasp_category=fix.owasp_category,  # issu du template
            fix_type=vuln.vuln_type,
            auto_applicable=True,
        )

    def _suggested_fix_to_dto(
        self, sf: SuggestedFix, vuln: Vulnerability
    ) -> FixProposalDTO | None:
        """
        Reconstruit un DTO depuis un SuggestedFix déjà persisté.

        owasp_category n'est pas stocké dans la table suggested_fixes ;
        il est recalculé via OWASP_CATEGORY_BY_FIX_TYPE pour garantir
        que chaque fix expose toujours sa catégorie OWASP 2025.
        """
        try:
            original_line = self._read_line(vuln.file_path, vuln.line_number)
        except OSError:
            original_line = "(fichier inaccessible)"

        fixed_line = (
            self._extract_fixed_lines_from_diff(sf.patch_diff)
            if sf.patch_diff
            else original_line
        )

        fix_type = sf.fix_type or vuln.vuln_type

        return FixProposalDTO(
            suggested_fix_id=sf.id,
            vuln_id=vuln.id,
            file_path=vuln.file_path,
            line_number=vuln.line_number,
            original_line=original_line,
            fixed_line=fixed_line,
            patch_diff=sf.patch_diff or "",
            description=sf.description or "",
            owasp_category=_owasp_for(fix_type),  # ← recalculé (était "" avant)
            fix_type=fix_type,
            auto_applicable=sf.auto_applicable,
        )

    def _resolve_path(self, relative_path: str) -> Path:
        """Résout le chemin et rejette toute tentative de path traversal."""
        resolved = (self.project_root / relative_path).resolve()
        if not resolved.is_relative_to(self.project_root.resolve()):
            raise ValueError(
                f"Path traversal détecté : '{relative_path}' sort de project_root."
            )
        return resolved

    def _read_line(self, relative_path: str, line_number: int) -> str:
        abs_path = self._resolve_path(relative_path)
        lines = self._read_file_lines(abs_path)
        idx = line_number - 1
        if idx < 0 or idx >= len(lines):
            raise OSError(
                f"Ligne {line_number} introuvable dans {abs_path} ({len(lines)} lignes)."
            )
        return lines[idx]

    @staticmethod
    def _read_file_lines(path: Path) -> list[str]:
        try:
            return path.read_text(encoding="utf-8", errors="replace").splitlines(
                keepends=True
            )
        except OSError as exc:
            raise OSError(f"Impossible de lire '{path}' : {exc}") from exc

    @staticmethod
    def _write_file_lines_atomic(path: Path, lines: list[str]) -> None:
        """Écrit via un fichier temporaire puis rename — évite la corruption en cas d'erreur."""
        tmp = path.with_suffix(path.suffix + ".sctmp")
        try:
            tmp.write_text("".join(lines), encoding="utf-8")
            tmp.replace(path)  # atomique sur POSIX
        except OSError:
            tmp.unlink(missing_ok=True)
            raise

    @staticmethod
    def _make_unified_diff(
        file_path: str, line_number: int, original: str, fixed: str
    ) -> str:
        import difflib

        return "".join(
            difflib.unified_diff(
                original.splitlines(keepends=True),
                fixed.splitlines(keepends=True),
                fromfile=f"{file_path} (ligne {line_number})",
                tofile=f"{file_path} (corrigé)",
                lineterm="",
            )
        )

    @staticmethod
    def _extract_fixed_lines_from_diff(patch_diff: str) -> str:
        """Extrait les lignes ajoutées (+) d'un diff unified pour reconstruire le contenu corrigé."""
        fixed_lines = [
            line[1:]
            for line in patch_diff.splitlines(keepends=True)
            if line.startswith("+") and not line.startswith("+++")
        ]
        return "".join(fixed_lines) if fixed_lines else patch_diff
