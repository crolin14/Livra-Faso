from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.utils import timezone
from location.models import Geofence

class User(AbstractUser):
    """Modèle utilisateur personnalisé"""
    USER_TYPE_CHOICES = [
        ('client', 'Client'),
        ('livreur', 'Livreur'),
        ('entreprise', 'Entreprise'),
        ('admin', 'Admin'),
    ]
    
    user_type = models.CharField(max_length=15, choices=USER_TYPE_CHOICES)
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Le numéro de téléphone doit être au format: '+999999999'. Jusqu'à 15 chiffres autorisés."
    )
    phone_number = models.CharField(validators=[phone_regex], max_length=17, blank=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Utilisateur"
        verbose_name_plural = "Utilisateurs"
    
    def __str__(self):
        return f"{self.username} ({self.get_user_type_display()})"

class LivreurProfile(models.Model):
    """Profil spécifique pour les livreurs"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='livreur_profile')
    vehicle_type = models.CharField(max_length=50, choices=[
        ('moto', 'Moto'),
        ('voiture', 'Voiture'),
        ('camion', 'Camion'),
        ('velo', 'Vélo'),
    ])
    vehicle_plate = models.CharField(max_length=20, blank=True)
    license_number = models.CharField(max_length=50, blank=True)
    experience_years = models.PositiveIntegerField(default=0)
    current_location = models.CharField(max_length=200, blank=True)
    is_available = models.BooleanField(default=True)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    total_missions = models.PositiveIntegerField(default=0)
    service_zones = models.ManyToManyField(Geofence, blank=True, related_name="livreurs_in_zone")
    
    class Meta:
        verbose_name = "Profil Livreur"
        verbose_name_plural = "Profils Livreurs"
    
    def __str__(self):
        return f"Livreur: {self.user.username}"

class EntrepriseProfile(models.Model):
    """Profil spécifique pour les entreprises"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='entreprise_profile')
    company_name = models.CharField(max_length=200)
    business_type = models.CharField(max_length=100, choices=[
        ('restaurant', 'Restaurant'),
        ('boutique', 'Boutique'),
        ('pharmacie', 'Pharmacie'),
        ('autre', 'Autre'),
    ])
    address = models.TextField()
    tax_id = models.CharField(max_length=50, blank=True)
    business_license = models.CharField(max_length=50, blank=True)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    total_orders = models.PositiveIntegerField(default=0)
    
    class Meta:
        verbose_name = "Profil Entreprise"
        verbose_name_plural = "Profils Entreprises"
    
    def __str__(self):
        return f"Entreprise: {self.company_name}"