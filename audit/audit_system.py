"""
Système d'audit complet pour LivraFaso - Logs sécurisés avec IP tracking
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.conf import settings
import json
import logging
from datetime import datetime, timedelta
from ipaddress import ip_address, ip_network

User = get_user_model()

class AuditLog(models.Model):
    """Modèle pour les logs d'audit complets"""
    
    ACTION_TYPES = [
        ('login', 'Connexion'),
        ('logout', 'Déconnexion'),
        ('create', 'Création'),
        ('update', 'Modification'),
        ('delete', 'Suppression'),
        ('view', 'Consultation'),
        ('download', 'Téléchargement'),
        ('upload', 'Upload'),
        ('permission_denied', 'Accès refusé'),
        ('suspicious_activity', 'Activité suspecte'),
        ('password_change', 'Changement mot de passe'),
        ('role_change', 'Changement de rôle'),
        ('mission_create', 'Création mission'),
        ('mission_accept', 'Acceptation mission'),
        ('mission_complete', 'Mission terminée'),
        ('payment', 'Paiement'),
        ('chat_message', 'Message chat'),
    ]
    
    SEVERITY_LEVELS = [
        ('info', 'Information'),
        ('warning', 'Avertissement'),
        ('error', 'Erreur'),
        ('critical', 'Critique'),
    ]
    
    # Informations de base
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    action = models.CharField(max_length=50, choices=ACTION_TYPES, db_index=True)
    severity = models.CharField(max_length=20, choices=SEVERITY_LEVELS, default='info', db_index=True)
    
    # Utilisateur et session
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    username = models.CharField(max_length=150, blank=True)
    user_type = models.CharField(max_length=50, blank=True)
    session_key = models.CharField(max_length=40, blank=True)
    
    # Informations réseau
    ip_address = models.GenericIPAddressField(db_index=True)
    user_agent = models.TextField(blank=True)
    referer = models.URLField(blank=True, null=True)
    
    # Informations de la requête
    path = models.CharField(max_length=500, db_index=True)
    method = models.CharField(max_length=10)
    status_code = models.IntegerField(null=True, blank=True)
    
    # Détails de l'action
    object_type = models.CharField(max_length=100, blank=True)  # Mission, User, etc.
    object_id = models.CharField(max_length=100, blank=True)
    object_repr = models.CharField(max_length=200, blank=True)
    
    # Données supplémentaires
    details = models.JSONField(default=dict, blank=True)
    changes = models.JSONField(default=dict, blank=True)  # Changements avant/après
    
    # Géolocalisation
    country = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    
    # Flags de sécurité
    is_suspicious = models.BooleanField(default=False, db_index=True)
    risk_score = models.IntegerField(default=0)  # 0-100
    
    class Meta:
        db_table = 'audit_logs'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['timestamp', 'action']),
            models.Index(fields=['ip_address', 'timestamp']),
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['is_suspicious', 'timestamp']),
        ]
    
    def __str__(self):
        return f"{self.timestamp} - {self.username} - {self.action} - {self.ip_address}"

class SecurityIncident(models.Model):
    """Modèle pour les incidents de sécurité"""
    
    INCIDENT_TYPES = [
        ('brute_force', 'Tentative de force brute'),
        ('suspicious_login', 'Connexion suspecte'),
        ('multiple_failures', 'Échecs multiples'),
        ('unusual_activity', 'Activité inhabituelle'),
        ('permission_escalation', 'Tentative d\'escalade'),
        ('data_breach', 'Tentative d\'accès non autorisé'),
        ('malicious_request', 'Requête malveillante'),
    ]
    
    STATUS_CHOICES = [
        ('open', 'Ouvert'),
        ('investigating', 'En cours d\'investigation'),
        ('resolved', 'Résolu'),
        ('false_positive', 'Faux positif'),
    ]
    
    # Informations de base
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    incident_type = models.CharField(max_length=50, choices=INCIDENT_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    
    # Détails de l'incident
    title = models.CharField(max_length=200)
    description = models.TextField()
    severity = models.CharField(max_length=20, choices=AuditLog.SEVERITY_LEVELS, default='warning')
    
    # Informations sur l'attaquant
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    affected_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Logs associés
    related_logs = models.ManyToManyField(AuditLog, blank=True)
    
    # Actions prises
    actions_taken = models.TextField(blank=True)
    resolved_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, 
        related_name='resolved_incidents'
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'security_incidents'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.incident_type} - {self.ip_address} - {self.status}"

class IPWhitelist(models.Model):
    """Liste blanche des IPs autorisées"""
    
    ip_address = models.GenericIPAddressField(unique=True)
    description = models.CharField(max_length=200)
    created_at = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'ip_whitelist'
    
    def __str__(self):
        return f"{self.ip_address} - {self.description}"

class IPBlacklist(models.Model):
    """Liste noire des IPs bloquées"""
    
    ip_address = models.GenericIPAddressField(unique=True)
    reason = models.CharField(max_length=200)
    blocked_at = models.DateTimeField(default=timezone.now)
    blocked_by = models.ForeignKey(User, on_delete=models.CASCADE)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'ip_blacklist'
    
    def __str__(self):
        return f"{self.ip_address} - {self.reason}"

