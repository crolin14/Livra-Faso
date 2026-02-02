from django.urls import path
from . import views
from monitoring.simple_health_check import simple_health_check_view, simple_metrics_view

app_name = 'public'

urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('faq/', views.faq, name='faq'),
    path('statistics/', views.statistics_view, name='statistics'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    
    # Health check endpoints (simple version)
    path('health/', simple_health_check_view, name='health_check'),
    path('metrics/', simple_metrics_view, name='metrics'),
]