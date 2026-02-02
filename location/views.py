from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.conf import settings
from .models import UserLocation, MissionLocation, LocationHistory, Geofence, LocationAlert
from .utils import (
    update_user_location, geocode_address, reverse_geocode,
    get_nearby_livreurs, calculate_distance, validate_coordinates
)
from missions.models import Mission
import json

@login_required
def location_dashboard(request):
    """Tableau de bord de géolocalisation"""
    user = request.user
    
    # Récupérer la position actuelle de l'utilisateur
    try:
        user_location = user.location
    except UserLocation.DoesNotExist:
        user_location = None
    
    # Récupérer l'historique récent
    recent_history = LocationHistory.objects.filter(user=user).order_by('-timestamp')[:10]
    
    # Récupérer les alertes non lues
    unread_alerts = LocationAlert.objects.filter(user=user, is_read=False).order_by('-created_at')
    
    # Récupérer les missions avec géolocalisation
    if user.user_type == 'livreur':
        missions = Mission.objects.filter(livreur=user).order_by('-created_at')[:5]
    elif user.user_type == 'entreprise':
        missions = Mission.objects.filter(client=user).order_by('-created_at')[:5]
    else:
        missions = []
    
    context = {
        'title': 'Géolocalisation',
        'user_location': user_location,
        'recent_history': recent_history,
        'unread_alerts': unread_alerts,
        'missions': missions,
        'map_config': settings.LOCATION_SETTINGS,
    }
    
    return render(request, 'location/dashboard.html', context)

@login_required
def update_location(request):
    """Mettre à jour la position de l'utilisateur (AJAX)"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            latitude = float(data.get('latitude'))
            longitude = float(data.get('longitude'))
            accuracy = data.get('accuracy')
            speed = data.get('speed')
            heading = data.get('heading')
            
            # Valider les coordonnées
            if not validate_coordinates(latitude, longitude):
                return JsonResponse({'error': 'Coordonnées invalides'}, status=400)
            
            # Mettre à jour la position
            user_location = update_user_location(
                request.user, latitude, longitude, accuracy, speed, heading
            )
            
            if user_location:
                return JsonResponse({
                    'success': True,
                    'message': 'Position mise à jour',
                    'location': {
                        'latitude': float(user_location.latitude),
                        'longitude': float(user_location.longitude),
                        'address': user_location.address,
                        'last_updated': user_location.last_updated.isoformat()
                    }
                })
            else:
                return JsonResponse({'error': 'Erreur lors de la mise à jour'}, status=500)
                
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            return JsonResponse({'error': f'Données invalides: {str(e)}'}, status=400)
    
    return JsonResponse({'error': 'Méthode non autorisée'}, status=405)

@login_required
def get_user_location(request):
    """Récupérer la position actuelle de l'utilisateur"""
    try:
        user_location = request.user.location
        return JsonResponse({
            'latitude': float(user_location.latitude),
            'longitude': float(user_location.longitude),
            'address': user_location.address,
            'last_updated': user_location.last_updated.isoformat()
        })
    except UserLocation.DoesNotExist:
        return JsonResponse({'error': 'Aucune position enregistrée'}, status=404)

@login_required
def geocode_address_view(request):
    """Géocoder une adresse"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            address = data.get('address')
            city = data.get('city', 'Ouagadougou')
            country = data.get('country', 'BF')
            
            if not address:
                return JsonResponse({'error': 'Adresse requise'}, status=400)
            
            result = geocode_address(address, city, country)
            return JsonResponse(result)
            
        except (json.JSONDecodeError, KeyError) as e:
            return JsonResponse({'error': f'Données invalides: {str(e)}'}, status=400)
    
    return JsonResponse({'error': 'Méthode non autorisée'}, status=405)

@login_required
def reverse_geocode_view(request):
    """Géocodage inverse (coordonnées vers adresse)"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            latitude = float(data.get('latitude'))
            longitude = float(data.get('longitude'))
            
            if not validate_coordinates(latitude, longitude):
                return JsonResponse({'error': 'Coordonnées invalides'}, status=400)
            
            result = reverse_geocode(latitude, longitude)
            return JsonResponse(result)
            
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            return JsonResponse({'error': f'Données invalides: {str(e)}'}, status=400)
    
    return JsonResponse({'error': 'Méthode non autorisée'}, status=405)

