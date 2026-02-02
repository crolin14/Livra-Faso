from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.shortcuts import redirect
from django.contrib import messages
from .models import PermissionCache, UserRole
import logging

logger = logging.getLogger(__name__)

class PermissionManager:
    """Gestionnaire centralisé des permissions"""
    
    # Définition des permissions par module
    PERMISSIONS = {
        'users': [
            ('users.view', 'Voir les utilisateurs'),
            ('users.create', 'Créer des utilisateurs'),
            ('users.edit', 'Modifier les utilisateurs'),
            ('users.delete', 'Supprimer les utilisateurs'),
            ('users.activate', 'Activer/désactiver les utilisateurs'),
            ('users.export', 'Exporter les données utilisateurs'),
        ],
        'roles': [
            ('roles.view', 'Voir les rôles'),
            ('roles.create', 'Créer des rôles'),
            ('roles.edit', 'Modifier les rôles'),
            ('roles.delete', 'Supprimer les rôles'),
            ('roles.assign', 'Assigner des rôles'),
        ],
        'orders': [
            ('orders.view', 'Voir les commandes'),
            ('orders.create', 'Créer des commandes'),
            ('orders.edit', 'Modifier les commandes'),
            ('orders.delete', 'Supprimer les commandes'),
            ('orders.assign', 'Assigner des livreurs'),
            ('orders.track', 'Suivre les commandes'),
            ('orders.export', 'Exporter les commandes'),
        ],
        'payments': [
            ('payments.view', 'Voir les paiements'),
            ('payments.refund', 'Effectuer des remboursements'),
            ('payments.export', 'Exporter les paiements'),
        ],
        'cms': [
            ('cms.view', 'Voir le contenu'),
            ('cms.create', 'Créer du contenu'),
            ('cms.edit', 'Modifier le contenu'),
            ('cms.delete', 'Supprimer le contenu'),
            ('cms.publish', 'Publier le contenu'),
            ('cms.media', 'Gérer les médias'),
        ],
        'analytics': [
            ('analytics.view', 'Voir les statistiques'),
            ('analytics.export', 'Exporter les rapports'),
            ('analytics.custom', 'Créer des rapports personnalisés'),
        ],
        'promotions': [
            ('promotions.view', 'Voir les promotions'),
            ('promotions.create', 'Créer des promotions'),
            ('promotions.edit', 'Modifier les promotions'),
            ('promotions.delete', 'Supprimer les promotions'),
        ],
        'support': [
            ('support.view', 'Voir les tickets'),
            ('support.create', 'Créer des tickets'),
            ('support.assign', 'Assigner des tickets'),
            ('support.resolve', 'Résoudre des tickets'),
        ],
        'settings': [
            ('settings.view', 'Voir la configuration'),
            ('settings.edit', 'Modifier la configuration'),
            ('settings.pricing', 'Gérer la tarification'),
            ('settings.zones', 'Gérer les zones'),
        ],
        'audit': [
            ('audit.view', 'Voir les logs d\'audit'),
            ('audit.export', 'Exporter les logs'),
        ],
        'notifications': [
            ('notifications.view', 'Voir les notifications'),
            ('notifications.send', 'Envoyer des notifications'),
            ('notifications.manage', 'Gérer les préférences'),
        ],
    }

    @classmethod
    def get_all_permissions(cls):
        """Retourne toutes les permissions définies"""
        all_perms = []
        for module, perms in cls.PERMISSIONS.items():
            for codename, name in perms:
                all_perms.append({
                    'codename': codename,
                    'name': name,
                    'module': module
                })
        return all_perms

    @classmethod
    def sync_permissions(cls):
        """Synchronise les permissions en base avec celles définies dans le code"""
        from .models import Permission
        
        for module, perms in cls.PERMISSIONS.items():
            for codename, name in perms:
                Permission.objects.get_or_create(
                    codename=codename,
                    defaults={
                        'name': name,
                        'module': module,
                        'description': f'Permission {name} pour le module {module}'
                    }
                )

def has_permission(user, permission_codename):
    """Vérifie si un utilisateur a une permission spécifique"""
    if not user.is_authenticated:
        return False
    
    if user.is_superuser:
        return True
    
    # Utiliser le cache de permissions
    try:
        cache, created = PermissionCache.objects.get_or_create(user=user)
        if created:
            cache.refresh_cache()
        return cache.has_permission(permission_codename)
    except Exception as e:
        logger.error(f"Erreur lors de la vérification des permissions pour {user.username}: {e}")
        return False

