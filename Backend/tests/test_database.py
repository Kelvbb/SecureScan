#!/usr/bin/env python3
"""Script pour tester la base de données et les inserts."""

import sys
sys.path.insert(0, '/Users/djidji/Documents/Projets/IPSSI/SecureScan/backend')

from sqlalchemy import create_engine, inspect, text
from app.config import settings

print("=" * 60)
print("TEST 1: Connexion à la base de données")
print("=" * 60)

try:
    engine = create_engine(settings.DATABASE_URL)
    
    # Test la connexion
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        print("✓ Database connection successful")
    
    # Vérifie quelles tables existent
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    print(f"\n✓ Tables existantes ({len(tables)}):")
    for table in sorted(tables):
        print(f"  - {table}")
        
    # Vérifie la structure de quelques tables clés
    for table_name in ['owasp_categories', 'scans', 'tool_executions', 'vulnerabilities']:
        if table_name in tables:
            print(f"\n✓ {table_name}:")
            cols = inspector.get_columns(table_name)
            for col in cols:
                print(f"  - {col['name']}: {col['type']}")
        else:
            print(f"\n✗ {table_name} does not exist")
        
except Exception as e:
    print(f"✗ Error: {e}")
    print(f"  Database URL: {settings.DATABASE_URL}")
    sys.exit(1)

print("\n" + "=" * 60)
print("TEST 2: Vérification des données existantes")
print("=" * 60)

try:
    with engine.connect() as conn:
        # Compte des données
        for table in ['owasp_categories', 'scans', 'tool_executions', 'vulnerabilities']:
            try:
                result = conn.execute(text(f"SELECT COUNT(*) as cnt FROM {table}"))
                count = result.scalar()
                print(f"  {table}: {count} row(s)")
            except Exception as e:
                print(f"  {table}: Error - {e}")
                
except Exception as e:
    print(f"✗ Error: {e}")

print("\n" + "=" * 60)
print("TEST 3: Test d'une insertion simple dans scans")
print("=" * 60)

try:
    from uuid import uuid4
    from datetime import datetime
    from sqlalchemy.orm import sessionmaker
    from app.models import Scan, User
    
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Création d'un utilisateur test si nécessaire
    try:
        # Vérifier un utilisateur existe
        user = session.query(User).first()
        if not user:
            print("⚠ Pas d'utilisateur en base, création d'un test...")
            user = User(
                id=uuid4(),
                email="test@example.com",
                hashed_password="test_hash",
                full_name="Test User"
            )
            session.add(user)
            session.commit()
            print("✓ Utilisateur test créé")
        else:
            print(f"✓ Utilisateur existant trouvé: {user.email}")
        
        # Test d'insertion d'un scan
        scan = Scan(
            id=uuid4(),
            user_id=user.id,
            repository_url="https://github.com/test/repo.git",
            status="test",
            created_at=datetime.utcnow()
        )
        session.add(scan)
        session.commit()
        
        print(f"✓ Scan inséré avec succès (ID: {scan.id})")
        
        # Vérification que c'est bien en base
        count_result = session.query(Scan).filter(Scan.id == scan.id).first()
        if count_result:
            print(f"✓ Scan vérifié en base de données")
            print(f"  - Repository: {count_result.repository_url}")
            print(f"  - Status: {count_result.status}")
        
        # Cleanup - supprimer le scan de test
        session.delete(scan)
        session.commit()
        print("✓ Scan de test supprimé")
        
    finally:
        session.close()
        
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("RÉSUMÉ")
print("=" * 60)
print("✓ Tests complétés")
