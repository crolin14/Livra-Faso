"""
Middleware de sécurité personnalisé - LivraFaso
Phase 2: Middleware avancé pour la sécurité
"""

import logging
import time
from django.http import HttpResponseForbidden
from django.core.cache import cache
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth.signals import user_login_failed
from django.dispatch import receiver

logger = logging.getLogger('livrafaso.security')

class SecurityLoggingMiddleware(MiddlewareMixin):
    """
    Middleware pour logger les événements de sécurité
    """
    
    def process_request(self, request):
        # Logger les tentatives d'accès suspects
        suspicious_patterns = [
            '/admin/login/',
            '/.env',
            '/wp-admin/',
            '/phpmyadmin/',
            'eval(',
            '<script>',
            'union select',
            '../',
        ]
        
        path = request.get_full_path().lower()
        for pattern in suspicious_patterns:
            if pattern in path:
                logger.warning(
                    f"Tentative d'accès suspect détectée: {request.META.get('REMOTE_ADDR')} "
                    f"-> {path} | User-Agent: {request.META.get('HTTP_USER_AGENT', 'Unknown')}"
                )
                break
        
        return None

class RateLimitMiddleware(MiddlewareMixin):
    """
    Middleware de limitation du taux de requêtes
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.rate_limit = getattr(settings, 'RATE_LIMIT_REQUESTS', 100)  # 100 requêtes
        self.rate_window = getattr(settings, 'RATE_LIMIT_WINDOW', 3600)  # par heure
        super().__init__(get_response)
    
    def process_request(self, request):
        if not getattr(settings, 'RATELIMIT_ENABLE', True):
            return None
        
        # Obtenir l'IP du client
        ip = self.get_client_ip(request)
        
        # Clé de cache pour cette IP
        cache_key = f"rate_limit:{ip}"
        
        # Obtenir le nombre de requêtes actuelles
        current_requests = cache.get(cache_key, 0)
        
        if current_requests >= self.rate_limit:
            logger.warning(f"Rate limit dépassé pour IP: {ip}")
            return HttpResponseForbidden("Trop de requêtes. Veuillez réessayer plus tard.")
        
        # Incrémenter le compteur
        cache.set(cache_key, current_requests + 1, self.rate_window)
        
        return None
    
    def get_client_ip(self, request):
        """Obtenir l'IP réelle du client"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

class LoginAttemptMiddleware(MiddlewareMixin):
    """
    Middleware pour surveiller les tentatives de connexion
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.max_attempts = getattr(settings, 'MAX_LOGIN_ATTEMPTS', 5)
        self.lockout_time = getattr(settings, 'LOGIN_LOCKOUT_TIME', 1800)  # 30 minutes
        super().__init__(get_response)
    
    def process_request(self, request):
        if request.path == '/login/' and request.method == 'POST':
            ip = self.get_client_ip(request)
            cache_key = f"login_attempts:{ip}"
            
            attempts = cache.get(cache_key, 0)
            if attempts >= self.max_attempts:
                logger.warning(f"IP bloquée pour tentatives de connexion: {ip}")
                return HttpResponseForbidden(
                    "Trop de tentatives de connexion. Compte temporairement bloqué."
                )
        
        return None
    
    def get_client_ip(self, request):
        """Obtenir l'IP réelle du client"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

@receiver(user_login_failed)
def login_failed_handler(sender, credentials, request, **kwargs):
    """
    Handler pour les échecs de connexion
    """
    ip = request.META.get('REMOTE_ADDR')
    username = credentials.get('username', 'Unknown')
    
    # Logger l'échec
    logger.warning(f"Échec de connexion: {username} depuis {ip}")
    
    # Incrémenter le compteur d'échecs pour cette IP
    cache_key = f"login_attempts:{ip}"
    attempts = cache.get(cache_key, 0)
    cache.set(cache_key, attempts + 1, 1800)  # 30 minutes

class ContentSecurityPolicyMiddleware(MiddlewareMixin):
    """
    Middleware pour ajouter les headers Content Security Policy
    """
    
    def process_response(self, request, response):
        # CSP pour prévenir les attaques XSS
        csp_policy = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://unpkg.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self';"
        )
        
        response['Content-Security-Policy'] = csp_policy
        
        # Headers de sécurité additionnels
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        
        return response

class RequestSizeMiddleware(MiddlewareMixin):
    """
    Middleware pour limiter la taille des requêtes
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.max_size = getattr(settings, 'MAX_REQUEST_SIZE', 10 * 1024 * 1024)  # 10MB
        super().__init__(get_response)
    
    def process_request(self, request):
        content_length = request.META.get('CONTENT_LENGTH')
        
        if content_length:
            try:
                content_length = int(content_length)
                if content_length > self.max_size:
                    logger.warning(f"Requête trop volumineuse rejetée: {content_length} bytes")
                    return HttpResponseForbidden("Requête trop volumineuse.")
            except ValueError:
                pass
        
        return None
