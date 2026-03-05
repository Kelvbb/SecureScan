#!/usr/bin/env python3
"""Script de test pour vérifier le pipeline complet de Semgrep."""

import asyncio
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# Ajouter le chemin du backend
sys.path.insert(0, str(Path(__file__).parent))

from app.services.semgrep_service import SemgrepService

# Code de test avec des vulnérabilités connues
TEST_CODE = """
# Fichier de test avec des vulnérabilités connues

import os
import subprocess
import sqlite3

# Vulnérabilité 1: Injection SQL
def unsafe_query(user_input):
    conn = sqlite3.connect('db.sqlite3')
    cursor = conn.cursor()
    query = f"SELECT * FROM users WHERE name = '{user_input}'"  # SQL injection
    cursor.execute(query)
    return cursor.fetchall()

# Vulnérabilité 2: Command injection
def unsafe_command(filename):
    os.system(f"cat {filename}")  # Command injection

# Vulnérabilité 3: Hardcoded secret
API_KEY = "sk_live_1234567890abcdef"  # Hardcoded secret

# Vulnérabilité 4: Weak cryptography
import hashlib
password = "user123"
hashed = hashlib.md5(password.encode()).hexdigest()  # Weak hash

# Vulnérabilité 5: Insecure deserialization
import pickle
data = pickle.loads(user_input)  # Insecure deserialization
"""

async def test_semgrep_pipeline():
    """Test le pipeline complet de Semgrep."""
    print("=" * 80)
    print("TEST DU PIPELINE SEMGREP")
    print("=" * 80)
    
    # Vérifier que Semgrep est installé
    semgrep_path = shutil.which("semgrep")
    if not semgrep_path:
        print("❌ Semgrep n'est pas installé dans le PATH")
        print("   Installez-le avec: pip install semgrep")
        return False
    
    print(f"✅ Semgrep trouvé: {semgrep_path}")
    
    # Créer un répertoire temporaire avec le fichier de test
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test_vulns.py"
        test_file.write_text(TEST_CODE)
        
        print(f"\n📝 Fichier de test créé: {test_file}")
        print(f"   Contient 5 vulnérabilités connues")
        
        # Test 1: Exécuter Semgrep directement
        print("\n" + "=" * 80)
        print("TEST 1: Exécution directe de Semgrep")
        print("=" * 80)
        
        cmd = [
            semgrep_path,
            "--json",
            "--no-git-ignore",
            "--config=auto",
            "-c", "p/security-audit",
            "-c", "p/owasp-top-ten",
            str(tmpdir),
        ]
        
        print(f"Commande: {' '.join(cmd)}")
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=60.0
            )
            
            if process.returncode != 0:
                print(f"❌ Semgrep a retourné un code d'erreur: {process.returncode}")
                if stderr:
                    print(f"Erreur: {stderr.decode()[:500]}")
                return False
            
            # Parser les résultats
            try:
                data = json.loads(stdout.decode())
                results = data.get("results", [])
                errors = data.get("errors", [])
                stats = data.get("stats", {})
                
                print(f"\n📊 Résultats bruts de Semgrep:")
                print(f"   - {len(results)} vulnérabilités trouvées")
                print(f"   - {len(errors)} erreurs")
                
                if results:
                    print(f"\n✅ Semgrep fonctionne correctement!")
                    print(f"\n🔍 Exemples de vulnérabilités détectées:")
                    for i, result in enumerate(results[:5], 1):
                        check_id = result.get("check_id", "Unknown")
                        message = result.get("extra", {}).get("message", "")
                        file_path = result.get("path", "")
                        line = result.get("start", {}).get("line", "?")
                        print(f"   {i}. {check_id} (ligne {line}): {message[:60]}")
                    
                    # Afficher un exemple complet
                    if results:
                        print(f"\n📄 Exemple de résultat complet (premier):")
                        print(json.dumps(results[0], indent=2)[:1000])
                else:
                    print(f"\n❌ Aucune vulnérabilité détectée par Semgrep!")
                    if errors:
                        print(f"\n   Erreurs:")
                        for error in errors[:5]:
                            print(f"   - {error}")
                    
                    print(f"\n   Stats: {json.dumps(stats, indent=2)[:500]}")
                    return False
                    
            except json.JSONDecodeError as e:
                print(f"\n❌ Erreur de parsing JSON: {e}")
                print(f"   Sortie: {stdout.decode()[:500]}")
                return False
                
        except asyncio.TimeoutError:
            print(f"\n❌ Timeout lors de l'exécution de Semgrep")
            return False
        except Exception as e:
            print(f"\n❌ Erreur: {e}")
            return False
        
        # Test 2: Utiliser SemgrepService
        print("\n" + "=" * 80)
        print("TEST 2: Utilisation de SemgrepService")
        print("=" * 80)
        
        try:
            result = await SemgrepService.run(str(tmpdir))
            
            print(f"\n📊 Résultat de SemgrepService:")
            print(f"   Status: {result.get('status')}")
            print(f"   Keys: {list(result.keys())}")
            
            if result.get("status") == "success":
                results_count = len(result.get("results", []))
                print(f"   Nombre de résultats: {results_count}")
                
                if results_count > 0:
                    print(f"\n✅ SemgrepService retourne des résultats!")
                    
                    # Test 3: Parser les vulnérabilités
                    print("\n" + "=" * 80)
                    print("TEST 3: Parsing des vulnérabilités")
                    print("=" * 80)
                    
                    vulns = SemgrepService.parse_vulnerabilities(result)
                    print(f"\n📊 Vulnérabilités parsées: {len(vulns)}")
                    
                    if vulns:
                        print(f"\n✅ Parsing réussi!")
                        print(f"\n🔍 Exemples de vulnérabilités parsées:")
                        for i, vuln in enumerate(vulns[:5], 1):
                            print(f"   {i}. {vuln.get('title', 'Unknown')[:60]}")
                            print(f"      Fichier: {vuln.get('file_path', 'Unknown')}")
                            print(f"      Lignes: {vuln.get('line_start')}-{vuln.get('line_end')}")
                            print(f"      Sévérité: {vuln.get('severity', 'Unknown')}")
                    else:
                        print(f"\n❌ Aucune vulnérabilité parsée!")
                        print(f"   Vérifiez le format des résultats Semgrep")
                        print(f"   Résultats bruts: {json.dumps(result, indent=2)[:1000]}")
                        return False
                else:
                    print(f"\n❌ SemgrepService ne retourne aucun résultat!")
                    print(f"   Résultat complet: {json.dumps(result, indent=2)[:1000]}")
                    return False
            else:
                error = result.get("error", "Unknown error")
                print(f"\n❌ SemgrepService a retourné une erreur: {error}")
                return False
                
        except Exception as e:
            print(f"\n❌ Erreur lors de l'appel à SemgrepService: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    print("\n" + "=" * 80)
    print("✅ TOUS LES TESTS SONT PASSÉS!")
    print("=" * 80)
    return True

if __name__ == "__main__":
    success = asyncio.run(test_semgrep_pipeline())
    sys.exit(0 if success else 1)
