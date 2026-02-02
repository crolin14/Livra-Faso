from django.urls import path
from . import chat_views

app_name = 'client_dashboard_chat'

urlpatterns = [
    path('', chat_views.mission_chat, name='mission_chat'),
    path('send/', chat_views.send_message_api, name='send_message'),
    path('messages/', chat_views.get_messages_api, name='get_messages'),
    path('status/', chat_views.chat_status_api, name='chat_status'),
]
