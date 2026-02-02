"""
Health Check and Monitoring System for LivraFaso
Provides real-time monitoring of system components
"""

import time
from django.http import JsonResponse

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
from django.db import connection
from django.core.cache import cache
from django.contrib.auth import get_user_model
from missions.models import Mission
from chat.models import ChatMessage
from subscriptions.models import UserSubscription
from datetime import datetime, timedelta

User = get_user_model()

class HealthCheckService:
    """Comprehensive health check service"""
    
    @staticmethod
    def get_system_health():
        """Get overall system health status"""
        start_time = time.time()
        
        health_data = {
            'timestamp': datetime.now().isoformat(),
            'status': 'healthy',
            'checks': {},
            'metrics': {},
            'response_time': 0
        }
        
        # Database health
        db_health = HealthCheckService._check_database()
        health_data['checks']['database'] = db_health
        
        # Cache health
        cache_health = HealthCheckService._check_cache()
        health_data['checks']['cache'] = cache_health
        
        # System resources
        system_health = HealthCheckService._check_system_resources()
        health_data['checks']['system'] = system_health
        
        # Application metrics
        app_metrics = HealthCheckService._get_application_metrics()
        health_data['metrics'] = app_metrics
        
        # Overall status
        if not all(check['status'] == 'healthy' for check in health_data['checks'].values()):
            health_data['status'] = 'degraded'
        
        health_data['response_time'] = round((time.time() - start_time) * 1000, 2)
        
        return health_data
    
    @staticmethod
    def _check_database():
        """Check database connectivity and performance"""
        try:
            start_time = time.time()
            
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
                
                # Check active connections
                cursor.execute("""
                    SELECT count(*) FROM pg_stat_activity 
                    WHERE state = 'active' AND pid != pg_backend_pid()
                """)
                active_connections = cursor.fetchone()[0]
                
                # Check database size
                cursor.execute("""
                    SELECT pg_size_pretty(pg_database_size(current_database()))
                """)
                db_size = cursor.fetchone()[0]
            
            response_time = round((time.time() - start_time) * 1000, 2)
            
            return {
                'status': 'healthy',
                'response_time_ms': response_time,
                'active_connections': active_connections,
                'database_size': db_size,
                'message': 'Database is responsive'
            }
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'message': 'Database connection failed'
            }
    
    @staticmethod
    def _check_cache():
        """Check cache connectivity and performance"""
        try:
            start_time = time.time()
            
            # Test cache write/read
            test_key = f'health_check_{int(time.time())}'
            test_value = 'test_value'
            
            cache.set(test_key, test_value, 60)
            retrieved_value = cache.get(test_key)
            cache.delete(test_key)
            
            if retrieved_value != test_value:
                raise Exception("Cache read/write test failed")
            
            response_time = round((time.time() - start_time) * 1000, 2)
            
            return {
                'status': 'healthy',
                'response_time_ms': response_time,
                'message': 'Cache is responsive'
            }
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'message': 'Cache connection failed'
            }
    
    @staticmethod
    def _check_system_resources():
        """Check system resource usage"""
        if not PSUTIL_AVAILABLE:
            return {
                'status': 'healthy',
                'message': 'System resource monitoring unavailable (psutil not installed)',
                'cpu_percent': 0,
                'memory_percent': 0,
                'disk_percent': 0,
                'warnings': []
            }
        
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            status = 'healthy'
            warnings = []
            
            if cpu_percent > 80:
                status = 'degraded'
                warnings.append(f'High CPU usage: {cpu_percent}%')
            
            if memory.percent > 85:
                status = 'degraded'
                warnings.append(f'High memory usage: {memory.percent}%')
            
            if disk.percent > 90:
                status = 'degraded'
                warnings.append(f'High disk usage: {disk.percent}%')
            
            return {
                'status': status,
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'disk_percent': disk.percent,
                'warnings': warnings,
                'message': 'System resources checked'
            }
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'message': 'System resource check failed'
            }
    
    @staticmethod
    def _get_application_metrics():
        """Get application-specific metrics"""
        try:
            now = datetime.now()
            last_hour = now - timedelta(hours=1)
            last_24h = now - timedelta(hours=24)
            
            # User metrics
            total_users = User.objects.count()
            active_users_24h = User.objects.filter(last_login__gte=last_24h).count()
            
            # Mission metrics
            total_missions = Mission.objects.count()
            missions_last_hour = Mission.objects.filter(created_at__gte=last_hour).count()
            missions_last_24h = Mission.objects.filter(created_at__gte=last_24h).count()
            
            # Mission status distribution
            mission_stats = {}
            for status in ['en_attente', 'acceptee', 'en_cours', 'livree', 'annulee']:
                count = Mission.objects.filter(status=status).count()
                mission_stats[status] = count
            
            # Chat metrics
            messages_count = ChatMessage.objects.count()
            recent_messages = ChatMessage.objects.filter(created_at__gte=last_24h).count()
            
            # Subscription metrics
            active_subscriptions = UserSubscription.objects.filter(
                is_active=True,
                end_date__gte=now
            ).count()
            
            return {
                'users': {
                    'total': total_users,
                    'active_24h': active_users_24h
                },
                'missions': {
                    'total': total_missions,
                    'last_hour': missions_last_hour,
                    'last_24h': missions_last_24h,
                    'by_status': mission_stats
                },
                'messages': {
                    'last_hour': messages_last_hour,
                    'last_24h': messages_last_24h
                },
                'subscriptions': {
                    'active': active_subscriptions
                }
            }
            
        except Exception as e:
            return {
                'error': str(e),
                'message': 'Failed to collect application metrics'
            }


