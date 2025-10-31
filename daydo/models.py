import uuid
import re
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError


def validate_hex_color(value):
    """Validate that the value is a valid HEX color code (#RRGGBB or #RGB)"""
    if not value:
        return
    hex_color_pattern = re.compile(r'^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$')
    if not hex_color_pattern.match(value):
        raise ValidationError('Enter a valid HEX color code (e.g., #FF5733 or #F57)')


class Family(models.Model):
    """
    The central unit that links all family members and profiles.
    Created during the first Parent's sign-up (User Story 1).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, help_text="The customizable family name (e.g., 'The Smiths')")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Families"
        ordering = ['name']
    
    def __str__(self):
        return self.name


class User(AbstractUser):
    """
    Custom User model extending Django's AbstractUser to handle authentication
    and the two login-enabled roles: PARENT and CHILD_USER.
    """
    ROLE_CHOICES = [
        ('PARENT', 'Parent'),
        ('CHILD_USER', 'Child User'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    family = models.ForeignKey(Family, on_delete=models.CASCADE, related_name='members')
    role = models.CharField(max_length=15, choices=ROLE_CHOICES)
    email = models.EmailField(unique=True, null=True, blank=True, help_text="Optional for CHILD_USER")
    phone_number = models.CharField(
        max_length=15, 
        blank=True, 
        validators=[RegexValidator(regex=r'^\+?1?\d{9,15}$', message="Enter a valid phone number")]
    )
    avatar = models.CharField(max_length=20, blank=True, help_text="Icon reference")
    color = models.CharField(
        max_length=7, 
        blank=True, 
        validators=[validate_hex_color],
        help_text="HEX color code (e.g., #FF5733)"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ['first_name', 'last_name']
    
    def __str__(self):
        return f"{self.first_name} ({self.get_role_display()})"
    
    @property
    def is_parent(self):
        """Check if user is a parent"""
        return self.role == 'PARENT'
    
    @property
    def is_child_user(self):
        """Check if user is a child user"""
        return self.role == 'CHILD_USER'
    
    def can_manage_family(self):
        """Check if user can manage family settings"""
        return self.is_parent
    
    def can_assign_tasks(self):
        """Check if user can assign tasks to children"""
        return self.is_parent
    
    def get_display_name(self):
        """Get display name for UI"""
        return f"{self.first_name} {self.last_name}".strip() or self.username


class ChildProfile(models.Model):
    """
    The child entity profile, separate from their potential login account.
    Covers both CHILD_USER and CHILD_VIEW types.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    family = models.ForeignKey(Family, on_delete=models.CASCADE, related_name='child_profiles')
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50, blank=True)
    
    # Differentiation fields
    is_view_only = models.BooleanField(
        default=True, 
        help_text="True for CHILD_VIEW, False for CHILD_USER"
    )
    linked_user = models.OneToOneField(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='child_profile',
        limit_choices_to={'role': 'CHILD_USER'}
    )
    
    # Management and display fields
    manager = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='managed_child_profiles', 
        limit_choices_to={'role': 'PARENT'}
    )
    avatar = models.CharField(max_length=20, blank=True, help_text="Icon reference")
    color = models.CharField(
        max_length=7, 
        blank=True, 
        validators=[validate_hex_color],
        help_text="HEX color code (e.g., #FF5733)"
    )
    birth_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Child Profile"
        verbose_name_plural = "Child Profiles"
        unique_together = ['family', 'first_name', 'last_name']
        ordering = ['first_name', 'last_name']
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.family.name})"
    
    @property
    def full_name(self):
        """Get full name"""
        return f"{self.first_name} {self.last_name}".strip()
    
    @property
    def has_login_account(self):
        """Check if this child has a login account (CHILD_USER)"""
        return self.linked_user is not None and not self.is_view_only
    
    @property
    def is_child_view(self):
        """Check if this is a view-only child profile"""
        return self.is_view_only
    
    def get_display_name(self):
        """Get display name for UI"""
        return self.first_name
    
    def create_login_account(self, username=None, password=None):
        """
        Convert CHILD_VIEW to CHILD_USER by creating login account
        """
        if self.has_login_account:
            raise ValueError("Child already has a login account")
        
        if not username:
            username = f"{self.first_name.lower()}_{self.family.name.lower()}"
        
        # Create User account
        user = User.objects.create_user(
            username=username,
            password=password,
            first_name=self.first_name,
            last_name=self.last_name,
            family=self.family,
            role='CHILD_USER'
        )
        
        # Link to child profile
        self.linked_user = user
        self.is_view_only = False
        self.save()
        
        # Create default permissions
        ChildUserPermissions.create_default_permissions(user)
        
        return user


class ChildUserPermissions(models.Model):
    """
    Permissions table for CHILD_USER role using Deny-by-Exception policy.
    Uses OneToOneField as primary key to link directly to the User.
    """
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        primary_key=True, 
        limit_choices_to={'role': 'CHILD_USER'}
    )
    
    # Family management permissions
    can_invite_parent = models.BooleanField(
        default=False, 
        help_text="Can invite other parents"
    )
    can_delete_child_profile = models.BooleanField(
        default=False, 
        help_text="Can delete child profiles"
    )
    can_access_admin_settings = models.BooleanField(
        default=False, 
        help_text="Can access family settings"
    )
    
    # Task management permissions
    can_delete_all_tasks = models.BooleanField(
        default=False, 
        help_text="Can delete tasks not assigned to them"
    )
    can_create_tasks = models.BooleanField(
        default=False, 
        help_text="Can create new tasks"
    )
    can_edit_task_details = models.BooleanField(
        default=False, 
        help_text="Can edit task titles and descriptions"
    )
    
    # Communication permissions
    can_send_messages = models.BooleanField(
        default=False, 
        help_text="Can send messages to family members"
    )
    can_view_family_calendar = models.BooleanField(
        default=False, 
        help_text="Can view family calendar"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Child User Permissions"
        verbose_name_plural = "Child User Permissions"
    
    def __str__(self):
        return f"Permissions for {self.user.username}"
    
    @classmethod
    def create_default_permissions(cls, user):
        """Create default permissions for a new CHILD_USER"""
        if user.role == 'CHILD_USER':
            return cls.objects.create(user=user)
        return None
    
    def has_permission(self, permission_name):
        """Check if user has a specific permission"""
        return getattr(self, permission_name, False)