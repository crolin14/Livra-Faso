from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
import math

class UserLocation(models.Model):
    """Position géographique d'un utilisateur"""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='location')
    latitude = models.DecimalField(max_digits=9, decimal_places=6, validators=[
        MinValueValidator(-90), MaxValueValidator(90)
    ])
    longitude = models.DecimalField(max_digits=9, decimal_places=6, validators=[
        MinValueValidator(-180), MaxValueValidator(180)
    ])
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, default='Ouagadougou')
    country = models.CharField(max_length=3, default='BF')
    accuracy = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)  # en mètres
    is_active = models.BooleanField(default=True)
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Position Utilisateur"
        verbose_name_plural = "Positions Utilisateurs"
        indexes = [
            models.Index(fields=['latitude', 'longitude']),
            models.Index(fields=['user', 'is_active']),
        ]
    
    def __str__(self):
        return f"Position de {self.user.username}: {self.latitude}, {self.longitude}"
    
    @property
    def coordinates(self):
        return (float(self.latitude), float(self.longitude))
    
    def distance_to(self, other_location):
        """Calculer la distance vers une autre position (formule de Haversine)"""
        if not other_location:
            return None
        
        lat1, lon1 = float(self.latitude), float(self.longitude)
        lat2, lon2 = float(other_location.latitude), float(other_location.longitude)
        
        # Rayon de la Terre en km
        R = 6371
        
        # Conversion en radians
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        
        # Différences
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        # Formule de Haversine
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        return R * c  # Distance en km

class MissionLocation(models.Model):
    """Position géographique d'une mission"""
    LOCATION_TYPES = [
        ('pickup', 'Point de ramassage'),
        ('delivery', 'Point de livraison'),
        ('current', 'Position actuelle'),
    ]
    
    mission = models.ForeignKey('missions.Mission', on_delete=models.CASCADE, related_name='locations')
    location_type = models.CharField(max_length=20, choices=LOCATION_TYPES)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, validators=[
        MinValueValidator(-90), MaxValueValidator(90)
    ])
    longitude = models.DecimalField(max_digits=9, decimal_places=6, validators=[
        MinValueValidator(-180), MaxValueValidator(180)
    ])
    address = models.TextField()
    city = models.CharField(max_length=100, default='Ouagadougou')
    country = models.CharField(max_length=3, default='BF')
    instructions = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Position de Mission"
        verbose_name_plural = "Positions de Missions"
        unique_together = ['mission', 'location_type']
        indexes = [
            models.Index(fields=['mission', 'location_type']),
            models.Index(fields=['latitude', 'longitude']),
        ]
    
    def __str__(self):
        return f"{self.get_location_type_display()} - Mission #{self.mission.id}"
    
    @property
    def coordinates(self):
        return (float(self.latitude), float(self.longitude))

class LocationHistory(models.Model):
    """Historique des positions d'un utilisateur"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='location_history')
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    accuracy = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    speed = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)  # km/h
    heading = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)  # degrés
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Historique de Position"
        verbose_name_plural = "Historiques de Positions"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['timestamp']),
        ]
    
    def __str__(self):
        return f"Position de {self.user.username} à {self.timestamp}"

class Geofence(models.Model):
    """Zone géographique pour les alertes"""
    GEOFENCE_TYPES = [
        ('pickup_zone', 'Zone de ramassage'),
        ('delivery_zone', 'Zone de livraison'),
        ('restricted_zone', 'Zone restreinte'),
        ('service_zone', 'Zone de service'),
    ]
    
    name = models.CharField(max_length=100)
    geofence_type = models.CharField(max_length=20, choices=GEOFENCE_TYPES)
    center_latitude = models.DecimalField(max_digits=9, decimal_places=6)
    center_longitude = models.DecimalField(max_digits=9, decimal_places=6)
    radius = models.DecimalField(max_digits=5, decimal_places=2)  # en km
    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Zone Géographique"
        verbose_name_plural = "Zones Géographiques"
        indexes = [
            models.Index(fields=['geofence_type', 'is_active']),
            models.Index(fields=['center_latitude', 'center_longitude']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_geofence_type_display()})"
    
    def contains_point(self, latitude, longitude):
        """Vérifier si un point est dans la zone"""
        from .utils import calculate_distance
        distance = calculate_distance(
            float(self.center_latitude), float(self.center_longitude),
            float(latitude), float(longitude)
        )
        return distance <= float(self.radius)

class LocationAlert(models.Model):
    """Alertes basées sur la géolocalisation"""
    ALERT_TYPES = [
        ('enter_zone', 'Entrée dans une zone'),
        ('exit_zone', 'Sortie d\'une zone'),
        ('near_destination', 'Proche de la destination'),
        ('off_route', 'Déviation de route'),
        ('speed_limit', 'Limite de vitesse'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='location_alerts')
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES)
    geofence = models.ForeignKey(Geofence, on_delete=models.CASCADE, null=True, blank=True)
    mission = models.ForeignKey('missions.Mission', on_delete=models.CASCADE, null=True, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Alerte de Géolocalisation"
        verbose_name_plural = "Alertes de Géolocalisation"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['alert_type', 'created_at']),
        ]
    
    def __str__(self):
        return f"Alerte {self.get_alert_type_display()} pour {self.user.username}"
