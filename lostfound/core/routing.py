"""
Routing WebSocket pour Django Channels
"""

from django.urls import re_path
from . import consumers

# Patterns WebSocket pour le chat en temps réel
websocket_urlpatterns = [
    # WebSocket pour une conversation spécifique
    # Format: ws://localhost:8000/ws/chat/{conversation_id}/
    re_path(r'ws/chat/(?P<conversation_id>\d+)/$', consumers.ChatConsumer.as_asgi()),
    
    # WebSocket pour les notifications globales d'un utilisateur
    # Format: ws://localhost:8000/ws/notifications/
    re_path(r'ws/notifications/$', consumers.NotificationConsumer.as_asgi()),
]