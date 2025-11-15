# Code Refactoring Suggestions for DayDo2Backend

## Overview
This document outlines refactoring suggestions to improve code quality, maintainability, and scalability. It includes a comprehensive analysis of the codebase and a step-by-step implementation guide.

---

## 1. **Views (views.py) - Code Duplication & Separation of Concerns**

### Issues:
- **Duplicate JWT token generation logic** (lines 46-47, 68-69) - ✅ Already addressed in AuthService
- **Repeated error response patterns** throughout views
- **LocationViewSet.family_locations() is too long** (178 lines, 1168-1346) with massive code duplication
- **Duplicate sharing status processing logic** (lines 1201-1215 and 1278-1292)
- **Duplicate payload building logic** (lines 1226-1259 and 1310-1343)
- **Legacy endpoints** in LocationViewSet (lines 990-1030) should be removed or deprecated

### Suggestions:

#### 1.1 Extract Location Service
```python
# Create: daydo/services/location_service.py
class LocationService:
    """Service for location-related business logic"""
    
    STALE_THRESHOLD_MINUTES = 5
    
    @staticmethod
    def process_sharing_status(sharing_status):
        """Process sharing status and handle expiration"""
        if not sharing_status:
            return {
                'is_sharing_live': False,
                'sharing_type': None,
                'expires_at': None,
                'started_at': None,
                'updated_at': None,
            }
        
        # Handle expiration
        if sharing_status.sharing_type == 'temporary' and sharing_status.is_expired():
            if sharing_status.is_sharing_live:
                sharing_status.is_sharing_live = False
                sharing_status.save(update_fields=['is_sharing_live', 'updated_at'])
            is_sharing_live = False
        else:
            is_sharing_live = sharing_status.is_sharing_live
        
        # One-time sharing is never "live"
        if sharing_status.sharing_type == 'one-time':
            is_sharing_live = False
        
        return {
            'is_sharing_live': is_sharing_live,
            'sharing_type': sharing_status.sharing_type,
            'expires_at': sharing_status.expires_at,
            'started_at': sharing_status.started_at,
            'updated_at': sharing_status.updated_at,
        }
    
    @staticmethod
    def build_location_payload(user_data, location_data, geofence_match, stale_threshold):
        """Build standardized location payload"""
        if geofence_match:
            return {
                'user_id': str(user_data['id']),
                'user_name': user_data['name'],
                'user_avatar': user_data.get('avatar'),
                'user_color': user_data.get('color'),
                'latitude': None,
                'longitude': None,
                'timestamp': location_data.get('timestamp'),
                'location_label': geofence_match.name,
                'geofence_id': str(geofence_match.id),
                'within_geofence': True,
                'accuracy': None,
                'is_stale': False,
            }
        else:
            return {
                'user_id': str(user_data['id']),
                'user_name': user_data['name'],
                'user_avatar': user_data.get('avatar'),
                'user_color': user_data.get('color'),
                'latitude': location_data.get('latitude'),
                'longitude': location_data.get('longitude'),
                'timestamp': location_data.get('timestamp'),
                'location_label': None,
                'geofence_id': None,
                'within_geofence': False,
                'accuracy': location_data.get('accuracy'),
                'is_stale': location_data.get('timestamp') and 
                           location_data['timestamp'] < stale_threshold,
            }
    
    @staticmethod
    def get_family_locations(family):
        """Get all family locations with optimized queries"""
        # Extract the complex logic from family_locations method
        # Returns list of location payloads
        pass
```

**Impact:** Reduces `family_locations` method from 178 lines to ~30 lines.

#### 1.2 Extract Error Response Helper
```python
# Create: daydo/utils/response_helpers.py
from rest_framework import status
from rest_framework.response import Response

class ResponseHelper:
    @staticmethod
    def error_response(message, status_code=status.HTTP_400_BAD_REQUEST, errors=None):
        """Create standardized error response"""
        response = {'error': message}
        if errors:
            response['errors'] = errors
        return Response(response, status=status_code)
    
    @staticmethod
    def success_response(data, message=None, status_code=status.HTTP_200_OK):
        """Create standardized success response"""
        response = {'data': data}
        if message:
            response['message'] = message
        return Response(response, status=status_code)
    
    @staticmethod
    def not_found_response(resource_name="Resource"):
        """Create standardized 404 response"""
        return Response(
            {'error': f'{resource_name} not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    @staticmethod
    def forbidden_response(message="You do not have permission for this action"):
        """Create standardized 403 response"""
        return Response(
            {'error': message},
            status=status.HTTP_403_FORBIDDEN
        )
```

**Usage:**
```python
# Before:
return Response(
    {'error': 'Only parents can create geofences.'},
    status=status.HTTP_403_FORBIDDEN,
)

# After:
return ResponseHelper.forbidden_response('Only parents can create geofences.')
```

#### 1.3 Remove Legacy Endpoints
The `LocationViewSet` has legacy endpoints (lines 990-1030) that duplicate `GeofenceViewSet` functionality. These should be:
- **Option A:** Removed entirely (if no clients use them)
- **Option B:** Deprecated with warning headers and redirect to new endpoints
- **Option C:** Kept but marked clearly as deprecated

**Recommendation:** Check API usage logs, then remove or deprecate.

---

## 2. **Permissions (permissions.py) - Already Refactored ✅**

### Status:
- ✅ Base permission class already created (`BaseChildPermission`)
- ✅ All child permission classes use the base class
- ✅ Code duplication eliminated

