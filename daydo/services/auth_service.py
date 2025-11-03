"""
Authentication service for DayDo application.
Handles JWT token generation and authentication-related operations.
"""
from rest_framework_simplejwt.tokens import RefreshToken
from daydo.models import User
from daydo.serializers import UserSerializer


class AuthService:
    """Service class for authentication operations"""
    
    @staticmethod
    def generate_tokens_for_user(user: User) -> dict:
        """
        Generate JWT tokens for a user.
        
        Args:
            user: User instance
            
        Returns:
            dict: Dictionary containing 'access' and 'refresh' tokens
        """
        refresh = RefreshToken.for_user(user)
        return {
            'access': str(refresh.access_token),
            'refresh': str(refresh)
        }
    
    @staticmethod
    def create_auth_response(user: User, message: str) -> dict:
        """
        Create standardized authentication response.
        
        Args:
            user: User instance
            message: Success message
            
        Returns:
            dict: Standardized response with message, user data, and tokens
        """
        return {
            'message': message,
            'user': UserSerializer(user).data,
            'tokens': AuthService.generate_tokens_for_user(user)
        }

