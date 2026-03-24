#!/usr/bin/env python
"""
Script pour nettoyer les données sensibles avant de push sur GitHub
"""
import os
import re
from pathlib import Path

def clean_settings_file():
    """Nettoie le fichier settings.py des données sensibles"""
    settings_file = Path('Livraison_Faso/settings.py')
    
    if not settings_file.exists():
        print("Fichier settings.py non trouvé")
        return
    
    with open(settings_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Remplacer la clé secrète par une variable d'environnement
    content = re.sub(
        r"SECRET_KEY = os\.environ\.get\('SECRET_KEY', 'django-insecure-[^']+'\)",
        "SECRET_KEY = os.environ.get('SECRET_KEY', '')",
        content
    )
    
    with open(settings_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✓ Fichier settings.py nettoyé")

def create_env_file():
    """Crée un fichier .env à partir de .env.example"""
    env_example = Path('.env.example')
    env_file = Path('.env')
    
    if env_example.exists() and not env_file.exists():
        with open(env_example, 'r', encoding='utf-8') as f:
            content = f.read()
        
        with open(env_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✓ Fichier .env créé à partir de .env.example")
    else:
        print("! Fichier .env existe déjà ou .env.example non trouvé")

def check_sensitive_files():
    """Vérifie la présence de fichiers sensibles"""
    sensitive_patterns = [
        '*.db', '*.sqlite3', '*.log', '.env', 
        'media/', 'staticfiles/', '__pycache__/'
    ]
    
    print("\nVérification des fichiers sensibles:")
    for pattern in sensitive_patterns:
        import glob
        files = glob.glob(pattern, recursive=True)
        if files:
            print(f"  ⚠ {pattern}: {len(files)} fichier(s) trouvé(s)")
        else:
            print(f"  ✓ {pattern}: aucun fichier trouvé")

if __name__ == '__main__':
    print("Nettoyage des données sensibles pour GitHub...")
    clean_settings_file()
    create_env_file()
    check_sensitive_files()
    print("\n✓ Préparation terminée!")
