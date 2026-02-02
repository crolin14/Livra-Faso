from django.urls import path
from . import views

app_name = 'geolocation'

urlpatterns = [
    path('livreur/<int:livreur_id>/', views.get_livreur_location, name='get_livreur_location'),
]
