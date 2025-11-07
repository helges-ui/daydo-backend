# Location Sharing Feature - Implementation Plan

## Overview
This document outlines the implementation plan for the "Share Position" feature (US-31 to US-39) in the DayDo Family App backend. The feature allows family members to share their location with the family for safety and coordination purposes.

## Analysis Summary

### User Stories Coverage
- **US-31**: One-time location share (immediate share, no tracking)
- **US-32**: Temporary sharing (15m, 1h, 1d durations)
- **US-33**: Always-on sharing (indefinite duration)
- **US-34**: View family members' last known positions
- **US-35**: Device location retrieval (frontend responsibility)
- **US-36**: Store last 10 positions per user
- **US-37**: Display timestamp with position
- **US-38**: Manual stop sharing
- **US-39**: Permission prompts (frontend responsibility)
- **US-44**: Live map view (future - not in scope)

### Technical Requirements
1. **Data Models**: Location and SharingStatus models
2. **API Endpoints**: 4 custom endpoints (share, update, stop, family)
3. **Performance**: Optimized queries for latest position retrieval
4. **Data Management**: Auto-delete oldest records when >10 per user
5. **Background Tasks**: Auto-expire temporary sharing sessions
6. **Security**: Family-scoped access, authentication required

---

## Phase 1: Database Models

### 1.1 Location Model
**File**: `daydo/models.py`

```python
class Location(models.Model):
    """
    Stores location data for users sharing their position.
    Tracks the last 10 positions per user (oldest auto-deleted).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sharing_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='locations',
        help_text="User who is sharing their location"
    )
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        help_text="Latitude coordinate (-90 to 90)"
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        help_text="Longitude coordinate (-180 to 180)"
    )
    timestamp = models.DateTimeField(auto_now_add=True, help_text="When this location was recorded")
    
    class Meta:
        verbose_name = "Location"
        verbose_name_plural = "Locations"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['sharing_user', '-timestamp']),
            models.Index(fields=['sharing_user', 'timestamp']),
        ]
    
    def __str__(self):
        return f"{self.sharing_user.get_display_name()} @ {self.latitude}, {self.longitude}"
```

**Key Points**:
- `DecimalField` for precise lat/lng (9,6 precision supports ~10cm accuracy)
- Auto-generated `timestamp` on creation
- Indexed on `sharing_user` and `timestamp` for efficient queries
- Cascade delete when user is deleted

### 1.2 SharingStatus Model
**File**: `daydo/models.py`

```python
class SharingStatus(models.Model):
    """
    Tracks the active sharing status for each user.
    One-to-One relationship with User (one status per user).
    """
    SHARING_TYPE_CHOICES = [
        ('one-time', 'One-Time'),
        ('temporary', 'Temporary'),
        ('always', 'Always'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='sharing_status',
        help_text="User whose sharing status this is"
    )
    is_sharing_live = models.BooleanField(
        default=False,
        help_text="Whether location sharing is currently active"
    )
    sharing_type = models.CharField(
        max_length=20,
        choices=SHARING_TYPE_CHOICES,
        default='one-time',
        help_text="Type of sharing: one-time, temporary, or always"
    )
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When temporary sharing expires (null for always/one-time)"
    )
    started_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When sharing was started"
    )
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Sharing Status"
        verbose_name_plural = "Sharing Statuses"
        indexes = [
            models.Index(fields=['user', 'is_sharing_live']),
            models.Index(fields=['expires_at']),  # For background task cleanup
        ]
    
    def __str__(self):
        status = "Active" if self.is_sharing_live else "Inactive"
        return f"{self.user.get_display_name()} - {status} ({self.sharing_type})"
    
    def is_expired(self):
        """Check if temporary sharing has expired"""
        if self.sharing_type == 'temporary' and self.expires_at:
            return timezone.now() > self.expires_at
        return False
```

**Key Points**:
- One-to-One with User ensures one status per user
- `expires_at` nullable for always/one-time sharing
- Index on `expires_at` for efficient background task queries
- Helper method `is_expired()` for expiration checks

---

## Phase 2: Serializers

### 2.1 LocationSerializer
**File**: `daydo/serializers.py`

