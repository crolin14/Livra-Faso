# 🚀 Commandes Django Spécifiques - Migration RBAC UUID

## 📋 **Commandes de Diagnostic**

### Vérifier l'état des migrations
```bash
# Voir toutes les migrations RBAC
python manage.py showmigrations rbac

# Voir l'état de toutes les migrations
python manage.py showmigrations

# Vérifier les migrations non appliquées
python manage.py showmigrations --plan
```

### Diagnostic des données existantes
```bash
# Accéder au shell Django
python manage.py shell

# Dans le shell Python:
from rbac.models import Role, Permission, RolePermission, UserRole
from django.db import connection

# Compter les enregistrements
print(f"Rôles: {Role.objects.count()}")
print(f"Permissions: {Permission.objects.count()}")
print(f"RolePermissions: {RolePermission.objects.count()}")
print(f"UserRoles: {UserRole.objects.count()}")

# Vérifier le type des colonnes ID
with connection.cursor() as cursor:
    cursor.execute("""
        SELECT table_name, column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name LIKE 'rbac_%' AND column_name = 'id'
        ORDER BY table_name;
    """)
    for row in cursor.fetchall():
        print(f"{row[0]}.{row[1]}: {row[2]}")

exit()
```

### Vérifier l'intégrité de la base
```bash
# Vérification complète Django
python manage.py check

# Vérification spécifique RBAC
python manage.py check rbac

# Test de connexion à la base
python manage.py dbshell
\dt rbac_*
\q
```

## 🔧 **Commandes de Correction**

### Option 1: Annuler la migration problématique
```bash
# Revenir à la migration précédente
python manage.py migrate rbac 0001 --fake

# Supprimer la migration problématique
del rbac\migrations\0002_alter_permission_options_alter_role_options_and_more.py

# Ou sur Linux/Mac:
rm rbac/migrations/0002_alter_permission_options_alter_role_options_and_more.py
```

### Option 2: Reset complet des migrations RBAC
```bash
# Revenir à zéro (ATTENTION: supprime les données)
python manage.py migrate rbac zero --fake

# Supprimer toutes les migrations RBAC
del rbac\migrations\000*.py

# Garder seulement __init__.py
# Recréer les migrations
python manage.py makemigrations rbac

# Appliquer les nouvelles migrations
python manage.py migrate rbac
```

### Option 3: Utiliser les scripts automatisés
```bash
# Script complet avec options
python fix_rbac_uuid_complete.py

# Mode automatique (recommandation)
python fix_rbac_uuid_complete.py auto

# Force le reset complet
python fix_rbac_uuid_complete.py reset

# Force la migration manuelle
python fix_rbac_uuid_complete.py manual

# Ou utiliser le script batch Windows
fix_rbac_migration.bat
```

## 💾 **Commandes de Sauvegarde**

### Sauvegarde avant migration
```bash
# Sauvegarde complète de la base
pg_dump -U username -h localhost -d livrafaso_db > backup_before_rbac_migration.sql

# Sauvegarde des données RBAC seulement
python manage.py dumpdata rbac --output=rbac_backup.json

# Sauvegarde avec indentation (plus lisible)
python manage.py dumpdata rbac --indent=2 --output=rbac_backup_readable.json

# Sauvegarde des utilisateurs (au cas où)
python manage.py dumpdata users --output=users_backup.json
```

### Restauration si nécessaire
```bash
# Restaurer depuis la sauvegarde JSON
python manage.py loaddata rbac_backup.json

# Restaurer depuis la sauvegarde PostgreSQL
psql -U username -h localhost -d livrafaso_db < backup_before_rbac_migration.sql
```

## 🔄 **Commandes de Migration Manuelle**

### Créer une migration vide personnalisée
```bash
# Créer une migration vide
python manage.py makemigrations rbac --empty --name bigint_to_uuid_manual

# Éditer le fichier créé dans rbac/migrations/
# Ajouter le code de migration manuelle

# Appliquer la migration personnalisée
python manage.py migrate rbac
```

### Exécuter du SQL personnalisé
```bash
# Accéder au shell de base de données
python manage.py dbshell

-- SQL pour vérifier les tables
\dt rbac_*

-- SQL pour voir la structure
\d rbac_role
\d rbac_permission

-- Quitter
\q
```

