from django.urls import re_path
from chat_consumer import consumers

websocket_urlpatterns = [
    re_path(r'ws/chat/(?P<room_name>\w+)/$', consumers.ChatConsumer.as_asgi()),
    re_path(r'ws/notifications/$', consumers.UserNotificationConsumer.as_asgi()),
]