```python
class LocationSerializer(serializers.ModelSerializer):
    """Serializer for Location model"""
    sharing_user_name = serializers.CharField(source='sharing_user.get_display_name', read_only=True)
    sharing_user_id = serializers.UUIDField(source='sharing_user.id', read_only=True)
    
    class Meta:
        model = Location
        fields = [
            'id', 'sharing_user', 'sharing_user_id', 'sharing_user_name',
            'latitude', 'longitude', 'timestamp'
        ]
        read_only_fields = ['id', 'sharing_user', 'timestamp']
    
    def validate_latitude(self, value):
        """Validate latitude is within valid range"""
        if value < -90 or value > 90:
            raise serializers.ValidationError("Latitude must be between -90 and 90")
        return value
    
    def validate_longitude(self, value):
        """Validate longitude is within valid range"""
        if value < -180 or value > 180:
            raise serializers.ValidationError("Longitude must be between -180 and 180")
        return value
```

### 2.2 SharingStatusSerializer
**File**: `daydo/serializers.py`

```python
class SharingStatusSerializer(serializers.ModelSerializer):
    """Serializer for SharingStatus model"""
    user_name = serializers.CharField(source='user.get_display_name', read_only=True)
    user_id = serializers.UUIDField(source='user.id', read_only=True)
    is_expired = serializers.SerializerMethodField()
    
    class Meta:
        model = SharingStatus
        fields = [
            'id', 'user', 'user_id', 'user_name',
            'is_sharing_live', 'sharing_type', 'expires_at',
            'started_at', 'updated_at', 'is_expired'
        ]
        read_only_fields = ['id', 'user', 'started_at', 'updated_at']
    
    def get_is_expired(self, obj):
        """Check if sharing has expired"""
        return obj.is_expired()
```

### 2.3 FamilyLocationSerializer (for GET /api/location/family/)
**File**: `daydo/serializers.py`

```python
class FamilyLocationSerializer(serializers.Serializer):
    """Serializer for family members' last known locations"""
    user_id = serializers.UUIDField()
    user_name = serializers.CharField()
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6)
    timestamp = serializers.DateTimeField()
    is_sharing_live = serializers.BooleanField()
    sharing_type = serializers.CharField()
```

---

## Phase 3: Views and API Endpoints

### 3.1 LocationViewSet
**File**: `daydo/views.py`

**Structure**: Custom ViewSet with `@action` decorators for custom endpoints

```python
class LocationViewSet(viewsets.ViewSet):
    """Location sharing endpoints"""
    permission_classes = [IsAuthenticated, FamilyMemberPermission]
    
    @action(detail=False, methods=['post'], url_path='share')
    def share(self, request):
        """
        POST /api/location/share/
        Start or update a sharing session (US-31, US-32, US-33)
        
        Payload:
        {
            "duration": "15m" | "1h" | "1d" | "always" | "one-time",
            "latitude": decimal (optional for one-time),
            "longitude": decimal (optional for one-time)
        }
        """
        # Implementation details below
    
    @action(detail=False, methods=['post'], url_path='update')
    def update_location(self, request):
        """
        POST /api/location/update/
        Push location update from device (US-35, US-36)
        
        Payload:
        {
            "latitude": decimal,
            "longitude": decimal
        }
        """
        # Implementation details below
    
    @action(detail=False, methods=['post'], url_path='stop')
    def stop_sharing(self, request):
        """
        POST /api/location/stop/
        Manually stop sharing (US-38)
        """
        # Implementation details below
    
    @action(detail=False, methods=['get'], url_path='family')
    def family_locations(self, request):
        """
        GET /api/location/family/
        Get last known positions of all sharing family members (US-34, US-37)
        """
        # Implementation details below
```

### 3.2 Endpoint Implementation Details

#### POST /api/location/share/
**Logic**:
1. Parse `duration` from request (15m, 1h, 1d, always, one-time)
2. Get or create `SharingStatus` for user
3. Calculate `expires_at` based on duration:
   - `15m` → now + 15 minutes
   - `1h` → now + 1 hour
   - `1d` → now + 24 hours
   - `always` → null
   - `one-time` → null
4. Set `is_sharing_live = True`
5. Set `sharing_type` accordingly
6. If `one-time` and lat/lng provided, create Location record immediately
7. Return updated SharingStatus

**Duration Parsing**:
```python
from datetime import timedelta
from django.utils import timezone

def parse_duration(duration_str):
    """Parse duration string to timedelta"""
    duration_map = {
        '15m': timedelta(minutes=15),
        '1h': timedelta(hours=1),
        '1d': timedelta(days=1),
    }
    return duration_map.get(duration_str)
```

