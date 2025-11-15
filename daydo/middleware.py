"""
Custom middleware for WebSocket authentication.
"""
from urllib.parse import parse_qs
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from channels.db import database_sync_to_async
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

User = get_user_model()


class JWTAuthMiddleware:
    """
    Custom middleware to authenticate WebSocket connections using JWT tokens.
    Token should be passed as a query parameter: ?token=<jwt_token>
    """
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        # Only process WebSocket connections
        if scope["type"] == "websocket":
            # Get token from query string
            query_string = scope.get("query_string", b"").decode()
            query_params = parse_qs(query_string)
            token = query_params.get("token", [None])[0]
            
            if token:
                try:
                    # Validate JWT token
                    access_token = AccessToken(token)
                    user_id = access_token.get("user_id")
                    user = await self.get_user(user_id)
                    scope["user"] = user
                except (TokenError, InvalidToken):
                    scope["user"] = AnonymousUser()
            else:
                scope["user"] = AnonymousUser()
        
        return await self.app(scope, receive, send)
    
    @database_sync_to_async
    def get_user(self, user_id):
        """Get user from database"""
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return AnonymousUser()

