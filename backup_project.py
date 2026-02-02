#!/usr/bin/env python3
"""
Script de sauvegarde complète du projet LivraFaso
Crée une sauvegarde avant implémentation de la nouvelle structure
"""

import os
import shutil
import zipfile
from pathlib import Path
from datetime import datetime

def create_backup():
    """Crée une sauvegarde complète du projet"""
    project_root = Path.cwd()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"livrafaso_backup_{timestamp}"
    
    # Créer le dossier de sauvegarde
    backup_dir = project_root.parent / backup_name
    backup_zip = project_root.parent / f"{backup_name}.zip"
    
    print(f"🔄 Création de la sauvegarde: {backup_name}")
    print("=" * 50)
    
    # Dossiers à ignorer
    ignore_patterns = {
        '__pycache__', '*.pyc', '.git', 'node_modules', 
        '.venv', 'venv', '.env', '*.log', '.DS_Store'
    }
    
    def ignore_function(dir, files):
        ignored = []
        for file in files:
            if any(pattern in file for pattern in ignore_patterns):
                ignored.append(file)
        return ignored
    
    try:
        # Copier le projet
        print("📁 Copie des fichiers...")
        shutil.copytree(
            project_root, 
            backup_dir, 
            ignore=ignore_function
        )
        
        # Créer l'archive ZIP
        print("📦 Création de l'archive ZIP...")
        with zipfile.ZipFile(backup_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(backup_dir):
                # Filtrer les dossiers à ignorer
                dirs[:] = [d for d in dirs if d not in ignore_patterns]
                
                for file in files:
                    if not any(pattern in file for pattern in ignore_patterns):
                        file_path = Path(root) / file
                        arc_path = file_path.relative_to(backup_dir)
                        zipf.write(file_path, arc_path)
        
        # Supprimer le dossier temporaire
        shutil.rmtree(backup_dir)
        
        # Statistiques
        backup_size = backup_zip.stat().st_size / (1024 * 1024)  # MB
        
        print("✅ Sauvegarde terminée avec succès!")
        print(f"📍 Emplacement: {backup_zip}")
        print(f"📊 Taille: {backup_size:.1f} MB")
        
        return str(backup_zip)
        
    except Exception as e:
        print(f"❌ Erreur lors de la sauvegarde: {e}")
        # Nettoyer en cas d'erreur
        if backup_dir.exists():
            shutil.rmtree(backup_dir)
        if backup_zip.exists():
            backup_zip.unlink()
        return None

def main():
    """Fonction principale"""
    print("💾 SAUVEGARDE COMPLÈTE LIVRAFASO")
    print("=" * 40)
    
    backup_path = create_backup()
    
    if backup_path:
        print("\n🎉 SAUVEGARDE RÉUSSIE!")
        print("📋 Vous pouvez maintenant procéder à l'implémentation")
        print("🔄 Pour restaurer: décompresser l'archive ZIP")
        print(f"📁 Sauvegarde: {backup_path}")
    else:
        print("\n❌ ÉCHEC DE LA SAUVEGARDE")
        print("⚠️  Ne pas procéder à l'implémentation sans sauvegarde")
    
    return backup_path is not None

if __name__ == "__main__":
    main()
