"""
Cache utilities for LivraFaso application
Provides Redis caching for dashboard data, mission stats, and real-time updates
"""

from django.core.cache import cache
from django.conf import settings
from django.db.models import Count, Sum, Avg
from datetime import datetime, timedelta
import json
import logging

logger = logging.getLogger(__name__)

class LivraFasoCache:
    """Redis cache manager for LivraFaso"""
    
    # Cache timeouts (in seconds)
    DASHBOARD_STATS_TIMEOUT = 300  # 5 minutes
    MISSION_LIST_TIMEOUT = 60      # 1 minute
    USER_PROFILE_TIMEOUT = 900     # 15 minutes
    ANALYTICS_TIMEOUT = 1800       # 30 minutes
    
    @staticmethod
    def get_dashboard_stats(user_id, user_type):
        """Get cached dashboard statistics"""
        cache_key = f"dashboard_stats_{user_type}_{user_id}"
        stats = cache.get(cache_key)
        
        if stats is None:
            logger.info(f"Cache miss for dashboard stats: {cache_key}")
            return None
        
        logger.info(f"Cache hit for dashboard stats: {cache_key}")
        return json.loads(stats)
    
    @staticmethod
    def set_dashboard_stats(user_id, user_type, stats_data):
        """Cache dashboard statistics"""
        cache_key = f"dashboard_stats_{user_type}_{user_id}"
        cache.set(
            cache_key, 
            json.dumps(stats_data, default=str),
            timeout=LivraFasoCache.DASHBOARD_STATS_TIMEOUT
        )
        logger.info(f"Cached dashboard stats: {cache_key}")
    
    @staticmethod
    def get_mission_list(user_id, filters=None):
        """Get cached mission list"""
        filter_hash = hash(str(sorted(filters.items()))) if filters else 'all'
        cache_key = f"missions_{user_id}_{filter_hash}"
        
        missions = cache.get(cache_key)
        if missions is None:
            logger.info(f"Cache miss for missions: {cache_key}")
            return None
        
        logger.info(f"Cache hit for missions: {cache_key}")
        return json.loads(missions)
    
    @staticmethod
    def set_mission_list(user_id, missions_data, filters=None):
        """Cache mission list"""
        filter_hash = hash(str(sorted(filters.items()))) if filters else 'all'
        cache_key = f"missions_{user_id}_{filter_hash}"
        
        cache.set(
            cache_key,
            json.dumps(missions_data, default=str),
            timeout=LivraFasoCache.MISSION_LIST_TIMEOUT
        )
        logger.info(f"Cached missions: {cache_key}")
    
    @staticmethod
    def invalidate_user_cache(user_id):
        """Invalidate all cache entries for a user"""
        patterns = [
            f"dashboard_stats_*_{user_id}",
            f"missions_{user_id}_*",
            f"profile_{user_id}",
            f"analytics_{user_id}_*"
        ]
        
        for pattern in patterns:
            cache.delete_pattern(pattern)
        
        logger.info(f"Invalidated cache for user: {user_id}")
    
    @staticmethod
    def get_analytics_data(user_id, period='week'):
        """Get cached analytics data"""
        cache_key = f"analytics_{user_id}_{period}"
        data = cache.get(cache_key)
        
        if data is None:
            logger.info(f"Cache miss for analytics: {cache_key}")
            return None
        
        logger.info(f"Cache hit for analytics: {cache_key}")
        return json.loads(data)
    
    @staticmethod
    def set_analytics_data(user_id, analytics_data, period='week'):
        """Cache analytics data"""
        cache_key = f"analytics_{user_id}_{period}"
        cache.set(
            cache_key,
            json.dumps(analytics_data, default=str),
            timeout=LivraFasoCache.ANALYTICS_TIMEOUT
        )
        logger.info(f"Cached analytics: {cache_key}")

