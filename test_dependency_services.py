#!/usr/bin/env python3
"""Test pip-audit and npm-audit dependency scanning services."""

import asyncio
import sys
import os
import json
import tempfile
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from app.services.pip_audit_service import PipAuditService
from app.services.npm_audit_service import NpmAuditService


async def test_pip_audit():
    """Test pip-audit service with a temporary requirements.txt."""
    print("\n📦 Testing pip-audit Service...")
    print("-" * 50)
    
    # Create a temporary requirements.txt with a known vulnerable package
    with tempfile.TemporaryDirectory() as tmpdir:
        req_file = Path(tmpdir) / "requirements.txt"
        # Using an older version of requests that has known vulnerabilities
        req_file.write_text("requests==2.7.0\ndjango==1.8.0\n")
        
        result = await PipAuditService.run(str(tmpdir))
        
        print(f"Status: {result.get('status')}")
        if result.get('status') == 'success':
            issues = result.get('results', {}).get('report', {}).get('vulnerabilities', [])
            print(f"Found {len(issues)} vulnerabilities")
            print(f"Tool: {result.get('tool')}")
            if issues:
                print(f"Sample issue: {issues[0] if issues else 'None'}")
        else:
            print(f"Error: {result.get('error')}")
    
    return result.get('status') == 'success'


async def test_npm_audit():
    """Test npm-audit service with a temporary package.json."""
    print("\n🔍 Testing npm-audit Service...")
    print("-" * 50)
    
    # Create a temporary package.json with a known vulnerable package
    with tempfile.TemporaryDirectory() as tmpdir:
        pkg_json = Path(tmpdir) / "package.json"
        # Using an older version of simple-get that has known vulnerabilities
        pkg_json.write_text(json.dumps({
            "name": "test-app",
            "version": "1.0.0",
            "dependencies": {
                "simple-get": "2.0.0"
            }
        }))
        
        result = await NpmAuditService.run(str(tmpdir))
        
        print(f"Status: {result.get('status')}")
        if result.get('status') == 'success':
            issues = result.get('results', {}).get('vulnerabilities', {})
            total_issues = len(issues)
            print(f"Found {total_issues} vulnerabilities")
            print(f"Tool: {result.get('tool')}")
            if issues:
                first_key = next(iter(issues))
                print(f"Sample issue: {issues[first_key]}")
        else:
            print(f"Error: {result.get('error')}")
    
    return result.get('status') == 'success'


async def main():
    """Run all tests."""
    print("\n🚀 Starting Dependency Service Tests")
    print("=" * 50)
    
    pip_audit_ok = await test_pip_audit()
    npm_audit_ok = await test_npm_audit()
    
    print("\n" + "=" * 50)
    print("\n✅ Test Results:")
    print(f"  pip-audit: {'✅ PASSED' if pip_audit_ok else '❌ FAILED'}")
    print(f"  npm-audit: {'✅ PASSED' if npm_audit_ok else '❌ FAILED'}")
    
    if pip_audit_ok and npm_audit_ok:
        print("\n🎉 All dependency services working correctly!")
        return 0
    else:
        print("\n⚠️  Some services need attention")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
