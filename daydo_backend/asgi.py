"""
ASGI config for daydo_backend project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'daydo_backend.settings')

django_asgi_app = get_asgi_application()

# Import WebSocket routing and custom JWT auth middleware
from daydo.routing import websocket_urlpatterns
from daydo.middleware import JWTAuthMiddleware

# Wrap WebSocket routing with JWT authentication middleware
# This allows JWT tokens to be passed as query parameters
websocket_auth_stack = JWTAuthMiddleware(
    AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    )
)

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AllowedHostsOriginValidator(
        websocket_auth_stack
    ),
})
