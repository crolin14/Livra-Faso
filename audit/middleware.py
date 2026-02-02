"""
Security Audit Middleware for LivraFaso
Tracks user actions, IP addresses, and security events
"""

import json
import time
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth.models import AnonymousUser
from django.http import JsonResponse
from django.core.cache import cache
# from audit.models import AuditLog, SecurityEvent
import logging

logger = logging.getLogger(__name__)

class SecurityAuditMiddleware(MiddlewareMixin):
    """Middleware to log security events and user actions"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)
    
    def process_request(self, request):
        """Process incoming requests for security logging"""
        request.start_time = time.time()
        request.client_ip = self.get_client_ip(request)
        
        # Check for suspicious activity
        if self.is_suspicious_request(request):
            self.log_security_event(request, 'SUSPICIOUS_REQUEST')
        
        # Rate limiting check
        if self.check_rate_limit(request):
            return JsonResponse({
                'error': 'Trop de requêtes. Veuillez patienter.',
                'code': 'RATE_LIMITED'
            }, status=429)
        
        return None
    
    def process_response(self, request, response):
        """Process responses and log audit information"""
        if hasattr(request, 'start_time'):
            response_time = time.time() - request.start_time
            
            # Log significant actions
            if self.should_log_action(request, response):
                self.create_audit_log(request, response, response_time)
            
            # Log failed authentication attempts
            if response.status_code == 401 or response.status_code == 403:
                self.log_security_event(request, 'AUTH_FAILURE', {
                    'status_code': response.status_code,
                    'path': request.path
                })
        
        return response
    
    def get_client_ip(self, request):
        """Extract real client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def is_suspicious_request(self, request):
        """Detect suspicious request patterns"""
        suspicious_patterns = [
            '/admin/login/',
            'wp-admin',
            'phpmyadmin',
            '.env',
            'config.php',
            'shell.php'
        ]
        
        path = request.path.lower()
        return any(pattern in path for pattern in suspicious_patterns)
    
    def check_rate_limit(self, request):
        """Check if request exceeds rate limits"""
        ip = request.client_ip
        cache_key = f"rate_limit_{ip}"
        
        # Get current request count
        current_count = cache.get(cache_key, 0)
        
        # Rate limit: 100 requests per minute per IP
        if current_count >= 100:
            self.log_security_event(request, 'RATE_LIMIT_EXCEEDED')
            return True
        
        # Increment counter
        cache.set(cache_key, current_count + 1, timeout=60)
        return False
    
    def should_log_action(self, request, response):
        """Determine if action should be logged"""
        # Log all POST, PUT, DELETE requests
        if request.method in ['POST', 'PUT', 'DELETE', 'PATCH']:
            return True
        
        # Log authentication related actions
        auth_paths = ['/login/', '/logout/', '/register/', '/dashboard/']
        if any(path in request.path for path in auth_paths):
            return True
        
        # Log API calls
        if request.path.startswith('/api/'):
            return True
        
        # Log admin actions
        if request.path.startswith('/admin/'):
            return True
        
        return False
    
    def create_audit_log(self, request, response, response_time):
        """Create audit log entry"""
        try:
            user = request.user if hasattr(request, 'user') and not isinstance(request.user, AnonymousUser) else None
            
            # Extract request data
            request_data = {}
            if request.method == 'POST' and request.content_type == 'application/json':
                try:
                    request_data = json.loads(request.body.decode('utf-8'))
                    # Remove sensitive data
                    sensitive_fields = ['password', 'token', 'secret', 'key']
                    for field in sensitive_fields:
                        if field in request_data:
                            request_data[field] = '[REDACTED]'
                except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
                    pass
            
            # AuditLog.objects.create(
            #     user=user,
            #     action_type='api_call' if request.path.startswith('/api/') else 'view',
            #     action_description=f"{request.method} {request.path}",
            #     user_ip=request.client_ip,
            #     user_agent=request.META.get('HTTP_USER_AGENT', ''),
            #     additional_data={
            #         'request_data': request_data,
            #         'response_status': response.status_code,
            #         'response_time': response_time
            #     },
            #     request_path=request.path,
            #     request_method=request.method,
            #     session_key=request.session.session_key if hasattr(request, 'session') else None
            # )
            logger.info(f"Audit: {request.method} {request.path} by {user} - {response.status_code}")
            
        except Exception as e:
            logger.error(f"Failed to create audit log: {str(e)}")
    
    def log_security_event(self, request, event_type, additional_data=None):
        """Log security events"""
        try:
            user = request.user if hasattr(request, 'user') and not isinstance(request.user, AnonymousUser) else None
            
            event_data = {
                'path': request.path,
                'method': request.method,
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                'referer': request.META.get('HTTP_REFERER', ''),
            }
            
            if additional_data:
                event_data.update(additional_data)
            
            # SecurityEvent.objects.create(
            #     user=user,
            #     event_type=event_type.lower(),
            #     source_ip=request.client_ip,
            #     user_agent=request.META.get('HTTP_USER_AGENT', ''),
            #     description=f"Security event: {event_type}",
            #     request_path=request.path,
            #     request_method=request.method,
            #     request_data=event_data,
            #     risk_level=self.get_event_severity(event_type)
            # )
            logger.warning(f"Security event: {event_type} from {request.client_ip}")
            
            logger.warning(f"Security event: {event_type} from {request.client_ip}")
            
        except Exception as e:
            logger.error(f"Failed to log security event: {str(e)}")
    
    def get_event_severity(self, event_type):
        """Get severity level for event type"""
        severity_map = {
            'suspicious_request': 'medium',
            'auth_failure': 'medium', 
            'rate_limit_exceeded': 'high',
            'brute_force_attempt': 'high',
            'sql_injection_attempt': 'critical',
            'xss_attempt': 'high',
            'unauthorized_access': 'high'
        }
        
        return severity_map.get(event_type, 'low')

