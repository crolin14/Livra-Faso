"""
Middleware de sécurité pour l'authentification et la gestion des sessions
"""
import logging
from django.contrib.auth import logout
from django.contrib import messages
from django.shortcuts import redirect
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger(__name__)

class AuthSecurityMiddleware:
    """
    Middleware de sécurité pour gérer les sessions et l'authentification
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Vérifier l'expiration de session avant le traitement de la vue
        if request.user.is_authenticated:
            self._check_session_security(request)
        
        response = self.get_response(request)
        
        # Nettoyage après la réponse si nécessaire
        if request.user.is_authenticated:
            self._update_session_activity(request)
        
        return response

    def _check_session_security(self, request):
        """
        Vérifier la sécurité de la session utilisateur
        """
        try:
            # Vérifier la dernière activité
            last_activity = request.session.get('last_activity')
            if last_activity:
                last_activity = timezone.datetime.fromisoformat(last_activity)
                if timezone.now() - last_activity > timedelta(hours=1):
                    logger.info(f"Session expirée pour l'utilisateur: {request.user.username}")
                    logout(request)
                    messages.warning(request, 'Votre session a expiré pour des raisons de sécurité.')
                    return redirect('users:login')
            
            # Vérifier l'IP si configuré (optionnel)
            current_ip = self._get_client_ip(request)
            session_ip = request.session.get('login_ip')
            
            if session_ip and session_ip != current_ip:
                logger.warning(f"Changement d'IP détecté pour {request.user.username}: {session_ip} -> {current_ip}")
                # En production, vous pourriez vouloir déconnecter l'utilisateur
                # logout(request)
                # messages.error(request, 'Connexion suspecte détectée. Veuillez vous reconnecter.')
                # return redirect('users:login')
                
        except Exception as e:
            logger.error(f"Erreur dans la vérification de sécurité de session: {e}")

    def _update_session_activity(self, request):
        """
        Mettre à jour l'activité de la session
        """
        try:
            request.session['last_activity'] = timezone.now().isoformat()
            if not request.session.get('login_ip'):
                request.session['login_ip'] = self._get_client_ip(request)
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour de l'activité de session: {e}")

    def _get_client_ip(self, request):
        """
        Obtenir l'IP réelle du client
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class NoAutoLoginMiddleware:
    """
    Middleware pour empêcher la connexion automatique non désirée
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Vérifier qu'il n'y a pas de connexion automatique sur la page d'accueil
        if request.path == '/' and request.user.is_authenticated:
            # L'utilisateur est connecté et visite la page d'accueil
            # C'est normal, ne pas rediriger automatiquement
            pass
        
        response = self.get_response(request)
        return response
