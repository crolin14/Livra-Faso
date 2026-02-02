#!/usr/bin/env python
"""
Script pour ajouter la colonne package_type manquante à la table missions_mission
"""
import os
import django
import psycopg2
from django.conf import settings

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Livraison_Faso.settings')
django.setup()

def add_package_type_column():
    """Ajoute la colonne package_type à la table missions_mission"""
    try:
        # Connexion directe à PostgreSQL
        conn = psycopg2.connect(
            host='localhost',
            database='livraison_faso',
            user='livraison_user',
            password='livraison123'
        )
        cur = conn.cursor()
        
        # Vérifier si la colonne existe déjà
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'missions_mission' 
            AND column_name = 'package_type';
        """)
        
        if cur.fetchone():
            print("✅ La colonne package_type existe déjà")
        else:
            # Ajouter la colonne
            cur.execute("""
                ALTER TABLE missions_mission 
                ADD COLUMN package_type VARCHAR(20) DEFAULT 'colis_petit';
            """)
            conn.commit()
            print("✅ Colonne package_type ajoutée avec succès")
        
        # Vérification finale
        cur.execute("""
            SELECT column_name, data_type, column_default 
            FROM information_schema.columns 
            WHERE table_name = 'missions_mission' 
            AND column_name = 'package_type';
        """)
        
        result = cur.fetchone()
        if result:
            print(f"📋 Colonne: {result[0]}, Type: {result[1]}, Défaut: {result[2]}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False

if __name__ == "__main__":
    add_package_type_column()
