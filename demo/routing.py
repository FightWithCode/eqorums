from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.urls import path
from websockets import consumers



application = ProtocolTypeRouter({
	'websocket': AllowedHostsOriginValidator(
		AuthMiddlewareStack(
			URLRouter([
					# path("send/", SendNotification.as_view()),
                    path("ws/ac/<str:grp_name>/", consumers.ChatConsumer.as_asgi())
			])
		)
	),
})
