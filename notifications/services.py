"""
Services de notifications multi-canal pour LivraFaso
Gère SMS, Push, Email selon la logique métier
"""
import logging
import requests
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()
logger = logging.getLogger(__name__)

class NotificationService:
    """Service principal de notifications"""
    
    def __init__(self):
        self.sms_providers = {
            'orange': OrangeMoneyNotificationService(),
            'moov': MoovMoneyNotificationService()
        }
    
    def send_mission_notification(self, mission, event_type, recipient_type='all'):
        """
        Envoie des notifications selon l'événement mission
        
        Args:
            mission: Instance de Mission
            event_type: 'created', 'accepted', 'picked_up', 'in_transit', 'delivered', 'problem'
            recipient_type: 'client', 'livreur', 'all'
        """
        notifications = self._get_notification_config(event_type)
        
        for notification in notifications:
            if recipient_type == 'all' or notification['recipient'] == recipient_type:
                self._send_notification(mission, notification)
    
    def _get_notification_config(self, event_type):
        """Configuration des notifications par événement"""
        configs = {
            'created': [
                {'recipient': 'client', 'channels': ['sms', 'push'], 'template': 'mission_created'},
                {'recipient': 'livreurs_zone', 'channels': ['push'], 'template': 'new_mission_available'}
            ],
            'accepted': [
                {'recipient': 'client', 'channels': ['sms', 'push'], 'template': 'mission_accepted'},
                {'recipient': 'livreur', 'channels': ['sms', 'push'], 'template': 'mission_assigned'}
            ],
            'picked_up': [
                {'recipient': 'client', 'channels': ['push'], 'template': 'pickup_confirmed'}
            ],
            'in_transit': [
                {'recipient': 'client', 'channels': ['push'], 'template': 'in_transit'}
            ],
            'delivered': [
                {'recipient': 'client', 'channels': ['sms', 'push', 'email'], 'template': 'delivered'},
                {'recipient': 'livreur', 'channels': ['sms'], 'template': 'payment_confirmed'}
            ],
            'problem': [
                {'recipient': 'client', 'channels': ['sms', 'push'], 'template': 'problem_detected'},
                {'recipient': 'livreur', 'channels': ['push'], 'template': 'problem_reported'}
            ]
        }
        return configs.get(event_type, [])
    
    def _send_notification(self, mission, notification_config):
        """Envoie une notification selon sa configuration"""
        recipient = notification_config['recipient']
        channels = notification_config['channels']
        template = notification_config['template']
        
        # Déterminer les destinataires
        recipients = self._get_recipients(mission, recipient)
        
        for user in recipients:
            for channel in channels:
                try:
                    if channel == 'sms':
                        self._send_sms(user, template, mission)
                    elif channel == 'push':
                        self._send_push(user, template, mission)
                    elif channel == 'email':
                        self._send_email(user, template, mission)
                except Exception as e:
                    logger.error(f"Erreur envoi {channel} à {user.phone}: {e}")
    
    def _get_recipients(self, mission, recipient_type):
        """Détermine les destinataires selon le type"""
        if recipient_type == 'client':
            return [mission.client]
        elif recipient_type == 'livreur' and mission.livreur:
            return [mission.livreur]
        elif recipient_type == 'livreurs_zone':
            # Livreurs disponibles dans la zone
            from location.utils import get_nearby_livreurs
            pickup_location = mission.locations.filter(location_type='pickup').first()
            if pickup_location:
                nearby = get_nearby_livreurs(
                    pickup_location.latitude, 
                    pickup_location.longitude,
                    radius_km=15
                )
                return [item['livreur'] for item in nearby]
        return []
    
    def _send_sms(self, user, template, mission):
        """Envoie un SMS"""
        if not user.phone_number:
            return
        
        message = self._get_message_content(template, mission, user)
        
        # Déterminer le provider selon le numéro
        provider = self._detect_sms_provider(user.phone_number)
        if provider in self.sms_providers:
            self.sms_providers[provider].send_sms(user.phone_number, message)
    
    def _send_push(self, user, template, mission):
        """Envoie une notification push"""
        # Intégration avec Firebase Cloud Messaging ou service similaire
        message = self._get_message_content(template, mission, user)
        
        # TODO: Implémenter l'envoi push réel
        logger.info(f"Push notification à {user.username}: {message}")
    
    def _send_email(self, user, template, mission):
        """Envoie un email"""
        if not user.email:
            return
        
        subject = self._get_email_subject(template, mission)
        message = self._get_message_content(template, mission, user)
        
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False
            )
        except Exception as e:
            logger.error(f"Erreur envoi email à {user.email}: {e}")
    
    def _detect_sms_provider(self, phone):
        """Détecte le provider SMS selon le numéro"""
        if phone.startswith('+226'):
            phone = phone[4:]
        
        # Préfixes Orange Burkina Faso
        orange_prefixes = ['70', '71', '72', '73']
        # Préfixes Moov Burkina Faso  
        moov_prefixes = ['60', '61', '62', '63', '64', '65', '66', '67']
        
        prefix = phone[:2]
        if prefix in orange_prefixes:
            return 'orange'
        elif prefix in moov_prefixes:
            return 'moov'
        
        return 'orange'  # Par défaut
    
    def _get_message_content(self, template, mission, user):
        """Génère le contenu du message selon le template"""
        templates = {
            'mission_created': f"Mission #{mission.id} créée. Montant: {mission.price} FCFA. Suivi: livrafaso.com/track/{mission.id}",
            'mission_accepted': f"Mission #{mission.id} acceptée par {mission.livreur.get_full_name()}. Tel: {mission.livreur.phone_number}",
            'new_mission_available': f"Nouvelle mission disponible: {mission.pickup_address} → {mission.delivery_address}. {mission.price} FCFA",
            'mission_assigned': f"Mission #{mission.id} assignée. Ramassage: {mission.pickup_address}",
            'pickup_confirmed': f"Colis ramassé pour mission #{mission.id}. Livraison en cours.",
            'in_transit': f"Mission #{mission.id} en transit. Suivi temps réel: livrafaso.com/track/{mission.id}",
            'delivered': f"Mission #{mission.id} livrée avec succès! Merci d'utiliser LivraFaso.",
            'payment_confirmed': f"Paiement reçu pour mission #{mission.id}. Montant: {mission.price} FCFA",
            'problem_detected': f"Problème détecté sur mission #{mission.id}. Notre équipe vous contacte.",
            'problem_reported': f"Problème signalé sur mission #{mission.id}. Contactez le support."
        }
        return templates.get(template, f"Notification mission #{mission.id}")
    
    def _get_email_subject(self, template, mission):
        """Génère le sujet email selon le template"""
        subjects = {
            'mission_created': f"Mission #{mission.id} créée - LivraFaso",
            'delivered': f"Livraison confirmée - Mission #{mission.id}",
            'problem_detected': f"Incident Mission #{mission.id} - Support LivraFaso"
        }
        return subjects.get(template, f"Notification LivraFaso - Mission #{mission.id}")


