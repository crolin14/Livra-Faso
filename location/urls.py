from django.urls import path
from . import views

app_name = 'location'

urlpatterns = [
    # Tableau de bord et vues principales
    path('', views.location_dashboard, name='dashboard'),
    path('history/', views.location_history, name='history'),
    path('alerts/', views.location_alerts, name='alerts'),
    path('geofences/', views.geofences, name='geofences'),
    
    # Suivi des missions
    path('mission/<int:mission_id>/tracking/', views.mission_tracking, name='mission_tracking'),
    
    # API pour la géolocalisation
    path('api/update-location/', views.update_location, name='update_location'),
    path('api/get-location/', views.get_user_location, name='get_user_location'),
    path('api/geocode/', views.geocode_address_view, name='geocode_address'),
    path('api/reverse-geocode/', views.reverse_geocode_view, name='reverse_geocode'),
    path('api/nearby-livreurs/', views.nearby_livreurs, name='nearby_livreurs'),
    
    # API pour applications mobiles
    path('api/mobile/update-location/', views.api_update_location, name='api_update_location'),
] 