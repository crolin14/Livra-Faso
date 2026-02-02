from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include(('public.urls', 'public'), namespace='public')),
    path('users/', include(('users.urls', 'users'), namespace='users')),
    path('missions/', include(('missions.urls', 'missions'), namespace='missions')),
    path('chat/', include(('chat.urls', 'chat'), namespace='chat')),
    path('ratings/', include(('ratings.urls', 'ratings'), namespace='ratings')),
    path('subscriptions/', include(('subscriptions.urls', 'subscriptions'), namespace='subscriptions')),
    path('location/', include(('location.urls', 'location'), namespace='location')),
    path('geolocation/', include(('geolocation.urls', 'geolocation'), namespace='geolocation')),
    path('legal/', include(('legal.urls', 'legal'), namespace='legal')),
    path('admin-dashboard/', include(('admin_dashboard.urls', 'admin_dashboard'), namespace='admin_dashboard')),
    path('support/', include(('support.urls', 'support'), namespace='support')),
    path('promotions/', include(('promotions.urls', 'promotions'), namespace='promotions')),
    path('api/', include(('api.urls', 'api'), namespace='api')),
    path('client/', include(('client_dashboard.urls', 'client_dashboard'), namespace='client_dashboard')),
    
    # Password reset URLs
    path('password_reset/', auth_views.PasswordResetView.as_view(template_name='registration/password_reset.html'), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='registration/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='registration/password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='registration/password_reset_complete.html'), name='password_reset_complete'),
]

# URLs pour les fichiers statiques et média en développement
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
