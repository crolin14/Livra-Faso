from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
import uuid
import string
import random

User = get_user_model()


class PromotionCampaign(models.Model):
    """
    Campagne promotionnelle principale
    """
    CAMPAIGN_TYPES = [
        ('percentage', 'Pourcentage'),
        ('fixed_amount', 'Montant fixe'),
        ('free_delivery', 'Livraison gratuite'),
        ('buy_x_get_y', 'Achetez X obtenez Y'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Brouillon'),
        ('active', 'Active'),
        ('paused', 'En pause'),
        ('expired', 'Expirée'),
        ('cancelled', 'Annulée'),
    ]
    
    TARGET_AUDIENCES = [
        ('all', 'Tous les utilisateurs'),
        ('new_users', 'Nouveaux utilisateurs'),
        ('existing_users', 'Utilisateurs existants'),
        ('enterprise', 'Entreprises'),
        ('individual', 'Particuliers'),
        ('vip', 'Utilisateurs VIP'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, verbose_name="Nom de la campagne")
    description = models.TextField(blank=True, verbose_name="Description")
    
    # Type et valeur de promotion
    campaign_type = models.CharField(max_length=20, choices=CAMPAIGN_TYPES, verbose_name="Type de promotion")
    discount_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="Pourcentage de réduction"
    )
    discount_amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0)],
        verbose_name="Montant de réduction (FCFA)"
    )
    
    # Conditions d'application
    minimum_order_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Montant minimum de commande"
    )
    maximum_discount_amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0)],
        verbose_name="Montant maximum de réduction"
    )
    
    # Période de validité
    start_date = models.DateTimeField(verbose_name="Date de début")
    end_date = models.DateTimeField(verbose_name="Date de fin")
    
    # Audience cible
    target_audience = models.CharField(
        max_length=20, choices=TARGET_AUDIENCES, default='all',
        verbose_name="Audience cible"
    )
    specific_users = models.ManyToManyField(
        User, blank=True,
        verbose_name="Utilisateurs spécifiques"
    )
    
    # Limites d'utilisation
    usage_limit_per_user = models.PositiveIntegerField(
        null=True, blank=True,
        verbose_name="Limite d'utilisation par utilisateur"
    )
    total_usage_limit = models.PositiveIntegerField(
        null=True, blank=True,
        verbose_name="Limite d'utilisation totale"
    )
    current_usage_count = models.PositiveIntegerField(
        default=0,
        verbose_name="Nombre d'utilisations actuelles"
    )
    
    # Statut et métadonnées
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_campaigns')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Statistiques
    total_savings_generated = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name="Économies totales générées"
    )
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'start_date', 'end_date']),
            models.Index(fields=['target_audience']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"
    
    def is_active(self):
        """Vérifie si la campagne est active"""
        now = timezone.now()
        return (
            self.status == 'active' and
            self.start_date <= now <= self.end_date and
            (self.total_usage_limit is None or self.current_usage_count < self.total_usage_limit)
        )
    
    def can_be_used_by_user(self, user):
        """Vérifie si un utilisateur peut utiliser cette campagne"""
        if not self.is_active():
            return False
        
        # Vérifier l'audience cible
        if self.target_audience == 'new_users' and user.missions.exists():
            return False
        elif self.target_audience == 'existing_users' and not user.missions.exists():
            return False
        elif self.target_audience == 'enterprise' and user.user_type != 'enterprise':
            return False
        elif self.target_audience == 'individual' and user.user_type == 'enterprise':
            return False
        
        # Vérifier les utilisateurs spécifiques
        if self.specific_users.exists() and user not in self.specific_users.all():
            return False
        
        # Vérifier la limite par utilisateur
        if self.usage_limit_per_user:
            user_usage = self.usages.filter(user=user).count()
            if user_usage >= self.usage_limit_per_user:
                return False
        
        return True
    
    def calculate_discount(self, order_amount):
        """Calcule le montant de réduction pour un montant de commande"""
        if order_amount < self.minimum_order_amount:
            return Decimal('0')
        
        if self.campaign_type == 'percentage':
            discount = order_amount * (self.discount_percentage / 100)
        elif self.campaign_type == 'fixed_amount':
            discount = self.discount_amount
        elif self.campaign_type == 'free_delivery':
            # Retourner le coût de livraison standard
            discount = Decimal('1000')  # Coût standard de livraison
        else:
            discount = Decimal('0')
        
        # Appliquer la limite maximale si définie
        if self.maximum_discount_amount and discount > self.maximum_discount_amount:
            discount = self.maximum_discount_amount
        
        return discount


class PromoCode(models.Model):
    """
    Code promo spécifique
    """
    GENERATION_TYPES = [
        ('manual', 'Manuel'),
        ('auto', 'Automatique'),
        ('bulk', 'En lot'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True, verbose_name="Code promo")
    campaign = models.ForeignKey(
        PromotionCampaign, on_delete=models.CASCADE,
        related_name='promo_codes', verbose_name="Campagne"
    )
    
    # Génération
    generation_type = models.CharField(
        max_length=10, choices=GENERATION_TYPES, default='manual'
    )
    generated_at = models.DateTimeField(default=timezone.now)
    generated_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='generated_codes'
    )
    
    # Utilisation
    is_single_use = models.BooleanField(default=True, verbose_name="Usage unique")
    usage_count = models.PositiveIntegerField(default=0)
    max_uses = models.PositiveIntegerField(
        null=True, blank=True,
        verbose_name="Nombre maximum d'utilisations"
    )
    
    # Statut
    is_active = models.BooleanField(default=True)
    deactivated_at = models.DateTimeField(null=True, blank=True)
    deactivated_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='deactivated_codes'
    )
    
    class Meta:
        ordering = ['-generated_at']
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['campaign', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.code} - {self.campaign.name}"
    
    def can_be_used(self):
        """Vérifie si le code peut être utilisé"""
        if not self.is_active:
            return False
        
        if self.max_uses and self.usage_count >= self.max_uses:
            return False
        
        if self.is_single_use and self.usage_count > 0:
            return False
        
        return self.campaign.is_active()
    
    @classmethod
    def generate_code(cls, length=8, prefix=''):
        """Génère un code promo aléatoirement"""
        characters = string.ascii_uppercase + string.digits
        code = prefix + ''.join(random.choices(characters, k=length))
        
        # Vérifier l'unicité
        while cls.objects.filter(code=code).exists():
            code = prefix + ''.join(random.choices(characters, k=length))
        
        return code


