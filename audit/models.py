from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.utils import timezone
import json
import uuid

User = get_user_model()


class AuditLog(models.Model):
    """
    Modèle principal pour l'audit trail
    Enregistre toutes les actions importantes du système
    """
    ACTION_TYPES = [
        ('create', 'Création'),
        ('update', 'Modification'),
        ('delete', 'Suppression'),
        ('login', 'Connexion'),
        ('logout', 'Déconnexion'),
        ('view', 'Consultation'),
        ('export', 'Export'),
        ('import', 'Import'),
        ('admin_action', 'Action Admin'),
        ('system_event', 'Événement Système'),
        ('security_event', 'Événement Sécurité'),
        ('api_call', 'Appel API'),
        ('error', 'Erreur'),
        ('warning', 'Avertissement'),
    ]
    
    SEVERITY_LEVELS = [
        ('low', 'Faible'),
        ('medium', 'Moyen'),
        ('high', 'Élevé'),
        ('critical', 'Critique'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    
    # Utilisateur qui a effectué l'action
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    user_ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    # Type et détails de l'action
    action_type = models.CharField(max_length=20, choices=ACTION_TYPES, db_index=True)
    action_description = models.CharField(max_length=255, default='Action système')
    severity = models.CharField(max_length=10, choices=SEVERITY_LEVELS, default='low')
    
    # Objet concerné (générique)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.CharField(max_length=255, null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Données supplémentaires
    old_values = models.JSONField(null=True, blank=True)
    new_values = models.JSONField(null=True, blank=True)
    additional_data = models.JSONField(null=True, blank=True)
    
    # Métadonnées
    session_key = models.CharField(max_length=40, blank=True)
    request_path = models.CharField(max_length=500, blank=True)
    request_method = models.CharField(max_length=10, blank=True)
    
    # Flags
    is_sensitive = models.BooleanField(default=False)
    requires_review = models.BooleanField(default=False)
    is_reviewed = models.BooleanField(default=False)
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_audits')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['timestamp', 'action_type']),
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['severity', 'timestamp']),
        ]
    
    def __str__(self):
        return f"{self.timestamp} - {self.get_action_type_display()} by {self.user or 'System'}"
    
    def get_changes_summary(self):
        """Résumé des changements pour affichage"""
        if not self.old_values or not self.new_values:
            return None
        
        changes = []
        for field, new_value in self.new_values.items():
            old_value = self.old_values.get(field)
            if old_value != new_value:
                changes.append({
                    'field': field,
                    'old_value': old_value,
                    'new_value': new_value
                })
        return changes


class SecurityEvent(models.Model):
    """
    Événements de sécurité spécifiques
    """
    EVENT_TYPES = [
        ('failed_login', 'Tentative de connexion échouée'),
        ('suspicious_activity', 'Activité suspecte'),
        ('permission_denied', 'Accès refusé'),
        ('rate_limit_exceeded', 'Limite de taux dépassée'),
        ('invalid_token', 'Token invalide'),
        ('sql_injection_attempt', 'Tentative d\'injection SQL'),
        ('xss_attempt', 'Tentative XSS'),
        ('csrf_failure', 'Échec CSRF'),
        ('brute_force', 'Attaque par force brute'),
        ('account_locked', 'Compte verrouillé'),
        ('password_changed', 'Mot de passe modifié'),
        ('admin_privilege_escalation', 'Escalade de privilèges admin'),
    ]
    
    RISK_LEVELS = [
        ('low', 'Faible'),
        ('medium', 'Moyen'),
        ('high', 'Élevé'),
        ('critical', 'Critique'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES, db_index=True)
    risk_level = models.CharField(max_length=10, choices=RISK_LEVELS, default='low')
    
    # Source de l'événement
    source_ip = models.GenericIPAddressField(db_index=True)
    user_agent = models.TextField(blank=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Détails
    description = models.TextField()
    request_path = models.CharField(max_length=500, blank=True)
    request_method = models.CharField(max_length=10, blank=True)
    request_data = models.JSONField(null=True, blank=True)
    
    # Réponse
    is_blocked = models.BooleanField(default=False)
    action_taken = models.CharField(max_length=255, blank=True)
    
    # Suivi
    is_investigated = models.BooleanField(default=False)
    investigated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='investigated_events')
    investigated_at = models.DateTimeField(null=True, blank=True)
    investigation_notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['timestamp', 'risk_level']),
            models.Index(fields=['source_ip', 'timestamp']),
            models.Index(fields=['event_type', 'timestamp']),
        ]
    
    def __str__(self):
        return f"{self.timestamp} - {self.get_event_type_display()} from {self.source_ip}"


