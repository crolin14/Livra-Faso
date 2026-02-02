#!/usr/bin/env python
"""
Script automatisé complet pour migration RBAC UUID
Exécute toutes les étapes automatiquement
"""

import os
import sys
import django
import subprocess
from pathlib import Path

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Livraison_Faso.settings')
django.setup()

from django.db import connection
from django.core.management import execute_from_command_line

def run_command(cmd, description):
    """Exécute une commande avec gestion d'erreur"""
    print(f"🔄 {description}...")
    try:
        if isinstance(cmd, str) and cmd.startswith('python manage.py'):
            # Utiliser execute_from_command_line pour les commandes Django
            django_cmd = cmd.replace('python manage.py ', '').split()
            execute_from_command_line(['manage.py'] + django_cmd)
        elif isinstance(cmd, list):
            result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
            if result.returncode != 0:
                print(f"❌ Erreur: {result.stderr}")
                return False
            if result.stdout:
                print(f"   {result.stdout.strip()}")
        else:
            # Pour les autres commandes
            result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
            if result.returncode != 0:
                print(f"❌ Erreur: {result.stderr}")
                return False
            if result.stdout:
                print(f"   {result.stdout.strip()}")
        print(f"   ✅ {description} terminé")
        return True
    except Exception as e:
        print(f"   ❌ Erreur {description}: {e}")
        return False

def clean_database():
    """Nettoie complètement la base de données RBAC"""
    print("🗑️ Nettoyage de la base de données...")
    
    with connection.cursor() as cursor:
        try:
            # Supprimer les tables RBAC
            tables = ['rbac_permissioncache', 'rbac_userrole', 'rbac_rolepermission', 'rbac_permission', 'rbac_role']
            for table in tables:
                cursor.execute(f"DROP TABLE IF EXISTS {table} CASCADE;")
                print(f"   ✅ Table {table} supprimée")
            
            # Nettoyer les migrations Django
            cursor.execute("DELETE FROM django_migrations WHERE app = 'rbac';")
            print("   ✅ Migrations RBAC supprimées")
            
            return True
        except Exception as e:
            print(f"   ❌ Erreur nettoyage base: {e}")
            return False

def clean_migration_files():
    """Supprime tous les fichiers de migration RBAC"""
    print("🗑️ Nettoyage des fichiers de migration...")
    
    migrations_dir = Path("rbac/migrations")
    if migrations_dir.exists():
        # Supprimer tous les fichiers de migration sauf __init__.py
        for file in migrations_dir.glob("0*.py"):
            try:
                file.unlink()
                print(f"   ✅ Supprimé {file.name}")
            except Exception as e:
                print(f"   ❌ Erreur suppression {file.name}: {e}")
        
        # Nettoyer le cache
        pycache_dir = migrations_dir / "__pycache__"
        if pycache_dir.exists():
            import shutil
            shutil.rmtree(pycache_dir)
            print("   ✅ Cache __pycache__ supprimé")
    
    return True

def create_migrations():
    """Crée les nouvelles migrations RBAC"""
    print("📝 Création des nouvelles migrations...")
    
    # Essayer plusieurs méthodes avec execute_from_command_line
    methods = [
        ['makemigrations', 'rbac'],
        ['makemigrations', 'rbac', '--name', 'initial_uuid'],
        ['makemigrations', 'rbac', '--empty', '--name', 'initial_uuid']
    ]
    
    for i, method in enumerate(methods, 1):
        print(f"   Tentative {i}: {' '.join(method)}")
        try:
            execute_from_command_line(['manage.py'] + method)
            print(f"   ✅ Migration créée avec succès")
            return True
        except Exception as e:
            print(f"   ❌ Erreur méthode {i}: {e}")
            continue
    
    print("❌ Toutes les méthodes de création de migration ont échoué")
    return False