def health_check_view(request):
    """Django view for health check endpoint"""
    health_data = HealthCheckService.get_system_health()
    
    status_code = 200 if health_data['status'] == 'healthy' else 503
    
    return JsonResponse(health_data, status=status_code)


def metrics_view(request):
    """Django view for metrics endpoint"""
    try:
        metrics = HealthCheckService._get_application_metrics()
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


class PerformanceMonitor:
    """Monitor performance metrics over time"""
    
    @staticmethod
    def log_performance_metrics():
        """Log performance metrics to cache for trending"""
        try:
            timestamp = int(time.time())
            health_data = HealthCheckService.get_system_health()
            
            # Store metrics in cache with TTL of 24 hours
            cache_key = f'performance_metrics_{timestamp}'
            cache.set(cache_key, health_data, 86400)
            
            # Keep only last 24 hours of metrics
            PerformanceMonitor._cleanup_old_metrics()
            
            return True
            
        except Exception as e:
            print(f"Failed to log performance metrics: {e}")
            return False
    
    @staticmethod
    def _cleanup_old_metrics():
        """Remove metrics older than 24 hours"""
        try:
            cutoff_time = int(time.time()) - 86400
            
            # This would require a more sophisticated cache implementation
            # For now, we rely on TTL to handle cleanup
            pass
            
        except Exception:
            pass
    
    @staticmethod
    def get_performance_trend(hours=24):
        """Get performance trend over specified hours"""
        try:
            current_time = int(time.time())
            start_time = current_time - (hours * 3600)
            
            metrics = []
            
            # This is a simplified implementation
            # In production, you'd want to use a time-series database
            for i in range(hours):
                timestamp = start_time + (i * 3600)
                cache_key = f'performance_metrics_{timestamp}'
                metric = cache.get(cache_key)
                
                if metric:
                    metrics.append({
                        'timestamp': timestamp,
                        'response_time': metric.get('response_time', 0),
                        'cpu_percent': metric.get('checks', {}).get('system', {}).get('cpu_percent', 0),
                        'memory_percent': metric.get('checks', {}).get('system', {}).get('memory_percent', 0)
                    })
            
            return metrics
            
        except Exception as e:
            return {'error': str(e)}


# Alerting system
class AlertManager:
    """Manage system alerts and notifications"""
    
    ALERT_THRESHOLDS = {
        'cpu_percent': 80,
        'memory_percent': 85,
        'disk_percent': 90,
        'response_time': 5000,  # 5 seconds
        'database_connections': 90
    }
    
    @staticmethod
    def check_alerts():
        """Check for alert conditions"""
        health_data = HealthCheckService.get_system_health()
        alerts = []
        
        # System resource alerts
        system_check = health_data.get('checks', {}).get('system', {})
        if system_check.get('cpu_percent', 0) > AlertManager.ALERT_THRESHOLDS['cpu_percent']:
            alerts.append({
                'type': 'cpu_high',
                'severity': 'warning',
                'message': f"High CPU usage: {system_check['cpu_percent']}%",
                'timestamp': datetime.now().isoformat()
            })
        
        if system_check.get('memory_percent', 0) > AlertManager.ALERT_THRESHOLDS['memory_percent']:
            alerts.append({
                'type': 'memory_high',
                'severity': 'warning',
                'message': f"High memory usage: {system_check['memory_percent']}%",
                'timestamp': datetime.now().isoformat()
            })
        
        # Response time alerts
        if health_data.get('response_time', 0) > AlertManager.ALERT_THRESHOLDS['response_time']:
            alerts.append({
                'type': 'response_time_high',
                'severity': 'critical',
                'message': f"High response time: {health_data['response_time']}ms",
                'timestamp': datetime.now().isoformat()
            })
        
        # Database alerts
        db_check = health_data.get('checks', {}).get('database', {})
        if db_check.get('status') != 'healthy':
            alerts.append({
                'type': 'database_unhealthy',
                'severity': 'critical',
                'message': db_check.get('message', 'Database is unhealthy'),
                'timestamp': datetime.now().isoformat()
            })
        
        return alerts
    
    @staticmethod
    def send_alert_notification(alert):
        """Send alert notification (implement with your preferred method)"""
        # This could integrate with email, Slack, SMS, etc.
        print(f"ALERT [{alert['severity'].upper()}]: {alert['message']}")
        
        # Store alert in cache for dashboard display
        alert_key = f"alert_{int(time.time())}"
        cache.set(alert_key, alert, 3600)  # Keep for 1 hour
