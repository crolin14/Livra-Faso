"""
Utilitaires pour la géolocalisation et calculs de prix
"""
import math
import requests
from django.conf import settings
from typing import Tuple, Optional


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calcule la distance entre deux points géographiques en kilomètres
    Utilise la formule de Haversine
    """
    # Rayon de la Terre en kilomètres
    R = 6371.0
    
    # Conversion en radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    # Différences
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    # Formule de Haversine
    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    distance = R * c
    return distance


def calculate_mission_price(pickup_address: str, delivery_address: str, 
                          package_type: str = 'standard', weight: float = 1.0,
                          priority: str = 'normale') -> float:
    """
    Calcule le prix d'une mission basé sur la distance et autres paramètres
    """
    # Prix de base
    base_price = 1000  # 1000 FCFA de base
    
    # Essayer de géocoder les adresses pour calculer la distance
    pickup_coords = geocode_address(pickup_address)
    delivery_coords = geocode_address(delivery_address)
    
    if pickup_coords and delivery_coords:
        distance = calculate_distance(
            pickup_coords[0], pickup_coords[1],
            delivery_coords[0], delivery_coords[1]
        )
        # Prix par kilomètre
        distance_price = distance * 200  # 200 FCFA par km
    else:
        # Distance estimée si géocodage échoue
        distance_price = 1000  # Prix fixe de 1000 FCFA
    
    # Multiplicateurs selon le type de colis
    package_multipliers = {
        'nourriture': 1.0,
        'document': 0.8,
        'colis': 1.2,
        'fragile': 1.5,
        'medical': 1.8
    }
    
    # Multiplicateur selon le poids
    weight_multiplier = 1.0
    if weight > 5:
        weight_multiplier = 1.3
    elif weight > 10:
        weight_multiplier = 1.6
    
    # Multiplicateur selon la priorité
    priority_multipliers = {
        'normale': 1.0,
        'urgente': 1.5,
        'express': 2.0
    }
    
    # Calcul final
    total_price = (base_price + distance_price) * \
                  package_multipliers.get(package_type, 1.0) * \
                  weight_multiplier * \
                  priority_multipliers.get(priority, 1.0)
    
    # Arrondir au multiple de 50 le plus proche
    return round(total_price / 50) * 50


def geocode_address(address: str) -> Optional[Tuple[float, float]]:
    """
    Géocode une adresse pour obtenir ses coordonnées latitude/longitude
    Retourne (latitude, longitude) ou None si échec
    """
    if not address:
        return None
    
    # Coordonnées par défaut pour Ouagadougou si géocodage échoue
    default_coords = {
        'ouagadougou': (12.3714, -1.5197),
        'bobo-dioulasso': (11.1781, -4.2967),
        'koudougou': (12.2530, -2.3621),
        'banfora': (10.6340, -4.7610),
        'ouahigouya': (13.5822, -2.4217)
    }
    
    # Recherche simple par mots-clés
    address_lower = address.lower()
    for city, coords in default_coords.items():
        if city in address_lower or city.replace('-', ' ') in address_lower:
            return coords
    
    # Si aucune ville reconnue, retourner Ouagadougou par défaut
    return default_coords['ouagadougou']


def get_service_zones():
    """
    Retourne les zones de service disponibles
    """
    return [
        {
            'name': 'Ouagadougou Centre',
            'coordinates': (12.3714, -1.5197),
            'radius': 10  # km
        },
        {
            'name': 'Ouagadougou Périphérie',
            'coordinates': (12.3714, -1.5197),
            'radius': 25  # km
        },
        {
            'name': 'Bobo-Dioulasso',
            'coordinates': (11.1781, -4.2967),
            'radius': 15  # km
        },
        {
            'name': 'Koudougou',
            'coordinates': (12.2530, -2.3621),
            'radius': 10  # km
        }
    ]


def is_address_in_service_zone(address: str) -> bool:
    """
    Vérifie si une adresse est dans une zone de service
    """
    coords = geocode_address(address)
    if not coords:
        return False
    
    zones = get_service_zones()
    for zone in zones:
        distance = calculate_distance(
            coords[0], coords[1],
            zone['coordinates'][0], zone['coordinates'][1]
        )
        if distance <= zone['radius']:
            return True
    
    return False


def update_user_location(user, latitude, longitude, accuracy=None):
    """
    Met à jour la position d'un utilisateur
    """
    from django.utils import timezone
    from .models import UserLocation, LocationHistory
    
    # Valider les coordonnées
    if not validate_coordinates(latitude, longitude):
        return False
    
    # Mettre à jour ou créer la position actuelle
    user_location, created = UserLocation.objects.update_or_create(
        user=user,
        defaults={
            'latitude': latitude,
            'longitude': longitude,
            'accuracy': accuracy,
            'timestamp': timezone.now()
        }
    )
    
    # Ajouter à l'historique
    LocationHistory.objects.create(
        user=user,
        latitude=latitude,
        longitude=longitude,
        accuracy=accuracy,
        timestamp=timezone.now()
    )
    
    return True


def reverse_geocode(latitude, longitude):
    """
    Convertit des coordonnées en adresse lisible
    """
    if not validate_coordinates(latitude, longitude):
        return None
    
    # Zones connues de Ouagadougou
    zones = {
        'centre_ville': {'lat': 12.3714, 'lon': -1.5197, 'name': 'Centre-ville, Ouagadougou'},
        'secteur_15': {'lat': 12.3850, 'lon': -1.5350, 'name': 'Secteur 15, Ouagadougou'},
        'zone_du_bois': {'lat': 12.3500, 'lon': -1.4800, 'name': 'Zone du Bois, Ouagadougou'},
        'cissin': {'lat': 12.4200, 'lon': -1.4500, 'name': 'Cissin, Ouagadougou'},
        'tampouy': {'lat': 12.4000, 'lon': -1.6000, 'name': 'Tampouy, Ouagadougou'},
        'samandin': {'lat': 12.3300, 'lon': -1.5800, 'name': 'Samandin, Ouagadougou'}
    }
    
    # Trouver la zone la plus proche
    min_distance = float('inf')
    closest_zone = None
    
    for zone_key, zone_data in zones.items():
        distance = calculate_distance(
            latitude, longitude,
            zone_data['lat'], zone_data['lon']
        )
        if distance < min_distance:
            min_distance = distance
            closest_zone = zone_data['name']
    
    # Si très proche d'une zone connue (moins de 2km)
    if min_distance < 2:
        return closest_zone
    
    # Sinon, retourner une adresse générique
    return f"Ouagadougou ({latitude:.4f}, {longitude:.4f})"


def get_nearby_livreurs(latitude, longitude, radius_km=10):
    """
    Trouve les livreurs disponibles dans un rayon donné
    """
    from users.models import User, LivreurProfile
    from .models import UserLocation
    
    if not validate_coordinates(latitude, longitude):
        return []
    
    # Récupérer tous les livreurs disponibles avec leur position
    nearby_livreurs = []
    
    livreurs = User.objects.filter(
        user_type='livreur',
        livreurprofile__is_available=True
    ).select_related('livreurprofile')
    
    for livreur in livreurs:
        try:
            location = UserLocation.objects.get(user=livreur)
            distance = calculate_distance(
                latitude, longitude,
                location.latitude, location.longitude
            )
            
            if distance <= radius_km:
                nearby_livreurs.append({
                    'user': livreur,
                    'distance': distance,
                    'location': location
                })
        except UserLocation.DoesNotExist:
            continue
    
    # Trier par distance
    nearby_livreurs.sort(key=lambda x: x['distance'])
    
    return nearby_livreurs


def validate_coordinates(latitude, longitude):
    """
    Valide que les coordonnées sont dans des limites raisonnables
    """
    try:
        lat = float(latitude)
        lon = float(longitude)
        
        # Limites approximatives du Burkina Faso
        # Latitude: 9.4° à 15.1° Nord
        # Longitude: -5.5° à 2.4° Est
        if not (9.0 <= lat <= 15.5):
            return False
        if not (-6.0 <= lon <= 3.0):
            return False
        
        return True
    except (ValueError, TypeError):
        return False


def check_geofence_alerts(user, latitude, longitude):
    """
    Vérifie si l'utilisateur entre/sort d'une zone géofence
    """
    from .models import Geofence, LocationAlert
    
    if not validate_coordinates(latitude, longitude):
        return []
    
    alerts = []
    geofences = Geofence.objects.filter(is_active=True)
    
    for geofence in geofences:
        distance = calculate_distance(
            latitude, longitude,
            geofence.center_latitude, geofence.center_longitude
        )
        
        is_inside = distance <= (geofence.radius / 1000)  # radius en mètres -> km
        
        # Vérifier si c'est un changement d'état
        last_alert = LocationAlert.objects.filter(
            user=user,
            geofence=geofence
        ).order_by('-created_at').first()
        
        if last_alert:
            last_state = last_alert.alert_type == 'enter'
            if is_inside != last_state:
                # Changement d'état détecté
                alert_type = 'enter' if is_inside else 'exit'
                alert = LocationAlert.objects.create(
                    user=user,
                    geofence=geofence,
                    alert_type=alert_type,
                    latitude=latitude,
                    longitude=longitude
                )
                alerts.append(alert)
        else:
            # Première fois dans cette geofence
            if is_inside:
                alert = LocationAlert.objects.create(
                    user=user,
                    geofence=geofence,
                    alert_type='enter',
                    latitude=latitude,
                    longitude=longitude
                )
                alerts.append(alert)
    
    return alerts