### Additional Suggestions:

#### 2.1 Add Permission Caching
```python
# Add caching for permission checks to avoid repeated database queries
from django.core.cache import cache

class BaseChildPermission(BasePermission):
    permission_field = None
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        if request.user.is_parent:
            return True
        
        if request.user.is_child_user:
            # Cache permission check for 5 minutes
            cache_key = f'permission:{request.user.id}:{self.permission_field}'
            cached = cache.get(cache_key)
            if cached is not None:
                return cached
            
            try:
                permissions = request.user.childuserpermissions
                has_perm = getattr(permissions, self.permission_field, False)
                cache.set(cache_key, has_perm, timeout=300)
                return has_perm
            except ChildUserPermissions.DoesNotExist:
                cache.set(cache_key, False, timeout=300)
                return False
        
        return False
```

---

## 3. **Models (models.py) - Business Logic & Validation**

### Issues:
- **Username generation logic** duplicated (lines 176, 170 in serializers)
- **Color validation** could be extracted to a shared utility
- **create_login_account** method is doing too much (lines 220-248)
- **Role checking logic** duplicated in `is_parent` and `is_child_user` properties (lines 104-118)
- **No model managers** for common queries

### Suggestions:

#### 3.1 Extract Username Generation
```python
# Create: daydo/utils/username_generator.py
class UsernameGenerator:
    @staticmethod
    def generate_from_child_profile(child_profile):
        """Generate username from child profile"""
        return f"{child_profile.first_name.lower()}_{child_profile.family.name.lower()}"
    
    @staticmethod
    def generate_from_name(first_name, last_name, family_name):
        """Generate username from name components"""
        return f"{first_name.lower()}_{family_name.lower()}"
```

#### 3.2 Extract Role Checking Logic
```python
# In User model, create a helper method:
def _get_role_key(self):
    """Get role key from relation or fallback to legacy field"""
    rk = getattr(self, 'user_role', None)
    if rk and rk.role:
        return rk.role.key
    return self.role

@property
def is_parent(self):
    """Check if user is a parent"""
    role_key = self._get_role_key()
    return role_key == 'PARENT'

@property
def is_child_user(self):
    """Check if user is a child user"""
    role_key = self._get_role_key()
    return role_key in ('CHILD', 'CHILD_USER')
```

#### 3.3 Add Model Managers
```python
# In models.py
class UserManager(models.Manager):
    def parents(self):
        """Get all parent users"""
        return self.filter(user_role__role__key='PARENT')
    
    def children(self):
        """Get all child users"""
        return self.filter(user_role__role__key='CHILD')
    
    def active(self):
        """Get all active users"""
        return self.filter(is_active=True)

class User(AbstractUser):
    objects = UserManager()
    # ... rest of model
```

---

## 4. **Serializers (serializers.py) - Duplication & Validation**

### Issues:
- **Password handling duplicated** (lines 55-62, 64-74)
- **Display name logic duplicated** (lines 92-94 in models, 39 in serializers)
- **Coordinate validation duplicated** (GeofenceSerializer and LocationSerializer both validate lat/lon)
- **ChildProfileCreateSerializer duplicates logic** from ChildProfile.create_login_account

### Suggestions:

#### 4.1 Extract Coordinate Validation Mixin
```python
# Create: daydo/serializers/mixins.py
class CoordinateValidationMixin:
    """Mixin for latitude/longitude validation"""
    
    def validate_latitude(self, value):
        if value < -90 or value > 90:
            raise serializers.ValidationError(
                'Latitude must be between -90 and 90 degrees.'
            )
        return value
    
    def validate_longitude(self, value):
        if value < -180 or value > 180:
            raise serializers.ValidationError(
                'Longitude must be between -180 and 180 degrees.'
            )
        return value

# Usage:
class GeofenceSerializer(serializers.ModelSerializer, CoordinateValidationMixin):
    # ... fields ...
    # validate_latitude and validate_longitude inherited

class LocationSerializer(serializers.ModelSerializer, CoordinateValidationMixin):
    # ... fields ...
    # validate_latitude and validate_longitude inherited
```

#### 4.2 Extract Password Handling Mixin
```python
# In daydo/serializers/mixins.py
class PasswordMixin:
    """Mixin for handling password fields in serializers"""
    password = serializers.CharField(write_only=True, required=False)
    
    def handle_password(self, instance, validated_data):
        """Handle password setting for create/update"""
        password = validated_data.pop('password', None)
        if password:
            instance.set_password(password)
            instance.save()
        return instance
```

---

## 5. **LocationViewSet - Massive Refactoring Needed**

### Issues:
- **family_locations method is 178 lines** with massive duplication
- **Duplicate sharing status processing** (lines 1201-1215 and 1278-1292)
- **Duplicate payload building** (lines 1226-1259 and 1310-1343)
- **Complex nested logic** that's hard to test
- **No separation of concerns** - view does everything

### Suggestions:

