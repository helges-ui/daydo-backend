"""
Dashboard service for DayDo application.
Handles dashboard data calculation and caching.
"""
from django.core.cache import cache
from django.db.models import Count, Q
from daydo.models import Family


class DashboardService:
    """Service class for dashboard operations"""
    
    CACHE_TIMEOUT = 300  # 5 minutes
    
    @staticmethod
    def get_cache_key(family_id, user_id=None):
        """Generate cache key for dashboard data"""
        if user_id:
            return f'dashboard:{family_id}:{user_id}'
        return f'dashboard:{family_id}'
    
    @staticmethod
    def calculate_family_metrics(family):
        """
        Calculate family dashboard metrics with optimized queries.
        
        Args:
            family: Family instance
            
        Returns:
            dict: Dashboard metrics including counts and activity
        """
        # Use a single annotated query to get all counts at once
        family_data = Family.objects.filter(id=family.id).annotate(
            total_members=Count('members', distinct=True),
            total_children=Count('child_profiles', distinct=True),
            children_with_accounts=Count(
                'child_profiles',
                filter=Q(child_profiles__is_view_only=False) & Q(child_profiles__linked_user__isnull=False),
                distinct=True
            ),
            children_view_only=Count(
                'child_profiles',
                filter=Q(child_profiles__is_view_only=True),
                distinct=True
            )
        ).first()
        
        return {
            'family_name': family.name,
            'total_members': family_data.total_members if family_data else 0,
            'total_children': family_data.total_children if family_data else 0,
            'children_with_accounts': family_data.children_with_accounts if family_data else 0,
            'children_view_only': family_data.children_view_only if family_data else 0,
        }
    
    @staticmethod
    def get_recent_activity(family, limit=10):
        """
        Get recent family activity (placeholder for future implementation).
        
        Args:
            family: Family instance
            limit: Maximum number of activities to return
            
        Returns:
            list: Recent activity items
        """
        # TODO: Implement when activity tracking is added
        return []
    
    @staticmethod
    def get_family_dashboard(family_id, user_id=None, use_cache=True):
        """
        Get dashboard data with caching.
        
        Args:
            family_id: Family UUID
            user_id: User UUID (optional, for user-specific caching)
            use_cache: Whether to use cache (default: True)
            
        Returns:
            dict: Dashboard data including metrics and activity
        """
        cache_key = DashboardService.get_cache_key(family_id, user_id)
        
        # Try to get from cache
        if use_cache:
            dashboard_data = cache.get(cache_key)
            if dashboard_data is not None:
                return dashboard_data
        
        # Calculate dashboard data
        try:
            family = Family.objects.get(id=family_id)
        except Family.DoesNotExist:
            return None
        
        dashboard_data = DashboardService.calculate_family_metrics(family)
        dashboard_data['recent_activity'] = DashboardService.get_recent_activity(family)
        
        # Cache the result
        if use_cache:
            cache.set(cache_key, dashboard_data, timeout=DashboardService.CACHE_TIMEOUT)
        
        return dashboard_data
    
    @staticmethod
    def invalidate_cache(family_id, user_id=None):
        """
        Invalidate dashboard cache for a family.
        
        Args:
            family_id: Family UUID
            user_id: User UUID (optional, for user-specific cache)
        """
        cache_key = DashboardService.get_cache_key(family_id, user_id)
        cache.delete(cache_key)
        
        # Also invalidate general family cache
        if user_id:
            general_cache_key = DashboardService.get_cache_key(family_id)
            cache.delete(general_cache_key)