def apply_migrations():
    """Applique les migrations RBAC"""
    print("🔄 Application des migrations RBAC...")
    try:
        execute_from_command_line(['manage.py', 'migrate', 'rbac'])
        print("   ✅ Migrations RBAC appliquées")
        return True
    except Exception as e:
        print(f"   ❌ Erreur application migrations: {e}")
        return False

def verify_system():
    """Vérifie l'intégrité du système"""
    print("🔄 Vérification du système...")
    try:
        execute_from_command_line(['manage.py', 'check'])
        print("   ✅ Vérification système terminée")
        return True
    except Exception as e:
        print(f"   ❌ Erreur vérification système: {e}")
        return False

def test_uuid_creation():
    """Test la création d'objets UUID"""
    print("🧪 Test de création UUID...")
    
    try:
        from rbac.models import Role
        
        # Créer un rôle de test
        test_role = Role.objects.create(
            name='test_uuid_auto',
            display_name='Test UUID Automatique',
            description='Test automatique de création UUID'
        )
        
        print(f"   ✅ Rôle créé avec UUID: {test_role.id}")
        print(f"   ✅ Type UUID: {type(test_role.id)}")
        
        # Supprimer le rôle de test
        test_role.delete()
        print("   ✅ Rôle de test supprimé")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Erreur test UUID: {e}")
        return False

def verify_database_structure():
    """Vérifie la structure de la base de données"""
    print("🔍 Vérification de la structure de la base...")
    
    with connection.cursor() as cursor:
        try:
            # Vérifier les tables créées
            cursor.execute("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name LIKE 'rbac_%'
                ORDER BY table_name;
            """)
            tables = [row[0] for row in cursor.fetchall()]
            
            if tables:
                print(f"   ✅ Tables RBAC créées: {', '.join(tables)}")
                
                # Vérifier les types de colonnes ID
                for table in tables:
                    cursor.execute(f"""
                        SELECT data_type FROM information_schema.columns 
                        WHERE table_name = '{table}' AND column_name = 'id';
                    """)
                    result = cursor.fetchone()
                    if result:
                        data_type = result[0]
                        if data_type == 'uuid':
                            print(f"   ✅ {table}.id: UUID")
                        else:
                            print(f"   ❌ {table}.id: {data_type} (devrait être UUID)")
                            return False
                
                return True
            else:
                print("   ❌ Aucune table RBAC trouvée")
                return False
                
        except Exception as e:
            print(f"   ❌ Erreur vérification structure: {e}")
            return False

def main():
    """Fonction principale d'exécution automatique"""
    print("🚀 MIGRATION AUTOMATIQUE RBAC UUID")
    print("=" * 50)
    
    steps = [
        ("Nettoyage base de données", clean_database),
        ("Nettoyage fichiers migration", clean_migration_files),
        ("Création nouvelles migrations", create_migrations),
        ("Application des migrations", apply_migrations),
        ("Vérification système", verify_system),
        ("Vérification structure base", verify_database_structure),
        ("Test création UUID", test_uuid_creation),
    ]
    
    success_count = 0
    
    for step_name, step_func in steps:
        print(f"\n📋 Étape: {step_name}")
        if step_func():
            success_count += 1
        else:
            print(f"❌ Échec à l'étape: {step_name}")
            break
    
    print(f"\n{'='*50}")
    if success_count == len(steps):
        print("🎉 MIGRATION RBAC UUID RÉUSSIE!")
        print("\n✅ Résultats:")
        print("- Tables RBAC créées avec UUID natifs")
        print("- Aucune erreur de conversion bigint→UUID")
        print("- Système vérifié et fonctionnel")
        print("- Test UUID réussi")
        print("\n🚀 Prochaines étapes:")
        print("1. python manage.py migrate (autres apps)")
        print("2. python manage.py runserver")
        return True
    else:
        print(f"❌ ÉCHEC DE LA MIGRATION ({success_count}/{len(steps)} étapes réussies)")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
