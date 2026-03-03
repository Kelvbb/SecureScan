# tests/test_service_disk.py  — remplacer la section stubs + test entier

import sys, uuid, types, tempfile, textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch

# Stubs imports circulaires (inchangés)
for mod in [
    "app.db",
    "app.db.base",
    "app.db.session",
    "app.models",
    "app.models.scan",
    "app.models.vulnerability",
    "app.models.suggested_fix",
    "app.config",
]:
    sys.modules.setdefault(mod, types.ModuleType(mod))

sys.modules["app.db.base"].Base = object
sys.modules["app.config"].settings = MagicMock(DATABASE_URL="sqlite://", DEBUG=False)
sys.modules["app.models.scan"].Scan = MagicMock
sys.modules["app.models.vulnerability"].Vulnerability = MagicMock
sys.modules["app.models.suggested_fix"].SuggestedFix = MagicMock

from app.remediation.service import RemediationService  # noqa: E402


def test_apply_fix_modifies_file_on_disk():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        vuln_file = root / "auth.py"
        vuln_file.write_text(textwrap.dedent("""\
            def login(username):
                cursor.execute(f"SELECT * FROM users WHERE name = {username}")
                return cursor.fetchone()
        """))

        mock_vuln = MagicMock()
        mock_vuln.id = uuid.uuid4()
        mock_vuln.file_path = "auth.py"
        mock_vuln.line_number = 2
        mock_vuln.vuln_type = "sql_injection"

        fix_id = uuid.uuid4()
        mock_fix = MagicMock()
        mock_fix.id = fix_id
        mock_fix.patch_diff = None
        mock_fix.vulnerability = mock_vuln

        # Le mock_db retourne directement [mock_fix] pour TOUT appel query/filter/all
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_fix]

        svc = RemediationService(project_root=root, db_session=mock_db)

        # ✅ Patcher SuggestedFix DANS le service pour court-circuiter SuggestedFix.id
        mock_sf_class = MagicMock()
        mock_sf_class.id = MagicMock()  # .id.in_() sera un MagicMock valide
        mock_sf_class.id.in_.return_value = True

        with patch("app.remediation.service.SuggestedFix", mock_sf_class):
            result = svc.apply_fixes(validated_fix_ids=[fix_id])

        assert fix_id in result.applied, f"Skipped : {result.errors}"

        content = vuln_file.read_text()
        assert "%s" in content, "Requête paramétrée absente"
        assert 'f"' not in content, "f-string vulnérable encore présent"
        print("\n✓ Fichier corrigé :\n", content)
