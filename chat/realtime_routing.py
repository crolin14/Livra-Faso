"""
Routing WebSocket pour le chat temps réel - LivraFaso
"""

from django.urls import re_path
from . import realtime_consumers

websocket_urlpatterns = [
    # Chat par mission
    re_path(r'ws/chat/mission/(?P<mission_id>\d+)/$', realtime_consumers.MissionChatConsumer.as_asgi()),
    
    # Notifications temps réel
    re_path(r'ws/notifications/$', realtime_consumers.NotificationConsumer.as_asgi()),
]
