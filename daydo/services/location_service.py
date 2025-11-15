"""
Location service for DayDo application.
Handles location sharing business logic and location data processing.
"""
import math
from typing import Dict, List, Optional
from django.utils import timezone
from datetime import timedelta
from django.db.models import OuterRef, Subquery

from ..models import Family, User, ChildProfile, Location, SharingStatus, Geofence


class LocationService:
    """Service for location sharing business logic"""
    
    STALE_THRESHOLD_MINUTES = 5
    
    @staticmethod
    def process_sharing_status(sharing_status: Optional[SharingStatus]) -> Dict:
        """
        Process sharing status and handle expiration.
        Returns dict with sharing status fields.
        
        Args:
            sharing_status: SharingStatus instance or None
            
        Returns:
            dict: Dictionary with sharing status fields
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
            user_data: Dict with user info (id, name, avatar, color, sharing_status)
            location_data: Dict with location info (latitude, longitude, timestamp, accuracy)
            geofence_match: Matched geofence or None
            stale_threshold: Timestamp threshold for stale locations
            
        Returns:
            dict: Location payload dictionary
        """
        is_stale = bool(
            location_data and 
            location_data.get('timestamp') and 
            location_data['timestamp'] < stale_threshold
        )
        
        # Process sharing status
        sharing_status_dict = LocationService.process_sharing_status(
            user_data.get('sharing_status')
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
                **sharing_status_dict
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
                **sharing_status_dict
            }
    
    @staticmethod
    def get_family_locations(family: Family) -> List[Dict]:
        """
        Get all family locations with optimized queries.
        
        Args:
            family: Family instance
            
        Returns:
            list: List of location payload dictionaries
        """
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
    def _match_geofence(latitude: Optional[float], longitude: Optional[float], geofences: List[Geofence]) -> Optional[Geofence]:
        """
        Match location to geofence.
        
        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            geofences: List of geofences to check against
            
        Returns:
            Geofence: First matching geofence or None
        """
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
    def _haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate the great-circle distance between two points on the Earth (in meters).
        
        Args:
            lat1: Latitude of first point
            lon1: Longitude of first point
            lat2: Latitude of second point
            lon2: Longitude of second point
            
        Returns:
            float: Distance in meters
        """
        radius = 6371000  # Earth radius in meters
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)
        
        a = math.sin(delta_phi / 2) ** 2 + \
            math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return radius * c

