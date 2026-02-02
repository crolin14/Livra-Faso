from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/chat/(?P<mission_id>\w+)/$', consumers.ChatConsumer.as_asgi()),
    re_path(r'ws/livreur/notifications/$', consumers.NotificationConsumer.as_asgi()),
    re_path(r'ws/client/notifications/$', consumers.NotificationConsumer.as_asgi()),
    re_path(r'ws/entreprise/notifications/$', consumers.NotificationConsumer.as_asgi()),
]
