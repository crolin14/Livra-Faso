from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from decimal import Decimal

class Mission(models.Model):
    """Modèle pour les missions de livraison"""
    # Livreurs ayant postulé à la mission
    candidats = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='missions_postulees', blank=True)
    STATUS_CHOICES = [
        ('en_attente', 'En attente'),
        ('acceptee', 'Acceptée'),
        ('en_cours', 'En cours'),
        ('livree', 'Livrée'),
        ('annulee', 'Annulée'),
    ]
    
    PRIORITY_CHOICES = [
        ('normale', 'Normale'),
        ('urgente', 'Urgente'),
        ('express', 'Express'),
    ]
    
    # Informations de base
    title = models.CharField(max_length=200)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='en_attente')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='normale')
    
    # Adresses
    pickup_address = models.TextField()
    delivery_address = models.TextField()
    pickup_instructions = models.TextField(blank=True)
    delivery_instructions = models.TextField(blank=True)
    
    # Détails de livraison
    PACKAGE_TYPE_CHOICES = [
        ('document', 'Document'),
        ('colis_petit', 'Petit colis'),
        ('colis_moyen', 'Colis moyen'),
        ('colis_volumineux', 'Colis volumineux'),
        ('nourriture', 'Nourriture'),
        ('medicament', 'Médicament'),
        ('autre', 'Autre'),
    ]
    
    package_type = models.CharField(max_length=20, choices=PACKAGE_TYPE_CHOICES, default='colis_petit')
    package_weight = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    package_dimensions = models.CharField(max_length=100, blank=True)
    is_fragile = models.BooleanField(default=False)
    requires_signature = models.BooleanField(default=False)
    
    # Prix et paiement
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    commission = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    estimated_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Dates
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    pickup_time = models.DateTimeField(null=True, blank=True)
    delivery_time = models.DateTimeField(null=True, blank=True)
    estimated_delivery_time = models.DateTimeField(null=True, blank=True)
    
    # Relations
    client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='missions_created')
    livreur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='missions_assigned')
    
    class Meta:
        verbose_name = "Mission"
        verbose_name_plural = "Missions"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Mission #{self.id}: {self.title}"
    
    @property
    def total_price(self):
        return self.price + self.commission
    
    def get_pickup_location(self):
        """Récupérer la localisation de ramassage"""
        from location.models import MissionLocation
        return MissionLocation.objects.filter(
            mission=self, 
            location_type='pickup'
        ).first()
    
    def get_delivery_location(self):
        """Récupérer la localisation de livraison"""
        from location.models import MissionLocation
        return MissionLocation.objects.filter(
            mission=self, 
            location_type='delivery'
        ).first()
    
    def calculate_distance(self):
        """Calculer la distance totale de la mission"""
        pickup = self.get_pickup_location()
        delivery = self.get_delivery_location()
        
        if pickup and delivery:
            from location.utils import calculate_distance
            return calculate_distance(
                pickup.latitude, pickup.longitude,
                delivery.latitude, delivery.longitude
            )
        return None
    
    def estimate_delivery_time(self):
        """Estimer le temps de livraison"""
        distance = self.calculate_distance()
        if distance and self.livreur:
            vehicle_type = getattr(self.livreur.livreur_profile, 'vehicle_type', 'moto')
            from location.utils import estimate_travel_time
            return estimate_travel_time(distance, vehicle_type)
        return None

class MissionTracking(models.Model):
    """Suivi des étapes de la mission"""
    mission = models.ForeignKey(Mission, on_delete=models.CASCADE, related_name='tracking_events')
    status = models.CharField(max_length=50)
    location = models.CharField(max_length=200, blank=True)
    description = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Suivi de Mission"
        verbose_name_plural = "Suivis de Missions"
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"Suivi {self.mission.id}: {self.status}"

class MissionDocument(models.Model):
    """Documents liés à la mission (photos, signatures, etc.)"""
    mission = models.ForeignKey(Mission, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=50, choices=[
        ('photo_pickup', 'Photo de ramassage'),
        ('photo_delivery', 'Photo de livraison'),
        ('signature', 'Signature'),
        ('autre', 'Autre'),
    ])
    file = models.FileField(upload_to='mission_documents/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    description = models.TextField(blank=True)
    
    class Meta:
        verbose_name = "Document de Mission"
        verbose_name_plural = "Documents de Missions"
    
    def __str__(self):
        return f"Document {self.mission.id}: {self.get_document_type_display()}"
