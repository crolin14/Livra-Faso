from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta

class SubscriptionPlan(models.Model):
    """Plans d'abonnement disponibles"""
    PLAN_TYPES = [
        ('basic', 'Basic'),
        ('premium', 'Premium'),
        ('pro', 'Pro'),
    ]
    
    name = models.CharField(max_length=100, verbose_name="Nom du plan")
    plan_type = models.CharField(max_length=20, choices=PLAN_TYPES, verbose_name="Type de plan")
    price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name="Prix (FCFA)"
    )
    duration = models.IntegerField(
        default=30,
        validators=[MinValueValidator(1)],
        help_text="Durée en jours (ex: 30, 90, 365)"
    )
    features = models.TextField(
        help_text="Liste des avantages séparés par des virgules",
        verbose_name="Fonctionnalités"
    )
    
    # Fonctionnalités spécifiques
    max_missions_per_month = models.PositiveIntegerField(
        default=10,
        verbose_name="Missions max/mois"
    )
    priority_support = models.BooleanField(
        default=False,
        verbose_name="Support prioritaire"
    )
    advanced_analytics = models.BooleanField(
        default=False,
        verbose_name="Analytics avancées"
    )
    multi_user_management = models.BooleanField(
        default=False,
        verbose_name="Gestion multi-utilisateurs"
    )
    
    is_active = models.BooleanField(default=True, verbose_name="Actif")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Plan d'Abonnement"
        verbose_name_plural = "Plans d'Abonnement"
    
    def __str__(self):
        return f"{self.name} - {self.price} FCFA"

class UserSubscription(models.Model):
    """Abonnement d'un utilisateur"""
    STATUS_CHOICES = [
        ('active', 'Actif'),
        ('expired', 'Expiré'),
        ('canceled', 'Annulé'),
        ('pending', 'En attente'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='subscriptions',
        verbose_name="Utilisateur"
    )
    plan = models.ForeignKey(
        SubscriptionPlan, 
        on_delete=models.CASCADE,
        verbose_name="Plan d'abonnement"
    )
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='pending',
        verbose_name="Statut"
    )
    
    # Dates
    start_date = models.DateTimeField(verbose_name="Date de début")
    end_date = models.DateTimeField(verbose_name="Date de fin")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Paiement
    payment_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'En attente'),
            ('completed', 'Complété'),
            ('failed', 'Échoué'),
            ('refunded', 'Remboursé'),
        ],
        default='pending',
        verbose_name="Statut du paiement"
    )
    amount_paid = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0.00,
        verbose_name="Montant payé"
    )
    payment_method = models.CharField(
        max_length=50, 
        choices=[
            ('mobile_money', 'Mobile Money'),
            ('card', 'Carte bancaire'),
            ('cash', 'Espèces'),
            ('stripe', 'Stripe'),
        ], 
        blank=True,
        verbose_name="Méthode de paiement"
    )
    
    class Meta:
        verbose_name = "Abonnement Utilisateur"
        verbose_name_plural = "Abonnements Utilisateurs"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.plan.name} ({self.status})"
    
    @property
    def is_active(self):
        return self.status == 'active' and timezone.now() <= self.end_date
    
    @property
    def days_remaining(self):
        if self.status == 'active':
            remaining = self.end_date - timezone.now()
            return max(0, remaining.days)
        return 0
    
    def activate(self):
        """Active l'abonnement"""
        self.status = 'active'
        self.start_date = timezone.now()
        self.end_date = self.start_date + timedelta(days=self.plan.duration)
        self.save()
    
    def cancel(self):
        """Annule l'abonnement"""
        self.status = 'canceled'
        self.save()

class Payment(models.Model):
    """Historique des paiements"""
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('completed', 'Complété'),
        ('failed', 'Échoué'),
        ('cancelled', 'Annulé'),
    ]
    
    PAYMENT_METHODS = [
        ('mobile_money', 'Mobile Money'),
        ('card', 'Carte bancaire'),
        ('cash', 'Espèces'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='payments')
    subscription = models.ForeignKey(UserSubscription, on_delete=models.CASCADE, related_name='payments', null=True, blank=True)
    
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    currency = models.CharField(max_length=3, default='XOF')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    
    # Informations de transaction
    transaction_id = models.CharField(max_length=100, blank=True)
    reference = models.CharField(max_length=100, blank=True)
    
    # Mobile Money spécifique
    phone_number = models.CharField(max_length=20, blank=True)
    operator = models.CharField(max_length=20, choices=[
        ('moov', 'Moov'),
        ('orange', 'Orange'),
        ('telecel', 'Telecel'),
    ], blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Paiement"
        verbose_name_plural = "Paiements"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Paiement {self.transaction_id}: {self.amount} {self.currency}"

class PaymentNotification(models.Model):
    """Notifications de paiement"""
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=50, choices=[
        ('payment_received', 'Paiement reçu'),
        ('payment_failed', 'Paiement échoué'),
        ('subscription_expiring', 'Abonnement expirant'),
        ('payment_reminder', 'Rappel de paiement'),
    ])
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Notification de Paiement"
        verbose_name_plural = "Notifications de Paiements"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Notification {self.notification_type}: {self.message[:50]}..."
