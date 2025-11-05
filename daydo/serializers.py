"""
Serializers for DayDo API endpoints.
These serializers handle the serialization and deserialization of data
for the role-based user management system.
"""
from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import User, Family, ChildProfile, ChildUserPermissions, UserRole, Role


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
        user = User.objects.create_user(**validated_data)
        if password:
            user.set_password(password)
            user.save()
        return user
    
    def update(self, instance, validated_data):
        """Update user instance"""
        password = validated_data.pop('password', None)
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
        """Create new user and family"""
        password = validated_data.pop('password')
        password_confirm = validated_data.pop('password_confirm')
        family_name = validated_data.pop('family_name')
        
        # Create family first
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
