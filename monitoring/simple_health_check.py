"""
Simple Health Check for LivraFaso (without psutil dependency)
"""

import time
from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache
from django.contrib.auth import get_user_model
from missions.models import Mission
from chat.models import ChatMessage
from subscriptions.models import UserSubscription
from datetime import datetime, timedelta

User = get_user_model()

def simple_health_check_view(request):
    """Simple health check endpoint without external dependencies"""
    start_time = time.time()
    
    health_data = {
        'timestamp': datetime.now().isoformat(),
        'status': 'healthy',
        'checks': {},
        'response_time': 0
    }
    
    # Database health
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        
        health_data['checks']['database'] = {
            'status': 'healthy',
            'message': 'Database is responsive'
        }
    except Exception as e:
        health_data['checks']['database'] = {
            'status': 'unhealthy',
            'error': str(e)
        }
        health_data['status'] = 'degraded'
    
    # Cache health
    try:
        test_key = f'health_check_{int(time.time())}'
        cache.set(test_key, 'test', 60)
        cache.get(test_key)
        cache.delete(test_key)
        
        health_data['checks']['cache'] = {
            'status': 'healthy',
            'message': 'Cache is responsive'
        }
    except Exception as e:
        health_data['checks']['cache'] = {
            'status': 'unhealthy',
            'error': str(e)
        }
        health_data['status'] = 'degraded'
    
    health_data['response_time'] = round((time.time() - start_time) * 1000, 2)
    
    status_code = 200 if health_data['status'] == 'healthy' else 503
    return JsonResponse(health_data, status=status_code)


def simple_metrics_view(request):
    """Simple metrics endpoint"""
    try:
        now = datetime.now()
        last_24h = now - timedelta(hours=24)
        
        metrics = {
            'users': {
                'total': User.objects.count(),
                'active_24h': User.objects.filter(last_login__gte=last_24h).count()
            },
            'missions': {
                'total': Mission.objects.count(),
                'last_24h': Mission.objects.filter(created_at__gte=last_24h).count()
            },
            'messages': {
                'last_24h': ChatMessage.objects.filter(created_at__gte=last_24h).count()
            },
            'subscriptions': {
                'active': UserSubscription.objects.filter(
                    is_active=True,
                    end_date__gte=now
                ).count()
            }
        }
        
        return JsonResponse({
            'status': 'success',
            'metrics': metrics,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }, status=500)
