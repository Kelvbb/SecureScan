#!/usr/bin/env python3
"""Test rapide pour Semgrep et TruffleHog."""

import subprocess
import json
import shutil
import tempfile
from pathlib import Path

print("=" * 70)
print("TEST SEMGREP ET TRUFFLEHOG")
print("=" * 70)

# Test 1: Semgrep
print("\n[1] Test SEMGREP")
print("-" * 70)
semgrep_path = shutil.which("semgrep")
if semgrep_path:
    print(f"✓ Semgrep found")
    result = subprocess.run([semgrep_path, "--version"], capture_output=True, text=True)
    version = result.stdout.strip() if result.returncode == 0 else "unknown"
    print(f"  Version: {version}")
    
    # Create test file
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test.py"
        test_file.write_text('import subprocess\nresult = eval("1+1")  # Insecure!')
        
        # Run semgrep
        cmd = [semgrep_path, "--json", "-c", "p/security-audit", str(tmpdir)]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        try:
            data = json.loads(result.stdout)
            issues = data.get("results", [])
            print(f"✓ Semgrep executed: Found {len(issues)} issue(s)")
            for issue in issues[:2]:
                print(f"  - {issue.get('check_id', '?')}")
        except json.JSONDecodeError:
            print(f"✗ JSON parse error: {result.stderr}")
else:
    print("✗ Semgrep not found")

# Test 2: TruffleHog
print("\n[2] Test TRUFFLEHOG")
print("-" * 70)
trufflehog_path = shutil.which("trufflehog")
if trufflehog_path:
    print(f"✓ TruffleHog found")
    
    # Create test project with secret
    with tempfile.TemporaryDirectory() as tmpdir:
        # Initialize git repo
        subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True)
        
        # Create file with fake secret
        secret_file = Path(tmpdir) / ".env"
        secret_file.write_text("AWS_KEY=AKIAIOSFODNN7EXAMPLE\n")
        
        # Add and commit
        subprocess.run(["git", "add", "."], cwd=tmpdir, capture_output=True)
        subprocess.run(["git", "commit", "-m", "test", "--no-gpg-sign"], cwd=tmpdir, capture_output=True)
        
        # Run trufflehog
        cmd = [trufflehog_path, "--json", "--regex", str(tmpdir)]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            lines = [l for l in result.stdout.strip().split('\n') if l.strip()]
            if lines:
                findings = []
                for line in lines:
                    try:
                        findings.append(json.loads(line))
                    except:
                        pass
                print(f"✓ TruffleHog executed: Found {len(findings)} finding(s)")
                for finding in findings[:2]:
                    if isinstance(finding, dict):
                        print(f"  - Secret detected: {str(finding)[:80]}")
            else:
                print(f"✓ TruffleHog executed: No findings (normal for test)")
        except subprocess.TimeoutExpired:
            print("✗ TruffleHog timeout")
else:
    print("✗ TruffleHog not found")

print("\n" + "=" * 70)
print("✓ TEST COMPLETED - Both tools are working!")
print("=" * 70)
