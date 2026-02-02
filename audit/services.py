from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from django.conf import settings
from .models import AuditLog, SecurityEvent, SystemMetrics, AdminAction, DataExport
import json
import logging
import psutil
import os

User = get_user_model()
logger = logging.getLogger(__name__)


class AuditService:
    """Service principal pour l'audit trail"""
    
    @staticmethod
    def log_action(user, action_type, description, content_object=None, 
                   old_values=None, new_values=None, request=None, 
                   severity='low', additional_data=None):
        """
        Enregistre une action dans l'audit trail
        """
        try:
            audit_data = {
                'user': user,
                'action_type': action_type,
                'action_description': description,
                'severity': severity,
                'old_values': old_values,
                'new_values': new_values,
                'additional_data': additional_data or {},
            }
            
            # Ajouter l'objet concerné si fourni
            if content_object:
                audit_data['content_type'] = ContentType.objects.get_for_model(content_object)
                audit_data['object_id'] = str(content_object.pk)
            
            # Ajouter les données de la requête si disponibles
            if request:
                audit_data.update({
                    'user_ip': AuditService.get_client_ip(request),
                    'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                    'session_key': request.session.session_key or '',
                    'request_path': request.path,
                    'request_method': request.method,
                })
            
            # Déterminer si l'action nécessite une révision
            audit_data['requires_review'] = AuditService.requires_review(action_type, severity)
            audit_data['is_sensitive'] = AuditService.is_sensitive_action(action_type, content_object)
            
            audit_log = AuditLog.objects.create(**audit_data)
            
            # Notifier en temps réel si critique
            if severity in ['high', 'critical']:
                AuditService.notify_critical_action(audit_log)
            
            return audit_log
            
        except Exception as e:
            logger.error(f"Erreur lors de l'enregistrement de l'audit: {e}")
            return None
    
    @staticmethod
    def log_security_event(event_type, source_ip, description, user=None, 
                          request=None, risk_level='medium', is_blocked=False):
        """
        Enregistre un événement de sécurité
        """
        try:
            event_data = {
                'event_type': event_type,
                'source_ip': source_ip,
                'description': description,
                'user': user,
                'risk_level': risk_level,
                'is_blocked': is_blocked,
            }
            
            if request:
                event_data.update({
                    'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                    'request_path': request.path,
                    'request_method': request.method,
                    'request_data': AuditService.sanitize_request_data(request),
                })
            
            security_event = SecurityEvent.objects.create(**event_data)
            
            # Notifier immédiatement les événements critiques
            if risk_level == 'critical':
                AuditService.notify_security_event(security_event)
            
            return security_event
            
        except Exception as e:
            logger.error(f"Erreur lors de l'enregistrement de l'événement de sécurité: {e}")
            return None
    
    @staticmethod
    def log_admin_action(admin_user, category, action, description, 
                        target_user=None, target_object_type=None, 
                        target_object_id=None, before_state=None, 
                        after_state=None, request=None, reason=''):
        """
        Enregistre une action d'administrateur
        """
        try:
            action_data = {
                'admin_user': admin_user,
                'category': category,
                'action': action,
                'description': description,
                'target_user': target_user,
                'target_object_type': target_object_type,
                'target_object_id': target_object_id,
                'before_state': before_state,
                'after_state': after_state,
                'reason': reason,
            }
            
            if request:
                action_data.update({
                    'ip_address': AuditService.get_client_ip(request),
                    'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                })
            
            # Déterminer si l'action est critique
            action_data['is_critical'] = AuditService.is_critical_admin_action(category, action)
            
            admin_action = AdminAction.objects.create(**action_data)
            
            # Log également dans l'audit général
            AuditService.log_action(
                user=admin_user,
                action_type='admin_action',
                description=f"Action admin: {action}",
                severity='high' if action_data['is_critical'] else 'medium',
                request=request,
                additional_data={
                    'admin_action_id': str(admin_action.id),
                    'category': category,
                    'target_user': target_user.username if target_user else None,
                }
            )
            
            return admin_action
            
        except Exception as e:
            logger.error(f"Erreur lors de l'enregistrement de l'action admin: {e}")
            return None
    
    @staticmethod
    def log_data_export(user, export_type, format, filters_applied=None, 
                       records_count=0, contains_sensitive_data=False, 
                       access_reason='', request=None):
        """
        Enregistre un export de données
        """
        try:
            export_data = {
                'user': user,
                'export_type': export_type,
                'format': format,
                'filters_applied': filters_applied,
                'records_count': records_count,
                'contains_sensitive_data': contains_sensitive_data,
                'access_reason': access_reason,
            }
            
            data_export = DataExport.objects.create(**export_data)
            
            # Log dans l'audit général
            AuditService.log_action(
                user=user,
                action_type='export',
                description=f"Export {export_type} ({format}) - {records_count} enregistrements",
                severity='high' if contains_sensitive_data else 'medium',
                request=request,
                additional_data={
                    'export_id': str(data_export.id),
                    'export_type': export_type,
                    'contains_sensitive_data': contains_sensitive_data,
                }
            )
            
            return data_export
            
        except Exception as e:
            logger.error(f"Erreur lors de l'enregistrement de l'export: {e}")
            return None
    
    @staticmethod
    def collect_system_metrics():
        """
        Collecte les métriques système
        """
        try:
            # Métriques système
            cpu_usage = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Métriques applicatives
            from django.contrib.sessions.models import Session
            from missions.models import Mission
            
            active_sessions = Session.objects.filter(
                expire_date__gte=timezone.now()
            ).count()
            
            today = timezone.now().date()
            missions_today = Mission.objects.filter(created_at__date=today)
            
            metrics_data = {
                'cpu_usage': cpu_usage,
                'memory_usage': memory.percent,
                'disk_usage': disk.percent,
                'active_sessions': active_sessions,
                'missions_created_today': missions_today.count(),
                'missions_completed_today': missions_today.filter(status='livree').count(),
                'revenue_today': sum(m.price or 0 for m in missions_today.filter(status='livree')),
                'new_users_today': User.objects.filter(date_joined__date=today).count(),
            }
            
            # Déterminer le statut système
            if cpu_usage > 90 or memory.percent > 90 or disk.percent > 90:
                metrics_data['system_status'] = 'critical'
            elif cpu_usage > 70 or memory.percent > 70 or disk.percent > 80:
                metrics_data['system_status'] = 'warning'
            else:
                metrics_data['system_status'] = 'healthy'
            
            return SystemMetrics.objects.create(**metrics_data)
            
        except Exception as e:
            logger.error(f"Erreur lors de la collecte des métriques: {e}")
            return None
    
    @staticmethod
    def get_client_ip(request):
        """Récupère l'IP réelle du client"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    @staticmethod
    def sanitize_request_data(request):
        """Nettoie les données de requête pour l'audit"""
        sensitive_fields = ['password', 'token', 'secret', 'key', 'csrf']
        
        data = {}
        if hasattr(request, 'POST') and request.POST:
            data['POST'] = {}
            for key, value in request.POST.items():
                if any(field in key.lower() for field in sensitive_fields):
                    data['POST'][key] = '[REDACTED]'
                else:
                    data['POST'][key] = value
        
        if hasattr(request, 'GET') and request.GET:
            data['GET'] = dict(request.GET.items())
        
        return data
    
    @staticmethod
    def requires_review(action_type, severity):
        """Détermine si une action nécessite une révision"""
        critical_actions = ['delete', 'admin_action', 'security_event']
        return action_type in critical_actions or severity in ['high', 'critical']
    
    @staticmethod
    def is_sensitive_action(action_type, content_object):
        """Détermine si une action est sensible"""
        sensitive_actions = ['delete', 'export', 'admin_action']
        if action_type in sensitive_actions:
            return True
        
        # Vérifier le type d'objet
        if content_object:
            sensitive_models = ['User', 'Mission', 'Payment']
            return content_object.__class__.__name__ in sensitive_models
        
        return False
    
    @staticmethod
    def is_critical_admin_action(category, action):
        """Détermine si une action admin est critique"""
        critical_categories = ['security', 'user_management', 'system_config']
        critical_actions = ['delete', 'disable', 'suspend', 'change_role', 'reset_password']
        
        return (category in critical_categories or 
                any(critical in action.lower() for critical in critical_actions))
    
    @staticmethod
    def notify_critical_action(audit_log):
        """Notifie les actions critiques en temps réel"""
        try:
            from notifications.websocket_service import send_role_notification, send_system_alert
            
            # Notifier les super admins
            send_role_notification(
                'super_admin',
                'Action critique détectée',
                f"{audit_log.user.username if audit_log.user else 'Système'}: {audit_log.action_description}",
                'security_alert',
                {
                    'audit_id': str(audit_log.id),
                    'severity': audit_log.severity,
                    'action_type': audit_log.action_type,
                }
            )
            
            # Alerte système
            send_system_alert(
                'critical_action',
                f"Action critique: {audit_log.action_description}",
                'critical'
            )
            
        except Exception as e:
            logger.error(f"Erreur lors de la notification d'action critique: {e}")
    
    @staticmethod
    def notify_security_event(security_event):
        """Notifie les événements de sécurité critiques"""
        try:
            from notifications.websocket_service import send_role_notification, send_system_alert
            
            # Notifier les admins sécurité
            send_role_notification(
                'admin',
                'Événement de sécurité critique',
                f"{security_event.get_event_type_display()} depuis {security_event.source_ip}",
                'security_alert',
                {
                    'event_id': str(security_event.id),
                    'risk_level': security_event.risk_level,
                    'source_ip': security_event.source_ip,
                }
            )
            
            # Alerte système
            send_system_alert(
                'security_event',
                f"Sécurité: {security_event.description}",
                'critical'
            )
            
        except Exception as e:
            logger.error(f"Erreur lors de la notification d'événement de sécurité: {e}")


class AuditMiddleware:
    """
    Middleware pour capturer automatiquement certaines actions
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Traitement avant la vue
        start_time = timezone.now()
        
        response = self.get_response(request)
        
        # Traitement après la vue
        self.log_request(request, response, start_time)
        
        return response
    
    def log_request(self, request, response, start_time):
        """Log les requêtes importantes"""
        try:
            # Ne logger que certaines requêtes
            if not self.should_log_request(request):
                return
            
            duration = (timezone.now() - start_time).total_seconds()
            
            # Détecter les erreurs
            if response.status_code >= 400:
                severity = 'high' if response.status_code >= 500 else 'medium'
                
                AuditService.log_action(
                    user=request.user if request.user.is_authenticated else None,
                    action_type='error',
                    description=f"Erreur HTTP {response.status_code} sur {request.path}",
                    severity=severity,
                    request=request,
                    additional_data={
                        'status_code': response.status_code,
                        'duration': duration,
                    }
                )
            
            # Logger les accès aux pages sensibles
            if self.is_sensitive_path(request.path):
                AuditService.log_action(
                    user=request.user if request.user.is_authenticated else None,
                    action_type='view',
                    description=f"Accès à {request.path}",
                    severity='medium',
                    request=request,
                    additional_data={
                        'duration': duration,
                    }
                )
                
        except Exception as e:
            logger.error(f"Erreur dans AuditMiddleware: {e}")
    
    def should_log_request(self, request):
        """Détermine si une requête doit être loggée"""
        # Ne pas logger les assets statiques
        if request.path.startswith('/static/') or request.path.startswith('/media/'):
            return False
        
        # Logger les requêtes admin et API
        if (request.path.startswith('/admin/') or 
            request.path.startswith('/api/') or
            request.method in ['POST', 'PUT', 'DELETE']):
            return True
        
        return False
    
    def is_sensitive_path(self, path):
        """Détermine si un chemin est sensible"""
        sensitive_paths = [
            '/admin/',
            '/api/users/',
            '/api/missions/',
            '/api/payments/',
            '/export/',
        ]
        return any(path.startswith(sensitive) for sensitive in sensitive_paths)