def cache_dashboard_data(view_func):
    """Decorator to cache dashboard data"""
    def wrapper(request, *args, **kwargs):
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return view_func(request, *args, **kwargs)
        
        user_id = request.user.id
        user_type = getattr(request.user, 'user_type', 'client')
        
        # Try to get cached data
        cached_stats = LivraFasoCache.get_dashboard_stats(user_id, user_type)
        
        if cached_stats:
            # Add cached data to request context
            request.cached_stats = cached_stats
        
        response = view_func(request, *args, **kwargs)
        
        # Cache new data if available
        if hasattr(request, 'dashboard_stats'):
            LivraFasoCache.set_dashboard_stats(user_id, user_type, request.dashboard_stats)
        
        return response
    
    return wrapper

def invalidate_mission_cache(mission_id):
    """Invalidate cache when mission is updated"""
    from missions.models import Mission
    
    try:
        mission = Mission.objects.get(id=mission_id)
        
        # Invalidate cache for client
        if mission.client:
            LivraFasoCache.invalidate_user_cache(mission.client.id)
        
        # Invalidate cache for livreur
        if mission.livreur:
            LivraFasoCache.invalidate_user_cache(mission.livreur.id)
        
        # Invalidate cache for entreprise
        if hasattr(mission, 'entreprise') and mission.entreprise:
            LivraFasoCache.invalidate_user_cache(mission.entreprise.id)
        
        logger.info(f"Invalidated mission cache for mission: {mission_id}")
        
    except Mission.DoesNotExist:
        logger.warning(f"Mission not found for cache invalidation: {mission_id}")

def warm_cache_for_user(user):
    """Pre-warm cache for a user"""
    from missions.models import Mission
    from django.db.models import Q
    
    try:
        user_id = user.id
        user_type = getattr(user, 'user_type', 'client')
        
        # Warm dashboard stats
        if user_type == 'client':
            stats = {
                'total_missions': Mission.objects.filter(client=user).count(),
                'active_missions': Mission.objects.filter(
                    client=user, 
                    status__in=['pending', 'accepted', 'in_progress']
                ).count(),
                'completed_missions': Mission.objects.filter(
                    client=user, 
                    status='delivered'
                ).count(),
                'total_spent': Mission.objects.filter(
                    client=user, 
                    status='delivered'
                ).aggregate(total=Sum('price'))['total'] or 0
            }
        
        elif user_type == 'livreur':
            stats = {
                'available_missions': Mission.objects.filter(
                    status='pending',
                    livreur__isnull=True
                ).count(),
                'my_missions': Mission.objects.filter(livreur=user).count(),
                'completed_missions': Mission.objects.filter(
                    livreur=user,
                    status='delivered'
                ).count(),
                'total_earnings': Mission.objects.filter(
                    livreur=user,
                    status='delivered'
                ).aggregate(total=Sum('price'))['total'] or 0
            }
        
        else:  # entreprise
            stats = {
                'total_missions': Mission.objects.filter(
                    Q(client=user) | Q(entreprise=user)
                ).count(),
                'active_missions': Mission.objects.filter(
                    Q(client=user) | Q(entreprise=user),
                    status__in=['pending', 'accepted', 'in_progress']
                ).count(),
                'available_livreurs': user.objects.filter(
                    user_type='livreur',
                    livreurprofile__is_available=True
                ).count() if hasattr(user, 'objects') else 0,
                'monthly_volume': Mission.objects.filter(
                    Q(client=user) | Q(entreprise=user),
                    created_at__gte=datetime.now() - timedelta(days=30)
                ).count()
            }
        
        LivraFasoCache.set_dashboard_stats(user_id, user_type, stats)
        logger.info(f"Warmed cache for user: {user_id} ({user_type})")
        
    except Exception as e:
        logger.error(f"Error warming cache for user {user.id}: {str(e)}")

# Redis health check
def check_redis_connection():
    """Check Redis connection health"""
    try:
        cache.set('health_check', 'ok', timeout=10)
        result = cache.get('health_check')
        cache.delete('health_check')
        
        return result == 'ok'
    except Exception as e:
        logger.error(f"Redis health check failed: {str(e)}")
        return False
