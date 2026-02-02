from django.urls import path
from . import views

app_name = 'admin'

urlpatterns = [
    path('dashboard/', views.admin_dashboard, name='dashboard'),
    path('users/', views.admin_users_management, name='users_management'),
    path('missions/', views.admin_missions_management, name='missions_management'),
    path('config/', views.admin_system_config, name='system_config'),
    path('reports/', views.admin_reports, name='reports'),
    path('security/', views.admin_security, name='security'),
    path('api/stats/', views.api_dashboard_stats, name='api_stats'),
]