#### 5.1 Extract Location Service (Critical)
```python
# Create: daydo/services/location_service.py
from typing import Dict, List, Optional, Tuple
from django.utils import timezone
from datetime import timedelta
from daydo.models import Family, User, ChildProfile, Location, SharingStatus, Geofence

class LocationService:
    """Service for location sharing business logic"""
    
    STALE_THRESHOLD_MINUTES = 5
    
    @staticmethod
    def process_sharing_status(sharing_status: Optional[SharingStatus]) -> Dict:
        """
        Process sharing status and handle expiration.
        Returns dict with sharing status fields.
        """
        if not sharing_status:
            return {
                'is_sharing_live': False,
                'sharing_type': None,
                'expires_at': None,
                'started_at': None,
                'updated_at': None,
            }
        
        # Handle temporary expiration
        if sharing_status.sharing_type == 'temporary' and sharing_status.is_expired():
            if sharing_status.is_sharing_live:
                sharing_status.is_sharing_live = False
                sharing_status.save(update_fields=['is_sharing_live', 'updated_at'])
            is_sharing_live = False
        else:
            is_sharing_live = sharing_status.is_sharing_live
        
        # One-time sharing is never "live"
        if sharing_status.sharing_type == 'one-time':
            is_sharing_live = False
        
        return {
            'is_sharing_live': is_sharing_live,
            'sharing_type': sharing_status.sharing_type,
            'expires_at': sharing_status.expires_at,
            'started_at': sharing_status.started_at,
            'updated_at': sharing_status.updated_at,
        }
    
    @staticmethod
    def build_location_payload(
        user_data: Dict,
        location_data: Optional[Dict],
        geofence_match: Optional[Geofence],
        stale_threshold: timezone.datetime
    ) -> Dict:
        """
        Build standardized location payload.
        
        Args:
            user_data: Dict with user info (id, name, avatar, color)
            location_data: Dict with location info (latitude, longitude, timestamp, accuracy)
            geofence_match: Matched geofence or None
            stale_threshold: Timestamp threshold for stale locations
            
        Returns:
            Dict with location payload
        """
        is_stale = bool(
            location_data and 
            location_data.get('timestamp') and 
            location_data['timestamp'] < stale_threshold
        )
        
        if geofence_match:
            return {
                'user_id': str(user_data['id']),
                'user_name': user_data['name'],
                'user_avatar': user_data.get('avatar'),
                'user_color': user_data.get('color'),
                'latitude': None,  # Hide coordinates when in geofence
                'longitude': None,
                'timestamp': location_data.get('timestamp') if location_data else None,
                'location_label': geofence_match.name,
                'geofence_id': str(geofence_match.id),
                'within_geofence': True,
                'accuracy': None,
                'is_stale': is_stale,
                **LocationService.process_sharing_status(user_data.get('sharing_status'))
            }
        else:
            return {
                'user_id': str(user_data['id']),
                'user_name': user_data['name'],
                'user_avatar': user_data.get('avatar'),
                'user_color': user_data.get('color'),
                'latitude': location_data.get('latitude') if location_data else None,
                'longitude': location_data.get('longitude') if location_data else None,
                'timestamp': location_data.get('timestamp') if location_data else None,
                'location_label': None,
                'geofence_id': None,
                'within_geofence': False,
                'accuracy': location_data.get('accuracy') if location_data else None,
                'is_stale': is_stale,
                **LocationService.process_sharing_status(user_data.get('sharing_status'))
            }
    
    @staticmethod
    def get_family_locations(family: Family) -> List[Dict]:
        """
        Get all family locations with optimized queries.
        
        Args:
            family: Family instance
            
        Returns:
            List of location payload dictionaries
        """
        from django.db.models import OuterRef, Subquery
        
        geofences = list(Geofence.objects.filter(family=family).order_by('name'))
        stale_threshold = timezone.now() - timedelta(minutes=LocationService.STALE_THRESHOLD_MINUTES)
        
        # Get family members with latest locations
        latest_location_subquery = Location.objects.filter(
            sharing_user=OuterRef('pk')
        ).order_by('-timestamp')
        
        family_members = family.members.select_related('sharing_status').annotate(
            latest_latitude=Subquery(latest_location_subquery.values('latitude')[:1]),
            latest_longitude=Subquery(latest_location_subquery.values('longitude')[:1]),
            latest_timestamp=Subquery(latest_location_subquery.values('timestamp')[:1]),
            latest_accuracy=Subquery(latest_location_subquery.values('accuracy')[:1]),
        )
        
        payload = []
        
        # Process family members (excluding CHILD_USER role)
        for member in family_members:
            if member.role == 'CHILD_USER':
                continue
            
            sharing_status = getattr(member, 'sharing_status', None)
            location_data = {
                'latitude': getattr(member, 'latest_latitude', None),
                'longitude': getattr(member, 'latest_longitude', None),
                'timestamp': getattr(member, 'latest_timestamp', None),
                'accuracy': getattr(member, 'latest_accuracy', None),
            }
            
            geofence_match = LocationService._match_geofence(
                location_data.get('latitude'),
                location_data.get('longitude'),
                geofences
            )
            
            user_data = {
                'id': member.id,
                'name': member.get_display_name(),
                'avatar': member.avatar,
                'color': member.color,
                'sharing_status': sharing_status,
            }
            
            payload.append(
                LocationService.build_location_payload(
                    user_data, location_data, geofence_match, stale_threshold
                )
            )
        
        # Process child profiles
        child_profiles = family.child_profiles.select_related(
            'linked_user', 'linked_user__sharing_status'
        )
        
        for child in child_profiles:
            linked_user = child.linked_user
            location_data = None
            sharing_status = None
            
            if linked_user:
                latest_location = Location.objects.filter(
                    sharing_user=linked_user
                ).order_by('-timestamp').first()
                
                if latest_location:
                    location_data = {
                        'latitude': latest_location.latitude,
                        'longitude': latest_location.longitude,
                        'timestamp': latest_location.timestamp,
                        'accuracy': latest_location.accuracy,
                    }
                
                sharing_status = getattr(linked_user, 'sharing_status', None)
            
            geofence_match = LocationService._match_geofence(
                location_data.get('latitude') if location_data else None,
                location_data.get('longitude') if location_data else None,
                geofences
            )
            
            user_data = {
                'id': child.id,
                'name': child.full_name or child.first_name,
                'avatar': child.avatar,
                'color': child.color,
                'sharing_status': sharing_status,
            }
            
            payload.append(
                LocationService.build_location_payload(
                    user_data, location_data, geofence_match, stale_threshold
                )
            )
        
        return payload
    
    @staticmethod
    def _match_geofence(latitude, longitude, geofences):
        """Match location to geofence (moved from LocationViewSet)"""
        if latitude is None or longitude is None:
            return None
        
        try:
            lat = float(latitude)
            lon = float(longitude)
        except (TypeError, ValueError):
            return None
        
        for geofence in geofences:
            try:
                fence_lat = float(geofence.latitude)
                fence_lon = float(geofence.longitude)
            except (TypeError, ValueError):
                continue
            
            distance = LocationService._haversine_distance_meters(
                lat, lon, fence_lat, fence_lon
            )
            if distance <= geofence.radius:
                return geofence
        
        return None
    
    @staticmethod
    def _haversine_distance_meters(lat1, lon1, lat2, lon2):
        """Calculate distance between two coordinates (moved from LocationViewSet)"""
        import math
        radius = 6371000  # Earth radius in meters
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)
        
        a = math.sin(delta_phi / 2) ** 2 + \
            math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return radius * c
```

