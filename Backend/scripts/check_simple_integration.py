#!/usr/bin/env python3
"""Simple integration test after tool optimization."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
import time
from uuid import uuid4
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from app.config import settings
from app.models import User
from app.models.tool_execution import ToolExecution
from app.models.vulnerability import Vulnerability

print("=" * 70)
print("SIMPLE INTEGRATION TEST - AFTER TIMEOUT FIXES")
print("=" * 70)

# 1. Create user
engine = create_engine(settings.DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

user = User(
    id=uuid4(),
    email=f"test_{uuid4().hex[:8]}@example.com",
    password_hash="test",
    full_name="Test",
)
session.add(user)
session.commit()
user_id = str(user.id)
print(f"\n[1] ✓ User created: {user_id}")

# 2. Create scan
try:
    r = requests.post(
        "http://127.0.0.1:8000/api/scans",
        json={
            "user_id": user_id,
            "repository_url": "file:///tmp/test_project",
            "language": "python",
        },
        timeout=10,
    )
    if r.status_code == 201:
        scan_id = r.json()["id"]
        print(f"[2] ✓ Scan created: {scan_id}")

        # 3. Run scan
        r = requests.post(f"http://127.0.0.1:8000/api/scans/{scan_id}/run", timeout=120)
        if r.status_code == 202:
            print(f"[3] ✓ Scan started (202 Accepted)")

            # 4. Wait for completion
            print(f"[4] Waiting for scan to complete...")
            for i in range(45):  # Max 90 seconds
                r = requests.get(
                    f"http://127.0.0.1:8000/api/scans/{scan_id}", timeout=10
                )
                status = r.json()["status"]
                if i % 5 == 0 or status != "running":
                    print(f"     [{i*2}s] Status: {status}")
                if status in ["completed", "failed"]:
                    break
                time.sleep(2)

            # 5. Check results
            session.expire_all()
            tools = (
                session.query(ToolExecution)
                .filter(ToolExecution.scan_id == scan_id)
                .all()
            )
            vulns = (
                session.query(Vulnerability)
                .filter(Vulnerability.scan_id == scan_id)
                .all()
            )

            print(f"\n[5] Results:")
            print(f"     Tools executed: {len(tools)}")
            for t in tools:
                tool_name = t.raw_output.get("tool", "?") if t.raw_output else "?"
                status_str = (
                    f"✓ {t.status}" if t.status == "success" else f"✗ {t.status}"
                )
                print(f"       - {tool_name}: {status_str}")
                if t.raw_output and t.raw_output.get("error"):
                    err_msg = t.raw_output["error"]
                    if len(err_msg) > 120:
                        print(f"         Error: {err_msg[:120]}...")
                    else:
                        print(f"         Error: {err_msg}")

            print(f"     Vulnerabilities found: {len(vulns)}")
            for v in vulns[:5]:
                print(f"       - {v.title} ({v.severity})")

            if tools and any(t.status == "success" for t in tools):
                print(f"\n✓ SUCCESS - Tools are working!")
            else:
                print(f"\n⚠ Tools did not execute successfully")
        else:
            print(f"[3] ✗ Failed to start scan: {r.status_code}")
    else:
        print(f"[2] ✗ Failed to create scan: {r.status_code}")
except Exception as e:
    print(f"✗ Error: {e}")

session.close()
