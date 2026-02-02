from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import Notification
import json

User = get_user_model()
channel_layer = get_channel_layer()


def send_notification(recipient, title, message, notification_type='info', data=None):
    """Envoie une notification à un utilisateur spécifique"""
    try:
        # Créer la notification en base
        notification = Notification.objects.create(
            recipient=recipient,
            title=title,
            message=message,
            type=notification_type,
            data=data or {}
        )
        
        # Envoyer via WebSocket
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                f"notifications_{recipient.id}",
                {
                    'type': 'notification_message',
                    'notification': {
                        'id': str(notification.id),
                        'title': title,
                        'message': message,
                        'type': notification_type,
                        'created_at': notification.created_at.isoformat(),
                        'data': data or {}
                    }
                }
            )
        
        return notification
        
    except Exception as e:
        print(f"Erreur lors de l'envoi de notification: {e}")
        return None


def send_role_notification(role_codename, title, message, notification_type='info', data=None):
    """Envoie une notification à tous les utilisateurs d'un rôle"""
    from rbac.models import UserRole
    
    users = User.objects.filter(
        user_roles__role__codename=role_codename
    ).distinct()
    
    # Créer les notifications en base
    notifications = []
    for user in users:
        notification = Notification.objects.create(
            recipient=user,
            title=title,
            message=message,
            type=notification_type,
            data=data or {}
        )
        notifications.append(notification)
    
    # Envoyer via WebSocket au groupe de rôle
    if channel_layer:
        async_to_sync(channel_layer.group_send)(
            f"role_{role_codename}",
            {
                'type': 'notification_message',
                'notification': {
                    'title': title,
                    'message': message,
                    'type': notification_type,
                    'created_at': notifications[0].created_at.isoformat() if notifications else None,
                    'data': data or {}
                }
            }
        )
    
    return notifications


def send_system_alert(alert_type, message, severity='info'):
    """Envoie une alerte système à tous les admins"""
    if channel_layer:
        async_to_sync(channel_layer.group_send)(
            "admin_dashboard",
            {
                'type': 'system_alert',
                'alert': {
                    'type': alert_type,
                    'message': message,
                    'severity': severity,
                    'timestamp': timezone.now().isoformat()
                }
            }
        )


def notify_mission_update(mission, update_type):
    """Notifie les changements de statut des missions"""
    # Notifier le client
    if mission.client:
        client_message = get_mission_message_for_client(mission, update_type)
        send_notification(
            mission.client,
            "Mise à jour de votre mission",
            client_message,
            'mission_update',
            {'mission_id': str(mission.id), 'status': mission.status}
        )
    
    # Notifier le livreur
    if mission.livreur:
        livreur_message = get_mission_message_for_livreur(mission, update_type)
        send_notification(
            mission.livreur,
            "Mise à jour de mission",
            livreur_message,
            'mission_update',
            {'mission_id': str(mission.id), 'status': mission.status}
        )
    
    # Notifier les admins
    send_role_notification(
        'admin',
        f"Mission #{mission.id} mise à jour",
        f"Statut changé vers: {mission.get_status_display()}",
        'admin_notification',
        {'mission_id': str(mission.id), 'status': mission.status}
    )
    
    # Envoyer mise à jour temps réel au dashboard admin
    if channel_layer:
        async_to_sync(channel_layer.group_send)(
            "admin_dashboard",
            {
                'type': 'mission_update',
                'mission': {
                    'id': str(mission.id),
                    'status': mission.status,
                    'client': mission.client.username if mission.client else None,
                    'livreur': mission.livreur.username if mission.livreur else None,
                    'updated_at': timezone.now().isoformat()
                }
            }
        )


def notify_new_user(user):
    """Notifie l'inscription d'un nouvel utilisateur"""
    # Notifier les admins
    send_role_notification(
        'admin',
        "Nouvel utilisateur inscrit",
        f"{user.username} ({user.get_user_type_display()}) vient de s'inscrire",
        'new_user',
        {'user_id': str(user.id), 'user_type': user.user_type}
    )
    
    # Envoyer au dashboard admin
    if channel_layer:
        async_to_sync(channel_layer.group_send)(
            "admin_dashboard",
            {
                'type': 'new_user',
                'user': {
                    'id': str(user.id),
                    'username': user.username,
                    'user_type': user.user_type,
                    'created_at': user.date_joined.isoformat()
                }
            }
        )


def send_dashboard_stats_update():
    """Envoie les statistiques mises à jour au dashboard admin"""
    from missions.models import Mission
    from datetime import timedelta
    
    now = timezone.now()
    today = now.date()
    
    stats = {
        'total_missions': Mission.objects.count(),
        'missions_today': Mission.objects.filter(created_at__date=today).count(),
        'active_missions': Mission.objects.filter(
            status__in=['en_attente', 'acceptee', 'en_cours']
        ).count(),
        'completed_missions': Mission.objects.filter(status='livree').count(),
        'revenue_today': sum(
            mission.price or 0 
            for mission in Mission.objects.filter(
                created_at__date=today,
                status='livree'
            )
        ),
        'active_users': User.objects.filter(
            last_login__gte=now - timedelta(minutes=15)
        ).count(),
        'timestamp': now.isoformat()
    }
    
    if channel_layer:
        async_to_sync(channel_layer.group_send)(
            "admin_dashboard",
            {
                'type': 'stats_update',
                'stats': stats
            }
        )


def get_mission_message_for_client(mission, update_type):
    """Génère le message de notification pour le client"""
    messages = {
        'status_change': f"Votre mission #{mission.id} est maintenant {mission.get_status_display().lower()}",
        'livreur_assigned': f"Un livreur a été assigné à votre mission #{mission.id}",
        'pickup_started': f"Le livreur est en route pour récupérer votre colis (Mission #{mission.id})",
        'delivery_started': f"Votre colis est en cours de livraison (Mission #{mission.id})",
        'delivered': f"Votre colis a été livré avec succès (Mission #{mission.id})",
        'cancelled': f"Votre mission #{mission.id} a été annulée"
    }
    return messages.get(update_type, f"Mise à jour de votre mission #{mission.id}")


def get_mission_message_for_livreur(mission, update_type):
    """Génère le message de notification pour le livreur"""
    messages = {
        'assigned': f"Nouvelle mission assignée: #{mission.id}",
        'pickup_reminder': f"N'oubliez pas de récupérer le colis pour la mission #{mission.id}",
        'delivery_reminder': f"Colis prêt à être livré pour la mission #{mission.id}",
        'completed': f"Mission #{mission.id} terminée avec succès",
        'cancelled': f"Mission #{mission.id} annulée"
    }
    return messages.get(update_type, f"Mise à jour de la mission #{mission.id}")