## ✅ **Commandes de Validation Post-Migration**

### Vérifier que tout fonctionne
```bash
# Vérification Django complète
python manage.py check

# Test des modèles RBAC
python manage.py shell

# Dans le shell:
from rbac.models import Role, Permission
import uuid

# Créer un rôle de test
role = Role.objects.create(
    name='test_uuid',
    display_name='Test UUID',
    description='Test après migration'
)

print(f"Rôle créé avec UUID: {role.id}")
print(f"Type de l'ID: {type(role.id)}")

# Vérifier que c'est bien un UUID
assert isinstance(role.id, uuid.UUID)
print("✅ UUID valide!")

# Nettoyer
role.delete()
print("✅ Test terminé")

exit()
```

### Tester les relations
```bash
python manage.py shell

# Test des relations entre modèles
from rbac.models import Role, Permission, RolePermission
from users.models import User

# Créer des objets de test
role = Role.objects.create(name='test_role', display_name='Test Role')
perm = Permission.objects.create(name='test_perm', display_name='Test Permission')

# Créer une relation
role_perm = RolePermission.objects.create(role=role, permission=perm)

print(f"Relation créée: {role_perm.id}")
print(f"Rôle: {role_perm.role.name}")
print(f"Permission: {role_perm.permission.name}")

# Nettoyer
role_perm.delete()
perm.delete()
role.delete()

print("✅ Relations fonctionnelles!")
exit()
```

## 🚀 **Commandes de Démarrage Final**

### Après migration réussie
```bash
# Appliquer toutes les migrations restantes
python manage.py migrate

# Collecter les fichiers statiques
python manage.py collectstatic --noinput

# Créer un superutilisateur si nécessaire
python manage.py createsuperuser

# Démarrer le serveur
python manage.py runserver
```

### Peupler avec des données par défaut
```bash
python manage.py shell

# Créer les rôles de base
from rbac.models import Role, Permission

# Rôles standards
admin_role = Role.objects.create(
    name='admin',
    display_name='Administrateur',
    description='Accès complet au système'
)

user_role = Role.objects.create(
    name='user',
    display_name='Utilisateur',
    description='Accès utilisateur standard'
)

print("✅ Rôles de base créés")
exit()
```

## 🔍 **Commandes de Dépannage**

### Si les migrations sont bloquées
```bash
# Marquer une migration comme appliquée sans l'exécuter
python manage.py migrate rbac 0001 --fake

# Marquer toutes les migrations comme appliquées
python manage.py migrate --fake

# Voir l'historique des migrations
python manage.py showmigrations --verbosity=2
```

### Si les tables existent déjà
```bash
# Marquer les migrations comme appliquées
python manage.py migrate --fake-initial

# Ou spécifiquement pour RBAC
python manage.py migrate rbac --fake-initial
```

### Nettoyer complètement (DANGER)
```bash
# ATTENTION: Supprime toutes les données RBAC
python manage.py dbshell

DROP TABLE IF EXISTS rbac_permissioncache CASCADE;
DROP TABLE IF EXISTS rbac_userrole CASCADE;
DROP TABLE IF EXISTS rbac_rolepermission CASCADE;
DROP TABLE IF EXISTS rbac_permission CASCADE;
DROP TABLE IF EXISTS rbac_role CASCADE;

DELETE FROM django_migrations WHERE app = 'rbac';

\q

# Puis recréer
python manage.py makemigrations rbac
python manage.py migrate rbac
```

## 📝 **Résumé des Commandes Essentielles**

```bash
# 1. Diagnostic
python manage.py showmigrations rbac
python fix_rbac_uuid_complete.py

# 2. Sauvegarde
python manage.py dumpdata rbac --output=rbac_backup.json

# 3. Correction (choisir une option)
python fix_rbac_uuid_complete.py auto          # Automatique
python fix_rbac_uuid_complete.py reset         # Reset complet
python fix_rbac_uuid_complete.py manual        # Migration manuelle

# 4. Validation
python manage.py check
python manage.py migrate

# 5. Démarrage
python manage.py runserver
```

**⚠️ IMPORTANT**: Toujours faire une sauvegarde avant toute migration critique!
