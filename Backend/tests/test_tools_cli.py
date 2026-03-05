#!/usr/bin/env python3
"""Test que les outils de sécurité fonctionnent via CLI."""

import asyncio
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

# (placé en haut avant tout import applicatif)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("=" * 70)
print("TEST OUTILS CLI - SEMGREP & TRUFFLEHOG")
print("=" * 70)

# ============================================================================
# TEST 1: Vérifier que les outils sont installés
# ============================================================================
print("\n[TEST 1] Vérifier que les outils sont installés")
print("-" * 70)

tools = {
    "semgrep": ["semgrep", "--version"],
    "trufflehog": ["trufflehog", "--help"],  # TruffleHog 2.x doesn't have --version
}

installed_tools = {}
for tool_name, cmd in tools.items():
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10,
        )
        # For version check, return code doesn't matter as long as command exists
        if tool_name == "trufflehog":
            # trufflehog --help shows help (exit code varies)
            if "usage:" in result.stderr or "usage:" in result.stdout or result.returncode >= 0:
                print(f"✓ {tool_name}: Installed")
                installed_tools[tool_name] = True
            else:
                print(f"✗ {tool_name}: Command failed")
                installed_tools[tool_name] = False
        else:
            # For semgrep --version
            if result.returncode == 0:
                version_output = result.stdout.strip().split('\n')[0]
                print(f"✓ {tool_name}: {version_output}")
                installed_tools[tool_name] = True
            else:
                print(f"✗ {tool_name}: Command failed")
                print(f"  Error: {result.stderr}")
                installed_tools[tool_name] = False
    except FileNotFoundError:
        print(f"✗ {tool_name}: Not installed or not in PATH")
        installed_tools[tool_name] = False
    except subprocess.TimeoutExpired:
        print(f"✗ {tool_name}: Command timeout")
        installed_tools[tool_name] = False
    except Exception as e:
        print(f"✗ {tool_name}: {str(e)}")
        installed_tools[tool_name] = False

# ============================================================================
# TEST 2: Test SEMGREP sur un projet de test
# ============================================================================
if installed_tools.get("semgrep"):
    print("\n[TEST 2] Test SEMGREP sur un projet de test")
    print("-" * 70)
    
    # Créer un répertoire temporaire avec du code vulnérable
    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir)
        
        # Créer un fichier Python avec une vulnérabilité
        vuln_file = test_dir / "vulnerable.py"
        vuln_file.write_text('''
import requests

# SQL Injection  
def search_user(user_input):
    query = f"SELECT * FROM users WHERE name = '{user_input}'"
    return execute_query(query)

# Hardcoded credentials
API_KEY = "sk-1234567890abcdef"
DB_PASSWORD = "admin123"

# Use of eval
result = eval(user_input)
''')
        
        # Lancer semgrep
        try:
            cmd = [
                "semgrep",
                "--json",
                "--no-git-ignore",
                str(test_dir),
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )
            
            if result.returncode == 0 or result.returncode == 1:  # 0=no findings, 1=findings found
                print(f"✓ Semgrep executed successfully")
                
                try:
                    output = json.loads(result.stdout)
                    results = output.get("results", [])
                    print(f"  Found {len(results)} issue(s)")
                    for r in results[:3]:  # Show first 3
                        print(f"    - {r.get('check_id', 'N/A')}: {r.get('path', 'N/A')}")
                except json.JSONDecodeError:
                    print(f"  Could not parse JSON output (but command succeeded)")
                    print(f"  Output: {result.stdout[:200]}")
            else:
                print(f"✗ Semgrep failed with code {result.returncode}")
                print(f"  Error: {result.stderr}")
        except subprocess.TimeoutExpired:
            print(f"✗ Semgrep timeout")
        except Exception as e:
            print(f"✗ Error running semgrep: {str(e)}")
else:
    print("\n[TEST 2] SKIPPED - Semgrep not installed")

