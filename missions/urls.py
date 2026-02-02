
from django.urls import path
from . import views

app_name = 'missions'

urlpatterns = [
    path('', views.mission_list, name='list'),
    path('enterprise-list/', views.enterprise_mission_list, name='enterprise_list'),
    path('create/', views.create_mission, name='create'),
    path('disponibles/', views.missions_disponibles, name='disponibles'),
    path('<int:mission_id>/', views.mission_detail, name='detail'),
    path('<int:mission_id>/accept/', views.accept_mission, name='accept'),
    path('<int:mission_id>/select-livreur/<int:livreur_id>/', views.select_livreur, name='select_livreur'),
    path('<int:mission_id>/postuler/', views.postuler_mission, name='postuler'),
    path('<int:mission_id>/update-status/', views.update_status, name='update_status'),
    path('<int:mission_id>/tracking/', views.mission_tracking, name='tracking'),
] 