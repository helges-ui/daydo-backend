"""
Role-based permission classes for DayDo application.
These permissions enforce the role-based access control defined in the product backlog.
"""
from rest_framework.permissions import BasePermission
from django.core.exceptions import PermissionDenied


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


class CanInviteParentPermission(BasePermission):
    """
    Permission class for inviting parents.
    Allows access to parents and child users with invite permission.
    """
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        if request.user.is_parent:
            return True
        
        if request.user.is_child_user:
            try:
                permissions = request.user.childuserpermissions
                return permissions.can_invite_parent
            except ChildUserPermissions.DoesNotExist:
                return False
        
        return False


class CanDeleteChildProfilePermission(BasePermission):
    """
    Permission class for deleting child profiles.
    Allows access to parents and child users with delete permission.
    """
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        if request.user.is_parent:
            return True
        
        if request.user.is_child_user:
            try:
                permissions = request.user.childuserpermissions
                return permissions.can_delete_child_profile
            except ChildUserPermissions.DoesNotExist:
                return False
        
        return False


class CanCreateTasksPermission(BasePermission):
    """
    Permission class for creating tasks.
    Allows access to parents and child users with create permission.
    """
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        if request.user.is_parent:
            return True
        
        if request.user.is_child_user:
            try:
                permissions = request.user.childuserpermissions
                return permissions.can_create_tasks
            except ChildUserPermissions.DoesNotExist:
                return False
        
        return False


class CanEditTaskDetailsPermission(BasePermission):
    """
    Permission class for editing task details.
    Allows access to parents and child users with edit permission.
    """
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        if request.user.is_parent:
            return True
        
        if request.user.is_child_user:
            try:
                permissions = request.user.childuserpermissions
                return permissions.can_edit_task_details
            except ChildUserPermissions.DoesNotExist:
                return False
        
        return False


class CanAccessAdminSettingsPermission(BasePermission):
    """
    Permission class for accessing admin settings.
    Allows access to parents and child users with admin permission.
    """
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        if request.user.is_parent:
            return True
        
        if request.user.is_child_user:
            try:
                permissions = request.user.childuserpermissions
                return permissions.can_access_admin_settings
            except ChildUserPermissions.DoesNotExist:
                return False
        
        return False


class CanSendMessagesPermission(BasePermission):
    """
    Permission class for sending messages.
    Allows access to parents and child users with message permission.
    """
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        if request.user.is_parent:
            return True
        
        if request.user.is_child_user:
            try:
                permissions = request.user.childuserpermissions
                return permissions.can_send_messages
            except ChildUserPermissions.DoesNotExist:
                return False
        
        return False


class CanViewFamilyCalendarPermission(BasePermission):
    """
    Permission class for viewing family calendar.
    Allows access to parents and child users with calendar permission.
    """
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        if request.user.is_parent:
            return True
        
        if request.user.is_child_user:
            try:
                permissions = request.user.childuserpermissions
                return permissions.can_view_family_calendar
            except ChildUserPermissions.DoesNotExist:
                return False
        
        return False


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