#### POST /api/location/update/
**Logic**:
1. Validate user has active sharing (`is_sharing_live = True` OR one-time share in progress)
2. Validate lat/lng are provided and within valid ranges
3. Create new Location record
4. **Auto-cleanup**: Check if user has >10 locations, delete oldest
5. Return created Location

**Auto-cleanup Implementation**:
```python
def enforce_location_limit(user):
    """Keep only the last 10 locations per user"""
    locations = Location.objects.filter(sharing_user=user).order_by('-timestamp')
    if locations.count() > 10:
        # Delete oldest (keep newest 10)
        locations_to_delete = locations[10:]
        Location.objects.filter(id__in=[loc.id for loc in locations_to_delete]).delete()
```

#### POST /api/location/stop/
**Logic**:
1. Get user's SharingStatus
2. Set `is_sharing_live = False`
3. Optionally clear `expires_at` if temporary
4. Return updated status

#### GET /api/location/family/
**Logic**:
1. Get all family members (via `request.user.family.members`)
2. Filter to only those with `is_sharing_live = True` and not expired
3. For each user, get **only the most recent** Location record
4. Use optimized query with `Max` or `Subquery` for performance
5. Return list of last known positions with timestamps

**Optimized Query**:
```python
from django.db.models import Max, OuterRef, Subquery

# Get latest location for each sharing user
latest_locations = Location.objects.filter(
    sharing_user=OuterRef('pk')
).order_by('-timestamp')[:1]

family_members = User.objects.filter(
    family=request.user.family,
    sharing_status__is_sharing_live=True
).annotate(
    latest_location=Subquery(latest_locations.values('id')[:1])
).select_related('sharing_status').prefetch_related('locations')
```

**Alternative (More Efficient)**:
```python
# Get all sharing family members
sharing_users = User.objects.filter(
    family=request.user.family,
    sharing_status__is_sharing_live=True
).exclude(
    sharing_status__expires_at__lt=timezone.now()
).select_related('sharing_status')

# Get latest location for each user in one query
user_ids = [user.id for user in sharing_users]
latest_locations = Location.objects.filter(
    sharing_user_id__in=user_ids
).values('sharing_user_id').annotate(
    latest_timestamp=Max('timestamp')
).values('sharing_user_id', 'latest_timestamp')

# Build a map for efficient lookup
location_map = {loc['sharing_user_id']: loc['latest_timestamp'] for loc in latest_locations}

# Fetch actual location records
locations = Location.objects.filter(
    sharing_user_id__in=user_ids,
    timestamp__in=[loc['latest_timestamp'] for loc in latest_locations]
).select_related('sharing_user')
```

---

## Phase 4: URL Routing

### 4.1 URL Configuration
**File**: `daydo/urls.py`

```python
from .views import LocationViewSet

router.register(r'location', LocationViewSet, basename='location')
```

**Resulting URLs**:
- `POST /api/location/share/`
- `POST /api/location/update/`
- `POST /api/location/stop/`
- `GET /api/location/family/`

---

## Phase 5: Background Tasks

### 5.1 Auto-Expire Temporary Sharing
**Requirement**: Automatically terminate expired temporary sharing sessions

**Options**:
1. **Django Management Command** (Recommended for MVP)
   - Create `management/commands/expire_sharing_sessions.py`
   - Run via cron every 5-10 minutes
   - Query `SharingStatus` where `expires_at < now()` and `is_sharing_live = True`
   - Set `is_sharing_live = False`

2. **Celery** (For production scale)
   - Periodic task to check and expire sessions
   - More robust but requires additional infrastructure

**Implementation (Management Command)**:
```python
# daydo/management/commands/expire_sharing_sessions.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from daydo.models import SharingStatus

class Command(BaseCommand):
    help = 'Expire temporary location sharing sessions'
    
    def handle(self, *args, **options):
        now = timezone.now()
        expired = SharingStatus.objects.filter(
            is_sharing_live=True,
            sharing_type='temporary',
            expires_at__lt=now
        )
        count = expired.update(is_sharing_live=False)
        self.stdout.write(f'Expired {count} sharing sessions')
```

