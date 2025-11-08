"""
URL configuration for DayDo API endpoints.
This file defines the URL patterns for all API endpoints
based on the product backlog requirements.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    AuthenticationViewSet, FamilyViewSet, ChildProfileViewSet,
    ChildUserPermissionsViewSet, UserViewSet, DashboardView, HealthCheckView,
    TaskViewSet, EventViewSet, ShoppingListViewSet, TodoListViewSet, NoteViewSet,
    LocationViewSet, GeofenceViewSet,
)

# Create router for ViewSets
router = DefaultRouter()
router.register(r'auth', AuthenticationViewSet, basename='auth')
router.register(r'family', FamilyViewSet, basename='family')
router.register(r'children', ChildProfileViewSet, basename='children')
router.register(r'permissions', ChildUserPermissionsViewSet, basename='permissions')
router.register(r'users', UserViewSet, basename='users')
router.register(r'tasks', TaskViewSet, basename='tasks')
router.register(r'events', EventViewSet, basename='events')
router.register(r'shopping-lists', ShoppingListViewSet, basename='shopping-lists')
router.register(r'todo-lists', TodoListViewSet, basename='todo-lists')
router.register(r'notes', NoteViewSet, basename='notes')
router.register(r'location', LocationViewSet, basename='location')
router.register(r'geofences', GeofenceViewSet, basename='geofence')

app_name = 'daydo'

urlpatterns = [
    # JWT Token endpoints
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Dashboard endpoint
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    # Health check endpoint
    path('health/', HealthCheckView.as_view(), name='health'),
    
    # Include router URLs
    path('', include(router.urls)),
]