def require_permission(permission_codename, redirect_url=None):
    """
    Décorateur pour vérifier si un utilisateur a une permission spécifique
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                if redirect_url:
                    messages.error(request, "Authentification requise")
                    return redirect('users:login')
                raise PermissionDenied("Authentification requise")
            
            # Vérifier le cache des permissions
            cache, created = PermissionCache.objects.get_or_create(user=request.user)
            if created or not cache.permissions:
                cache.refresh_cache()
            
            if not cache.has_permission(permission_codename):
                if redirect_url:
                    messages.error(request, f"Permission '{permission_codename}' requise")
                    return redirect(redirect_url)
                raise PermissionDenied(f"Permission '{permission_codename}' requise")
            
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

def require_role(role_name, redirect_url=None):
    """
    Décorateur pour vérifier si un utilisateur a un rôle spécifique
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                if redirect_url:
                    messages.error(request, "Authentification requise")
                    return redirect('users:login')
                raise PermissionDenied("Authentification requise")
            
            from .models import UserRole
            user_roles = UserRole.objects.filter(
                user=request.user,
                role__name=role_name,
                is_active=True
            )
            
            if not user_roles.exists() or any(ur.is_expired() for ur in user_roles):
                if redirect_url:
                    messages.error(request, f"Rôle '{role_name}' requis")
                    return redirect(redirect_url)
                raise PermissionDenied(f"Rôle '{role_name}' requis")
            
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

def has_module_access(user, module_name):
    """Vérifie si un utilisateur a accès à un module"""
    if not user.is_authenticated:
        return False
    
    if user.is_superuser:
        return True

def has_role(role_name, redirect_url=None):
    """
    Décorateur pour vérifier si un utilisateur a un rôle spécifique
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                if redirect_url:
                    messages.error(request, "Authentification requise")
                    return redirect('users:login')
                raise PermissionDenied("Authentification requise")
            
            user_roles = UserRole.objects.filter(
                user=request.user,
                role__name=role_name,
                is_active=True
            )
            
            if not user_roles.exists() or any(ur.is_expired() for ur in user_roles):
                if redirect_url:
                    messages.error(request, f"Rôle '{role_name}' requis")
                    return redirect(redirect_url)
                raise PermissionDenied(f"Rôle '{role_name}' requis")
            
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

def has_any_role(*role_names, redirect_url=None):
    """
    Décorateur pour vérifier si un utilisateur a au moins un des rôles spécifiés
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                if redirect_url:
                    messages.error(request, "Authentification requise")
                    return redirect('users:login')
                raise PermissionDenied("Authentification requise")
            
            user_roles = UserRole.objects.filter(
                user=request.user,
                role__name__in=role_names,
                is_active=True
            )
            
            if not user_roles.exists() or all(ur.is_expired() for ur in user_roles):
                if redirect_url:
                    messages.error(request, f"Un des rôles suivants requis: {', '.join(role_names)}")
                    return redirect(redirect_url)
                raise PermissionDenied(f"Un des rôles suivants requis: {', '.join(role_names)}")
            
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

