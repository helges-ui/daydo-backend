"""
Views for DayDo API endpoints.
These views implement the role-based access control and API endpoints
defined in the product backlog.
"""
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404
from django.contrib.auth import authenticate
from django.utils import timezone
from datetime import timedelta
from django.http import JsonResponse

from .models import User, Family, ChildProfile, ChildUserPermissions
from .services.auth_service import AuthService
from .serializers import (
    FamilySerializer, UserSerializer, UserRegistrationSerializer,
    ChildProfileSerializer, ChildProfileCreateSerializer,
    ChildUserPermissionsSerializer, LoginSerializer,
    InviteParentSerializer, FamilyMembersSerializer, DashboardSerializer
)
from .permissions import (
    IsParentPermission, IsChildUserPermission, CanManageFamilyPermission,
    CanAssignTasksPermission, FamilyMemberPermission, CanInviteParentPermission,
    CanDeleteChildProfilePermission, CanCreateTasksPermission,
    CanEditTaskDetailsPermission, CanAccessAdminSettingsPermission,
    CanSendMessagesPermission, CanViewFamilyCalendarPermission,
    IsOwnerOrParentPermission
)


class AuthenticationViewSet(viewsets.ViewSet):
    """Authentication endpoints for user registration and login"""
    
    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def register(self, request):
        """Register a new parent and create family (US-1)"""
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response(
                AuthService.create_auth_response(user, 'User registered successfully'),
                status=status.HTTP_201_CREATED
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def login(self, request):
        """Login user and return JWT tokens"""
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            return Response(
                AuthService.create_auth_response(user, 'Login successful'),
                status=status.HTTP_200_OK
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated, CanInviteParentPermission])
    def invite_parent(self, request):
        """Invite another parent to join the family (US-2)"""
        serializer = InviteParentSerializer(data=request.data)
        if serializer.is_valid():
            # In a real implementation, you would send an email invitation
            # For now, we'll just return success
            return Response({
                'message': 'Parent invitation sent successfully',
                'invited_email': serializer.validated_data['email']
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class FamilyViewSet(viewsets.ModelViewSet):
    """Family management endpoints"""
    serializer_class = FamilySerializer
    permission_classes = [IsAuthenticated, CanManageFamilyPermission]
    
    def get_queryset(self):
        """Return families that the user belongs to"""
        return Family.objects.filter(members=self.request.user)
    
    @action(detail=True, methods=['get'])
    def members(self, request, pk=None):
        """Get all family members"""
        family = self.get_object()
        members = family.members.all()
        serializer = FamilyMembersSerializer(members, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def children(self, request, pk=None):
        """Get all child profiles in the family"""
        family = self.get_object()
        children = family.child_profiles.all()
        serializer = ChildProfileSerializer(children, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def dashboard(self, request, pk=None):
        """Get family dashboard data (US-7)"""
        family = self.get_object()
        
        # Calculate dashboard metrics
        total_members = family.members.count()
        total_children = family.child_profiles.count()
        children_with_accounts = family.child_profiles.filter(
            is_view_only=False, linked_user__isnull=False
        ).count()
        children_view_only = family.child_profiles.filter(is_view_only=True).count()
        
        # Recent activity (placeholder for now)
        recent_activity = []
        
        dashboard_data = {
            'family_name': family.name,
            'total_members': total_members,
            'total_children': total_children,
            'children_with_accounts': children_with_accounts,
            'children_view_only': children_view_only,
            'recent_activity': recent_activity
        }
        
        serializer = DashboardSerializer(dashboard_data)
        return Response(serializer.data)


class ChildProfileViewSet(viewsets.ModelViewSet):
    """Child profile management endpoints (US-3)"""
    serializer_class = ChildProfileSerializer
    permission_classes = [IsAuthenticated, FamilyMemberPermission]
    
    def get_queryset(self):
        """Return child profiles in the user's family"""
        return ChildProfile.objects.filter(family=self.request.user.family)
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'create':
            return ChildProfileCreateSerializer
        return ChildProfileSerializer
    
    def perform_create(self, serializer):
        """Create child profile with current user as manager"""
        serializer.save(
            family=self.request.user.family,
            manager=self.request.user
        )
    
    @action(detail=True, methods=['post'])
    def create_login_account(self, request, pk=None):
        """Convert CHILD_VIEW to CHILD_USER by creating login account"""
        child_profile = self.get_object()
        
        if child_profile.has_login_account:
            return Response(
                {'error': 'Child already has a login account'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        username = request.data.get('username')
        password = request.data.get('password')
        
        if not password:
            return Response(
                {'error': 'Password is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = child_profile.create_login_account(username=username, password=password)
            return Response({
                'message': 'Login account created successfully',
                'user': UserSerializer(user).data
            }, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['delete'])
    def remove_login_account(self, request, pk=None):
        """Convert CHILD_USER back to CHILD_VIEW by removing login account"""
        child_profile = self.get_object()
        
        if not child_profile.has_login_account:
            return Response(
                {'error': 'Child does not have a login account'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Remove the linked user
        linked_user = child_profile.linked_user
        child_profile.linked_user = None
        child_profile.is_view_only = True
        child_profile.save()
        
        # Delete the user account
        linked_user.delete()
        
        return Response({
            'message': 'Login account removed successfully'
        }, status=status.HTTP_200_OK)


class ChildUserPermissionsViewSet(viewsets.ModelViewSet):
    """Child user permissions management"""
    serializer_class = ChildUserPermissionsSerializer
    permission_classes = [IsAuthenticated, CanManageFamilyPermission]
    
    def get_queryset(self):
        """Return permissions for child users in the user's family"""
        return ChildUserPermissions.objects.filter(
            user__family=self.request.user.family,
            user__role='CHILD_USER'
        )
    
    def get_object(self):
        """Get specific permission object"""
        queryset = self.get_queryset()
        obj = get_object_or_404(queryset, pk=self.kwargs['pk'])
        return obj


class UserViewSet(viewsets.ModelViewSet):
    """User management endpoints"""
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, FamilyMemberPermission]
    
    def get_queryset(self):
        """Return users in the same family"""
        return User.objects.filter(family=self.request.user.family)
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get current user profile"""
        serializer = UserSerializer(request.user)
        return Response(serializer.data)
    
    @action(detail=False, methods=['put'])
    def update_profile(self, request):
        """Update current user profile"""
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def permissions(self, request, pk=None):
        """Get permissions for a child user"""
        user = self.get_object()
        
        if not user.is_child_user:
            return Response(
                {'error': 'User is not a child user'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            permissions = user.childuserpermissions
            serializer = ChildUserPermissionsSerializer(permissions)
            return Response(serializer.data)
        except ChildUserPermissions.DoesNotExist:
            return Response(
                {'error': 'Permissions not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )


class DashboardView(APIView):
    """Dashboard view for monitoring child progress (US-7)"""
    permission_classes = [IsAuthenticated, FamilyMemberPermission]
    
    def get(self, request):
        """Get dashboard data with children's progress"""
        family = request.user.family
        
        # Get all children in the family
        children = family.child_profiles.filter(is_active=True)
        
        children_progress = []
        for child in children:
            # For now, we'll return placeholder data
            # In the future, this will include actual task data
            children_progress.append({
                'child_id': str(child.id),
                'name': child.get_display_name(),
                'progress': "0/0",  # Placeholder: completed/total tasks
                'tasks': [],  # Placeholder: list of tasks
                'has_login_account': child.has_login_account,
                'avatar': child.avatar
            })
        
        return Response({
            'family_name': family.name,
            'timestamp': timezone.now().isoformat(),
            'children': children_progress
        })


class HealthCheckView(APIView):
    """Simple health check endpoint returning 200 OK for load balancer checks"""

    authentication_classes = []
    permission_classes = []

    def get(self, request):
        return JsonResponse({'status': 'ok'}, status=200)