#!/usr/bin/env python3
"""
Nettoyage complet des références dashboard restantes dans le code
"""

import os
import re
from pathlib import Path

def clean_dashboard_references():
    """Nettoyer toutes les références dashboard restantes"""
    
    base_dir = Path(__file__).parent.absolute()
    cleaned_files = []
    
    print("🧹 NETTOYAGE DES RÉFÉRENCES DASHBOARD RESTANTES", flush=True)
    
    # Fichiers Python à nettoyer
    python_files = [
        "users/views.py",
        "users/views_secure.py", 
        "test_interactions_frontend.py",
        "test_frontend_simple.py",
        "validate_fixes.py",
        "validate_refactoring.py"
    ]
    
    for py_file in python_files:
        file_path = base_dir / py_file
        if file_path.exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                original_content = content
                lines_removed = 0
                
                # Supprimer les lignes contenant 'dashboard'
                lines = content.split('\n')
                cleaned_lines = []
                
                for line in lines:
                    if 'dashboard' in line.lower():
                        lines_removed += 1
                        print(f"🗑️ Ligne supprimée dans {py_file}: {line.strip()[:60]}...", flush=True)
                        
                        # Remplacer les redirections dashboard par home
                        if 'redirect(' in line and 'dashboard' in line.lower():
                            new_line = line.replace("'public:dashboard'", "'public:home'")
                            new_line = new_line.replace('"public:dashboard"', '"public:home"')
                            new_line = new_line.replace("'/dashboard/'", "'/'")
                            cleaned_lines.append(new_line)
                            print(f"✅ Redirection remplacée: {new_line.strip()}", flush=True)
                        # Sinon, supprimer complètement la ligne
                    else:
                        cleaned_lines.append(line)
                
                if lines_removed > 0:
                    # Réécrire le fichier
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write('\n'.join(cleaned_lines))
                    
                    print(f"✅ {py_file}: {lines_removed} lignes nettoyées", flush=True)
                    cleaned_files.append(py_file)
                
            except Exception as e:
                print(f"❌ Erreur {py_file}: {e}")
    
    # Nettoyer les fichiers de documentation
    doc_files = [
        "VERIFICATION_LIENS_RESSOURCES.md"
    ]
    
    for doc_file in doc_files:
        file_path = base_dir / doc_file
        if file_path.exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Supprimer les lignes contenant dashboard
                lines = content.split('\n')
                cleaned_lines = []
                lines_removed = 0
                
                for line in lines:
                    if 'dashboard' not in line.lower():
                        cleaned_lines.append(line)
                    else:
                        lines_removed += 1
                        print(f"🗑️ Doc supprimée: {line.strip()[:60]}...", flush=True)
                
                if lines_removed > 0:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write('\n'.join(cleaned_lines))
                    
                    print(f"✅ {doc_file}: {lines_removed} lignes nettoyées", flush=True)
                    cleaned_files.append(doc_file)
                    
            except Exception as e:
                print(f"❌ Erreur doc {doc_file}: {e}")
    
    # Supprimer le script ultimate_dashboard_destroyer.py
    destroyer_script = base_dir / "ultimate_dashboard_destroyer.py"
    if destroyer_script.exists():
        try:
            destroyer_script.unlink()
            print("✅ Script ultimate_dashboard_destroyer.py supprimé", flush=True)
            cleaned_files.append("ultimate_dashboard_destroyer.py")
        except Exception as e:
            print(f"❌ Erreur suppression script: {e}")
    
    print(f"\n🎉 NETTOYAGE TERMINÉ!")
    print(f"📊 Fichiers nettoyés: {len(cleaned_files)}")
    
    if cleaned_files:
        print("\n📝 FICHIERS MODIFIÉS:")
        for file in cleaned_files:
            print(f"  ✅ {file}")
    
    return len(cleaned_files)

if __name__ == "__main__":
    count = clean_dashboard_references()
    print(f"\n✅ NETTOYAGE COMPLET: {count} fichiers traités!")