def has_module_access(module_name, redirect_url=None):
    """
    Décorateur pour vérifier l'accès à un module
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                if redirect_url:
                    messages.error(request, "Authentification requise")
                    return redirect('users:login')
                raise PermissionDenied("Authentification requise")
            
            cache, created = PermissionCache.objects.get_or_create(user=request.user)
            if created or not cache.permissions:
                cache.refresh_cache()
            
            if not cache.has_module_access(module_name):
                if redirect_url:
                    messages.error(request, f"Accès au module '{module_name}' requis")
                    return redirect(redirect_url)
                raise PermissionDenied(f"Accès au module '{module_name}' requis")
            
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

def admin_required(view_func):
    """
    Décorateur spécifique pour les vues admin
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "Authentification requise")
            return redirect('users:login')
        
        if not user_has_any_role(request.user, 'super_admin', 'admin'):
            messages.error(request, "Accès administrateur requis")
            return redirect('public:home')
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def manager_required(view_func):
    """
    Décorateur pour les gestionnaires et plus
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "Authentification requise")
            return redirect('users:login')
        
        if not user_has_any_role(request.user, 'super_admin', 'admin', 'manager', 'support_manager'):
            messages.error(request, "Accès gestionnaire requis")
            return redirect('public:home')
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view

# Fonctions utilitaires

def user_has_permission(user, permission_codename):
    """
    Vérifie si un utilisateur a une permission (fonction utilitaire)
    """
    if not user.is_authenticated:
        return False
    
    cache, created = PermissionCache.objects.get_or_create(user=user)
    if created or not cache.permissions:
        cache.refresh_cache()
    
    return cache.has_permission(permission_codename)

def user_has_role(user, role_name):
    """
    Vérifie si un utilisateur a un rôle (fonction utilitaire)
    """
    if not user.is_authenticated:
        return False
    
    user_roles = UserRole.objects.filter(
        user=user,
        role__name=role_name,
        is_active=True
    )
    
    return user_roles.exists() and not any(ur.is_expired() for ur in user_roles)

def user_has_any_role(user, *role_names):
    """
    Vérifie si un utilisateur a au moins un des rôles spécifiés
    """
    if not user.is_authenticated:
        return False
    
    user_roles = UserRole.objects.filter(
        user=user,
        role__name__in=role_names,
        is_active=True
    )
    
    return user_roles.exists() and not all(ur.is_expired() for ur in user_roles)

def get_user_permissions(user):
    """
    Récupère toutes les permissions d'un utilisateur
    """
    if not user.is_authenticated:
        return []
    
    cache, created = PermissionCache.objects.get_or_create(user=user)
    if created or not cache.permissions:
        cache.refresh_cache()
    
    return cache.permissions

def get_user_roles(user):
    """
    Récupère tous les rôles actifs d'un utilisateur
    """
    if not user.is_authenticated:
        return []
    
    return UserRole.objects.filter(
        user=user,
        is_active=True
    ).select_related('role')

def get_user_highest_role(user):
    """
    Récupère le rôle le plus élevé de l'utilisateur
    """
    if not user.is_authenticated:
        return None
    
    user_roles = get_user_roles(user)
    if not user_roles:
        return None
    
    return min(user_roles, key=lambda ur: ur.role.level).role

def assign_role_to_user(user, role_name, assigned_by=None, expires_at=None):
    """
    Assigne un rôle à un utilisateur
    """
    try:
        role = Role.objects.get(name=role_name)
        user_role, created = UserRole.objects.get_or_create(
            user=user,
            role=role,
            defaults={
                'assigned_by': assigned_by,
                'expires_at': expires_at,
                'is_active': True
            }
        )
        
        if not created:
            user_role.is_active = True
            user_role.expires_at = expires_at
            user_role.save()
        
        # Actualiser le cache des permissions
        cache, _ = PermissionCache.objects.get_or_create(user=user)
        cache.refresh_cache()
        
        return user_role
    except Role.DoesNotExist:
        raise ValueError(f"Rôle '{role_name}' non trouvé")

def remove_role_from_user(user, role_name):
    """
    Retire un rôle d'un utilisateur
    """
    try:
        user_role = UserRole.objects.get(
            user=user,
            role__name=role_name,
            is_active=True
        )
        user_role.is_active = False
        user_role.save()
        
        # Actualiser le cache des permissions
        cache, _ = PermissionCache.objects.get_or_create(user=user)
        cache.refresh_cache()
        
        return True
    except UserRole.DoesNotExist:
        return False

def refresh_user_permissions(user):
    """
    Force l'actualisation du cache des permissions d'un utilisateur
    """
    cache, _ = PermissionCache.objects.get_or_create(user=user)
    return cache.refresh_cache()

def api_require_permission(permission_codename):
    """Décorateur pour les vues API avec vérification de permissions"""
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return JsonResponse({'error': 'Authentication required'}, status=401)
            
            if not user_has_permission(request.user, permission_codename):
                return JsonResponse({
                    'error': 'Permission denied',
                    'required_permission': permission_codename
                }, status=403)
            
            return view_func(request, *args, **kwargs)
        
        # Ajout des méthodes au modèle User via monkey patching
        return _wrapped_view
    return decorator

from django.contrib.auth import get_user_model

User = get_user_model()

def user_has_permission_method(self, permission_codename):
    return user_has_permission(self, permission_codename)

def user_has_role_method(self, role_name):
    return user_has_role(self, role_name)

def user_has_any_role_method(self, *role_names):
    return user_has_any_role(self, *role_names)

def get_user_permissions_method(self):
    return get_user_permissions(self)

def get_user_roles_method(self):
    return get_user_roles(self)

def get_user_highest_role_method(self):
    return get_user_highest_role(self)

def assign_role_method(self, role_name, assigned_by=None, expires_at=None):
    return assign_role_to_user(self, role_name, assigned_by, expires_at)

def remove_role_method(self, role_name):
    return remove_role_from_user(self, role_name)

def refresh_permissions_method(self):
    return refresh_user_permissions(self)

def is_admin_method(self):
    return self.has_any_role('super_admin', 'admin')

def is_manager_method(self):
    return self.has_any_role('super_admin', 'admin', 'manager', 'support_manager')

# Ajouter les méthodes au modèle User
User.add_to_class('has_permission', user_has_permission_method)
User.add_to_class('has_role', user_has_role_method)
User.add_to_class('has_any_role', user_has_any_role_method)
User.add_to_class('get_permissions', get_user_permissions_method)
User.add_to_class('get_roles', get_user_roles_method)
User.add_to_class('get_highest_role', get_user_highest_role_method)
User.add_to_class('assign_role', assign_role_method)
User.add_to_class('remove_role', remove_role_method)
User.add_to_class('refresh_permissions', refresh_permissions_method)
User.add_to_class('is_admin', is_admin_method)
User.add_to_class('is_manager', is_manager_method)
def get_user_modules(user):
    """Retourne les modules accessibles par un utilisateur"""
    permissions = get_user_permissions(user)
    modules = set()
    for perm in permissions:
        modules.add(perm['module'])
    return list(modules)
