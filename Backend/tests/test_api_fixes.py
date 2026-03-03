import uuid
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from app.main import app

SCAN_ID = uuid.uuid4()
FIX_ID = uuid.uuid4()
VULN_ID = uuid.uuid4()


def make_mock_proposal():
    from app.remediation.service import FixProposalDTO

    return FixProposalDTO(
        suggested_fix_id=FIX_ID,
        vuln_id=VULN_ID,
        file_path="app/auth.py",
        line_number=12,
        original_line='    cursor.execute(f"SELECT * FROM users WHERE id={uid}")',
        fixed_line='    cursor.execute("SELECT * FROM users WHERE id=%s", (uid,))',
        patch_diff="--- app/auth.py\n+++ app/auth.py\n-    cursor...\n+    cursor...",
        description="Requête paramétrée pour éviter l'injection SQL.",
        owasp_category="A05 – Injection",
        fix_type="sql_injection",
        auto_applicable=True,
    )


# --- GET /scans/{scan_id}/fixes ---
@patch("app.db.session.get_db")
@patch("app.api.routes.fixes._get_scan_or_404")
@patch("app.api.routes.fixes._build_service")
def test_get_fixes(mock_svc_builder, mock_get_scan, mock_get_db):
    mock_service = MagicMock()
    mock_service.get_or_create_fix_proposals.return_value = [make_mock_proposal()]
    mock_svc_builder.return_value = mock_service
    mock_get_db.return_value = MagicMock()

    client = TestClient(app)
    resp = client.get(f"/api/scans/{SCAN_ID}/fixes")

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["proposals"][0]["fix_type"] == "sql_injection"
    assert "%s" in data["proposals"][0]["fixed_line"]
    print("✓ GET /fixes →", data["total"], "proposition(s)")


# --- POST /scans/{scan_id}/fixes/apply ---
@patch("app.db.session.get_db")
@patch("app.api.routes.fixes._get_scan_or_404")
@patch("app.api.routes.fixes._build_service")
@patch("app.api.routes.fixes.GitService")
def test_apply_fixes(mock_git_cls, mock_svc_builder, mock_get_scan, mock_get_db):
    from app.remediation.service import ApplyResult

    mock_service = MagicMock()
    mock_service.apply_fixes.return_value = ApplyResult(applied=[FIX_ID])
    mock_svc_builder.return_value = mock_service

    mock_git = MagicMock()
    mock_git.create_fix_branch.return_value = "fix/securescan-2026-03-05"
    mock_git.commit_fixes.return_value = "abc1234"
    mock_git_cls.return_value = mock_git

    client = TestClient(app)
    resp = client.post(
        f"/api/scans/{SCAN_ID}/fixes/apply", json={"fix_ids": [str(FIX_ID)]}
    )

    assert resp.status_code == 200
    data = resp.json()
    assert str(FIX_ID) in [str(i) for i in data["applied_fix_ids"]]
    assert data["git_branch"] == "fix/securescan-2026-03-05"
    assert data["git_pushed"] is True
    print("✓ POST /apply → branche :", data["git_branch"])