class SystemMetrics(models.Model):
    """
    Métriques système pour monitoring
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    
    # Métriques de performance
    cpu_usage = models.FloatField(null=True, blank=True)
    memory_usage = models.FloatField(null=True, blank=True)
    disk_usage = models.FloatField(null=True, blank=True)
    
    # Métriques applicatives
    active_users = models.IntegerField(default=0)
    active_sessions = models.IntegerField(default=0)
    api_requests_per_minute = models.IntegerField(default=0)
    database_connections = models.IntegerField(default=0)
    
    # Métriques métier
    missions_created_today = models.IntegerField(default=0)
    missions_completed_today = models.IntegerField(default=0)
    revenue_today = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    new_users_today = models.IntegerField(default=0)
    
    # Métriques d'erreur
    error_rate = models.FloatField(default=0)
    failed_requests = models.IntegerField(default=0)
    
    # Statut système
    system_status = models.CharField(max_length=20, choices=[
        ('healthy', 'Sain'),
        ('warning', 'Avertissement'),
        ('critical', 'Critique'),
        ('down', 'Hors service'),
    ], default='healthy')
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['timestamp']),
            models.Index(fields=['system_status', 'timestamp']),
        ]
    
    def __str__(self):
        return f"Métriques {self.timestamp} - {self.system_status}"


class AdminAction(models.Model):
    """
    Actions spécifiques des administrateurs
    """
    ACTION_CATEGORIES = [
        ('user_management', 'Gestion utilisateurs'),
        ('mission_management', 'Gestion missions'),
        ('system_config', 'Configuration système'),
        ('security', 'Sécurité'),
        ('content_management', 'Gestion contenu'),
        ('financial', 'Financier'),
        ('reporting', 'Rapports'),
        ('maintenance', 'Maintenance'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    
    admin_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='admin_actions')
    category = models.CharField(max_length=30, choices=ACTION_CATEGORIES, db_index=True)
    action = models.CharField(max_length=255)
    description = models.TextField()
    
    # Cible de l'action
    target_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='targeted_by_admin')
    target_object_type = models.CharField(max_length=50, blank=True)
    target_object_id = models.CharField(max_length=255, blank=True)
    
    # Détails
    before_state = models.JSONField(null=True, blank=True)
    after_state = models.JSONField(null=True, blank=True)
    reason = models.TextField(blank=True)
    
    # Métadonnées
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    
    # Flags
    is_critical = models.BooleanField(default=False)
    requires_approval = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=False)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_actions')
    approved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['admin_user', 'timestamp']),
            models.Index(fields=['category', 'timestamp']),
            models.Index(fields=['is_critical', 'timestamp']),
        ]
    
    def __str__(self):
        return f"{self.timestamp} - {self.admin_user.username}: {self.action}"


class DataExport(models.Model):
    """
    Suivi des exports de données
    """
    EXPORT_TYPES = [
        ('users', 'Utilisateurs'),
        ('missions', 'Missions'),
        ('financial', 'Données financières'),
        ('analytics', 'Analytics'),
        ('audit_logs', 'Logs d\'audit'),
        ('system_data', 'Données système'),
    ]
    
    FORMATS = [
        ('csv', 'CSV'),
        ('xlsx', 'Excel'),
        ('json', 'JSON'),
        ('pdf', 'PDF'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    export_type = models.CharField(max_length=20, choices=EXPORT_TYPES, db_index=True)
    format = models.CharField(max_length=10, choices=FORMATS)
    
    # Filtres appliqués
    filters_applied = models.JSONField(null=True, blank=True)
    date_range_start = models.DateTimeField(null=True, blank=True)
    date_range_end = models.DateTimeField(null=True, blank=True)
    
    # Résultats
    records_count = models.IntegerField(default=0)
    file_size = models.BigIntegerField(null=True, blank=True)  # en bytes
    file_path = models.CharField(max_length=500, blank=True)
    
    # Statut
    is_completed = models.BooleanField(default=False)
    error_message = models.TextField(blank=True)
    
    # Sécurité
    contains_sensitive_data = models.BooleanField(default=False)
    access_reason = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['export_type', 'timestamp']),
        ]
    
    def __str__(self):
        return f"Export {self.get_export_type_display()} par {self.user.username} - {self.timestamp}"
