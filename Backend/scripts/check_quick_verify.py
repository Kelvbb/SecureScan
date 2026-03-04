#!/usr/bin/env python3
"""Quick verification that Semgrep works via discovered path."""

import shutil
import asyncio
import subprocess
import json


async def verify_semgrep():
    """Verify Semgrep can be discovered and executed."""
    print("=" * 60)
    print("QUICK VERIFICATION - Semgrep Discovery & Execution")
    print("=" * 60)

    # 1. Discover semgrep path
    path = shutil.which("semgrep")
    if not path:
        print("✗ Semgrep NOT found in PATH")
        return False
    print(f"✓ Semgrep found at: {path}")

    # 2. Check version
    result = subprocess.run([path, "--version"], capture_output=True, text=True)
    version = result.stdout.strip() if result.returncode == 0 else "unknown"
    print(f"✓ Version: {version}")

    # 3. Run scan on test project
    project = "/tmp/test_project"
    cmd = [path, "--json", "-c", "p/security-audit", "--timeout=30", project]
    print(f"\n[Running scan on {project}...]")

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=60.0)
        data = json.loads(stdout.decode())
        results = data.get("results", [])
        print(f"✓ Scan completed")
        print(f"  Issues found: {len(results)}")
        for r in results[:3]:
            rule = r.get("check_id", "?")
            file = r.get("path", "?").replace(project + "/", "")
            print(f"    - {rule} in {file}")
        return True
    except asyncio.TimeoutError:
        print("✗ Scan timeout")
        return False
    except json.JSONDecodeError as e:
        print(f"✗ JSON parse error: {e}")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(verify_semgrep())
    print("\n" + "=" * 60)
    if success:
        print("✓ VERIFICATION SUCCESSFUL - Semgrep is working!")
    else:
        print("✗ VERIFICATION FAILED")
    print("=" * 60)
