#!/usr/bin/env python3
"""Script pour vérifier les imports."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from app.services.semgrep_service import SemgrepService

    print("✓ SemgrepService imported")
except Exception as e:
    print(f"✗ SemgrepService error: {e}")

try:
    from app.services.pip_audit_service import PipAuditService, NpmAuditService

    print("✓ PipAuditService & NpmAuditService imported")
except Exception as e:
    print(f"✗ PipAuditService error: {e}")

try:
    from app.services.trufflehog_service import TruffleHogService

    print("✓ TruffleHogService imported")
except Exception as e:
    print(f"✗ TruffleHogService error: {e}")

try:
    from app.services.scan_orchestrator import ScanOrchestrator

    print("✓ ScanOrchestrator imported")
except Exception as e:
    print(f"✗ ScanOrchestrator error: {e}")

try:
    from app.api.routes import scans

    print("✓ Scans routes imported")
except Exception as e:
    print(f"✗ Scans routes error: {e}")

print("\n✓ All imports successful!")