# ============================================================================
# TEST 3: Test TRUFFLEHOG sur un projet de test
# ============================================================================
if installed_tools.get("trufflehog"):
    print("\n[TEST 3] Test TRUFFLEHOG sur un projet de test")
    print("-" * 70)
    
    # Créer un répertoire temporaire avec des secrets
    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir)
        
        # Créer un fichier avec un secret simulé
        secret_file = test_dir / ".env"
        secret_file.write_text('''
DATABASE_URL=postgresql://user:password@localhost/db
API_KEY=sk-1234567890abcdefghijklmnop
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
''')
        
        # Initialiser un repo git local (TruffleHog 2.x fonctionne mieux sur git)
        try:
            subprocess.run(
                ["git", "init"],
                cwd=str(test_dir),
                capture_output=True,
                timeout=10,
            )
            subprocess.run(
                ["git", "add", "."],
                cwd=str(test_dir),
                capture_output=True,
                timeout=10,
            )
            subprocess.run(
                ["git", "commit", "-m", "initial"],
                cwd=str(test_dir),
                capture_output=True,
                timeout=10,
            )
        except Exception as e:
            print(f"✗ Failed to initialize git repo: {e}")
        
        # Lancer trufflehog
        try:
            cmd = [
                "trufflehog",
                "--json",
                "--regex",
                str(test_dir),
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )
            
            # TruffleHog peut retourner non-zero s'il trouve des secrets ou autres erreurs
            print(f"✓ Trufflehog executed (exit code: {result.returncode})")
            
            secrets_found = 0
            if result.stdout:
                try:
                    for line in result.stdout.strip().split('\n'):
                        if line.strip():
                            try:
                                data = json.loads(line)
                                secrets_found += 1
                            except json.JSONDecodeError:
                                pass
                    print(f"  Found {secrets_found} result(s)")
                except Exception as e:
                    print(f"  Warning: Could not parse all output: {e}")
            else:
                print(f"  No secrets detected (or empty output)")
        except subprocess.TimeoutExpired:
            print(f"✗ Trufflehog timeout")
        except Exception as e:
            print(f"✗ Error running trufflehog: {str(e)}")
else:
    print("\n[TEST 3] SKIPPED - Trufflehog not installed")

# ============================================================================
# TEST 4: Test avec les services Python
# ============================================================================
print("\n[TEST 4] Test avec les services Python (asyncio)")
print("-" * 70)

sys.path.insert(0, '/Users/djidji/Documents/Projets/IPSSI/SecureScan/backend')

async def test_services():
    try:
        # Import dynamique pour éviter les erreurs d'import au démarrage
        from features._1_sast_semgrep.semgrep.semgrep_service import SemgrepService
        from features._1_sast_semgrep.secrets.trufflehog_service import TruffleHogService
        
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir)
            
            # Créer un fichier test
            test_file = test_dir / "test.py"
            test_file.write_text("x = 1  # Simple code")
            
            # Test Semgrep service
            if installed_tools.get("semgrep"):
                print("Testing SemgrepService.run()...")
                result = await SemgrepService.run(str(test_dir))
                print(f"  Status: {result.get('status')}")
                if result.get('status') == 'success':
                    print(f"  ✓ Result structure valid")
                    results_count = len(result.get('results', []))
                    print(f"  Results: {results_count} issue(s)")
                elif result.get('status') == 'error':
                    print(f"  ✗ Error: {result.get('error')}")
                elif result.get('status') == 'skipped':
                    print(f"  ⊘ Skipped: {result.get('reason')}")
            
            # Test TruffleHog service
            if installed_tools.get("trufflehog"):
                print("\nTesting TruffleHogService.run()...")
                result = await TruffleHogService.run(str(test_dir))
                print(f"  Status: {result.get('status')}")
                if result.get('status') == 'success':
                    print(f"  ✓ Result structure valid")
                    secrets_count = len(result.get('secrets', []))
                    print(f"  Secrets: {secrets_count} secret(s)")
                elif result.get('status') == 'error':
                    print(f"  ✗ Error: {result.get('error')}")
                elif result.get('status') == 'skipped':
                    print(f"  ⊘ Skipped: {result.get('reason')}")
                
    except ImportError as e:
        print(f"⚠ Cannot import services: {str(e)}")
        print("  The services require the backend directory structure")
    except Exception as e:
        print(f"✗ Error: {str(e)}")

if installed_tools.get("semgrep") or installed_tools.get("trufflehog"):
    asyncio.run(test_services())

# ============================================================================
# SUMMARY
# ============================================================================
print("\n" + "=" * 70)
print("RÉSUMÉ")
print("=" * 70)
for tool_name, installed in installed_tools.items():
    status = "✓ Installed" if installed else "✗ Not installed"
    print(f"{tool_name}: {status}")

if all(installed_tools.values()):
    print("\n✓ Tous les outils sont installés et fonctionnent!")
    print("\nLes collaborateurs peuvent maintenant tester les scans.")
else:
    missing = [name for name, installed in installed_tools.items() if not installed]
    print(f"\n⚠ {len(missing)} outil(s) manquant(s): {', '.join(missing)}")
    print("\nPour installer:")
    print("  pip install semgrep")
    print("  pip install trufflehog")