@login_required
def nearby_livreurs(request):
    """Trouver les livreurs à proximité"""
    if request.method == 'GET':
        try:
            latitude = float(request.GET.get('latitude'))
            longitude = float(request.GET.get('longitude'))
            radius = float(request.GET.get('radius', 10))
            max_results = int(request.GET.get('max_results', 10))
            
            if not validate_coordinates(latitude, longitude):
                return JsonResponse({'error': 'Coordonnées invalides'}, status=400)
            
            nearby = get_nearby_livreurs(latitude, longitude, radius, max_results)
            
            results = []
            for livreur_data in nearby:
                livreur = livreur_data['livreur']
                results.append({
                    'id': livreur.id,
                    'username': livreur.username,
                    'name': f"{livreur.first_name} {livreur.last_name}",
                    'distance': livreur_data['distance'],
                    'vehicle_type': livreur.livreur_profile.vehicle_type if hasattr(livreur, 'livreur_profile') else None,
                    'rating': float(livreur.livreur_profile.rating) if hasattr(livreur, 'livreur_profile') else 0.0,
                    'location': {
                        'latitude': float(livreur_data['location'].latitude),
                        'longitude': float(livreur_data['location'].longitude),
                        'address': livreur_data['location'].address
                    }
                })
            
            return JsonResponse({'livreurs': results})
            
        except (ValueError, KeyError) as e:
            return JsonResponse({'error': f'Paramètres invalides: {str(e)}'}, status=400)
    
    return JsonResponse({'error': 'Méthode non autorisée'}, status=405)

@login_required
def mission_tracking(request, mission_id):
    """Suivi en temps réel d'une mission"""
    mission = get_object_or_404(Mission, id=mission_id)
    
    # Vérifier les permissions
    if request.user != mission.client and request.user != mission.livreur:
        messages.error(request, 'Vous n\'avez pas accès à cette mission.')
        return redirect('missions:list')
    
    # Récupérer les positions de la mission
    pickup_location = mission.locations.filter(location_type='pickup').first()
    delivery_location = mission.locations.filter(location_type='delivery').first()
    
    # Récupérer la position du livreur si disponible
    livreur_location = None
    if mission.livreur:
        try:
            livreur_location = mission.livreur.location
        except UserLocation.DoesNotExist:
            pass
    
    context = {
        'title': f'Suivi Mission #{mission.id}',
        'mission': mission,
        'pickup_location': pickup_location,
        'delivery_location': delivery_location,
        'livreur_location': livreur_location,
        'map_config': settings.LOCATION_SETTINGS,
    }
    
    return render(request, 'location/mission_tracking.html', context)

@login_required
def location_history(request):
    """Historique des positions de l'utilisateur"""
    user = request.user
    
    # Pagination
    page = request.GET.get('page', 1)
    try:
        page = int(page)
    except ValueError:
        page = 1
    
    per_page = 50
    start = (page - 1) * per_page
    end = start + per_page
    
    history = LocationHistory.objects.filter(user=user).order_by('-timestamp')
    total_count = history.count()
    history_page = history[start:end]
    
    context = {
        'title': 'Historique des positions',
        'history': history_page,
        'total_count': total_count,
        'current_page': page,
        'total_pages': (total_count + per_page - 1) // per_page,
        'per_page': per_page,
    }
    
    return render(request, 'location/history.html', context)

@login_required
def location_alerts(request):
    """Alertes de géolocalisation"""
    user = request.user
    
    # Marquer les alertes comme lues
    if request.method == 'POST':
        alert_id = request.POST.get('alert_id')
        if alert_id:
            try:
                alert = LocationAlert.objects.get(id=alert_id, user=user)
                alert.is_read = True
                alert.save()
                return JsonResponse({'success': True})
            except LocationAlert.DoesNotExist:
                return JsonResponse({'error': 'Alerte non trouvée'}, status=404)
    
    # Récupérer les alertes
    alerts = LocationAlert.objects.filter(user=user).order_by('-created_at')
    
    context = {
        'title': 'Alertes de géolocalisation',
        'alerts': alerts,
    }
    
    return render(request, 'location/alerts.html', context)

@login_required
def geofences(request):
    """Gestion des zones géographiques (admin)"""
    if not request.user.is_staff:
        messages.error(request, 'Accès non autorisé.')
        return redirect('location:dashboard')
    
    geofences = Geofence.objects.all().order_by('-created_at')
    
    context = {
        'title': 'Zones géographiques',
        'geofences': geofences,
    }
    
    return render(request, 'location/geofences.html', context)

# API endpoints pour les applications mobiles
@csrf_exempt
@require_http_methods(["POST"])
def api_update_location(request):
    """API pour mettre à jour la position (pour applications mobiles)"""
    try:
        data = json.loads(request.body)
        user_id = data.get('user_id')
        latitude = float(data.get('latitude'))
        longitude = float(data.get('longitude'))
        accuracy = data.get('accuracy')
        speed = data.get('speed')
        heading = data.get('heading')
        
        # Authentification simple (en production, utiliser des tokens)
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return JsonResponse({'error': 'Utilisateur non trouvé'}, status=404)
        
        # Valider les coordonnées
        if not validate_coordinates(latitude, longitude):
            return JsonResponse({'error': 'Coordonnées invalides'}, status=400)
        
        # Mettre à jour la position
        user_location = update_user_location(user, latitude, longitude, accuracy, speed, heading)
        
        if user_location:
            return JsonResponse({
                'success': True,
                'message': 'Position mise à jour',
                'timestamp': timezone.now().isoformat()
            })
        else:
            return JsonResponse({'error': 'Erreur lors de la mise à jour'}, status=500)
            
    except (json.JSONDecodeError, ValueError, KeyError) as e:
        return JsonResponse({'error': f'Données invalides: {str(e)}'}, status=400)