# Services pour l'audit
class AuditService:
    """Service pour gérer les logs d'audit"""
    
    @staticmethod
    def log_action(request, action, user=None, object_type=None, object_id=None, 
                   object_repr=None, details=None, changes=None, severity='info'):
        """Enregistrer une action dans les logs d'audit"""
        
        if user is None:
            user = request.user if request.user.is_authenticated else None
        
        # Extraire les informations de la requête
        ip_address = AuditService.get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        referer = request.META.get('HTTP_REFERER', '')
        
        # Détecter les activités suspectes
        is_suspicious, risk_score = AuditService.analyze_risk(
            ip_address, user, action, details
        )
        
        # Créer le log d'audit
        audit_log = AuditLog.objects.create(
            action=action,
            severity=severity,
            user=user,
            username=user.username if user else 'anonymous',
            user_type=getattr(user, 'user_type', '') if user else '',
            session_key=request.session.session_key or '',
            ip_address=ip_address,
            user_agent=user_agent,
            referer=referer,
            path=request.path,
            method=request.method,
            object_type=object_type or '',
            object_id=str(object_id) if object_id else '',
            object_repr=object_repr or '',
            details=details or {},
            changes=changes or {},
            is_suspicious=is_suspicious,
            risk_score=risk_score
        )
        
        # Si activité suspecte, créer un incident
        if is_suspicious and risk_score > 70:
            AuditService.create_security_incident(audit_log)
        
        return audit_log
    
    @staticmethod
    def get_client_ip(request):
        """Récupérer l'IP réelle du client"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '')
        return ip
    
    @staticmethod
    def analyze_risk(ip_address, user, action, details):
        """Analyser le niveau de risque d'une action"""
        risk_score = 0
        is_suspicious = False
        
        # Vérifier la liste noire
        if IPBlacklist.objects.filter(ip_address=ip_address, is_active=True).exists():
            risk_score += 100
            is_suspicious = True
        
        # Vérifier les tentatives multiples
        recent_failures = AuditLog.objects.filter(
            ip_address=ip_address,
            action='permission_denied',
            timestamp__gte=timezone.now() - timedelta(minutes=15)
        ).count()
        
        if recent_failures > 5:
            risk_score += 50
            is_suspicious = True
        
        # Vérifier les connexions depuis des pays inhabituels
        # (à implémenter avec une API de géolocalisation)
        
        # Actions sensibles
        sensitive_actions = ['delete', 'role_change', 'permission_denied']
        if action in sensitive_actions:
            risk_score += 20
        
        # Heures inhabituelles (nuit)
        current_hour = timezone.now().hour
        if current_hour < 6 or current_hour > 22:
            risk_score += 10
        
        return is_suspicious, min(risk_score, 100)
    
    @staticmethod
    def create_security_incident(audit_log):
        """Créer un incident de sécurité"""
        incident_type = 'suspicious_login'
        if audit_log.action == 'permission_denied':
            incident_type = 'permission_escalation'
        
        incident = SecurityIncident.objects.create(
            incident_type=incident_type,
            title=f"Activité suspecte détectée - {audit_log.ip_address}",
            description=f"Action: {audit_log.action}, Utilisateur: {audit_log.username}, IP: {audit_log.ip_address}",
            severity=audit_log.severity,
            ip_address=audit_log.ip_address,
            user_agent=audit_log.user_agent,
            affected_user=audit_log.user
        )
        
        incident.related_logs.add(audit_log)
        return incident
    
    @staticmethod
    def get_user_activity(user, days=30):
        """Récupérer l'activité d'un utilisateur"""
        since = timezone.now() - timedelta(days=days)
        return AuditLog.objects.filter(
            user=user,
            timestamp__gte=since
        ).order_by('-timestamp')
    
    @staticmethod
    def get_ip_activity(ip_address, days=7):
        """Récupérer l'activité d'une IP"""
        since = timezone.now() - timedelta(days=days)
        return AuditLog.objects.filter(
            ip_address=ip_address,
            timestamp__gte=since
        ).order_by('-timestamp')
    
    @staticmethod
    def get_security_dashboard_data():
        """Données pour le dashboard de sécurité"""
        now = timezone.now()
        today = now.date()
        week_ago = now - timedelta(days=7)
        
        return {
            'total_logs_today': AuditLog.objects.filter(timestamp__date=today).count(),
            'suspicious_activities_today': AuditLog.objects.filter(
                timestamp__date=today, is_suspicious=True
            ).count(),
            'open_incidents': SecurityIncident.objects.filter(status='open').count(),
            'unique_ips_today': AuditLog.objects.filter(
                timestamp__date=today
            ).values('ip_address').distinct().count(),
            'failed_logins_today': AuditLog.objects.filter(
                timestamp__date=today, action='permission_denied'
            ).count(),
            'top_ips_week': AuditLog.objects.filter(
                timestamp__gte=week_ago
            ).values('ip_address').annotate(
                count=models.Count('id')
            ).order_by('-count')[:10],
            'recent_incidents': SecurityIncident.objects.filter(
                status='open'
            ).order_by('-created_at')[:5]
        }

# Middleware pour l'audit automatique
class AuditMiddleware:
    """Middleware pour l'audit automatique des requêtes"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Traitement avant la vue
        start_time = timezone.now()
        
        response = self.get_response(request)
        
        # Traitement après la vue
        if self.should_log_request(request):
            AuditService.log_action(
                request=request,
                action='view',
                details={
                    'response_time': (timezone.now() - start_time).total_seconds(),
                    'content_length': len(response.content) if hasattr(response, 'content') else 0
                },
                severity='info'
            )
        
        return response
    
    def should_log_request(self, request):
        """Déterminer si la requête doit être loggée"""
        # Ne pas logger les fichiers statiques
        if request.path.startswith('/static/') or request.path.startswith('/media/'):
            return False
        
        # Logger les APIs et pages importantes
        important_paths = ['/api/', '/dashboard/', '/admin/', '/missions/']
        return any(request.path.startswith(path) for path in important_paths)
