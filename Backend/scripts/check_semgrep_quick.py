#!/usr/bin/env python3
"""Test simple pour vérifier que Semgrep fonctionne avec la nouvelle config."""

import subprocess
import json
import tempfile
from pathlib import Path

print("Tester Semgrep avec la configuration rapide...")
print("=" * 70)

code = """\
import os
user = input()
os.system(f"echo {user}")
x = eval(input())
"""

with tempfile.TemporaryDirectory() as tmpdir:
    test_dir = Path(tmpdir)
    (test_dir / "test.py").write_text(code)

    cmd = [
        "semgrep",
        "--json",
        "--no-git-ignore",
        "--timeout=60",
        "--max-target-bytes=1000000",
        "-c",
        "p/security-audit",
        str(test_dir),
    ]

    print(f"Commande: {' '.join(cmd)}")
    print()

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

        print(f"Exit code: {result.returncode}")

        if result.stdout:
            try:
                data = json.loads(result.stdout)
                results = data.get("results", [])
                print(f"✓ Résultats: {len(results)} issue(s) trouvée(s)")
                for r in results[:3]:
                    print(f"  - {r.get('check_id')}: {r.get('path')}")
            except json.JSONDecodeError as e:
                print(f"✗ Erreur JSON: {e}")
                print(f"Output: {result.stdout[:200]}")
        else:
            print(f"Pas de résultats (stdout vide)")

        if result.stderr:
            print(f"\nStderr: {result.stderr[:200]}")

    except subprocess.TimeoutExpired:
        print(f"✗ Timeout après 120s")
    except Exception as e:
        print(f"✗ Erreur: {e}")