**Refactored LocationViewSet.family_locations:**
```python
@action(detail=False, methods=['get'], url_path='family')
def family_locations(self, request):
    """Get all family locations"""
    family = request.user.family
    payload = LocationService.get_family_locations(family)
    serializer = FamilyLocationSerializer(payload, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)
```

**Impact:** Reduces method from 178 lines to 5 lines.

---

## 6. **Settings (settings.py) - Configuration Management**

### Issues:
- **Large monolithic settings file** (294 lines)
- **Hard-coded defaults** scattered throughout
- **No separation of concerns** (dev vs production)
- **Environment variable handling** could be more robust

### Suggestions:

#### 6.1 Split Settings into Modules
```python
# Create structure:
daydo_backend/
  settings/
    __init__.py          # Import and combine all settings
    base.py              # Base settings (common)
    database.py          # Database configuration
    security.py          # Security settings
    rest_framework.py    # DRF configuration
    jwt.py               # JWT configuration
    cors.py              # CORS configuration
    logging.py           # Logging configuration
    cache.py             # Cache configuration
    email.py             # Email configuration
    aws.py               # AWS configuration
    mapbox.py            # Mapbox configuration
    development.py       # Development overrides
    production.py        # Production overrides
```

**Example split:**
```python
# settings/mapbox.py
from decouple import config

MAPBOX_PUBLIC_TOKEN = config('MAPBOX_PUBLIC_TOKEN', default='')

# settings/security.py
from decouple import config

SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_SECONDS = config('SECURE_HSTS_SECONDS', default=31536000, cast=int)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=True, cast=bool)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
X_FRAME_OPTIONS = 'DENY'
```

---

## 7. **Error Handling - Missing Exception Handling**

### Issues:
- **No custom exception classes**
- **Generic error responses** (no error codes)
- **No logging of errors** in views
- **Inconsistent error formats** across endpoints

### Suggestions:

#### 7.1 Create Custom Exceptions
```python
# Create: daydo/exceptions.py
from rest_framework import status

class DayDoException(Exception):
    """Base exception for DayDo application"""
    default_message = "An error occurred"
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code = "GENERIC_ERROR"
    
    def __init__(self, message=None, error_code=None):
        self.message = message or self.default_message
        self.error_code = error_code or self.error_code
        super().__init__(self.message)

class ChildProfileException(DayDoException):
    """Exception for child profile operations"""
    status_code = status.HTTP_400_BAD_REQUEST
    error_code = "CHILD_PROFILE_ERROR"

class UserAlreadyHasAccountException(ChildProfileException):
    default_message = "Child already has a login account"
    error_code = "USER_ALREADY_HAS_ACCOUNT"

class InvalidPermissionException(DayDoException):
    default_message = "Invalid permission"
    status_code = status.HTTP_403_FORBIDDEN
    error_code = "INVALID_PERMISSION"

class LocationSharingException(DayDoException):
    """Exception for location sharing operations"""
    status_code = status.HTTP_400_BAD_REQUEST
    error_code = "LOCATION_SHARING_ERROR"

class LocationSharingNotActiveException(LocationSharingException):
    default_message = "Location sharing is not active for this user"
    error_code = "SHARING_NOT_ACTIVE"

class LocationSharingExpiredException(LocationSharingException):
    default_message = "Location sharing session has expired"
    error_code = "SHARING_EXPIRED"
```

