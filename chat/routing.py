from django.urls import path
from .consumers import ChatConsumer
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    path("ws/chat/<str:room_name>/", ChatConsumer.as_asgi()),
    re_path(r'ws/notifications/$', consumers.NotificationConsumer.as_asgi()),
]