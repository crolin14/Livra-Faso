from django.db import models
from django.conf import settings

class Conversation(models.Model):
    """Conversation entre utilisateurs"""
    mission = models.OneToOneField('missions.Mission', on_delete=models.CASCADE, related_name='conversation', null=True, blank=True)
    client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='client_conversations', null=True, blank=True)
    livreur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='livreur_conversations', null=True, blank=True)
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='conversations', blank=True)
    last_message = models.ForeignKey('ChatMessage', on_delete=models.SET_NULL, null=True, blank=True, related_name='last_message_conversations')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Conversation"
        verbose_name_plural = "Conversations"
        ordering = ['-updated_at']
    
    def __str__(self):
        participant_names = ", ".join([user.username for user in self.participants.all()])
        return f"Conversation: {participant_names}"
    
    @property
    def last_message(self):
        return self.messages.order_by('-timestamp').first()
    
    def has_unread_messages(self, user):
        """Vérifie si l'utilisateur a des messages non lus dans cette conversation"""
        return self.messages.filter(is_read=False).exclude(sender=user).exists()
    
    def unread_count(self, user):
        """Compte les messages non lus pour un utilisateur"""
        return self.messages.filter(is_read=False).exclude(sender=user).count()

class ChatMessage(models.Model):
    """Message dans une conversation"""
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_messages')
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    message_type = models.CharField(max_length=20, choices=[
        ('text', 'Texte'),
        ('image', 'Image'),
        ('file', 'Fichier'),
        ('location', 'Localisation'),
    ], default='text')
    attachment = models.FileField(upload_to='message_attachments/', blank=True, null=True)
    
    class Meta:
        verbose_name = "Message"
        verbose_name_plural = "Messages"
        ordering = ['timestamp']
    
    def __str__(self):
        return f"Message de {self.sender.username}: {self.message[:50]}..."

class MessageNotification(models.Model):
    """Notifications pour les messages non lus"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='message_notifications')
    message = models.ForeignKey(ChatMessage, on_delete=models.CASCADE, related_name='notifications')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Notification de Message"
        verbose_name_plural = "Notifications de Messages"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Notification pour {self.user.username}: {self.message.message[:30]}..."