#### 7.2 Add Exception Handler
```python
# Create: daydo/exceptions/handlers.py
import logging
from rest_framework.views import exception_handler
from rest_framework.response import Response
from .exceptions import DayDoException

logger = logging.getLogger(__name__)

def daydo_exception_handler(exc, context):
    """Custom exception handler for DayDo exceptions"""
    if isinstance(exc, DayDoException):
        logger.warning(f"DayDo exception: {exc.error_code} - {exc.message}")
        return Response(
            {
                'error': exc.message,
                'error_code': exc.error_code
            },
            status=exc.status_code
        )
    
    # Let DRF handle other exceptions
    response = exception_handler(exc, context)
    if response is not None:
        logger.error(f"DRF exception: {exc.__class__.__name__} - {str(exc)}")
        # Standardize error format
        if 'detail' in response.data:
            response.data = {
                'error': response.data['detail'],
                'error_code': exc.__class__.__name__
            }
    return response

# In settings.py:
REST_FRAMEWORK = {
    # ... existing settings ...
    'EXCEPTION_HANDLER': 'daydo.exceptions.handlers.daydo_exception_handler',
}
```

---

## 8. **Performance - N+1 Queries & Caching**

### Issues:
- **Potential N+1 queries** in FamilyMembersSerializer.get_permissions
- **No caching** for frequently accessed data
- **Multiple database queries** in dashboard calculations
- **Location queries** could be optimized further

### Suggestions:

#### 8.1 Add Select Related / Prefetch Related (Already Partially Done)
```python
# In FamilyViewSet.members - already optimized ✅
# In ChildProfileViewSet.get_queryset - already optimized ✅

# Additional optimization needed:
# In LocationViewSet.family_locations - add prefetch_related for locations
family_members = user.family.members.select_related(
    'sharing_status'
).prefetch_related(
    'locations'  # Prefetch all locations for batch processing
)
```

#### 8.2 Add Caching for Family Locations
```python
# In LocationService:
from django.core.cache import cache

@staticmethod
def get_family_locations(family: Family, use_cache=True) -> List[Dict]:
    """Get all family locations with caching"""
    cache_key = f'family_locations:{family.id}'
    
    if use_cache:
        cached = cache.get(cache_key)
        if cached is not None:
            return cached
    
    payload = LocationService._calculate_family_locations(family)
    
    if use_cache:
        cache.set(cache_key, payload, timeout=60)  # 1 minute cache
    
    return payload
```

---

## 9. **Testing - Missing Test Coverage**

### Issues:
- **No test files** visible (tests.py exists but likely empty)
- **No integration tests** for API endpoints
- **No permission tests**
- **No service layer tests**

### Suggestions:

#### 9.1 Create Test Structure
```
daydo/
  tests/
    __init__.py
    test_models.py          # Model tests
    test_views.py           # View tests
    test_serializers.py     # Serializer tests
    test_permissions.py     # Permission tests
    test_services.py        # Service tests
    test_location_service.py  # Location service tests
    factories.py            # Model factories for testing
    conftest.py             # Pytest configuration
    test_utils.py            # Test utilities
```

#### 9.2 Example Test
```python
# tests/test_location_service.py
import pytest
from django.utils import timezone
from datetime import timedelta
from daydo.models import Family, User, Location, SharingStatus, Geofence
from daydo.services.location_service import LocationService

@pytest.mark.django_db
class TestLocationService:
    def test_process_sharing_status_expired(self):
        """Test processing expired sharing status"""
        user = User.objects.create_user(
            username='testuser',
            password='testpass',
            family=Family.objects.create(name='Test Family')
        )
        sharing_status = SharingStatus.objects.create(
            user=user,
            sharing_type='temporary',
            is_sharing_live=True,
            expires_at=timezone.now() - timedelta(hours=1)
        )
        
        result = LocationService.process_sharing_status(sharing_status)
        
        assert result['is_sharing_live'] is False
        assert sharing_status.is_sharing_live is False  # Should be updated
    
    def test_build_location_payload_with_geofence(self):
        """Test building payload when location matches geofence"""
        family = Family.objects.create(name='Test Family')
        geofence = Geofence.objects.create(
            family=family,
            name='Home',
            latitude=52.5200,
            longitude=13.4050,
            created_by=User.objects.create_user(
                username='parent',
                password='pass',
                family=family
            )
        )
        
        user_data = {
            'id': 'user-id',
            'name': 'Test User',
            'avatar': 'bear',
            'color': '#FF5733',
            'sharing_status': None,
        }
        location_data = {
            'latitude': 52.5201,  # Very close to geofence
            'longitude': 13.4051,
            'timestamp': timezone.now(),
            'accuracy': 10.0,
        }
        
        payload = LocationService.build_location_payload(
            user_data,
            location_data,
            geofence,
            timezone.now()
        )
        
        assert payload['location_label'] == 'Home'
        assert payload['within_geofence'] is True
        assert payload['latitude'] is None  # Hidden when in geofence
        assert payload['longitude'] is None
```

---

## 10. **URLs (urls.py) - Organization**

### Issues:
- **All URLs in one file** - will become hard to maintain as app grows
- **No API versioning**
- **Legacy endpoints** mixed with new ones

### Suggestions:

#### 10.1 Split URLs by Feature
```python
# daydo/urls.py
from django.urls import path, include

app_name = 'daydo'

urlpatterns = [
    path('auth/', include('daydo.urls.auth')),
    path('family/', include('daydo.urls.family')),
    path('children/', include('daydo.urls.children')),
    path('users/', include('daydo.urls.users')),
    path('tasks/', include('daydo.urls.tasks')),
    path('events/', include('daydo.urls.events')),
    path('location/', include('daydo.urls.location')),
    path('geofences/', include('daydo.urls.geofences')),
    # ... etc
]

# daydo/urls/location.py
from rest_framework.routers import DefaultRouter
from daydo.views import LocationViewSet, MapboxTokenView

router = DefaultRouter()
router.register(r'', LocationViewSet, basename='location')

urlpatterns = [
    path('mapbox-token/', MapboxTokenView.as_view(), name='mapbox-token'),
    path('', include(router.urls)),
]
```

