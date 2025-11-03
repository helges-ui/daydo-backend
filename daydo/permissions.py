"""
Role-based permission classes for DayDo application.
These permissions enforce the role-based access control defined in the product backlog.
"""
from rest_framework.permissions import BasePermission
from django.core.exceptions import PermissionDenied
from daydo.models import ChildUserPermissions


class IsParentPermission(BasePermission):
    """
    Permission class for parent-only actions.
    Allows access only to authenticated users with PARENT role.
    """
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_parent


class IsChildUserPermission(BasePermission):
    """
    Permission class for child user actions.
    Allows access only to authenticated users with CHILD_USER role.
    """
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_child_user


class CanManageFamilyPermission(BasePermission):
    """
    Permission class for family management actions.
    Allows access only to users who can manage family settings (parents).
    """
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.can_manage_family()


class CanAssignTasksPermission(BasePermission):
    """
    Permission class for task assignment actions.
    Allows access only to users who can assign tasks (parents).
    """
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.can_assign_tasks()


class FamilyMemberPermission(BasePermission):
    """
    Permission class for family member actions.
    Allows access only to authenticated users who belong to the same family.
    """
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Get family from URL or request
        family_id = view.kwargs.get('family_id')
        if family_id:
            return str(request.user.family.id) == str(family_id)
        
        return True  # If no family_id in URL, allow access


class BaseChildPermission(BasePermission):
    """
    Base permission class for child user permissions.
    Allows access to parents and child users with specific permission.
    
    Subclasses must set the 'permission_field' attribute to specify
    which permission field to check in ChildUserPermissions.
    """
    permission_field = None  # Must be set by subclasses
    
    def has_permission(self, request, view):
        """Check if user has permission based on role and permission field"""
        if not request.user.is_authenticated:
            return False
        
        # Parents always have access
        if request.user.is_parent:
            return True
        
        # Child users need specific permission
        if request.user.is_child_user:
            try:
                permissions = request.user.childuserpermissions
                return getattr(permissions, self.permission_field, False)
            except ChildUserPermissions.DoesNotExist:
                return False
        
        return False


class CanInviteParentPermission(BaseChildPermission):
    """
    Permission class for inviting parents.
    Allows access to parents and child users with invite permission.
    """
    permission_field = 'can_invite_parent'


class CanDeleteChildProfilePermission(BaseChildPermission):
    """
    Permission class for deleting child profiles.
    Allows access to parents and child users with delete permission.
    """
    permission_field = 'can_delete_child_profile'


class CanCreateTasksPermission(BaseChildPermission):
    """
    Permission class for creating tasks.
    Allows access to parents and child users with create permission.
    """
    permission_field = 'can_create_tasks'


class CanEditTaskDetailsPermission(BaseChildPermission):
    """
    Permission class for editing task details.
    Allows access to parents and child users with edit permission.
    """
    permission_field = 'can_edit_task_details'


class CanAccessAdminSettingsPermission(BaseChildPermission):
    """
    Permission class for accessing admin settings.
    Allows access to parents and child users with admin permission.
    """
    permission_field = 'can_access_admin_settings'


class CanSendMessagesPermission(BaseChildPermission):
    """
    Permission class for sending messages.
    Allows access to parents and child users with message permission.
    """
    permission_field = 'can_send_messages'


class CanViewFamilyCalendarPermission(BaseChildPermission):
    """
    Permission class for viewing family calendar.
    Allows access to parents and child users with calendar permission.
    """
    permission_field = 'can_view_family_calendar'


class IsOwnerOrParentPermission(BasePermission):
    """
    Permission class for actions that require ownership or parent access.
    Allows access if user owns the resource or is a parent in the same family.
    """
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Parents can access anything in their family
        if request.user.is_parent:
            return True
        
        # Child users can only access their own resources
        return request.user.is_child_user
    
    def has_object_permission(self, request, view, obj):
        """
        Check if user has permission to access the specific object.
        Override this method in views that use this permission.
        """
        if request.user.is_parent:
            return True
        
        if request.user.is_child_user:
            # Check if the object belongs to the user
            if hasattr(obj, 'user'):
                return obj.user == request.user
            elif hasattr(obj, 'assigned_to'):
                return obj.assigned_to == request.user
            elif hasattr(obj, 'created_by'):
                return obj.created_by == request.user
        
        return False
