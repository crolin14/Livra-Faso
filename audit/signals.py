from django.db.models.signals import post_save, post_delete, pre_save
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from .services import AuditService
import json

User = get_user_model()


@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    """Log successful user login"""
    AuditService.log_action(
        user=user,
        action_type='login',
        description=f"Connexion réussie pour {user.username}",
        severity='low',
        request=request,
        additional_data={
            'login_method': 'standard',
            'user_type': getattr(user, 'user_type', 'unknown'),
        }
    )


@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    """Log user logout"""
    if user:
        AuditService.log_action(
            user=user,
            action_type='logout',
            description=f"Déconnexion de {user.username}",
            severity='low',
            request=request
        )


@receiver(user_login_failed)
def log_failed_login(sender, credentials, request, **kwargs):
    """Log failed login attempts"""
    username = credentials.get('username', 'unknown')
    
    # Log as security event
    AuditService.log_security_event(
        event_type='failed_login',
        source_ip=AuditService.get_client_ip(request),
        description=f"Tentative de connexion échouée pour: {username}",
        risk_level='medium',
        request=request
    )


@receiver(post_save, sender=User)
def log_user_changes(sender, instance, created, **kwargs):
    """Log user creation and modifications"""
    if created:
        AuditService.log_action(
            user=None,  # System action for registration
            action_type='create',
            description=f"Nouvel utilisateur créé: {instance.username}",
            content_object=instance,
            severity='medium',
            additional_data={
                'user_type': getattr(instance, 'user_type', 'unknown'),
                'email': instance.email,
            }
        )
    else:
        # For updates, we need to track what changed
        # This would require storing the old values before save
        AuditService.log_action(
            user=instance,  # Assume user updated themselves
            action_type='update',
            description=f"Utilisateur modifié: {instance.username}",
            content_object=instance,
            severity='low'
        )


@receiver(post_delete, sender=User)
def log_user_deletion(sender, instance, **kwargs):
    """Log user deletion"""
    AuditService.log_action(
        user=None,  # Will be set by admin action
        action_type='delete',
        description=f"Utilisateur supprimé: {instance.username}",
        severity='high',
        additional_data={
            'deleted_user_id': instance.id,
            'deleted_username': instance.username,
            'user_type': getattr(instance, 'user_type', 'unknown'),
        }
    )


# Generic model change tracking
@receiver(post_save)
def log_model_changes(sender, instance, created, **kwargs):
    """Log changes to important models"""
    # Only track specific models
    tracked_models = ['Mission', 'Payment', 'Subscription', 'Enterprise']
    
    if sender.__name__ not in tracked_models:
        return
    
    action_type = 'create' if created else 'update'
    severity = 'medium' if created else 'low'
    
    # Try to get the current user from thread local storage
    # This would require implementing thread local user storage
    current_user = getattr(instance, '_current_user', None)
    
    AuditService.log_action(
        user=current_user,
        action_type=action_type,
        description=f"{sender.__name__} {'créé' if created else 'modifié'}: {str(instance)}",
        content_object=instance,
        severity=severity,
        additional_data={
            'model_name': sender.__name__,
            'object_str': str(instance),
        }
    )


@receiver(post_delete)
def log_model_deletion(sender, instance, **kwargs):
    """Log deletion of important models"""
    tracked_models = ['Mission', 'Payment', 'Subscription', 'Enterprise']
    
    if sender.__name__ not in tracked_models:
        return
    
    current_user = getattr(instance, '_current_user', None)
    
    AuditService.log_action(
        user=current_user,
        action_type='delete',
        description=f"{sender.__name__} supprimé: {str(instance)}",
        severity='high',
        additional_data={
            'model_name': sender.__name__,
            'deleted_object_str': str(instance),
            'deleted_object_id': instance.pk,
        }
    )
