"""
Django admin configuration for DayDo models.
This provides an admin interface for managing users, families, and child profiles.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html

from .models import User, Family, ChildProfile, ChildUserPermissions


@admin.register(Family)
class FamilyAdmin(admin.ModelAdmin):
    """Admin interface for Family model"""
    list_display = ['name', 'created_at', 'members_count', 'children_count']
    list_filter = ['created_at']
    search_fields = ['name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    def members_count(self, obj):
        """Display count of family members"""
        return obj.members.count()
    members_count.short_description = 'Members'
    
    def children_count(self, obj):
        """Display count of child profiles"""
        return obj.child_profiles.count()
    children_count.short_description = 'Children'


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin interface for custom User model"""
    list_display = ['username', 'email', 'first_name', 'last_name', 'role', 'family', 'is_active']
    list_filter = ['role', 'is_active', 'family', 'created_at']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('DayDo Information', {
            'fields': ('family', 'role', 'phone_number', 'avatar', 'id', 'created_at', 'updated_at')
        }),
    )
    
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('DayDo Information', {
            'fields': ('family', 'role', 'phone_number', 'avatar')
        }),
    )


@admin.register(ChildProfile)
class ChildProfileAdmin(admin.ModelAdmin):
    """Admin interface for ChildProfile model"""
    list_display = ['first_name', 'last_name', 'family', 'is_view_only', 'has_login_account', 'manager', 'is_active']
    list_filter = ['is_view_only', 'is_active', 'family', 'created_at']
    search_fields = ['first_name', 'last_name', 'family__name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('first_name', 'last_name', 'family', 'avatar', 'birth_date')
        }),
        ('Account Settings', {
            'fields': ('is_view_only', 'linked_user', 'manager')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('System Information', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def has_login_account(self, obj):
        """Display if child has login account"""
        if obj.has_login_account:
            return format_html('<span style="color: green;">✓ Yes</span>')
        return format_html('<span style="color: red;">✗ No</span>')
    has_login_account.short_description = 'Has Login Account'


@admin.register(ChildUserPermissions)
class ChildUserPermissionsAdmin(admin.ModelAdmin):
    """Admin interface for ChildUserPermissions model"""
    list_display = ['user', 'user_family', 'can_invite_parent', 'can_delete_child_profile', 'can_access_admin_settings']
    list_filter = ['can_invite_parent', 'can_delete_child_profile', 'can_access_admin_settings', 'can_create_tasks']
    search_fields = ['user__username', 'user__first_name', 'user__last_name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Family Management Permissions', {
            'fields': ('can_invite_parent', 'can_delete_child_profile', 'can_access_admin_settings')
        }),
        ('Task Management Permissions', {
            'fields': ('can_delete_all_tasks', 'can_create_tasks', 'can_edit_task_details')
        }),
        ('Communication Permissions', {
            'fields': ('can_send_messages', 'can_view_family_calendar')
        }),
        ('System Information', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def user_family(self, obj):
        """Display user's family"""
        return obj.user.family.name
    user_family.short_description = 'Family'


# Customize admin site
admin.site.site_header = "DayDo Administration"
admin.site.site_title = "DayDo Admin"
admin.site.index_title = "Welcome to DayDo Administration"