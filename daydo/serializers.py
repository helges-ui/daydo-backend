"""
Serializers for DayDo API endpoints.
These serializers handle the serialization and deserialization of data
for the role-based user management system.
"""
from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db.models import Max
from .models import User, Family, ChildProfile, ChildUserPermissions, UserRole, Role, Task, Event, EventAssignment, ShoppingList, ShoppingItem, TodoList, TodoTask, Note


class FamilySerializer(serializers.ModelSerializer):
    """Serializer for Family model"""
    members_count = serializers.SerializerMethodField()
    children_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Family
        fields = [
            'id', 'name', 'created_at', 'updated_at', 
            'members_count', 'children_count'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_members_count(self, obj):
        """Get total number of family members"""
        return obj.members.count()
    
    def get_children_count(self, obj):
        """Get total number of child profiles"""
        return obj.child_profiles.count()


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model"""
    # Expose role as read-only string from relation (fallback to legacy field)
    role = serializers.SerializerMethodField(read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    family_name = serializers.CharField(source='family.name', read_only=True)
    display_name = serializers.CharField(source='get_display_name', read_only=True)
    password = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 
            'role', 'role_display', 'family', 'family_name', 
            'phone_number', 'avatar', 'color', 'is_active', 'display_name',
            'created_at', 'password'
        ]
        read_only_fields = ['id', 'created_at', 'role']
        extra_kwargs = {
            'password': {'write_only': True, 'required': False}
        }
    
    def create(self, validated_data):
        """Create a new user with hashed password"""
        password = validated_data.pop('password', None)
        # Remove role from validated_data - it's set via UserRole relation
        validated_data.pop('role', None)
        # Convert empty email string to None to avoid unique constraint violation
        # Django's create_user normalizes None to empty string, so we need to use create() directly
        email = validated_data.pop('email', None)
        if email == '' or email is None:
            email = None
        
        # Create user directly using create() to avoid Django's email normalization
        # This allows us to set email=None explicitly
        if email is None:
            # Use create() directly to set email=None (not empty string)
            user = User.objects.create(email=None, **validated_data)
        else:
            # Use create_user for users with email
            user = User.objects.create_user(email=email, **validated_data)
        
        if password:
            user.set_password(password)
            user.save()
        
        return user
    
    def update(self, instance, validated_data):
        """Update user instance"""
        password = validated_data.pop('password', None)
        # Remove role from validated_data - it's read-only
        validated_data.pop('role', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        if password:
            instance.set_password(password)
        
        instance.save()
        return instance

    def get_role(self, obj):
        # Prefer relational role
        try:
            if hasattr(obj, 'user_role') and obj.user_role and obj.user_role.role:
                return obj.user_role.role.key
        except Exception:
            pass
        # Fallback to legacy char field
        return obj.role


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration"""
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    family_name = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = [
            'username', 'email', 'first_name', 'last_name', 
            'password', 'password_confirm', 'family_name',
            'phone_number', 'avatar', 'color'
        ]
    
    def validate(self, attrs):
        """Validate registration data"""
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords don't match")
        
        return attrs
    
    def create(self, validated_data):
        """Create new user and family (or join existing family if family_id provided)"""
        password = validated_data.pop('password')
        password_confirm = validated_data.pop('password_confirm')
        family_name = validated_data.pop('family_name', '')
        
        # Check if family_id was passed in context (for invite links)
        family_id = self.context.get('family_id', None)
        
        if family_id:
            # Join existing family (invite link registration)
            try:
                family = Family.objects.get(id=family_id)
            except Family.DoesNotExist:
                raise serializers.ValidationError("Family not found")
        else:
            # Create new family (normal registration)
            if not family_name:
                raise serializers.ValidationError({"family_name": "Family name is required for new registrations"})
            family = Family.objects.create(name=family_name)
        
        # Create user
        user = User.objects.create_user(
            family=family,
            password=password,
            **validated_data
        )
        # Assign role via relation
        role_obj, _ = Role.objects.get_or_create(key='PARENT', defaults={'name': 'Parent'})
        UserRole.objects.create(user=user, role=role_obj)
        
        return user


class ChildProfileSerializer(serializers.ModelSerializer):
    """Serializer for ChildProfile model"""
    full_name = serializers.CharField(read_only=True)
    has_login_account = serializers.BooleanField(read_only=True)
    manager_name = serializers.CharField(source='manager.get_display_name', read_only=True)
    linked_username = serializers.CharField(source='linked_user.username', read_only=True)
    
    class Meta:
        model = ChildProfile
        fields = [
            'id', 'first_name', 'last_name', 'full_name', 'family',
            'is_view_only', 'linked_user', 'linked_username', 'manager', 'manager_name',
            'avatar', 'color', 'birth_date', 'is_active', 'has_login_account',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'manager']
    
    def create(self, validated_data):
        """Create child profile with current user as manager"""
        validated_data['manager'] = self.context['request'].user
        return super().create(validated_data)


class ChildProfileCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating child profiles"""
    create_login_account = serializers.BooleanField(write_only=True, default=False)
    username = serializers.CharField(write_only=True, required=False)
    password = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = ChildProfile
        fields = [
            'first_name', 'last_name', 'avatar', 'color', 'birth_date',
            'create_login_account', 'username', 'password'
        ]
    
    def create(self, validated_data):
        """Create child profile and optionally login account"""
        create_login_account = validated_data.pop('create_login_account', False)
        username = validated_data.pop('username', None)
        password = validated_data.pop('password', None)
        
        # Create child profile
        child_profile = ChildProfile.objects.create(
            family=self.context['request'].user.family,
            manager=self.context['request'].user,
            **validated_data
        )
        
        # Create login account if requested
        if create_login_account:
            if not username:
                username = f"{child_profile.first_name.lower()}_{child_profile.family.name.lower()}"
            
            if not password:
                raise serializers.ValidationError("Password is required when creating login account")
            
            child_profile.create_login_account(username=username, password=password)
        
        return child_profile


class ChildUserPermissionsSerializer(serializers.ModelSerializer):
    """Serializer for ChildUserPermissions model"""
    username = serializers.CharField(source='user.username', read_only=True)
    user_display_name = serializers.CharField(source='user.get_display_name', read_only=True)
    
    class Meta:
        model = ChildUserPermissions
        fields = [
            'user', 'username', 'user_display_name',
            'can_invite_parent', 'can_delete_child_profile', 'can_access_admin_settings',
            'can_delete_all_tasks', 'can_create_tasks', 'can_edit_task_details',
            'can_send_messages', 'can_view_family_calendar',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['user', 'created_at', 'updated_at']


class LoginSerializer(serializers.Serializer):
    """Serializer for user login"""
    username = serializers.CharField()
    password = serializers.CharField()
    
    def validate(self, attrs):
        """Validate login credentials"""
        username = attrs.get('username')
        password = attrs.get('password')
        
        if username and password:
            user = authenticate(username=username, password=password)
            if not user:
                raise serializers.ValidationError('Invalid credentials')
            if not user.is_active:
                raise serializers.ValidationError('User account is disabled')
            attrs['user'] = user
        else:
            raise serializers.ValidationError('Must include username and password')
        
        return attrs


class InviteParentSerializer(serializers.Serializer):
    """Serializer for inviting parents"""
    email = serializers.EmailField()
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    message = serializers.CharField(max_length=500, required=False)
    
    def validate_email(self, value):
        """Validate that email is not already registered"""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('User with this email already exists')
        return value


class FamilyMembersSerializer(serializers.ModelSerializer):
    """Serializer for family members list"""
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    display_name = serializers.CharField(source='get_display_name', read_only=True)
    child_profile = ChildProfileSerializer(read_only=True)
    permissions = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'role', 'role_display', 'display_name', 'avatar', 'color',
            'is_active', 'created_at', 'child_profile', 'permissions'
        ]
    
    def get_permissions(self, obj):
        """Get permissions for child users"""
        if obj.is_child_user:
            try:
                permissions = obj.childuserpermissions
                return ChildUserPermissionsSerializer(permissions).data
            except ChildUserPermissions.DoesNotExist:
                return None
        return None


class DashboardSerializer(serializers.Serializer):
    """Serializer for dashboard data"""
    family_name = serializers.CharField()
    total_members = serializers.IntegerField()
    total_children = serializers.IntegerField()
    children_with_accounts = serializers.IntegerField()
    children_view_only = serializers.IntegerField()
    recent_activity = serializers.ListField(child=serializers.DictField())
    
    class Meta:
        fields = [
            'family_name', 'total_members', 'total_children',
            'children_with_accounts', 'children_view_only', 'recent_activity'
        ]


class TaskSerializer(serializers.ModelSerializer):
    """Serializer for Task model"""
    assigned_to_name = serializers.CharField(source='assigned_to.get_display_name', read_only=True)
    assigned_to_avatar = serializers.CharField(source='assigned_to.avatar', read_only=True)
    assigned_to_color = serializers.CharField(source='assigned_to.color', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_display_name', read_only=True)
    
    class Meta:
        model = Task
        fields = [
            'id', 'family', 'assigned_to', 'assigned_to_name', 'assigned_to_avatar', 
            'assigned_to_color', 'title', 'description', 'date', 'completed', 
            'completed_at', 'points', 'icon', 'created_by', 'created_by_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'family', 'created_by', 'created_at', 'updated_at', 'completed_at']
    
    def create(self, validated_data):
        """Create task with family and created_by from request context"""
        request = self.context.get('request')
        if request and request.user:
            validated_data['family'] = request.user.family
            validated_data['created_by'] = request.user
        return super().create(validated_data)


class EventSerializer(serializers.ModelSerializer):
    """Serializer for Event model"""
    assigned_to = serializers.SerializerMethodField()
    assigned_to_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=User.objects.all(),
        write_only=True,
        required=False
    )
    created_by_name = serializers.CharField(source='created_by.get_display_name', read_only=True)
    
    def to_internal_value(self, data):
        """Handle assigned_to field (list of IDs) and convert to assigned_to_ids"""
        # Make a mutable copy if needed
        if hasattr(data, '_mutable'):
            data = data.copy()
        elif isinstance(data, dict):
            data = data.copy()
        
        if 'assigned_to' in data and 'assigned_to_ids' not in data:
            # Convert assigned_to (list of IDs) to assigned_to_ids
            # PrimaryKeyRelatedField will handle the conversion from IDs to User objects
            assigned_to_ids = data.get('assigned_to', [])
            if assigned_to_ids:
                data['assigned_to_ids'] = assigned_to_ids
            # Remove assigned_to from data since it's read-only
            data.pop('assigned_to', None)
        return super().to_internal_value(data)
    
    class Meta:
        model = Event
        fields = [
            'id', 'family', 'title', 'description', 'start_datetime', 'end_datetime',
            'location', 'reminder_minutes', 'recurrence_rule', 'created_by', 
            'created_by_name', 'assigned_to', 'assigned_to_ids', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'family', 'created_by', 'created_at', 'updated_at']
    
    def get_assigned_to(self, obj):
        """Get list of assigned user IDs"""
        return [assignment.user.id for assignment in obj.assignments.all()]
    
    def create(self, validated_data):
        """Create event with family and created_by from request context"""
        request = self.context.get('request')
        assigned_user_ids = validated_data.pop('assigned_to_ids', [])
        
        if request and request.user:
            validated_data['family'] = request.user.family
            validated_data['created_by'] = request.user
        
        event = super().create(validated_data)
        
        # Create event assignments
        for user in assigned_user_ids:
            EventAssignment.objects.create(event=event, user=user)
        
        return event
    
    def update(self, instance, validated_data):
        """Update event and assignments"""
        # Get assigned_user_ids (converted from assigned_to in to_internal_value if needed)
        assigned_user_ids = validated_data.pop('assigned_to_ids', None)
        
        # Update event fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update assignments if provided
        if assigned_user_ids is not None:
            # Clear existing assignments
            instance.assignments.all().delete()
            # Create new assignments
            for user in assigned_user_ids:
                EventAssignment.objects.create(event=instance, user=user)
        
        return instance


class ShoppingItemSerializer(serializers.ModelSerializer):
    """Serializer for ShoppingItem model"""
    
    class Meta:
        model = ShoppingItem
        fields = [
            'id', 'shopping_list', 'name', 'checked', 'order',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'shopping_list', 'created_at', 'updated_at']

    def create(self, validated_data):
        """Create shopping item with shopping_list from request context"""
        request = self.context.get('request')
        shopping_list = self.context.get('shopping_list')
        
        if shopping_list:
            validated_data['shopping_list'] = shopping_list
        
        return super().create(validated_data)


class ShoppingListSerializer(serializers.ModelSerializer):
    """Serializer for ShoppingList model"""
    items = ShoppingItemSerializer(many=True, read_only=True)
    items_count = serializers.SerializerMethodField()
    unchecked_items_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ShoppingList
        fields = [
            'id', 'family', 'items', 'items_count', 'unchecked_items_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'family', 'created_at', 'updated_at']
    
    def get_items_count(self, obj):
        """Get total number of items"""
        return obj.items.count()
    
    def get_unchecked_items_count(self, obj):
        """Get number of unchecked items"""
        return obj.items.filter(checked=False).count()


class TodoTaskSerializer(serializers.ModelSerializer):
    """Serializer for TodoTask model"""
    
    class Meta:
        model = TodoTask
        fields = [
            'id', 'todo_list', 'title', 'completed', 'order',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'todo_list', 'created_at', 'updated_at']

    def create(self, validated_data):
        """Create todo task with todo_list from request context"""
        todo_list = self.context.get('todo_list')
        
        if todo_list:
            validated_data['todo_list'] = todo_list
        
        # Set order based on current max order + 1
        if 'order' not in validated_data or validated_data.get('order') == 0:
            max_order = todo_list.tasks.aggregate(
                max_order=Max('order')
            )['max_order'] or 0
            validated_data['order'] = max_order + 1
        
        return super().create(validated_data)


class TodoListSerializer(serializers.ModelSerializer):
    """Serializer for TodoList model"""
    tasks = TodoTaskSerializer(many=True, read_only=True)
    tasks_count = serializers.SerializerMethodField()
    completed_count = serializers.SerializerMethodField()
    created_by_name = serializers.CharField(source='created_by.get_display_name', read_only=True)
    
    class Meta:
        model = TodoList
        fields = [
            'id', 'family', 'name', 'description', 'is_shared', 'color',
            'created_by', 'created_by_name', 'tasks', 'tasks_count', 'completed_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'family', 'created_by', 'created_at', 'updated_at']
    
    def get_tasks_count(self, obj):
        """Get total number of tasks"""
        return obj.tasks.count()
    
    def get_completed_count(self, obj):
        """Get number of completed tasks"""
        return obj.tasks.filter(completed=True).count()


class NoteSerializer(serializers.ModelSerializer):
    """Serializer for Note model"""
    created_by_name = serializers.CharField(source='created_by.get_display_name', read_only=True)
    updated_by_name = serializers.CharField(source='updated_by.get_display_name', read_only=True)
    
    class Meta:
        model = Note
        fields = [
            'id', 'family', 'created_by', 'created_by_name',
            'updated_by', 'updated_by_name', 'title', 'content',
            'is_shared', 'color', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'family', 'created_by', 'updated_by', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        """Create note with family and created_by from request context"""
        request = self.context.get('request')
        if request and request.user:
            validated_data['family'] = request.user.family
            validated_data['created_by'] = request.user
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        """Update note and set updated_by"""
        request = self.context.get('request')
        if request and request.user:
            validated_data['updated_by'] = request.user
        return super().update(instance, validated_data)
