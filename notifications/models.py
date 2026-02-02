from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import json

User = get_user_model()

class Notification(models.Model):
    """Modèle pour les notifications système"""
    
    TYPE_CHOICES = [
        ('info', 'Information'),
        ('success', 'Succès'),
        ('warning', 'Avertissement'),
        ('error', 'Erreur'),
        ('mission', 'Mission'),
        ('payment', 'Paiement'),
        ('support', 'Support'),
        ('system', 'Système'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Basse'),
        ('medium', 'Moyenne'),
        ('high', 'Haute'),
        ('urgent', 'Urgente'),
    ]
    
    recipient = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='notifications',
        verbose_name="Destinataire"
    )
    title = models.CharField(max_length=200, verbose_name="Titre")
    message = models.TextField(verbose_name="Message")
    notification_type = models.CharField(
        max_length=20, 
        choices=TYPE_CHOICES, 
        default='info',
        verbose_name="Type"
    )
    priority = models.CharField(
        max_length=10, 
        choices=PRIORITY_CHOICES, 
        default='medium',
        verbose_name="Priorité"
    )
    
    # Métadonnées
    data = models.JSONField(default=dict, blank=True, verbose_name="Données")
    url = models.URLField(blank=True, null=True, verbose_name="Lien")
    
    # Statut
    is_read = models.BooleanField(default=False, verbose_name="Lu")
    is_sent = models.BooleanField(default=False, verbose_name="Envoyé")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Créé le")
    read_at = models.DateTimeField(null=True, blank=True, verbose_name="Lu le")
    expires_at = models.DateTimeField(null=True, blank=True, verbose_name="Expire le")
    
    class Meta:
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', '-created_at']),
            models.Index(fields=['is_read', 'recipient']),
            models.Index(fields=['notification_type']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.recipient.username}"
    
    def mark_as_read(self):
        """Marquer la notification comme lue"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])
    
    def is_expired(self):
        """Vérifier si la notification a expiré"""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False
    
    def to_dict(self):
        """Convertir en dictionnaire pour WebSocket"""
        return {
            'id': self.id,
            'title': self.title,
            'message': self.message,
            'type': self.notification_type,
            'priority': self.priority,
            'url': self.url,
            'data': self.data,
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat(),
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
        }


class NotificationTemplate(models.Model):
    """Templates pour les notifications"""
    
    name = models.CharField(max_length=100, unique=True, verbose_name="Nom")
    title_template = models.CharField(max_length=200, verbose_name="Template titre")
    message_template = models.TextField(verbose_name="Template message")
    notification_type = models.CharField(
        max_length=20, 
        choices=Notification.TYPE_CHOICES, 
        default='info',
        verbose_name="Type"
    )
    priority = models.CharField(
        max_length=10, 
        choices=Notification.PRIORITY_CHOICES, 
        default='medium',
        verbose_name="Priorité"
    )
    
    # Configuration
    is_active = models.BooleanField(default=True, verbose_name="Actif")
    send_email = models.BooleanField(default=False, verbose_name="Envoyer par email")
    send_websocket = models.BooleanField(default=True, verbose_name="Envoyer par WebSocket")
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Créé le")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Modifié le")
    
    class Meta:
        verbose_name = "Template de notification"
        verbose_name_plural = "Templates de notification"
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def render(self, context=None):
        """Rendre le template avec le contexte"""
        if context is None:
            context = {}
        
        title = self.title_template
        message = self.message_template
        
        # Simple template rendering (remplacer {key} par context[key])
        for key, value in context.items():
            placeholder = f"{{{key}}}"
            title = title.replace(placeholder, str(value))
            message = message.replace(placeholder, str(value))
        
        return {
            'title': title,
            'message': message,
            'type': self.notification_type,
            'priority': self.priority,
        }


class NotificationPreference(models.Model):
    """Préférences de notification par utilisateur"""
    
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='notification_preferences',
        verbose_name="Utilisateur"
    )
    
    # Préférences par type
    receive_mission_notifications = models.BooleanField(default=True, verbose_name="Notifications missions")
    receive_payment_notifications = models.BooleanField(default=True, verbose_name="Notifications paiements")
    receive_support_notifications = models.BooleanField(default=True, verbose_name="Notifications support")
    receive_system_notifications = models.BooleanField(default=True, verbose_name="Notifications système")
    
    # Canaux de notification
    email_notifications = models.BooleanField(default=True, verbose_name="Notifications email")
    websocket_notifications = models.BooleanField(default=True, verbose_name="Notifications temps réel")
    
    # Horaires
    quiet_hours_start = models.TimeField(null=True, blank=True, verbose_name="Début heures silencieuses")
    quiet_hours_end = models.TimeField(null=True, blank=True, verbose_name="Fin heures silencieuses")
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Créé le")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Modifié le")
    
    class Meta:
        verbose_name = "Préférence de notification"
        verbose_name_plural = "Préférences de notification"
    
    def __str__(self):
        return f"Préférences - {self.user.username}"
    
    def should_receive_notification(self, notification_type):
        """Vérifier si l'utilisateur doit recevoir ce type de notification"""
        type_mapping = {
            'mission': self.receive_mission_notifications,
            'payment': self.receive_payment_notifications,
            'support': self.receive_support_notifications,
            'system': self.receive_system_notifications,
        }
        return type_mapping.get(notification_type, True)
    
    def is_quiet_hours(self):
        """Vérifier si nous sommes dans les heures silencieuses"""
        if not self.quiet_hours_start or not self.quiet_hours_end:
            return False
        
        now = timezone.now().time()
        return self.quiet_hours_start <= now <= self.quiet_hours_end


class NotificationLog(models.Model):
    """Log des notifications envoyées"""
    
    notification = models.ForeignKey(
        Notification, 
        on_delete=models.CASCADE, 
        related_name='logs',
        verbose_name="Notification"
    )
    channel = models.CharField(max_length=20, verbose_name="Canal")  # websocket, email, etc.
    status = models.CharField(max_length=20, verbose_name="Statut")  # sent, failed, pending
    error_message = models.TextField(blank=True, verbose_name="Message d'erreur")
    
    sent_at = models.DateTimeField(auto_now_add=True, verbose_name="Envoyé le")
    
    class Meta:
        verbose_name = "Log de notification"
        verbose_name_plural = "Logs de notification"
        ordering = ['-sent_at']
    
    def __str__(self):
        return f"{self.notification.title} - {self.channel} - {self.status}"