class OrangeMoneyNotificationService:
    """Service SMS Orange Money"""
    
    def send_sms(self, phone, message):
        """Envoie SMS via API Orange"""
        try:
            # Configuration API Orange SMS
            url = "https://api.orange.com/smsmessaging/v1/outbound/tel%3A%2B226XXXXXXXX/requests"
            
            headers = {
                'Authorization': f'Bearer {self._get_orange_token()}',
                'Content-Type': 'application/json'
            }
            
            data = {
                'outboundSMSMessageRequest': {
                    'address': f'tel:+226{phone}',
                    'senderAddress': 'tel:+226LIVRAFASO',
                    'outboundSMSTextMessage': {
                        'message': message
                    }
                }
            }
            
            # TODO: Implémenter l'appel API réel
            logger.info(f"SMS Orange envoyé à {phone}: {message}")
            
        except Exception as e:
            logger.error(f"Erreur SMS Orange: {e}")
    
    def _get_orange_token(self):
        """Récupère le token d'authentification Orange"""
        # TODO: Implémenter l'authentification OAuth Orange
        return "ORANGE_API_TOKEN"


class MoovMoneyNotificationService:
    """Service SMS Moov Money"""
    
    def send_sms(self, phone, message):
        """Envoie SMS via API Moov"""
        try:
            # Configuration API Moov SMS
            # TODO: Implémenter l'appel API réel
            logger.info(f"SMS Moov envoyé à {phone}: {message}")
            
        except Exception as e:
            logger.error(f"Erreur SMS Moov: {e}")


class EnterpriseNotificationService:
    """Service de notifications pour entreprises"""
    
    def send_daily_report(self, enterprise_user):
        """Envoie le rapport quotidien par email"""
        try:
            # Récupérer les statistiques du jour
            from missions.models import Mission
            from django.utils import timezone
            from datetime import timedelta
            
            today = timezone.now().date()
            missions_today = Mission.objects.filter(
                client=enterprise_user,
                created_at__date=today
            )
            
            context = {
                'user': enterprise_user,
                'date': today,
                'total_missions': missions_today.count(),
                'completed_missions': missions_today.filter(status='livree').count(),
                'total_amount': sum(m.price for m in missions_today),
                'missions': missions_today[:10]  # Dernières 10 missions
            }
            
            subject = f"Rapport quotidien LivraFaso - {today.strftime('%d/%m/%Y')}"
            message = render_to_string('emails/daily_report.html', context)
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[enterprise_user.email],
                html_message=message,
                fail_silently=False
            )
            
        except Exception as e:
            logger.error(f"Erreur rapport quotidien pour {enterprise_user.email}: {e}")
    
    def send_threshold_alert(self, enterprise_user, current_missions, threshold):
        """Alerte quand le seuil de missions est atteint"""
        try:
            subject = "Seuil de missions atteint - LivraFaso"
            message = f"""
            Bonjour {enterprise_user.get_full_name()},
            
            Vous avez atteint {current_missions} missions ce mois-ci.
            Seuil de votre abonnement: {threshold} missions.
            
            Considérez une mise à niveau vers Premium pour des missions illimitées.
            
            L'équipe LivraFaso
            """
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[enterprise_user.email],
                fail_silently=False
            )
            
        except Exception as e:
            logger.error(f"Erreur alerte seuil pour {enterprise_user.email}: {e}")


# Instance globale du service
notification_service = NotificationService()
enterprise_notification_service = EnterpriseNotificationService()
