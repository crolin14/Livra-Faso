from django.urls import path
from . import views

app_name = 'promotions'

urlpatterns = [
    # API endpoints for promo code validation
    path('api/validate-code/', views.validate_promo_code, name='validate_code'),
    path('api/apply-code/', views.apply_promo_code, name='apply_code'),
    path('api/available-promotions/', views.get_available_promotions, name='available_promotions'),
    path('api/user-savings/', views.get_user_savings, name='user_savings'),
    
    # Admin views
    path('admin/campaigns/', views.admin_campaigns_list, name='admin_campaigns'),
    path('admin/campaigns/create/', views.admin_campaign_create, name='admin_campaign_create'),
    path('admin/campaigns/<uuid:campaign_id>/', views.admin_campaign_detail, name='admin_campaign_detail'),
    path('admin/campaigns/<uuid:campaign_id>/edit/', views.admin_campaign_edit, name='admin_campaign_edit'),
    path('admin/campaigns/<uuid:campaign_id>/analytics/', views.admin_campaign_analytics, name='admin_campaign_analytics'),
    path('admin/campaigns/<uuid:campaign_id>/generate-codes/', views.admin_generate_codes, name='admin_generate_codes'),
    
    path('admin/codes/', views.admin_codes_list, name='admin_codes'),
    path('admin/codes/create/', views.admin_code_create, name='admin_code_create'),
    path('admin/codes/<uuid:code_id>/toggle/', views.admin_code_toggle, name='admin_code_toggle'),
    
    path('admin/usage/', views.admin_usage_list, name='admin_usage'),
    path('admin/analytics/', views.admin_analytics_dashboard, name='admin_analytics'),
]
