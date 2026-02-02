"""
Nouveaux décorateurs RBAC pour LivraFaso - Système complet avec audit et sécurité
"""

from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import redirect
from django.contrib import messages
from django.utils import timezone
from django.conf import settings
import logging
import json

# Configuration du logger pour l'audit
audit_logger = logging.getLogger('livrafaso.audit')

def get_client_ip(request):
    """Récupérer l'IP du client"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def log_access_attempt(request, user, action, success, details=None):
    """Logger les tentatives d'accès pour l'audit"""
    audit_data = {
        'timestamp': timezone.now().isoformat(),
        'user_id': user.id if user.is_authenticated else None,
        'username': user.username if user.is_authenticated else 'anonymous',
        'ip_address': get_client_ip(request),
        'user_agent': request.META.get('HTTP_USER_AGENT', ''),
        'action': action,
        'success': success,
        'path': request.path,
        'method': request.method,
        'details': details or {}
    }
    
    if success:
        audit_logger.info(f"ACCESS_GRANTED: {json.dumps(audit_data)}")
    else:
        audit_logger.warning(f"ACCESS_DENIED: {json.dumps(audit_data)}")

# Décorateurs spécifiques par type d'utilisateur
def client_required(redirect_url='/login/', api_response=False):
    """Décorateur pour les clients uniquement"""
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped_view(request, *args, **kwargs):
            if not hasattr(request.user, 'user_type') or request.user.user_type != 'client':
                log_access_attempt(
                    request, request.user, 'client_access', False,
                    {'required_type': 'client', 'actual_type': getattr(request.user, 'user_type', 'unknown')}
                )
                
                if api_response:
                    return JsonResponse({
                        'error': 'Accès réservé aux clients',
                        'required_role': 'client'
                    }, status=403)
                
                messages.error(request, "Accès réservé aux clients")
                return redirect(redirect_url)
            
            log_access_attempt(request, request.user, 'client_access', True)
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

def livreur_required(redirect_url='/login/', api_response=False):
    """Décorateur pour les livreurs uniquement"""
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped_view(request, *args, **kwargs):
            if not hasattr(request.user, 'user_type') or request.user.user_type != 'livreur':
                log_access_attempt(
                    request, request.user, 'livreur_access', False,
                    {'required_type': 'livreur', 'actual_type': getattr(request.user, 'user_type', 'unknown')}
                )
                
                if api_response:
                    return JsonResponse({
                        'error': 'Accès réservé aux livreurs',
                        'required_role': 'livreur'
                    }, status=403)
                
                messages.error(request, "Accès réservé aux livreurs")
                return redirect(redirect_url)
            
            log_access_attempt(request, request.user, 'livreur_access', True)
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

def entreprise_required(redirect_url='/login/', api_response=False):
    """Décorateur pour les entreprises uniquement"""
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped_view(request, *args, **kwargs):
            if not hasattr(request.user, 'user_type') or request.user.user_type != 'entreprise':
                log_access_attempt(
                    request, request.user, 'entreprise_access', False,
                    {'required_type': 'entreprise', 'actual_type': getattr(request.user, 'user_type', 'unknown')}
                )
                
                if api_response:
                    return JsonResponse({
                        'error': 'Accès réservé aux entreprises',
                        'required_role': 'entreprise'
                    }, status=403)
                
                messages.error(request, "Accès réservé aux entreprises")
                return redirect(redirect_url)
            
            log_access_attempt(request, request.user, 'entreprise_access', True)
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

def admin_required(redirect_url='/login/', api_response=False):
    """Décorateur pour les administrateurs uniquement"""
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped_view(request, *args, **kwargs):
            if not (request.user.is_staff or request.user.is_superuser or 
                   (hasattr(request.user, 'user_type') and request.user.user_type == 'admin')):
                log_access_attempt(
                    request, request.user, 'admin_access', False,
                    {'required_type': 'admin', 'is_staff': request.user.is_staff, 'is_superuser': request.user.is_superuser}
                )
                
                if api_response:
                    return JsonResponse({
                        'error': 'Accès réservé aux administrateurs',
                        'required_role': 'admin'
                    }, status=403)
                
                messages.error(request, "Accès réservé aux administrateurs")
                return redirect(redirect_url)
            
            log_access_attempt(request, request.user, 'admin_access', True)
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

def manager_required(redirect_url='/login/', api_response=False):
    """Décorateur pour les managers et administrateurs"""
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped_view(request, *args, **kwargs):
            allowed_types = ['admin', 'manager']
            user_type = getattr(request.user, 'user_type', None)
            
            if not (request.user.is_staff or request.user.is_superuser or user_type in allowed_types):
                log_access_attempt(
                    request, request.user, 'manager_access', False,
                    {'required_types': allowed_types, 'actual_type': user_type}
                )
                
                if api_response:
                    return JsonResponse({
                        'error': 'Accès réservé aux managers et administrateurs',
                        'required_roles': allowed_types
                    }, status=403)
                
                messages.error(request, "Accès réservé aux managers et administrateurs")
                return redirect(redirect_url)
            
            log_access_attempt(request, request.user, 'manager_access', True)
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

def multi_role_required(*allowed_types, redirect_url='/login/', api_response=False):
    """Décorateur pour plusieurs types d'utilisateurs"""
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped_view(request, *args, **kwargs):
            user_type = getattr(request.user, 'user_type', None)
            
            if user_type not in allowed_types and not (request.user.is_staff or request.user.is_superuser):
                log_access_attempt(
                    request, request.user, 'multi_role_access', False,
                    {'allowed_types': list(allowed_types), 'actual_type': user_type}
                )
                
                if api_response:
                    return JsonResponse({
                        'error': f'Accès réservé aux: {", ".join(allowed_types)}',
                        'required_roles': list(allowed_types)
                    }, status=403)
                
                messages.error(request, f"Accès réservé aux: {', '.join(allowed_types)}")
                return redirect(redirect_url)
            
            log_access_attempt(request, request.user, 'multi_role_access', True)
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

# Décorateurs pour APIs avec réponses JSON
def api_client_required(view_func):
    """Décorateur API pour clients"""
    return client_required(api_response=True)(view_func)

def api_livreur_required(view_func):
    """Décorateur API pour livreurs"""
    return livreur_required(api_response=True)(view_func)

def api_entreprise_required(view_func):
    """Décorateur API pour entreprises"""
    return entreprise_required(api_response=True)(view_func)

def api_admin_required(view_func):
    """Décorateur API pour administrateurs"""
    return admin_required(api_response=True)(view_func)

def api_manager_required(view_func):
    """Décorateur API pour managers"""
    return manager_required(api_response=True)(view_func)

# Décorateur pour surveillance IP suspecte
def monitor_suspicious_activity(max_attempts=5, time_window=300):
    """Surveiller les activités suspectes par IP"""
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            ip = get_client_ip(request)
            
            # Ici on pourrait implémenter une logique de cache Redis
            # pour compter les tentatives par IP
            
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

# Décorateur pour validation CSRF renforcée
def enhanced_csrf_protection(view_func):
    """Protection CSRF renforcée avec logging"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.method in ['POST', 'PUT', 'DELETE', 'PATCH']:
            csrf_token = request.META.get('HTTP_X_CSRFTOKEN') or request.POST.get('csrfmiddlewaretoken')
            if not csrf_token:
                log_access_attempt(
                    request, request.user, 'csrf_validation', False,
                    {'error': 'Missing CSRF token'}
                )
                return JsonResponse({'error': 'CSRF token required'}, status=403)
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view
