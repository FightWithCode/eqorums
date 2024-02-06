from django.urls import path
from . import consumers
websocket_urlpatterns = [
    path("ws/ac/<str:grp_name>/", consumers.ChatConsumer.as_asgi())
]
