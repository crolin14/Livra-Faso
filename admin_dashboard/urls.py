from django.urls import path
from . import views

app_name = 'admin_dashboard'

urlpatterns = [
    path('dashboard/', views.admin_dashboard, name='dashboard'),
    path('users/', views.users_management, name='users'),
    path('missions/', views.missions_management, name='missions'),
    path('config/', views.system_config, name='config'),
    path('reports/', views.reports, name='reports'),
    path('security/', views.security_logs, name='security'),
    
    # AJAX endpoints for missions
    path('missions/<int:mission_id>/details/', views.mission_details, name='mission_details'),
    path('missions/<int:mission_id>/cancel/', views.cancel_mission, name='cancel_mission'),
    path('missions/export/', views.export_missions, name='export_missions'),
    
    # System configuration endpoints
    path('config/save/', views.save_config, name='save_config'),
    path('system/check/', views.system_check, name='system_check'),
    path('backup/create/', views.create_backup, name='create_backup'),
    path('cache/clear/', views.clear_cache, name='clear_cache'),
    path('api/regenerate-key/', views.regenerate_api_key, name='regenerate_api_key'),
    path('logs/download/', views.export_security_logs, name='download_logs'),
    
    # Reports endpoints
    path('reports/generate/', views.generate_report, name='generate_report'),
    
    # Security logs endpoints
    path('security-logs/export/', views.export_security_logs, name='export_security_logs'),
    path('security-logs/<int:log_id>/details/', views.log_details, name='log_details'),
    path('security-logs/<int:log_id>/resolve/', views.resolve_log, name='resolve_log'),
    path('security-logs/<int:log_id>/export/', views.export_security_logs, name='export_single_log'),
    path('security-logs/check-new/', views.check_new_logs, name='check_new_logs'),
    
    # New API endpoints for interactive dashboard
    path('api/system-check/', views.system_check_api, name='system_check_api'),
    path('api/backup/', views.backup_api, name='backup_api'),
    path('api/clear-cache/', views.clear_cache_api, name='clear_cache_api'),
    path('api/stats/', views.stats_api, name='api_stats'),  # Unified stats endpoint
]
