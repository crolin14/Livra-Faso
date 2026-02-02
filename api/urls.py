from django.urls import path, include
from . import views, entreprise_views

app_name = 'api'

urlpatterns = [
    # Livreur API endpoints
    path('livreur/', include([
        path('available-missions/', views.livreur_available_missions, name='livreur_available_missions'),
        path('profile/', views.livreur_profile, name='livreur_profile'),
        path('stats/', views.livreur_stats, name='livreur_stats'),
        path('earnings/', views.livreur_earnings, name='livreur_earnings'),
        path('missions/accept/<int:mission_id>/', views.accept_mission, name='accept_mission'),
        path('missions/complete/<int:mission_id>/', views.complete_mission, name='complete_mission'),
    ])),
    
    # Client API endpoints
    path('client/', include([
        path('missions/', views.client_missions, name='client_missions'),
        path('create-mission/', views.create_mission_api, name='create_mission_api'),
        path('mission/<int:mission_id>/status/', views.mission_status, name='mission_status'),
    ])),
    
    # Entreprise API endpoints
    path('entreprise/', include([
        path('kpis/', entreprise_views.entreprise_kpis, name='entreprise_kpis'),
        path('missions/', entreprise_views.entreprise_missions, name='entreprise_missions'),
        path('missions/bulk-create/', entreprise_views.bulk_create_missions, name='bulk_create_missions'),
        path('analytics/export/', entreprise_views.analytics_export, name='analytics_export'),
        path('livreurs/', views.available_livreurs, name='available_livreurs'),
    ])),
    
    # Admin API endpoints
    path('admin/', include([
        path('stats/', views.admin_stats, name='admin_stats'),
        path('users/', views.admin_users, name='admin_users'),
        path('missions/', views.admin_missions, name='admin_missions'),
        path('reports/', views.admin_reports, name='admin_reports'),
    ])),
    
    # Chat API endpoints
    path('chat/mission/<int:mission_id>/', include('chat.api_urls')),
    
    # Real-time notifications
    path('notifications/', views.get_notifications, name='get_notifications'),
    path('notifications/mark-read/', views.mark_notifications_read, name='mark_notifications_read'),
]
