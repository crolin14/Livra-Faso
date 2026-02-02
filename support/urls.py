from django.urls import path, include
from . import views

app_name = 'support'

# URLs principales pour les utilisateurs
urlpatterns = [
    # Tickets utilisateur
    path('', views.ticket_list, name='ticket_list'),
    path('create/', views.create_ticket, name='create_ticket'),
    path('ticket/<uuid:ticket_id>/', views.ticket_detail, name='ticket_detail'),
    path('ticket/<uuid:ticket_id>/message/', views.add_message, name='add_message'),
    path('ticket/<uuid:ticket_id>/satisfaction/', views.submit_satisfaction, name='submit_satisfaction'),
    
    # Base de connaissances
    path('kb/', views.knowledge_base, name='knowledge_base'),
    path('kb/<slug:slug>/', views.knowledge_article, name='knowledge_article'),
    
    # Admin URLs
    path('admin/', include([
        path('', views.admin_dashboard, name='admin_dashboard'),
        path('tickets/', views.admin_ticket_list, name='admin_ticket_list'),
    ])),
    
    # API endpoints
    path('api/', include([
        path('ticket/<uuid:ticket_id>/assign/', views.api_assign_ticket, name='api_assign_ticket'),
        path('ticket/<uuid:ticket_id>/resolve/', views.api_resolve_ticket, name='api_resolve_ticket'),
        path('ticket/<uuid:ticket_id>/escalate/', views.api_escalate_ticket, name='api_escalate_ticket'),
        path('stats/', views.api_ticket_stats, name='api_ticket_stats'),
        path('article/<uuid:article_id>/vote/', views.api_vote_article, name='api_vote_article'),
    ])),
]
