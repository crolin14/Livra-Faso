from django.urls import path, include
from . import views, chat_views, views_courses

app_name = 'client_dashboard'

urlpatterns = [
    # Dashboard principal
    path('', views.client_dashboard, name='dashboard'),
    
    # Livraisons
    path('livraisons/', views.mes_livraisons, name='mes_livraisons'),
    path('nouvelle-livraison/', views.nouvelle_livraison, name='nouvelle_livraison'),
    path('suivi/<int:mission_id>/', views.suivi_mission, name='suivi_mission'),
    path('mission/<int:mission_id>/', views.detail_mission, name='detail_mission'),
    path('mission/<int:mission_id>/annuler/', views.annuler_mission, name='annuler_mission'),
    
    # Courses
    path('courses/', views.faire_courses, name='faire_courses'),
    path('shopping/', views.faire_courses, name='shopping'),  # Alias pour shopping
    path('courses/<int:liste_id>/', views.detail_liste_courses, name='detail_liste_courses'),
    
    # Historique et profil
    path('historique/', views.historique_recu, name='historique_recu'),
    path('history/', views.historique_recu, name='history'),
    path('profil/', views.mon_profil, name='mon_profil'),
    path('profile/', views.mon_profil, name='profile'),
    
    # APIs
    path('api/estimation-prix/', views.estimation_prix, name='estimation_prix_api'),
    path('api/ajouter-adresse/', views.ajouter_adresse, name='ajouter_adresse_api'),
    path('api/ajouter-moyen-paiement/', views.ajouter_moyen_paiement, name='ajouter_moyen_paiement_api'),
    

    
    # Chat
    path('chat/<int:mission_id>/', chat_views.mission_chat, name='mission_chat'),
    
    # Paiements
    path('paiement/', include('client_dashboard.payment_urls')),
    
    # Module "Faire mes courses"
    path('courses/creer/', views_courses.creer_mission_courses, name='creer_mission_courses'),
    path('courses/calculer-prix/', views_courses.calculer_prix_courses, name='calculer_prix_courses'),
    path('courses/<int:mission_id>/paiement/', views_courses.paiement_mission_courses, name='paiement_mission_courses'),
    path('courses/<int:mission_id>/', views_courses.detail_mission_courses, name='detail_mission_courses'),
    path('courses/disponibles/', views_courses.missions_courses_disponibles, name='missions_courses_disponibles'),
    path('courses/<int:mission_id>/postuler/', views_courses.postuler_mission_courses, name='postuler_mission_courses'),
    path('courses/<int:mission_id>/executer/', views_courses.executer_mission_courses, name='executer_mission_courses'),
    path('courses/<int:mission_id>/etape/<int:etape_id>/valider/', views_courses.valider_etape_courses, name='valider_etape_courses'),
]