#### 10.2 Add API Versioning
```python
# daydo_backend/urls.py
urlpatterns = [
    path('api/v1/', include('daydo.urls')),
    # Future: path('api/v2/', include('daydo.v2.urls')),
    path('admin/', admin.site.urls),
]
```

---

## 11. **Type Hints & Documentation**

### Issues:
- **No type hints** in code
- **Minimal docstrings** in some methods
- **No API documentation** (Swagger/OpenAPI)

### Suggestions:

#### 11.1 Add Type Hints
```python
# Before:
def get_display_name(self):
    return f"{self.first_name} {self.last_name}".strip() or self.username

# After:
def get_display_name(self) -> str:
    """Get display name for UI"""
    return f"{self.first_name} {self.last_name}".strip() or self.username
```

#### 11.2 Add API Documentation
```python
# Install: pip install drf-spectacular

# In settings.py:
INSTALLED_APPS = [
    # ... existing apps ...
    'drf_spectacular',
]

REST_FRAMEWORK = {
    # ... existing settings ...
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'DayDo API',
    'DESCRIPTION': 'Family task management API',
    'VERSION': '1.0.0',
}

# In urls.py:
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]
```

---

## 12. **Security Enhancements**

### Issues:
- **No rate limiting** on authentication endpoints
- **No password strength validation** beyond Django defaults
- **No account lockout** after failed login attempts
- **No input sanitization** for user-generated content

### Suggestions:

#### 12.1 Add Rate Limiting
```python
# Install: pip install django-ratelimit

# In views.py:
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator

@method_decorator(ratelimit(key='ip', rate='5/m', method='POST'), name='login')
class AuthenticationViewSet(viewsets.ViewSet):
    # ... existing code ...
```

#### 12.2 Add Account Lockout
```python
# Create: daydo/services/auth_service.py (extend existing)
class AuthService:
    MAX_LOGIN_ATTEMPTS = 5
    LOCKOUT_DURATION = timedelta(minutes=15)
    
    @staticmethod
    def check_account_lockout(user):
        """Check if account is locked due to failed login attempts"""
        # TODO: Implement lockout tracking
        # Could use cache or a separate model
        pass
    
    @staticmethod
    def record_failed_login(user):
        """Record a failed login attempt"""
        # TODO: Implement
        pass
```

---

## 13. **Code Organization - Missing Services Layer**

### Current Structure:
```
daydo/
  models.py       # Data layer
  views.py       # Presentation layer (contains business logic)
  serializers.py # Data transformation
  permissions.py # Authorization
  services/      # Partial services layer
    auth_service.py
    dashboard_service.py
```

### Suggested Structure:
```
daydo/
  models.py          # Data layer
  views.py           # Presentation layer (thin)
  serializers.py     # Data transformation
  permissions.py     # Authorization
  services/          # Business logic layer
    __init__.py
    auth_service.py
    dashboard_service.py
    location_service.py      # NEW
    child_profile_service.py # NEW
    user_service.py          # NEW
    task_service.py          # NEW (optional)
    event_service.py         # NEW (optional)
  utils/             # Utility functions
    __init__.py
    username_generator.py
    validators.py
    response_helpers.py
    coordinate_validator.py  # NEW
  exceptions/        # Custom exceptions
    __init__.py
    exceptions.py
    handlers.py
  managers/          # Custom model managers (optional)
    __init__.py
    user_manager.py
```

---

## 14. **Additional Issues Found**

### 14.1 LocationViewSet - Duration Parsing
**Issue:** `_parse_duration` method (lines 1038-1047) returns tuple `(sharing_type, expires_at, is_live)` which is hard to understand.

**Suggestion:**
```python
# Create: daydo/models/location_enums.py
from dataclasses import dataclass
from typing import Optional
from django.utils import timezone
from datetime import timedelta

@dataclass
class SharingDuration:
    """Data class for sharing duration configuration"""
    sharing_type: str
    expires_at: Optional[timezone.datetime]
    is_live: bool

class DurationParser:
    DURATION_MAP = {
        '15m': timedelta(minutes=15),
        '1h': timedelta(hours=1),
        '1d': timedelta(days=1),
    }
    
    @staticmethod
    def parse(duration_str: str) -> Optional[SharingDuration]:
        """Parse duration string to SharingDuration object"""
        duration_str = (duration_str or '').lower()
        
        if duration_str in DurationParser.DURATION_MAP:
            delta = DurationParser.DURATION_MAP[duration_str]
            return SharingDuration(
                sharing_type='temporary',
                expires_at=timezone.now() + delta,
                is_live=True
            )
        elif duration_str == 'always':
            return SharingDuration(
                sharing_type='always',
                expires_at=None,
                is_live=True
            )
        elif duration_str == 'one-time':
            return SharingDuration(
                sharing_type='one-time',
                expires_at=timezone.now(),
                is_live=False
            )
        return None
```

### 14.2 LocationViewSet - Method Organization
**Issue:** LocationViewSet mixes helper methods with action methods. Hard to follow.