**Cron Setup** (on server):
```bash
# Run every 5 minutes
*/5 * * * * cd /opt/daydo/app && python manage.py expire_sharing_sessions
```

---

## Phase 6: Security & Permissions

### 6.1 Permission Checks
- **All endpoints**: Require `IsAuthenticated`
- **Family scoping**: Use `FamilyMemberPermission` (existing)
- **Location updates**: Verify user owns the sharing session
- **Family locations**: Only return locations for same family members

### 6.2 Validation Rules
1. **Latitude**: -90 to 90
2. **Longitude**: -180 to 180
3. **Sharing status**: User can only update their own sharing status
4. **Location updates**: Only allowed if `is_sharing_live = True` or one-time share

---

## Phase 7: Database Migrations

### 7.1 Migration File
**File**: `daydo/migrations/0012_location_sharingstatus.py`

**Operations**:
1. Create `Location` model
2. Create `SharingStatus` model
3. Add indexes for performance
4. Add foreign key constraints

---

## Phase 8: Testing

### 8.1 Test Cases
1. **Share endpoint**:
   - Test all duration types (15m, 1h, 1d, always, one-time)
   - Test one-time with immediate location
   - Test expiration calculation

2. **Update endpoint**:
   - Test location creation
   - Test auto-cleanup (verify only 10 locations kept)
   - Test validation (invalid lat/lng)
   - Test unauthorized update (not sharing)

3. **Stop endpoint**:
   - Test stopping active sharing
   - Test stopping when not sharing

4. **Family endpoint**:
   - Test returns only family members
   - Test returns only latest position per user
   - Test excludes expired sessions
   - Test performance with multiple users

5. **Background task**:
   - Test expiration of temporary sessions
   - Test cron job execution

---

## Phase 9: Performance Optimization

### 9.1 Database Indexes
- `Location`: Index on `(sharing_user, -timestamp)` for latest position queries
- `SharingStatus`: Index on `(user, is_sharing_live)` and `(expires_at)` for cleanup

### 9.2 Query Optimization
- Use `select_related()` for foreign keys
- Use `prefetch_related()` for reverse relations
- Use `Subquery` or `Max` aggregation for latest position
- Limit queryset results appropriately

### 9.3 Caching Considerations (Future)
- Cache family locations for 30-60 seconds
- Invalidate on location update

---

## Implementation Order

1. **Phase 1**: Create models (`Location`, `SharingStatus`)
2. **Phase 2**: Create serializers
3. **Phase 3**: Implement ViewSet with all 4 endpoints
4. **Phase 4**: Add URL routing
5. **Phase 5**: Create management command for expiration
6. **Phase 6**: Add security checks and validation
7. **Phase 7**: Create and apply migration
8. **Phase 8**: Write and run tests
9. **Phase 9**: Performance testing and optimization

---

## Estimated Time

- **Phase 1-2** (Models & Serializers): 2-3 hours
- **Phase 3** (Views & Endpoints): 4-5 hours
- **Phase 4-5** (URLs & Background Tasks): 1-2 hours
- **Phase 6** (Security): 1 hour
- **Phase 7** (Migration): 30 minutes
- **Phase 8** (Testing): 2-3 hours
- **Phase 9** (Optimization): 1-2 hours

**Total**: ~12-17 hours (1.5-2 days)

---

## Open Questions / Decisions Needed

1. **One-time share behavior**: Should one-time share create a Location immediately, or wait for first update?
   - **Decision**: Create immediately if lat/lng provided in share request

2. **Location history**: Should we store more than 10 positions for analytics?
   - **Decision**: Keep only 10 for now (per US-36)

3. **Expiration cleanup**: Should we delete Location records when sharing stops, or keep them?
   - **Decision**: Keep Location records (they're already limited to 10 per user)

4. **Background task frequency**: How often should we check for expired sessions?
   - **Decision**: Every 5 minutes (balance between responsiveness and server load)

5. **Always-on sharing**: Should there be a maximum duration even for "always"?
   - **Decision**: No maximum, but user can manually stop anytime

---

## Notes

- US-35 (Device location retrieval) and US-39 (Permission prompts) are frontend responsibilities
- US-44 (Live map view) is future work and not in scope
- The implementation follows existing patterns in the codebase (ViewSet, Serializers, Permissions)
- Background tasks use Django management commands (simpler than Celery for MVP)

