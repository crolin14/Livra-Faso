from django.urls import path
from . import api_views

urlpatterns = [
    path('', api_views.mission_chat_messages, name='mission_chat_messages'),
    path('send/', api_views.send_mission_message, name='send_mission_message'),
]
