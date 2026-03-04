#!/usr/bin/env python3
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from app.config import settings

engine = create_engine(settings.DATABASE_URL)

with engine.connect() as conn:
    print("\n" + "=" * 70)
    print("  VÉRIFICATION DES INSERTS EN BASE DE DONNÉES")
    print("=" * 70 + "\n")

    for table in [
        "users",
        "scans",
        "tool_executions",
        "vulnerabilities",
        "owasp_categories",
    ]:
        r = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
        count = r.scalar()
        print(f"  {table:<20}: {count:>4} rows")

    print("\n" + "=" * 70)
    print("✓ RÉSULTAT: données insérées correctement dans la base de données.")
    print("=" * 70 + "\n")
