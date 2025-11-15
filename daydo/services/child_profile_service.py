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
    def _validate_login_account_creation(child_profile: ChildProfile, password: Optional[str]) -> None:
        """
        Validate that login account can be created.
        
        Args:
            child_profile: ChildProfile instance
            password: Password for the account
            
        Raises:
            ValueError: If child already has a login account or password is missing
        """
        if child_profile.has_login_account:
            raise ValueError("Child already has a login account")
        
        if not password:
            raise ValueError("Password is required when creating login account")
    
    @staticmethod
    def _create_user_account(
        child_profile: ChildProfile,
        username: str,
        password: str
    ) -> User:
        """
        Create the User account for the child profile.
        
        Args:
            child_profile: ChildProfile instance
            username: Username for the account
            password: Password for the account
            
        Returns:
            User: Created User instance
        """
        return User.objects.create_user(
            username=username,
            password=password,
            first_name=child_profile.first_name,
            last_name=child_profile.last_name,
            family=child_profile.family,
            role='CHILD_USER'
        )
    
    @staticmethod
    def _link_profile_to_user(child_profile: ChildProfile, user: User) -> None:
        """
        Link child profile to user account.
        
        Args:
            child_profile: ChildProfile instance
            user: User instance to link
        """
        child_profile.linked_user = user
        child_profile.is_view_only = False
        child_profile.save()
    
    @staticmethod
    def create_login_account(
        child_profile: ChildProfile,
        username: Optional[str] = None,
        password: Optional[str] = None
    ) -> User:
        """
        Create login account for child profile.
        
        This method orchestrates the creation of a login account by:
        1. Validating prerequisites
        2. Generating username if needed
        3. Creating the user account
        4. Linking profile to user
        5. Setting up default permissions
        
        Args:
            child_profile: ChildProfile instance
            username: Optional username (will be generated if not provided)
            password: Password for the account (required)
            
        Returns:
            User: Created User instance
            
        Raises:
            ValueError: If child already has a login account or password is missing
        """
        # Validate prerequisites
        ChildProfileService._validate_login_account_creation(child_profile, password)
        
        # Generate username if not provided
        if not username:
            username = ChildProfileService.generate_username_from_child_profile(child_profile)
        
        # Create User account
        user = ChildProfileService._create_user_account(child_profile, username, password)
        
        # Link profile to user
        ChildProfileService._link_profile_to_user(child_profile, user)
        
        # Create default permissions
        ChildUserPermissions.create_default_permissions(user)
        
        return user

