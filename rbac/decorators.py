"""
RBAC Decorators - LivraFaso Dashboard Security System
Décorateurs pour contrôle d'accès basé sur les rôles avec support complet des dashboards
"""

from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.shortcuts import redirect
from django.contrib import messages
from .permissions import (
    require_permission, require_role, admin_required, manager_required,
    user_has_permission, user_has_role, user_has_any_role
)

# Décorateurs spécialisés pour les dashboards LivraFaso
__all__ = [
    'require_permission',
    'require_role', 
    'admin_required',
    'manager_required',
    'require_any_role',
    'require_admin',
    'require_manager',
    'api_require_permission',
    'api_require_role',
    'client_required',
    'livreur_required', 
    'entreprise_required',
    'admin_dashboard_required',
    'manager_dashboard_required'
]

def require_any_role(*role_names, redirect_url=None):
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
            
            if not user_has_any_role(request.user, *role_names):
                if redirect_url:
                    messages.error(request, f"Un des rôles suivants requis: {', '.join(role_names)}")
                    return redirect(redirect_url)
                raise PermissionDenied(f"Un des rôles suivants requis: {', '.join(role_names)}")
            
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

def require_admin(redirect_url=None):
    """Décorateur spécifique pour les administrateurs"""
    return require_any_role('admin', 'super_admin', redirect_url=redirect_url)

def require_manager(redirect_url=None):
    """Décorateur pour les gestionnaires et plus"""
    return require_any_role('admin', 'super_admin', 'manager', 'support_manager', redirect_url=redirect_url)

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
        return _wrapped_view
    return decorator

def api_require_role(role_name):
    """Décorateur pour les vues API avec vérification de rôle"""
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return JsonResponse({'error': 'Authentication required'}, status=401)
            
            if not user_has_role(request.user, role_name):
                return JsonResponse({
                    'error': 'Role required',
                    'required_role': role_name
                }, status=403)
            
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

# Décorateurs spécialisés pour les dashboards LivraFaso

@login_required
def client_required(view_func):
    """Décorateur pour les vues client uniquement"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.user_type != 'client':
            messages.error(request, "Accès réservé aux clients")
            return redirect('public:home')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

@login_required
def livreur_required(view_func):
    """Décorateur pour les vues livreur uniquement"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.user_type != 'livreur':
            messages.error(request, "Accès réservé aux livreurs")
            return redirect('public:home')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

@login_required
def entreprise_required(view_func):
    """Décorateur pour les vues entreprise uniquement"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.user_type != 'entreprise':
            messages.error(request, "Accès réservé aux entreprises")
            return redirect('public:home')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

@login_required
def admin_dashboard_required(view_func):
    """Décorateur pour les vues admin dashboard"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_staff and not user_has_any_role(request.user, 'admin', 'super_admin'):
            messages.error(request, "Accès réservé aux administrateurs")
            return redirect('public:home')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

@login_required
def manager_dashboard_required(view_func):
    """Décorateur pour les vues manager dashboard"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not user_has_any_role(request.user, 'admin', 'super_admin', 'manager', 'support_manager'):
            messages.error(request, "Accès réservé aux gestionnaires")
            return redirect('public:home')
        return view_func(request, *args, **kwargs)
    return _wrapped_view