class PromotionUsage(models.Model):
    """
    Suivi de l'utilisation des promotions
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Promotion utilisée
    campaign = models.ForeignKey(
        PromotionCampaign, on_delete=models.CASCADE,
        related_name='usages'
    )
    promo_code = models.ForeignKey(
        PromoCode, on_delete=models.CASCADE, null=True, blank=True,
        related_name='usages'
    )
    
    # Utilisateur et commande
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    mission = models.ForeignKey(
        'missions.Mission', on_delete=models.CASCADE, null=True, blank=True
    )
    
    # Détails de l'utilisation
    original_amount = models.DecimalField(
        max_digits=10, decimal_places=2,
        verbose_name="Montant original"
    )
    discount_amount = models.DecimalField(
        max_digits=10, decimal_places=2,
        verbose_name="Montant de réduction"
    )
    final_amount = models.DecimalField(
        max_digits=10, decimal_places=2,
        verbose_name="Montant final"
    )
    
    # Métadonnées
    used_at = models.DateTimeField(default=timezone.now)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    # Statut
    is_valid = models.BooleanField(default=True)
    invalidated_at = models.DateTimeField(null=True, blank=True)
    invalidation_reason = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-used_at']
        indexes = [
            models.Index(fields=['user', 'used_at']),
            models.Index(fields=['campaign', 'used_at']),
            models.Index(fields=['promo_code', 'used_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.campaign.name} - {self.discount_amount} FCFA"


class PromotionRule(models.Model):
    """
    Règles avancées pour les promotions
    """
    RULE_TYPES = [
        ('user_attribute', 'Attribut utilisateur'),
        ('order_attribute', 'Attribut commande'),
        ('time_based', 'Basé sur le temps'),
        ('location_based', 'Basé sur la localisation'),
        ('usage_based', 'Basé sur l\'utilisation'),
    ]
    
    OPERATORS = [
        ('equals', 'Égal à'),
        ('not_equals', 'Différent de'),
        ('greater_than', 'Supérieur à'),
        ('less_than', 'Inférieur à'),
        ('contains', 'Contient'),
        ('in_list', 'Dans la liste'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey(
        PromotionCampaign, on_delete=models.CASCADE,
        related_name='rules'
    )
    
    rule_type = models.CharField(max_length=20, choices=RULE_TYPES)
    field_name = models.CharField(max_length=100, verbose_name="Nom du champ")
    operator = models.CharField(max_length=20, choices=OPERATORS)
    value = models.TextField(verbose_name="Valeur")
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['campaign', 'rule_type']
    
    def __str__(self):
        return f"{self.campaign.name} - {self.field_name} {self.get_operator_display()} {self.value}"
    
    def evaluate(self, user, mission=None):
        """Évalue la règle pour un utilisateur et une mission donnés"""
        try:
            if self.rule_type == 'user_attribute':
                actual_value = getattr(user, self.field_name, None)
            elif self.rule_type == 'order_attribute' and mission:
                actual_value = getattr(mission, self.field_name, None)
            else:
                return True  # Règle non applicable
            
            return self._compare_values(actual_value, self.value, self.operator)
        except Exception:
            return False
    
    def _compare_values(self, actual, expected, operator):
        """Compare deux valeurs selon l'opérateur"""
        if operator == 'equals':
            return str(actual) == expected
        elif operator == 'not_equals':
            return str(actual) != expected
        elif operator == 'greater_than':
            return float(actual) > float(expected)
        elif operator == 'less_than':
            return float(actual) < float(expected)
        elif operator == 'contains':
            return expected.lower() in str(actual).lower()
        elif operator == 'in_list':
            return str(actual) in expected.split(',')
        return False


class PromotionAnalytics(models.Model):
    """
    Analytics des promotions par jour
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey(
        PromotionCampaign, on_delete=models.CASCADE,
        related_name='analytics'
    )
    
    date = models.DateField(verbose_name="Date")
    
    # Métriques d'utilisation
    total_uses = models.PositiveIntegerField(default=0)
    unique_users = models.PositiveIntegerField(default=0)
    total_discount_given = models.DecimalField(
        max_digits=12, decimal_places=2, default=0
    )
    total_revenue_impact = models.DecimalField(
        max_digits=12, decimal_places=2, default=0
    )
    
    # Métriques de conversion
    views = models.PositiveIntegerField(default=0)
    clicks = models.PositiveIntegerField(default=0)
    conversions = models.PositiveIntegerField(default=0)
    conversion_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=0
    )
    
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        unique_together = ['campaign', 'date']
        ordering = ['-date']
    
    def __str__(self):
        return f"{self.campaign.name} - {self.date}"
