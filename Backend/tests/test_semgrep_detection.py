"""Script pour tester que Semgrep détecte bien des vulnérabilités connues."""

import asyncio
import json
import tempfile
import shutil
from pathlib import Path

from app.services.semgrep_service import SemgrepService


async def test_semgrep_detection():
    """Test Semgrep avec des vulnérabilités connues."""
    
    # Créer un répertoire temporaire avec des fichiers contenant des vulnérabilités
    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir)
        
        # Fichier Python avec vulnérabilités
        python_file = test_dir / "vulnerable.py"
        python_file.write_text("""
import subprocess
import os
import pickle
import eval

# Vulnérabilité 1: Command injection
user_input = input("Enter command: ")
subprocess.call(user_input, shell=True)  # DANGER: Command injection

# Vulnérabilité 2: Use of eval
code = input("Enter code: ")
result = eval(code)  # DANGER: Code injection

# Vulnérabilité 3: Insecure pickle
data = pickle.loads(user_input)  # DANGER: Insecure deserialization

# Vulnérabilité 4: Hardcoded password
password = "admin123"  # DANGER: Hardcoded secret

# Vulnérabilité 5: SQL injection (simulé)
query = f"SELECT * FROM users WHERE id = {user_input}"  # DANGER: SQL injection
""")
        
        # Fichier JavaScript avec vulnérabilités
        js_file = test_dir / "vulnerable.js"
        js_file.write_text("""
// Vulnérabilité 1: eval usage
const userCode = req.body.code;
eval(userCode);  // DANGER: Code injection

// Vulnérabilité 2: innerHTML with user input
const userInput = req.query.input;
document.getElementById('content').innerHTML = userInput;  // DANGER: XSS

// Vulnérabilité 3: setTimeout with string
setTimeout(userInput, 1000);  // DANGER: Code injection

// Vulnérabilité 4: Hardcoded secret
const apiKey = "sk_live_1234567890abcdef";  // DANGER: Hardcoded secret

// Vulnérabilité 5: Weak crypto
const crypto = require('crypto');
const hash = crypto.createHash('md5').update(password).digest('hex');  // DANGER: Weak hash
""")
        
        print(f"📁 Répertoire de test créé: {test_dir}")
        print(f"📄 Fichiers créés:")
        print(f"   - {python_file.name}")
        print(f"   - {js_file.name}")
        print()
        
        # Lancer Semgrep
        print("🔍 Lancement de Semgrep...")
        result = await SemgrepService.run(str(test_dir))
        
        print(f"\n📊 Résultats Semgrep:")
        print(f"   Status: {result.get('status')}")
        print(f"   Résultats bruts: {len(result.get('results', []))}")
        print(f"   Fichiers analysés: {len(result.get('analyzed_files', []))}")
        
        # Parser les vulnérabilités
        print(f"\n🔎 Parsing des vulnérabilités...")
        vulns = SemgrepService.parse_vulnerabilities(result)
        print(f"   Vulnérabilités parsées: {len(vulns)}")
        
        if vulns:
            print(f"\n✅ Vulnérabilités détectées:")
            for i, vuln in enumerate(vulns[:10], 1):  # Limiter à 10 pour l'affichage
                print(f"   {i}. {vuln.get('title', 'Unknown')}")
                print(f"      Fichier: {vuln.get('file_path', 'Unknown')}")
                print(f"      Ligne: {vuln.get('line_start', 'Unknown')}")
                print(f"      Sévérité: {vuln.get('severity', 'Unknown')}")
                print()
        else:
            print(f"\n❌ AUCUNE vulnérabilité détectée!")
            print(f"   Cela indique un problème avec Semgrep ou sa configuration.")
            print(f"\n📋 Détails de debug:")
            print(f"   raw_output keys: {list(result.get('raw_output', {}).keys())}")
            if 'raw_output' in result:
                raw = result['raw_output']
                print(f"   raw_output.results: {len(raw.get('results', []))}")
                print(f"   raw_output.errors: {len(raw.get('errors', []))}")
                if raw.get('errors'):
                    print(f"   Erreurs: {raw['errors'][:3]}")
        
        return len(vulns) > 0


if __name__ == "__main__":
    # Vérifier que Semgrep est installé
    if not shutil.which("semgrep"):
        print("❌ Semgrep n'est pas installé!")
        print("   Installez-le avec: pip install semgrep")
        exit(1)
    
    print("=" * 80)
    print("TEST DE DÉTECTION SEMGREP")
    print("=" * 80)
    print()
    
    success = asyncio.run(test_semgrep_detection())
    
    print("=" * 80)
    if success:
        print("✅ TEST RÉUSSI: Semgrep détecte des vulnérabilités")
    else:
        print("❌ TEST ÉCHOUÉ: Semgrep ne détecte pas de vulnérabilités")
        print("   Vérifiez la configuration et les règles Semgrep")
    print("=" * 80)
