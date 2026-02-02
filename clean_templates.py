#!/usr/bin/env python3
"""
Script pour nettoyer complètement le dossier templates et recréer la structure
"""
import os
import shutil

def clean_templates():
    """Nettoie complètement le dossier templates"""
    
    templates_dir = r"c:\Users\hp\Documents\Livraison_Faso\templates"
    
    # Supprimer complètement le dossier templates
    if os.path.exists(templates_dir):
        try:
            shutil.rmtree(templates_dir)
            print(f"✅ Dossier templates supprimé: {templates_dir}")
        except Exception as e:
            print(f"❌ Erreur suppression: {e}")
    
    # Recréer la structure
    os.makedirs(os.path.join(templates_dir, "public"), exist_ok=True)
    os.makedirs(os.path.join(templates_dir, "admin"), exist_ok=True)
    os.makedirs(os.path.join(templates_dir, "analytics"), exist_ok=True)
    os.makedirs(os.path.join(templates_dir, "chat"), exist_ok=True)
    
    print("✅ Structure templates recréée")

if __name__ == "__main__":
    clean_templates()
