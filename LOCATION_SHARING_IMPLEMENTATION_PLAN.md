# Location Sharing Feature - Implementation Plan

## Overview
This document outlines the implementation plan for the "Share Position" feature (US-31 to US-39) in the DayDo Family App backend, with forward-looking considerations for US-44 and US-45. The feature allows family members to share their location with the family for safety and coordination purposes.

## Implementation Progress
- **Phase 1 (Models)**: ✅ Completed — `Location` and `SharingStatus` models added to `daydo/models.py` with indexed fields and helper methods.
- **Phase 2 (Serializers)**: ✅ Completed — `LocationSerializer`, `SharingStatusSerializer`, and `FamilyLocationSerializer` implemented in `daydo/serializers.py`.
- **Phase 3 (ViewSet & Endpoints)**: ✅ Completed — `LocationViewSet` added to `daydo/views.py` with share/update/stop/family actions, duration parsing, and location history enforcement.
- **Phase 4 (URL Routing)**: ✅ Completed — `LocationViewSet` registered in `daydo/urls.py` under `/api/location/`.
- **Phase 5 (Background Tasks)**: ✅ Completed — `expire_sharing_sessions` management command created to disable expired temporary sessions.
- **Phase 6 (Migrations, Security, Tests, Optimization)**: ✅ Completed — Migration `0011_location_sharingstatus` added, integration tests (`test_integration.sh`) now cover location-sharing scenarios, and permission/expiry guardrails verified.

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
- **US-44**: Live map view (future - not in scope for current iteration)
- **US-45**: Radius-based naming of locations (future - data model must support)

### Technical Requirements
1. **Data Models**: Location and SharingStatus models
2. **API Endpoints**: 4 custom endpoints (share, update, stop, family)
3. **Performance**: Optimized queries for latest position retrieval
4. **Data Management**: Auto-delete oldest records when >10 per user
5. **Background Tasks**: Auto-expire temporary sharing sessions
6. **Security**: Family-scoped access, authentication required
7. **Future Readiness**: Data model extensibility for named geofenced zones (US-45)

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
- Future-ready for geofence lookups (US-45) by keeping raw coordinates per sample

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

### 1.3 (Future) LocationAnchor Model (US-45)
> _Deferred to a later phase; documented here to keep the database design future-proof._

US-45 requires storing named places (e.g., "Home", "School") with a radius. The current iteration will not implement the model, but we plan to introduce:

```python
class LocationAnchor(models.Model):
    """Named geofence/anchor for a family."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    family = models.ForeignKey(Family, on_delete=models.CASCADE, related_name='location_anchors')
    name = models.CharField(max_length=100)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    radius_meters = models.PositiveIntegerField(default=100)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_anchors')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        unique_together = ('family', 'name')
```

**Rationale**:
- By documenting the future model now, we ensure current migrations leave room for easy addition later.
- The `Location` model already stores raw coordinates allowing future calculations (point-in-radius checks) without schema changes.

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
2. Get or create `