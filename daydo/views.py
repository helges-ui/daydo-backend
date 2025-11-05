"""
Views for DayDo API endpoints.
These views implement the role-based access control and API endpoints
defined in the product backlog.
"""
from rest_framework import viewsets, status, permissions
from django.db.models import Max
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404
from django.contrib.auth import authenticate
from django.utils import timezone
from datetime import timedelta
from django.http import JsonResponse
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError as DRFValidationError

from .models import User, Family, ChildProfile, ChildUserPermissions, Role, UserRole, Task, Event, EventAssignment, ShoppingList, ShoppingItem, TodoList, TodoTask
from .services.auth_service import AuthService
from .services.dashboard_service import DashboardService
from .serializers import (
    FamilySerializer, UserSerializer, UserRegistrationSerializer,
    ChildProfileSerializer, ChildProfileCreateSerializer,
    ChildUserPermissionsSerializer, LoginSerializer,
    InviteParentSerializer, FamilyMembersSerializer, DashboardSerializer,
    TaskSerializer, EventSerializer, ShoppingListSerializer, ShoppingItemSerializer,
    TodoListSerializer, TodoTaskSerializer
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
        """Register a new parent and create family (US-1) or join existing family via invite token"""
        # Check if family_token is provided (invite link registration)
        family_token = request.data.get('family_token', None)
        family_id = None
        
        if family_token:
            # Decode family token to get family ID
            import base64
            try:
                # Add padding if needed
                padding = 4 - len(family_token) % 4
                if padding != 4:
                    family_token += '=' * padding
                family_id = base64.urlsafe_b64decode(family_token.encode()).decode()
                
                # Verify family exists
                try:
                    family = Family.objects.get(id=family_id)
                except Family.DoesNotExist:
                    return Response(
                        {'error': 'Invalid invite link. Family not found.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            except Exception as e:
                return Response(
                    {'error': 'Invalid invite link token.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        serializer = UserRegistrationSerializer(data=request.data, context={'request': request, 'family_id': family_id})
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
        # Note: select_related() without arguments doesn't work, removed empty call
        return Family.objects.filter(members=self.request.user).prefetch_related(
            'members', 'child_profiles'
        )
    
    @action(detail=False, methods=['post'], url_path='generate-invite-link')
    def generate_invite_link(self, request):
        """Generate an invite link for the user's family"""
        if not request.user.is_parent:
            return Response(
                {'error': 'Only parents can generate invite links.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        family = request.user.family
        # Generate a secure token that includes the family ID
        # Using base64 encoding of family ID for simplicity (can be enhanced with JWT later)
        import base64
        from django.conf import settings
        family_token = base64.urlsafe_b64encode(str(family.id).encode()).decode().rstrip('=')
        
        # Get frontend URL from settings or use request origin
        # Frontend URL should be set in settings.FRONTEND_URL
        frontend_url = getattr(settings, 'FRONTEND_URL', None)
        if not frontend_url:
            # Fallback: try to construct from request
            # In production, this should be set to the Amplify URL
            frontend_url = f"{request.scheme}://{request.get_host()}"
            # Remove /api if present
            if frontend_url.endswith('/api'):
                frontend_url = frontend_url[:-4]
        
        # Create invite link
        invite_link = f"{frontend_url}/register/{family_token}"
        
        return Response({
            'invite_link': invite_link,
            'token': family_token,
            'family_id': str(family.id),
            'family_name': family.name
        }, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['get'])
    def members(self, request, pk=None):
        """Get all family members"""
        family = self.get_object()
        # Optimize queries: select_related for foreign keys, prefetch_related for reverse relations
        members = family.members.select_related('family').prefetch_related(
            'childuserpermissions', 'child_profile'
        ).all()
        serializer = FamilyMembersSerializer(members, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def children(self, request, pk=None):
        """Get all child profiles in the family"""
        family = self.get_object()
        # Optimize queries: select_related for foreign keys, prefetch_related for reverse relations
        children = family.child_profiles.select_related(
            'family', 'manager', 'linked_user'
        ).prefetch_related('linked_user__childuserpermissions').all()
        serializer = ChildProfileSerializer(children, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def current(self, request):
        """Get current user's family info"""
        family = request.user.family
        if not family:
            return Response(
                {'error': 'User has no family assigned'},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = FamilySerializer(family)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def dashboard(self, request, pk=None):
        """Get family dashboard data (US-7)"""
        family = self.get_object()
        
        # Use DashboardService with caching
        dashboard_data = DashboardService.get_family_dashboard(
            family_id=family.id,
            user_id=request.user.id,
            use_cache=True
        )
        
        if dashboard_data is None:
            return Response(
                {'error': 'Family not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = DashboardSerializer(dashboard_data)
        return Response(serializer.data)


class ChildProfileViewSet(viewsets.ModelViewSet):
    """Child profile management endpoints (US-3)"""
    serializer_class = ChildProfileSerializer
    permission_classes = [IsAuthenticated, FamilyMemberPermission]
    
    def get_queryset(self):
        """Return child profiles in the user's family"""
        # Optimize queries: select_related for foreign keys, prefetch_related for reverse relations
        return ChildProfile.objects.filter(
            family=self.request.user.family
        ).select_related('family', 'manager', 'linked_user').prefetch_related(
            'linked_user__childuserpermissions'
        )
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'create':
            return ChildProfileCreateSerializer
        return ChildProfileSerializer
    
    def perform_create(self, serializer):
        """Create child profile with current user as manager"""
        child_profile = serializer.save(
            family=self.request.user.family,
            manager=self.request.user
        )
        # Invalidate dashboard cache when a child is added
        DashboardService.invalidate_cache(self.request.user.family.id, self.request.user.id)
    
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
            # Invalidate dashboard cache when a login account is created
            DashboardService.invalidate_cache(request.user.family.id, request.user.id)
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
        
        # Invalidate dashboard cache when a login account is removed
        DashboardService.invalidate_cache(request.user.family.id, request.user.id)
        
        return Response({
            'message': 'Login account removed successfully'
        }, status=status.HTTP_200_OK)


class ChildUserPermissionsViewSet(viewsets.ModelViewSet):
    """Child user permissions management"""
    serializer_class = ChildUserPermissionsSerializer
    permission_classes = [IsAuthenticated, CanManageFamilyPermission]
    
    def get_queryset(self):
        """Return permissions for child users in the user's family"""
        # Optimize queries: select_related for foreign keys
        return ChildUserPermissions.objects.filter(
            user__family=self.request.user.family,
            user__role='CHILD_USER'
        ).select_related('user', 'user__family')
    
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
        # Optimize queries: select_related for foreign keys, prefetch_related for reverse relations
        return User.objects.filter(
            family=self.request.user.family
        ).select_related('family').prefetch_related('childuserpermissions')
    
    @action(detail=False, methods=['post'], url_path='children')
    def create_child(self, request):
        """Create a child user (no email required)."""
        family = request.user.family
        if not family:
            return Response(
                {'error': 'User has no family assigned'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        data = request.data.copy()
        data['family'] = str(family.id)
        # Ensure email is not required for child - convert empty string to None
        if 'email' in data and (data['email'] == '' or data['email'] is None):
            data['email'] = None
        else:
            data.setdefault('email', None)
        # Remove role from data - it will be set via UserRole relation
        data.pop('role', None)
        
        serializer = UserSerializer(data=data)
        if serializer.is_valid():
            user = serializer.save()
            
            # Assign CHILD role via UserRole relation
            try:
                child_role, _ = Role.objects.get_or_create(
                    key='CHILD',
                    defaults={'name': 'Child'}
                )
                UserRole.objects.create(
                    user=user,
                    role=child_role,
                    assigned_by=request.user
                )
            except Exception as e:
                # If role assignment fails, delete the user and return error
                user.delete()
                return Response(
                    {'error': f'Failed to assign role: {str(e)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def update(self, request, *args, **kwargs):
        """Update user (PATCH/PUT) - Ensure role cannot be updated"""
        # Remove role from data if present (it's read-only)
        if 'role' in request.data:
            request.data.pop('role')
        
        # Ensure user can only update own profile or parent can update any child
        instance = self.get_object()
        if not (request.user == instance or (request.user.is_parent and instance.is_child_user)):
            return Response(
                {'error': 'You do not have permission to update this user.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        return super().update(request, *args, **kwargs)
    
    def partial_update(self, request, *args, **kwargs):
        """Partial update user (PATCH) - Ensure role cannot be updated"""
        # Remove role from data if present (it's read-only)
        if 'role' in request.data:
            request.data.pop('role')
        
        # Ensure user can only update own profile or parent can update any child
        instance = self.get_object()
        if not (request.user == instance or (request.user.is_parent and instance.is_child_user)):
            return Response(
                {'error': 'You do not have permission to update this user.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        return super().partial_update(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        """Delete user - Only parents can delete children, cannot delete last parent"""
        instance = self.get_object()
        
        # Only parents can delete users
        if not request.user.is_parent:
            return Response(
                {'error': 'Only parents can delete users.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Cannot delete yourself
        if request.user == instance:
            return Response(
                {'error': 'You cannot delete your own account.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if deleting last parent in family
        if instance.is_parent:
            family_parents = User.objects.filter(
                family=instance.family,
                user_role__role__key='PARENT'
            ).exclude(id=instance.id)
            
            if not family_parents.exists():
                return Response(
                    {'error': 'Cannot delete the last parent in the family.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # UserRole will be cascade deleted automatically
        return super().destroy(request, *args, **kwargs)
    
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
        
        # Optimize queries: select_related for foreign keys, prefetch_related for reverse relations
        children = family.child_profiles.filter(is_active=True).select_related(
            'family', 'manager', 'linked_user'
        ).prefetch_related('linked_user__childuserpermissions')
        
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


class TaskViewSet(viewsets.ModelViewSet):
    """Task management endpoints"""
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated, FamilyMemberPermission]
    
    def get_queryset(self):
        """Return tasks for the user's family"""
        user = self.request.user
        queryset = Task.objects.filter(family=user.family).select_related(
            'family', 'assigned_to', 'created_by'
        )
        
        # Filter by assigned_to if provided
        assigned_to = self.request.query_params.get('assigned_to', None)
        if assigned_to:
            queryset = queryset.filter(assigned_to_id=assigned_to)
        
        # Filter by date if provided
        date = self.request.query_params.get('date', None)
        if date:
            queryset = queryset.filter(date=date)
        
        # Filter by completed status if provided
        completed = self.request.query_params.get('completed', None)
        if completed is not None:
            completed_bool = completed.lower() == 'true'
            queryset = queryset.filter(completed=completed_bool)
        
        return queryset.order_by('-date', 'title')
    
    def perform_create(self, serializer):
        """Create task with family and created_by from request"""
        serializer.save(
            family=self.request.user.family,
            created_by=self.request.user
        )
    
    @action(detail=True, methods=['post'], url_path='toggle-complete')
    def toggle_complete(self, request, pk=None):
        """Toggle task completion status"""
        task = self.get_object()
        
        # Only the assigned user or a parent can toggle completion
        if task.assigned_to != request.user and not request.user.is_parent:
            return Response(
                {'error': 'You do not have permission to toggle this task.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if task.completed:
            task.mark_incomplete()
        else:
            task.mark_completed()
        
        serializer = self.get_serializer(task)
        return Response(serializer.data)


class EventViewSet(viewsets.ModelViewSet):
    """Event management endpoints"""
    serializer_class = EventSerializer
    permission_classes = [IsAuthenticated, FamilyMemberPermission]
    
    def get_queryset(self):
        """Return events for the user's family"""
        user = self.request.user
        queryset = Event.objects.filter(family=user.family).select_related(
            'family', 'created_by'
        ).prefetch_related('assignments__user')
        
        # Filter by date range if provided
        start_date = self.request.query_params.get('start_date', None)
        end_date = self.request.query_params.get('end_date', None)
        
        if start_date:
            queryset = queryset.filter(start_datetime__gte=start_date)
        if end_date:
            queryset = queryset.filter(start_datetime__lte=end_date)
        
        # Filter by assigned_to if provided
        assigned_to = self.request.query_params.get('assigned_to', None)
        if assigned_to:
            queryset = queryset.filter(assignments__user_id=assigned_to)
        
        return queryset.order_by('start_datetime')
    
    def perform_create(self, serializer):
        """Create event with family and created_by from request"""
        serializer.save(
            family=self.request.user.family,
            created_by=self.request.user
        )


class ShoppingListViewSet(viewsets.ModelViewSet):
    """Shopping list management endpoints"""
    serializer_class = ShoppingListSerializer
    permission_classes = [IsAuthenticated, FamilyMemberPermission]

    def get_queryset(self):
        """Return shopping list for the user's family"""
        user = self.request.user
        # Get or create shopping list for the family
        shopping_list, _ = ShoppingList.objects.get_or_create(family=user.family)
        return ShoppingList.objects.filter(family=user.family).prefetch_related('items')

    def retrieve(self, request, *args, **kwargs):
        """Get shopping list for the family (or create if doesn't exist)"""
        user = request.user
        shopping_list, created = ShoppingList.objects.get_or_create(family=user.family)
        serializer = self.get_serializer(shopping_list)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='current')
    def current(self, request):
        """Get current family's shopping list"""
        user = request.user
        shopping_list, created = ShoppingList.objects.get_or_create(family=user.family)
        serializer = self.get_serializer(shopping_list)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='items')
    def add_item(self, request, pk=None):
        """Add item to shopping list"""
        shopping_list = self.get_object()
        serializer = ShoppingItemSerializer(
            data=request.data,
            context={'request': request, 'shopping_list': shopping_list}
        )
        if serializer.is_valid():
            # Set order based on current max order + 1
            max_order = shopping_list.items.aggregate(
                max_order=Max('order')
            )['max_order'] or 0
            serializer.save(order=max_order + 1)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['patch'], url_path='items/(?P<item_id>[^/.]+)')
    def update_item(self, request, pk=None, item_id=None):
        """Update shopping item"""
        shopping_list = self.get_object()
        item = get_object_or_404(
            ShoppingItem,
            id=item_id,
            shopping_list=shopping_list
        )
        serializer = ShoppingItemSerializer(item, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['delete'], url_path='items/(?P<item_id>[^/.]+)')
    def delete_item(self, request, pk=None, item_id=None):
        """Delete shopping item"""
        shopping_list = self.get_object()
        item = get_object_or_404(
            ShoppingItem,
            id=item_id,
            shopping_list=shopping_list
        )
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'], url_path='items/(?P<item_id>[^/.]+)/toggle')
    def toggle_item(self, request, pk=None, item_id=None):
        """Toggle checked status of shopping item"""
        shopping_list = self.get_object()
        item = get_object_or_404(
            ShoppingItem,
            id=item_id,
            shopping_list=shopping_list
        )
        item.checked = not item.checked
        item.save(update_fields=['checked', 'updated_at'])
        serializer = ShoppingItemSerializer(item)
        return Response(serializer.data)


class TodoListViewSet(viewsets.ModelViewSet):
    """Todo list management endpoints"""
    serializer_class = TodoListSerializer
    permission_classes = [IsAuthenticated, FamilyMemberPermission]

    def get_queryset(self):
        """Return todo lists for the user's family"""
        user = self.request.user
        queryset = TodoList.objects.filter(family=user.family).select_related(
            'family', 'created_by'
        ).prefetch_related('tasks')

        # Filter by is_shared if provided
        is_shared = self.request.query_params.get('is_shared', None)
        if is_shared is not None:
            is_shared_bool = is_shared.lower() == 'true'
            queryset = queryset.filter(is_shared=is_shared_bool)

        return queryset.order_by('-created_at')

    def perform_create(self, serializer):
        """Create todo list with family and created_by from request"""
        serializer.save(
            family=self.request.user.family,
            created_by=self.request.user
        )

    @action(detail=True, methods=['post'], url_path='tasks')
    def add_task(self, request, pk=None):
        """Add task to todo list"""
        todo_list = self.get_object()
        serializer = TodoTaskSerializer(
            data=request.data,
            context={'request': request, 'todo_list': todo_list}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['patch'], url_path='tasks/(?P<task_id>[^/.]+)')
    def update_task(self, request, pk=None, task_id=None):
        """Update todo task"""
        todo_list = self.get_object()
        task = get_object_or_404(
            TodoTask,
            id=task_id,
            todo_list=todo_list
        )
        serializer = TodoTaskSerializer(task, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['delete'], url_path='tasks/(?P<task_id>[^/.]+)')
    def delete_task(self, request, pk=None, task_id=None):
        """Delete todo task"""
        todo_list = self.get_object()
        task = get_object_or_404(
            TodoTask,
            id=task_id,
            todo_list=todo_list
        )
        task.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'], url_path='tasks/(?P<task_id>[^/.]+)/toggle')
    def toggle_task(self, request, pk=None, task_id=None):
        """Toggle completed status of todo task"""
        todo_list = self.get_object()
        task = get_object_or_404(
            TodoTask,
            id=task_id,
            todo_list=todo_list
        )
        task.completed = not task.completed
        task.save(update_fields=['completed', 'updated_at'])
        serializer = TodoTaskSerializer(task)
        return Response(serializer.data)