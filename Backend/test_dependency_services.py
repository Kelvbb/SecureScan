#!/usr/bin/env python3
"""Test rapide pour pip-audit et npm-audit services."""

import asyncio
import tempfile
from pathlib import Path

print("=" * 70)
print("TEST PIP-AUDIT ET NPM-AUDIT SERVICES")
print("=" * 70)

async def test_pip_audit():
    """Test le service pip-audit."""
    from app.services.pip_audit_service import PipAuditService
    
    print("\n[1] Test PIP-AUDIT SERVICE")
    print("-" * 70)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Créer un requirements.txt avec une vulnérabilité connue
        req_file = Path(tmpdir) / "requirements.txt"
        req_file.write_text("flask==1.0.0\n")  # Version avec vulnérabilités
        
        result = await PipAuditService.run(tmpdir)
        print(f"Status: {result.get('status')}")
        if result.get('status') == 'success':
            issues = result.get('results', [])
            print(f"✓ Issues found: {len(issues)}")
            for issue in issues[:2]:
                print(f"  - {issue}")
        elif result.get('status') == 'skipped':
            print(f"⊘ Skipped: {result.get('reason')}")
        else:
            print(f"✗ Error: {result.get('error')}")

async def test_npm_audit():
    """Test le service npm-audit."""
    from app.services.npm_audit_service import NpmAuditService
    
    print("\n[2] Test NPM-AUDIT SERVICE")
    print("-" * 70)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Créer un package.json avec une dépendance vulnérable
        pkg_json = Path(tmpdir) / "package.json"
        pkg_json.write_text('''{
  "name": "test",
  "version": "1.0.0",
  "dependencies": {
    "express": "3.0.0"
  }
}
''')
        
        result = await NpmAuditService.run(tmpdir)
        print(f"Status: {result.get('status')}")
        if result.get('status') == 'success':
            issues = result.get('results', {})
            print(f"✓ Vulnerabilities found: {len(issues)}")
            for pkg_name, vulns in list(issues.items())[:2]:
                print(f"  - {pkg_name}: {vulns}")
        elif result.get('status') == 'skipped':
            print(f"⊘ Skipped: {result.get('reason')}")
        else:
            print(f"✗ Error: {result.get('error')}")

async def main():
    """Lance les tests."""
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    await test_pip_audit()
    await test_npm_audit()
    
    print("\n" + "=" * 70)
    print("✓ Tests completed!")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(main())