class IPBlockingMiddleware(MiddlewareMixin):
    """Middleware to block malicious IP addresses"""
    
    def process_request(self, request):
        """Check if IP is blocked"""
        client_ip = self.get_client_ip(request)
        
        # Check if IP is in blocked list (cached)
        blocked_ips = cache.get('blocked_ips', set())
        
        if client_ip in blocked_ips:
            logger.warning(f"Blocked request from IP: {client_ip}")
            return JsonResponse({
                'error': 'Accès refusé',
                'code': 'IP_BLOCKED'
            }, status=403)
        
        return None
    
    def get_client_ip(self, request):
        """Extract real client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

def block_ip(ip_address, reason="Manual block", duration_hours=24):
    """Block an IP address"""
    blocked_ips = cache.get('blocked_ips', set())
    blocked_ips.add(ip_address)
    
    # Cache for specified duration
    cache.set('blocked_ips', blocked_ips, timeout=duration_hours * 3600)
    
    logger.info(f"Blocked IP {ip_address} for {duration_hours} hours. Reason: {reason}")

def unblock_ip(ip_address):
    """Unblock an IP address"""
    blocked_ips = cache.get('blocked_ips', set())
    blocked_ips.discard(ip_address)
    
    cache.set('blocked_ips', blocked_ips, timeout=86400)  # 24 hours
    
    logger.info(f"Unblocked IP {ip_address}")

def get_security_stats():
    """Get security statistics for dashboard"""
    from datetime import datetime, timedelta
    
    now = datetime.now()
    last_24h = now - timedelta(hours=24)
    last_7d = now - timedelta(days=7)
    
    stats = {
        'total_events_24h': SecurityEvent.objects.filter(
            created_at__gte=last_24h
        ).count(),
        'critical_events_24h': SecurityEvent.objects.filter(
            created_at__gte=last_24h,
            severity='critical'
        ).count(),
        'blocked_ips': len(cache.get('blocked_ips', set())),
        'top_threats': list(SecurityEvent.objects.filter(
            created_at__gte=last_7d
        ).values('event_type').annotate(
            count=models.Count('id')
        ).order_by('-count')[:5]),
        'recent_events': list(SecurityEvent.objects.filter(
            created_at__gte=last_24h
        ).order_by('-created_at')[:10].values(
            'event_type', 'ip_address', 'severity', 'created_at'
        ))
    }
    
    return stats
