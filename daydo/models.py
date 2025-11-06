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


class Role(models.Model):
    """System roles (e.g., PARENT, CHILD_USER)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    key = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Role"
        verbose_name_plural = "Roles"
        ordering = ['key']

    def __str__(self):
        return self.key


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
    # Deprecated: keep for backfill; do not trust for authorization
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
        constraints = [
            models.CheckConstraint(
                name='chk_parent_requires_email',
                check=(models.Q(role='PARENT', email__isnull=False) | ~models.Q(role='PARENT')),
            )
        ]
    
    def __str__(self):
        return f"{self.first_name} ({self.get_role_display()})"
    
    def clean(self):
        # Parents must have an email; children may omit it
        if self.is_parent and not self.email:
            raise ValidationError("Parent users must have an email.")
    
    @property
    def is_parent(self):
        """Check if user is a parent (via user role relation if present)."""
        rk = getattr(self, 'user_role', None)
        if rk and rk.role:
            return rk.role.key in ('PARENT', 'PARENT_USER', 'PARENT_ROLE') or rk.role.key == 'PARENT'
        return self.role == 'PARENT'
    
    @property
    def is_child_user(self):
        """Check if user is a child user (via user role relation if present)."""
        rk = getattr(self, 'user_role', None)
        if rk and rk.role:
            return rk.role.key in ('CHILD', 'CHILD_USER')
        return False
    
    def can_manage_family(self):
        """Check if user can manage family settings"""
        return self.is_parent
    
    def can_assign_tasks(self):
        """Check if user can assign tasks to children"""
        return self.is_parent
    
    def get_display_name(self):
        """Get display name for UI"""
        return f"{self.first_name} {self.last_name}".strip() or self.username


class UserRole(models.Model):
    """One active role per user (simplified model)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='user_role')
    role = models.ForeignKey(Role, on_delete=models.PROTECT, related_name='assigned_users')
    assigned_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='assigned_roles')
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "User Role"
        verbose_name_plural = "User Roles"

    def __str__(self):
        return f"{self.user.username} -> {self.role.key}"


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
        if getattr(user, 'user_role', None) and getattr(user.user_role, 'role', None) and user.user_role.role.key in ('CHILD', 'CHILD_USER'):
            return cls.objects.create(user=user)
        return None
    
    def has_permission(self, permission_name):
        """Check if user has a specific permission"""
        return getattr(self, permission_name, False)