**Suggestion:** Group methods logically:
```python
class LocationViewSet(viewsets.ViewSet):
    # Constants
    STALE_THRESHOLD_MINUTES = 5
    
    # Public action methods
    @action(...)
    def share(self, request): ...
    
    @action(...)
    def update_location(self, request): ...
    
    @action(...)
    def stop_sharing(self, request): ...
    
    @action(...)
    def family_locations(self, request): ...
    
    # Private helper methods (prefixed with _)
    def _get_or_create_sharing_status(self, user): ...
    def _enforce_location_limit(self, user): ...
    def _validate_lat_lon(self, request): ...
    def _serialize_status(self, status, request): ...
    def _serialize_location(self, location, request): ...
```

### 14.3 Model Methods - Role Checking
**Issue:** `is_parent` and `is_child_user` properties have complex logic that could be simplified.

**Suggestion:** Already addressed in section 3.2

### 14.4 Serializer Validation - Duplication
**Issue:** Latitude/longitude validation appears in both `GeofenceSerializer` and `LocationSerializer`.

**Suggestion:** Already addressed in section 4.1

---

## 15. **Step-by-Step Refactoring Guide**

### Phase 1: Foundation (Week 1)
**Goal:** Set up infrastructure for refactoring

#### Step 1.1: Create Utility Modules ✅ COMPLETE
1. ✅ Create `daydo/utils/__init__.py`
2. ✅ Create `daydo/utils/response_helpers.py` with `ResponseHelper` class
3. ⏳ Create `daydo/utils/username_generator.py` with `UsernameGenerator` class (pending)
4. ⏳ Create `daydo/utils/validators.py` with coordinate validation (pending)
5. ✅ **Test:** Run existing tests to ensure no regressions

#### Step 1.2: Create Exception Framework ✅ COMPLETE
1. ✅ Create `daydo/exceptions/__init__.py`
2. ✅ Create `daydo/exceptions/exceptions.py` with custom exception classes
3. ✅ Create `daydo/exceptions/handlers.py` with exception handler
4. ✅ Update `settings.py` to use custom exception handler
5. ✅ **Test:** Verify error responses are standardized

#### Step 1.3: Extract Coordinate Validation Mixin ✅ COMPLETE
1. ✅ Create `daydo/serializers/mixins.py`
2. ✅ Add `CoordinateValidationMixin` class
3. ✅ Update `GeofenceSerializer` to use mixin
4. ✅ Update `LocationSerializer` to use mixin
5. ✅ **Test:** Verify validation still works

### Phase 2: Service Layer Extraction (Week 2)
**Goal:** Extract business logic from views

#### Step 2.1: Extract Location Service (Critical) ✅ COMPLETE
1. ✅ Create `daydo/services/location_service.py`
2. ✅ Move `_haversine_distance_meters` to service
3. ✅ Move `_match_geofence` to service
4. ✅ Create `process_sharing_status` method
5. ✅ Create `build_location_payload` method
6. ✅ Create `get_family_locations` method
7. ✅ Refactor `LocationViewSet.family_locations` to use service (reduced from 178 lines to 5 lines)
8. ⏳ **Test:** Create comprehensive tests for LocationService (pending)
9. ✅ **Test:** Verify API endpoints still work

#### Step 2.2: Extract Child Profile Service
1. Create `daydo/services/child_profile_service.py`
2. Move username generation logic
3. Extract child profile creation logic
4. Update views to use service
5. **Test:** Verify child profile operations

#### Step 2.3: Extract Task Service (Optional)
1. Create `daydo/services/task_service.py`
2. Move star count adjustment logic
3. Extract task assignment logic
4. **Test:** Verify task operations

### Phase 3: View Refactoring (Week 3)
**Goal:** Simplify views by using services

#### Step 3.1: Refactor LocationViewSet
1. Replace error responses with `ResponseHelper`
2. Use `LocationService` for all location operations
3. Remove legacy endpoints or mark as deprecated
4. Simplify action methods
5. **Test:** Full integration test of location endpoints

#### Step 3.2: Refactor Other ViewSets
1. Replace error responses with `ResponseHelper` in all views
2. Use services where available
3. Add type hints to all methods
4. **Test:** Verify all endpoints work

### Phase 4: Model Improvements (Week 4)
**Goal:** Improve models and add managers

#### Step 4.1: Extract Role Checking Logic
1. Create `_get_role_key` helper method in User model
2. Simplify `is_parent` and `is_child_user` properties
3. **Test:** Verify role checking still works

#### Step 4.2: Add Model Managers
1. Create `UserManager` with custom querysets
2. Add `parents()`, `children()`, `active()` methods
3. Update views to use managers
4. **Test:** Verify queries are optimized

#### Step 4.3: Split create_login_account
1. Break down into smaller private methods
2. Use `UsernameGenerator` service
3. **Test:** Verify child account creation

### Phase 5: Settings Refactoring (Week 5)
**Goal:** Organize settings into modules

#### Step 5.1: Create Settings Structure
1. Create `daydo_backend/settings/` directory
2. Create `base.py`, `database.py`, `security.py`, etc.
3. Create `__init__.py` to combine settings
4. Update `manage.py` and `wsgi.py` to use new settings
5. **Test:** Verify application starts correctly

#### Step 5.2: Environment-Specific Settings
1. Create `development.py` and `production.py`
2. Move environment-specific overrides
3. Update deployment scripts
4. **Test:** Verify both environments work

### Phase 6: Testing Infrastructure (Week 6)
**Goal:** Add comprehensive test coverage

#### Step 6.1: Set Up Test Structure
1. Create `daydo/tests/` directory
2. Create test files for each module
3. Set up pytest configuration
4. Create model factories

