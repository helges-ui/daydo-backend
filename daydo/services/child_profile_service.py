"""
Child profile service for DayDo application.
Handles child profile creation and login account management.
"""
from typing import Optional
from ..models import ChildProfile, User, ChildUserPermissions


class ChildProfileService:
    """Service for child profile operations"""
    
    @staticmethod
    def generate_username_from_child_profile(child_profile: ChildProfile) -> str:
        """
        Generate username from child profile.
        
        Args:
            child_profile: ChildProfile instance
            
        Returns:
            str: Generated username
        """
        return f"{child_profile.first_name.lower()}_{child_profile.family.name.lower()}"
    
    @staticmethod
    def generate_username_from_name(first_name: str, family_name: str) -> str:
        """
        Generate username from name components.
        
        Args:
            first_name: First name
            family_name: Family name
            
        Returns:
            str: Generated username
        """
        return f"{first_name.lower()}_{family_name.lower()}"
    
    @staticmethod
    def create_login_account(
        child_profile: ChildProfile,
        username: Optional[str] = None,
        password: Optional[str] = None
    ) -> User:
        """
        Create login account for child profile.
        
        Args:
            child_profile: ChildProfile instance
            username: Optional username (will be generated if not provided)
            password: Password for the account (required)
            
        Returns:
            User: Created User instance
            
        Raises:
            ValueError: If child already has a login account
            ValueError: If password is not provided
        """
        if child_profile.has_login_account:
            raise ValueError("Child already has a login account")
        
        if not password:
            raise ValueError("Password is required when creating login account")
        
        if not username:
            username = ChildProfileService.generate_username_from_child_profile(child_profile)
        
        # Create User account
        user = User.objects.create_user(
            username=username,
            password=password,
            first_name=child_profile.first_name,
            last_name=child_profile.last_name,
            family=child_profile.family,
            role='CHILD_USER'
        )
        
        # Link to child profile
        child_profile.linked_user = user
        child_profile.is_view_only = False
        child_profile.save()
        
        # Create default permissions
        ChildUserPermissions.create_default_permissions(user)
        
        return user

