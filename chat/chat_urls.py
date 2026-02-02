"""
URLs pour le chat temps réel - LivraFaso
"""

from django.urls import path
from . import chat_views

app_name = 'chat'

urlpatterns = [
    # Vues principales
    path('mission/<int:mission_id>/', chat_views.mission_chat_view, name='mission_chat'),
    
    # APIs
    path('api/conversations/', chat_views.user_conversations, name='user_conversations'),
    path('api/conversation/<int:conversation_id>/messages/', chat_views.conversation_messages, name='conversation_messages'),
    path('api/send-message/', chat_views.send_message, name='send_message'),
    path('api/mark-read/', chat_views.mark_messages_read, name='mark_messages_read'),
    path('api/search/', chat_views.chat_search, name='chat_search'),
    
    # Modération (Admin)
    path('moderation/', chat_views.chat_moderation_view, name='moderation'),
    path('api/moderate-message/', chat_views.moderate_message, name='moderate_message'),
]
