#!/usr/bin/env python3
"""Script de diagnostic pour vérifier pourquoi aucune vulnérabilité n'est détectée."""

import asyncio
import json
import sys
from pathlib import Path

# Ajouter le chemin du backend
sys.path.insert(0, str(Path(__file__).parent))

from app.services.semgrep_service import SemgrepService

async def debug_scan(project_path: str):
    """Debug un scan sur un projet."""
    print("=" * 80)
    print(f"DIAGNOSTIC DU SCAN SUR: {project_path}")
    print("=" * 80)
    
    if not Path(project_path).exists():
        print(f"❌ Le chemin {project_path} n'existe pas")
        return
    
    # Test 1: Exécuter SemgrepService
    print("\n" + "=" * 80)
    print("ÉTAPE 1: Exécution de SemgrepService.run()")
    print("=" * 80)
    
    try:
        result = await SemgrepService.run(project_path)
        
        print(f"\n📊 Résultat de SemgrepService:")
        print(f"   Status: {result.get('status')}")
        print(f"   Keys disponibles: {list(result.keys())}")
        
        if result.get("status") == "error":
            print(f"\n❌ Erreur: {result.get('error')}")
            return
        
        if result.get("status") == "skipped":
            print(f"\n⚠️  Skipped: {result.get('reason')}")
            return
        
        # Afficher les statistiques
        stats = result.get("stats", {})
        if stats:
            print(f"\n📈 Statistiques:")
            print(f"   - Temps total: {stats.get('total_time', 0)}s")
            paths = stats.get("paths", {})
            if isinstance(paths, dict):
                scanned = paths.get("scanned", [])
                print(f"   - Fichiers analysés: {len(scanned)}")
                if scanned:
                    print(f"   - Exemples: {scanned[:5]}")
        
        # Afficher les résultats bruts
        results = result.get("results", [])
        print(f"\n📋 Résultats bruts de Semgrep:")
        print(f"   - Nombre de résultats: {len(results)}")
        
        if results:
            print(f"\n✅ Semgrep a trouvé {len(results)} résultats!")
            print(f"\n🔍 Exemples de résultats (3 premiers):")
            for i, res in enumerate(results[:3], 1):
                print(f"\n   {i}. Check ID: {res.get('check_id', 'Unknown')}")
                print(f"      Fichier: {res.get('path', 'Unknown')}")
                start = res.get("start", {})
                if isinstance(start, dict):
                    print(f"      Ligne: {start.get('line', '?')}")
                message = res.get("extra", {}).get("message", "No message")
                print(f"      Message: {message[:80]}")
        else:
            print(f"\n❌ Aucun résultat trouvé par Semgrep!")
            
            # Vérifier les erreurs
            errors = result.get("errors", [])
            if errors:
                print(f"\n   Erreurs ({len(errors)}):")
                for error in errors[:5]:
                    print(f"   - {error}")
            
            # Vérifier raw_output
            raw_output = result.get("raw_output", {})
            if raw_output:
                raw_results = raw_output.get("results", [])
                if raw_results:
                    print(f"\n   ⚠️  Mais raw_output contient {len(raw_results)} résultats!")
                    print(f"   Premier résultat: {json.dumps(raw_results[0], indent=2)[:500]}")
        
    except Exception as e:
        print(f"\n❌ Erreur lors de l'exécution: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Test 2: Parser les vulnérabilités
    print("\n" + "=" * 80)
    print("ÉTAPE 2: Parsing des vulnérabilités")
    print("=" * 80)
    
    try:
        vulns = SemgrepService.parse_vulnerabilities(result)
        print(f"\n📊 Vulnérabilités parsées: {len(vulns)}")
        
        if vulns:
            print(f"\n✅ Parsing réussi!")
            print(f"\n🔍 Exemples de vulnérabilités parsées (3 premières):")
            for i, vuln in enumerate(vulns[:3], 1):
                print(f"\n   {i}. {vuln.get('title', 'Unknown')[:60]}")
                print(f"      Fichier: {vuln.get('file_path', 'Unknown')}")
                print(f"      Lignes: {vuln.get('line_start')}-{vuln.get('line_end')}")
                print(f"      Sévérité: {vuln.get('severity', 'Unknown')}")
                print(f"      CWE: {vuln.get('cwe_id', 'N/A')}")
        else:
            print(f"\n❌ Aucune vulnérabilité parsée!")
            print(f"\n   Vérifiez que:")
            print(f"   1. Le status est 'success'")
            print(f"   2. Les résultats sont dans 'results' ou 'raw_output.results'")
            print(f"   3. Le format des résultats est correct")
            
            # Afficher un exemple de résultat brut pour debug
            if results:
                print(f"\n   Exemple de résultat brut:")
                print(json.dumps(results[0], indent=2)[:1000])
                
    except Exception as e:
        print(f"\n❌ Erreur lors du parsing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 debug_scan.py <chemin_du_projet>")
        print("\nExemple:")
        print("  python3 debug_scan.py /tmp/securescan/projects/SCAN_ID")
        sys.exit(1)
    
    project_path = sys.argv[1]
    asyncio.run(debug_scan(project_path))
