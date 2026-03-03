import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.remediation.templates import VulnerabilityType, generate_fix


def test_sql_injection_fstring():
    line = '    cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")'
    r = generate_fix(VulnerabilityType.SQL_INJECTION, line)
    assert "%s" in r.fixed_line
    assert "user_id" in r.fixed_line
    assert 'f"' not in r.fixed_line


def test_xss_php_echo():
    line = "    echo $user_input;"
    r = generate_fix(VulnerabilityType.XSS, line)
    assert "htmlspecialchars" in r.fixed_line
    assert "ENT_QUOTES" in r.fixed_line


def test_xss_js_innerhtml():
    line = "    element.innerHTML = userContent;"
    r = generate_fix(VulnerabilityType.XSS, line)
    assert "DOMPurify.sanitize" in r.fixed_line


def test_exposed_secret():
    line = 'API_KEY = "sk-prod-abc123"'
    r = generate_fix(VulnerabilityType.EXPOSED_SECRET, line)
    assert "os.getenv" in r.fixed_line
    assert '"API_KEY"' in r.fixed_line


def test_plaintext_password():
    line = "    user.password = request.form['password']"
    r = generate_fix(VulnerabilityType.PLAINTEXT_PWD, line)
    assert "PasswordHasher" in r.fixed_line
    assert "_ph.hash" in r.fixed_line


def test_unknown_type_raises():
    import pytest

    with pytest.raises(KeyError):
        generate_fix("type_inconnu", "some line")
