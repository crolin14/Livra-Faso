from django.urls import path
from . import views

app_name = 'ratings'

urlpatterns = [
    path('user/<int:user_id>/', views.user_ratings, name='user_ratings'),
    path('rate/<int:user_id>/', views.rate_user, name='rate_user'),
    path('mission/<int:mission_id>/rate/', views.rate_mission, name='rate_mission'),
] 