#!/usr/bin/env python3
"""Test rapide pour pip-audit et npm-audit services."""

import asyncio
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.pip_audit_service import PipAuditService
from app.services.npm_audit_service import NpmAuditService

print("=" * 70)
print("TEST PIP-AUDIT ET NPM-AUDIT SERVICES")
print("=" * 70)


async def test_pip_audit():
    """Test le service pip-audit."""
    print("\n[1] Test PIP-AUDIT SERVICE")
    print("-" * 70)

    with tempfile.TemporaryDirectory() as tmpdir:
        req_file = Path(tmpdir) / "requirements.txt"
        req_file.write_text("flask==1.0.0\n")  # Version avec vulnérabilités

        result = await PipAuditService.run(tmpdir)
        print(f"Status: {result.get('status')}")
        if result.get("status") == "success":
            issues = result.get("results", [])
            print(f"✓ Issues found: {len(issues)}")
            for issue in issues[:2]:
                print(f"  - {issue}")
        elif result.get("status") == "skipped":
            print(f"⊘ Skipped: {result.get('reason')}")
        else:
            print(f"✗ Error: {result.get('error')}")

    return result.get("status") in ("success", "skipped")


async def test_npm_audit():
    """Test le service npm-audit."""
    print("\n[2] Test NPM-AUDIT SERVICE")
    print("-" * 70)

    with tempfile.TemporaryDirectory() as tmpdir:
        pkg_json = Path(tmpdir) / "package.json"
        pkg_json.write_text("""\
{
  "name": "test",
  "version": "1.0.0",
  "dependencies": {
    "express": "3.0.0"
  }
}
""")

        result = await NpmAuditService.run(tmpdir)
        print(f"Status: {result.get('status')}")
        if result.get("status") == "success":
            issues = result.get("results", {})
            print(f"✓ Vulnerabilities found: {len(issues)}")
            for pkg_name, vulns in list(issues.items())[:2]:
                print(f"  - {pkg_name}: {vulns}")
        elif result.get("status") == "skipped":
            print(f"⊘ Skipped: {result.get('reason')}")
        else:
            print(f"✗ Error: {result.get('error')}")

    return result.get("status") in ("success", "skipped")


async def main():
    pip_ok = await test_pip_audit()
    npm_ok = await test_npm_audit()

    print("\n" + "=" * 70)
    print("RÉSUMÉ")
    print("=" * 70)
    print(f"  pip-audit : {'✓ OK' if pip_ok else '✗ FAILED'}")
    print(f"  npm-audit : {'✓ OK' if npm_ok else '✗ FAILED'}")
    print("=" * 70)

    return 0 if (pip_ok and npm_ok) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