class Task(models.Model):
    """
    Daily tasks assigned to users (children).
    Tasks are family-scoped and can be assigned to child users.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    family = models.ForeignKey(Family, on_delete=models.CASCADE, related_name='tasks')
    assigned_to = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='assigned_tasks',
        limit_choices_to={'user_role__role__key': 'CHILD'}
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    date = models.DateField(help_text="Date for which this task is assigned")
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    points = models.IntegerField(default=1, help_text="Points awarded upon completion")
    icon = models.CharField(max_length=20, blank=True, help_text="Emoji or icon reference")
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_tasks',
        limit_choices_to={'user_role__role__key': 'PARENT'}
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Task"
        verbose_name_plural = "Tasks"
        ordering = ['date', 'title']
        indexes = [
            models.Index(fields=['family', 'date']),
            models.Index(fields=['assigned_to', 'date']),
            models.Index(fields=['completed']),
        ]

    def __str__(self):
        return f"{self.title} ({self.assigned_to.get_display_name()})"

    def mark_completed(self):
        """Mark task as completed"""
        from django.utils import timezone
        self.completed = True
        self.completed_at = timezone.now()
        self.save(update_fields=['completed', 'completed_at', 'updated_at'])

    def mark_incomplete(self):
        """Mark task as incomplete"""
        self.completed = False
        self.completed_at = None
        self.save(update_fields=['completed', 'completed_at', 'updated_at'])


class Event(models.Model):
    """
    Calendar events for the family.
    Events can be assigned to multiple users via EventAssignment.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    family = models.ForeignKey(Family, on_delete=models.CASCADE, related_name='events')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    start_datetime = models.DateTimeField(help_text="Start date and time of the event")
    end_datetime = models.DateTimeField(null=True, blank=True, help_text="End date and time of the event")
    location = models.CharField(max_length=200, blank=True, null=True)
    reminder_minutes = models.IntegerField(null=True, blank=True, help_text="Reminder minutes before event")
    recurrence_rule = models.CharField(
        max_length=500, 
        blank=True, 
        null=True,
        help_text="RRULE string for recurring events (RFC 5545)"
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_events'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Event"
        verbose_name_plural = "Events"
        ordering = ['start_datetime']
        indexes = [
            models.Index(fields=['family', 'start_datetime']),
            models.Index(fields=['start_datetime']),
        ]

    def __str__(self):
        return f"{self.title} ({self.start_datetime})"


class EventAssignment(models.Model):
    """
    Many-to-many relationship between events and users.
    Links events to family members who are assigned to the event.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='assignments')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='event_assignments')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Event Assignment"
        verbose_name_plural = "Event Assignments"
        unique_together = ['event', 'user']
        ordering = ['event', 'user']

    def __str__(self):
        return f"{self.event.title} -> {self.user.get_display_name()}"


class ShoppingList(models.Model):
    """
    Shopping list for a family.
    One shopping list per family (OneToOne relationship).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    family = models.OneToOneField(
        Family,
        on_delete=models.CASCADE,
        related_name='shopping_list',
        help_text="The family that owns this shopping list"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Shopping List"
        verbose_name_plural = "Shopping Lists"
        ordering = ['family__name']

    def __str__(self):
        return f"Shopping List for {self.family.name}"


class ShoppingItem(models.Model):
    """
    Individual items in a shopping list.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    shopping_list = models.ForeignKey(
        ShoppingList,
        on_delete=models.CASCADE,
        related_name='items',
        help_text="The shopping list this item belongs to"
    )
    name = models.CharField(max_length=200, help_text="Name of the shopping item")
    checked = models.BooleanField(default=False, help_text="Whether the item has been checked off")
    order = models.IntegerField(default=0, help_text="Display order of the item")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Shopping Item"
        verbose_name_plural = "Shopping Items"
        ordering = ['order', 'created_at']
        indexes = [
            models.Index(fields=['shopping_list', 'checked']),
            models.Index(fields=['shopping_list', 'order']),
        ]

    def __str__(self):
        status = "✓" if self.checked else "○"
        return f"{status} {self.name}"


class TodoList(models.Model):
    """
    Todo lists that can be shared or personal.
    Multiple todo lists per family.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    family = models.ForeignKey(
        Family,
        on_delete=models.CASCADE,
        related_name='todo_lists',
        help_text="The family that owns this todo list"
    )
    name = models.CharField(max_length=200, help_text="Name of the todo list")
    description = models.TextField(blank=True, null=True, help_text="Optional description")
    is_shared = models.BooleanField(default=True, help_text="Whether the list is shared with family")
    color = models.CharField(max_length=20, blank=True, default='blue', help_text="Color theme for the list")
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_todo_lists',
        help_text="User who created this todo list"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Todo List"
        verbose_name_plural = "Todo Lists"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['family', 'is_shared']),
            models.Index(fields=['created_by']),
        ]

    def __str__(self):
        share_status = "Shared" if self.is_shared else "Personal"
        return f"{self.name} ({share_status})"


class TodoTask(models.Model):
    """
    Individual tasks within a todo list.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    todo_list = models.ForeignKey(
        TodoList,
        on_delete=models.CASCADE,
        related_name='tasks',
        help_text="The todo list this task belongs to"
    )
    title = models.CharField(max_length=200, help_text="Title of the task")
    completed = models.BooleanField(default=False, help_text="Whether the task is completed")
    order = models.IntegerField(default=0, help_text="Display order of the task")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Todo Task"
        verbose_name_plural = "Todo Tasks"
        ordering = ['order', 'created_at']
        indexes = [
            models.Index(fields=['todo_list', 'completed']),
            models.Index(fields=['todo_list', 'order']),
        ]

    def __str__(self):
        status = "✓" if self.completed else "○"
        return f"{status} {self.title}"


class Note(models.Model):
    """
    Notes that can be shared or personal.
    Multiple notes per family.
    Rich text content stored as HTML.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    family = models.ForeignKey(
        Family,
        on_delete=models.CASCADE,
        related_name='notes',
        help_text="The family that owns this note"
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_notes',
        help_text="User who created this note"
    )
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name='updated_notes',
        null=True,
        blank=True,
        help_text="User who last updated this note"
    )
    title = models.CharField(max_length=200, help_text="Title of the note")
    content = models.TextField(blank=True, help_text="Rich text content (HTML)")
    is_shared = models.BooleanField(default=False, help_text="Whether the note is shared with family")
    color = models.CharField(max_length=20, blank=True, default='blue', help_text="Color theme for the note")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Note"
        verbose_name_plural = "Notes"
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['family', 'is_shared']),
            models.Index(fields=['family', '-updated_at']),
            models.Index(fields=['created_by']),
        ]

    def __str__(self):
        share_status = "Shared" if self.is_shared else "Personal"
        return f"{self.title} ({share_status})"