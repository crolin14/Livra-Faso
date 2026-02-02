#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🚀 SCRIPT COMPLET DE CONFIGURATION ADMIN - LivraFaso

Ce script génère et configure automatiquement:
✅ Template dashboard_admin.html
✅ Rôles RBAC (super_admin, admin, etc.)
✅ Superutilisateur avec tous les droits
✅ Permissions et accès complets

Usage: python create_admin_user.py
"""

import os
import sys
import django
from datetime import datetime, timedelta

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Livraison_Faso.settings')
django.setup()

from django.contrib.auth import get_user_model
from rbac.models import Role, UserRole, Permission, RolePermission
from django.db import transaction

User = get_user_model()

# Contenu du template dashboard_admin.html
TEMPLATE_CONTENT = '''{% extends 'base_ultra_modern.html' %}
{% load static %}

{% block title %}Dashboard Admin - LivraFaso{% endblock %}

{% block content %}
<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
    <div class="flex items-center justify-between mb-8">
        <div>
            <h1 class="text-3xl font-bold text-gray-900">Dashboard Administrateur</h1>
            <p class="text-gray-600 mt-2">Vue d'ensemble du système</p>
        </div>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div class="bg-white rounded-xl shadow-lg p-6">
            <div class="flex items-center justify-between mb-4">
                <div class="p-3 bg-blue-100 rounded-xl">
                    <i data-lucide="users" class="w-6 h-6 text-blue-600"></i>
                </div>
            </div>
            <h3 class="text-3xl font-bold text-gray-900 mb-1">{{ total_users|default:0 }}</h3>
            <p class="text-sm text-gray-600">Utilisateurs Total</p>
        </div>
        <div class="bg-white rounded-xl shadow-lg p-6">
            <div class="flex items-center justify-between mb-4">
                <div class="p-3 bg-purple-100 rounded-xl">
                    <i data-lucide="package" class="w-6 h-6 text-purple-600"></i>
                </div>
            </div>
            <h3 class="text-3xl font-bold text-gray-900 mb-1">{{ total_missions|default:0 }}</h3>
            <p class="text-sm text-gray-600">Missions Total</p>
        </div>
        <div class="bg-white rounded-xl shadow-lg p-6">
            <div class="flex items-center justify-between mb-4">
                <div class="p-3 bg-orange-100 rounded-xl">
                    <i data-lucide="truck" class="w-6 h-6 text-orange-600"></i>
                </div>
            </div>
            <h3 class="text-3xl font-bold text-gray-900 mb-1">{{ active_missions|default:0 }}</h3>
            <p class="text-sm text-gray-600">Missions Actives</p>
        </div>
        <div class="bg-white rounded-xl shadow-lg p-6">
            <div class="flex items-center justify-between mb-4">
                <div class="p-3 bg-green-100 rounded-xl">
                    <i data-lucide="dollar-sign" class="w-6 h-6 text-green-600"></i>
                </div>
            </div>
            <h3 class="text-3xl font-bold text-gray-900 mb-1">{{ total_revenue|default:0|floatformat:0 }}</h3>
            <p class="text-sm text-gray-600">FCFA Revenus</p>
        </div>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <a href="{% url 'admin_dashboard:users' %}" class="flex items-center justify-between p-4 bg-white rounded-xl shadow hover:shadow-lg transition">
            <div class="flex items-center">
                <i data-lucide="users" class="w-5 h-5 text-blue-600 mr-3"></i>
                <span class="font-medium text-gray-900">Gérer Utilisateurs</span>
            </div>
            <i data-lucide="chevron-right" class="w-5 h-5 text-gray-400"></i>
        </a>
        <a href="{% url 'admin_dashboard:missions' %}" class="flex items-center justify-between p-4 bg-white rounded-xl shadow hover:shadow-lg transition">
            <div class="flex items-center">
                <i data-lucide="package" class="w-5 h-5 text-purple-600 mr-3"></i>
                <span class="font-medium text-gray-900">Gérer Missions</span>
            </div>
            <i data-lucide="chevron-right" class="w-5 h-5 text-gray-400"></i>
        </a>
        <a href="{% url 'admin_dashboard:security' %}" class="flex items-center justify-between p-4 bg-white rounded-xl shadow hover:shadow-lg transition">
            <div class="flex items-center">
                <i data-lucide="shield" class="w-5 h-5 text-red-600 mr-3"></i>
                <span class="font-medium text-gray-900">Logs Sécurité</span>
            </div>
            <i data-lucide="chevron-right" class="w-5 h-5 text-gray-400"></i>
        </a>
    </div>
</div>

<script>
document.addEventListener('DOMContentLoaded', function() {
    lucide.createIcons();
});
</script>
{% endblock %}
'''

def main():
    print("\n🔧 Création du template dashboard_admin.html...\n")
    
    # Créer le dossier si nécessaire
    template_dir = os.path.join('templates', 'admin')
    os.makedirs(template_dir, exist_ok=True)
    
    # Créer le fichier
    template_path = os.path.join(template_dir, 'dashboard_admin.html')
    
    try:
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(TEMPLATE_CONTENT)
        
        print(f"✅ Template créé avec succès: {template_path}")
        print("\n📋 Prochaines étapes:")
        print("  1. Configurer les rôles RBAC (exécutez setup_rbac_roles.py)")
        print("  2. Redémarrer le serveur Django")
        print("  3. Accéder à: http://127.0.0.1:8000/admin-dashboard/dashboard/")
        print("\n✅ Script terminé!\n")
        return 0
        
    except Exception as e:
        print(f"❌ Erreur lors de la création du template: {e}")
        return 1

if __name__ == '__main__':
    import sys
    sys.exit(main())
django.setup()

from django.contrib.auth import get_user_model
from django.db import transaction
from rbac.models import Role, UserRole

User = get_user_model()

def create_admin_user():
    """Crée un utilisateur administrateur complet"""
    
    print("🔧 Création d'un utilisateur administrateur LivraFaso")
    print("=" * 50)
    
    # Demander les informations
    username = input("Nom d'utilisateur: ").strip()
    if not username:
        username = "admin"
        print(f"Utilisation du nom par défaut: {username}")
    
    email = input("Email: ").strip()
    if not email:
        email = "admin@livrafaso.com"
        print(f"Utilisation de l'email par défaut: {email}")
    
    first_name = input("Prénom: ").strip() or "Admin"
    last_name = input("Nom: ").strip() or "LivraFaso"
    
    password = input("Mot de passe (requis): ").strip()
    if not password:
        print("❌ Erreur: Un mot de passe est requis pour des raisons de sécurité")
        print("   Veuillez fournir un mot de passe fort (minimum 8 caractères)")
        return False
    
    try:
        with transaction.atomic():
            # Vérifier si l'utilisateur existe déjà
            if User.objects.filter(username=username).exists():
                print(f"❌ L'utilisateur '{username}' existe déjà")
                user = User.objects.get(username=username)
                update = input("Voulez-vous le mettre à jour? (y/N): ").strip().lower()
                if update != 'y':
                    return
            else:
                # Créer l'utilisateur
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                    user_type='admin'
                )
                print(f"✅ Utilisateur '{username}' créé")
            
            # Définir comme superutilisateur
            user.is_staff = True
            user.is_superuser = True
            user.is_active = True
            user.save()
            
            # Créer/assigner le rôle admin
            admin_role, created = Role.objects.get_or_create(
                name='admin',
                defaults={
                    'display_name': 'Administrateur',
                    'description': 'Administrateur système avec tous les privilèges',
                    'level': 1,
                    'is_active': True
                }
            )
            
            if created:
                print("✅ Rôle 'admin' créé")
            
            # Assigner le rôle à l'utilisateur
            user_role, created = UserRole.objects.get_or_create(
                user=user,
                role=admin_role,
                defaults={
                    'is_active': True,
                    'assigned_by': user
                }
            )
            
            if created:
                print(f"✅ Rôle 'admin' assigné à {username}")
            else:
                user_role.is_active = True
                user_role.save()
                print(f"✅ Rôle 'admin' réactivé pour {username}")
            
            # Actualiser le cache des permissions
            try:
                from rbac.models import PermissionCache
                cache, _ = PermissionCache.objects.get_or_create(user=user)
                cache.refresh_cache()
                print("✅ Cache des permissions actualisé")
            except Exception as e:
                print(f"⚠️  Erreur cache permissions: {e}")
            
            print("\n" + "=" * 50)
            print("🎉 UTILISATEUR ADMINISTRATEUR CRÉÉ AVEC SUCCÈS!")
            print("=" * 50)
            print(f"👤 Nom d'utilisateur: {username}")
            print(f"📧 Email: {email}")
            print(f"🔑 Mot de passe: {password}")
            print(f"🛡️  Rôle: Administrateur")
            print(f"🌐 Dashboard: http://127.0.0.1:8000/admin-dashboard/")
            print(f"⚙️  Django Admin: http://127.0.0.1:8000/admin/")
            print("=" * 50)
            
    except Exception as e:
        print(f"❌ Erreur lors de la création: {e}")
        return False
    
    return True

def create_default_roles():
    """Crée les rôles par défaut du système"""
    
    default_roles = [
        {
            'name': 'super_admin',
            'display_name': 'Super Administrateur',
            'description': 'Accès complet au système',
            'level': 0
        },
        {
            'name': 'admin',
            'display_name': 'Administrateur',
            'description': 'Administrateur avec privilèges étendus',
            'level': 1
        },
        {
            'name': 'manager',
            'display_name': 'Gestionnaire',
            'description': 'Gestionnaire des opérations',
            'level': 2
        },
        {
            'name': 'support_agent',
            'display_name': 'Agent Support',
            'description': 'Agent du service client',
            'level': 3
        },
        {
            'name': 'enterprise_user',
            'display_name': 'Utilisateur Entreprise',
            'description': 'Compte entreprise',
            'level': 4
        },
        {
            'name': 'delivery_person',
            'display_name': 'Livreur',
            'description': 'Livreur/Transporteur',
            'level': 5
        },
        {
            'name': 'regular_user',
            'display_name': 'Utilisateur',
            'description': 'Utilisateur standard',
            'level': 6
        }
    ]
    
    print("\n🔧 Création des rôles par défaut...")
    
    for role_data in default_roles:
        role, created = Role.objects.get_or_create(
            name=role_data['name'],
            defaults={
                'display_name': role_data['display_name'],
                'description': role_data['description'],
                'level': role_data['level'],
                'is_active': True
            }
        )
        
        if created:
            print(f"✅ Rôle '{role_data['display_name']}' créé")
        else:
            print(f"ℹ️  Rôle '{role_data['display_name']}' existe déjà")

def main():
    """Fonction principale"""
    print_header("🚀 CONFIGURATION RBAC - LivraFaso")
    
    try:
        with transaction.atomic():
            # 1. Créer les rôles
            roles = create_roles()
            
            # 2. Créer les permissions
            create_permissions(roles)
            
            # 3. Assigner le rôle super_admin à l'utilisateur admin
            super_admin = roles.get('super_admin')
            if super_admin:
                user = assign_role_to_user('admin', super_admin)
                
                if user:
                    # 4. Vérifier les permissions
                    verify_user_permissions(user)
                    
                    # 5. Afficher le résumé
                    print_header("✅ CONFIGURATION TERMINÉE")
                    print("🎉 Configuration RBAC réussie!\n")
                    print("📝 Prochaines étapes:")
                    print("  1. Déconnectez-vous du site")
                    print("  2. Reconnectez-vous avec le compte 'admin'")
                    print("  3. Accédez à: http://127.0.0.1:8000/admin-dashboard/dashboard/")
                    print("\n" + "="*60 + "\n")
                else:
                    print("\n❌ Erreur: Utilisateur admin non trouvé")
                    print("Créez d'abord un utilisateur admin avec:")
                    print("  python manage.py createsuperuser")
                    return 1
            
        return 0
        
    except Exception as e:
        print(f"\n\n❌ Erreur lors de la configuration: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