#### Step 6.2: Write Critical Tests
1. Test LocationService thoroughly
2. Test AuthService
3. Test permission classes
4. Test API endpoints (integration tests)
5. **Target:** 70%+ code coverage

### Phase 7: Documentation & Type Hints (Week 7)
**Goal:** Improve code documentation

#### Step 7.1: Add Type Hints
1. Add type hints to all service methods
2. Add type hints to all view methods
3. Add type hints to model methods
4. **Verify:** Run mypy or similar type checker

#### Step 7.2: Add API Documentation
1. Install `drf-spectacular`
2. Configure OpenAPI schema
3. Add docstrings to all endpoints
4. Generate and review API documentation

### Phase 8: Performance Optimization (Week 8)
**Goal:** Optimize database queries and add caching

#### Step 8.1: Query Optimization
1. Review all querysets for N+1 queries
2. Add `select_related` and `prefetch_related` where needed
3. Add database indexes if missing
4. **Measure:** Use Django Debug Toolbar or similar

#### Step 8.2: Add Caching
1. Add caching to `LocationService.get_family_locations`
2. Add caching to permission checks
3. Add caching to dashboard data
4. **Measure:** Verify cache hit rates

### Phase 9: Security Hardening (Week 9)
**Goal:** Add security features

#### Step 9.1: Rate Limiting
1. Install `django-ratelimit`
2. Add rate limiting to auth endpoints
3. Add rate limiting to location update endpoint
4. **Test:** Verify rate limiting works

#### Step 9.2: Account Lockout
1. Implement failed login tracking
2. Add account lockout logic
3. Add unlock mechanism
4. **Test:** Verify lockout works

### Phase 10: Cleanup & Final Review (Week 10)
**Goal:** Remove deprecated code and finalize

#### Step 10.1: Remove Legacy Code
1. Remove or deprecate legacy location endpoints
2. Remove unused imports
3. Remove commented-out code
4. **Test:** Full regression test

#### Step 10.2: Code Review
1. Review all refactored code
2. Check for remaining duplication
3. Verify all tests pass
4. Update documentation

---

## Priority Ranking (Updated)

### Critical Priority (Do First):
1. **Extract Location Service** (#5.1) - Eliminates 178 lines of duplication
2. **Extract Error Response Helper** (#1.2) - Standardizes error handling
3. **Add select_related/prefetch_related** (#8.1) - Performance improvement
4. **Remove legacy endpoints** (#1.3) - Code cleanup

### High Priority:
5. **Extract Coordinate Validation Mixin** (#4.1) - Eliminates duplication
6. **Add exception handling** (#7) - Better error management
7. **Extract Child Profile Service** (#2.2) - Better organization
8. **Add type hints** (#11.1) - Better IDE support and documentation

### Medium Priority:
9. **Split settings file** (#6.1) - Better maintainability
10. **Add model managers** (#3.3) - Better query organization
11. **Add API documentation** (#11.2) - Developer experience
12. **Add testing infrastructure** (#9) - Code quality

### Low Priority (Nice to Have):
13. **Add rate limiting** (#12.1) - Security hardening
14. **Reorganize URLs** (#10) - Better organization
15. **Add account lockout** (#12.2) - Security hardening

---

## Estimated Impact

- **Code Reduction**: ~300-400 lines of duplicated code eliminated
- **Performance**: 
  - 50-70% reduction in database queries with prefetch_related
  - 30-50% faster location endpoint with service extraction
- **Maintainability**: Significantly improved with services layer
- **Testability**: Much easier with extracted services
- **Documentation**: Better code understanding with type hints and docstrings
- **Error Handling**: Consistent error responses across all endpoints

---

## Risk Assessment

### Low Risk:
- Adding type hints
- Adding docstrings
- Creating utility modules
- Adding tests

### Medium Risk:
- Extracting services (requires thorough testing)
- Refactoring views (requires integration testing)
- Splitting settings (requires deployment verification)

### High Risk:
- Removing legacy endpoints (must verify no clients use them)
- Changing error response formats (must coordinate with frontend)

---

## Migration Strategy

### For Each Refactoring:
1. **Create new code** alongside old code
2. **Add feature flag** or configuration to switch between old/new
3. **Test thoroughly** with new code
4. **Deploy with feature flag disabled** (old code active)
5. **Enable feature flag** in staging
6. **Monitor for issues**
7. **Enable in production**
8. **Remove old code** after verification period

### Rollback Plan:
- Keep old code commented for 2-4 weeks
- Use feature flags for easy rollback
- Maintain comprehensive test suite
- Monitor error rates and performance metrics

---

## Success Metrics

### Code Quality:
- [ ] Reduce code duplication by 50%+
- [ ] Achieve 70%+ test coverage
- [ ] All methods have type hints
- [ ] All public methods have docstrings

### Performance:
- [ ] Reduce database queries by 50%+
- [ ] Location endpoint response time < 200ms
- [ ] Dashboard endpoint response time < 100ms

### Maintainability:
- [ ] All business logic in services layer
- [ ] Views are thin (mostly delegation)
- [ ] Clear separation of concerns
- [ ] Easy to add new features

---

## Notes

- **Do not refactor everything at once** - work incrementally
- **Test after each change** - don't break existing functionality
- **Coordinate with frontend team** - some changes may require frontend updates
- **Document as you go** - update API docs and code comments
- **Measure impact** - track performance before/after
