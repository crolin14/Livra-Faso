"""
Consumers WebSocket pour le chat temps réel par mission - LivraFaso
"""

import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import Conversation, Message
from missions.models import Mission
from audit.audit_system import AuditService

User = get_user_model()
logger = logging.getLogger(__name__)

class MissionChatConsumer(AsyncWebsocketConsumer):
    """Consumer pour le chat temps réel par mission"""
    
    async def connect(self):
        """Connexion au WebSocket"""
        self.mission_id = self.scope['url_route']['kwargs']['mission_id']
        self.room_group_name = f'mission_chat_{self.mission_id}'
        self.user = self.scope['user']
        
        # Vérifier les permissions
        if not await self.check_mission_access():
            await self.close()
            return
        
        # Rejoindre le groupe de la mission
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Logger la connexion
        await self.log_chat_action('chat_connect')
        
        # Envoyer l'historique des messages
        await self.send_message_history()
    
    async def disconnect(self, close_code):
        """Déconnexion du WebSocket"""
        await self.log_chat_action('chat_disconnect')
        
        # Quitter le groupe
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        """Recevoir un message"""
        try:
            text_data_json = json.loads(text_data)
            message_type = text_data_json.get('type', 'chat_message')
            
            if message_type == 'chat_message':
                await self.handle_chat_message(text_data_json)
            elif message_type == 'typing':
                await self.handle_typing(text_data_json)
            elif message_type == 'file_upload':
                await self.handle_file_upload(text_data_json)
                
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'error': 'Format JSON invalide'
            }))
        except Exception as e:
            logger.error(f"Erreur dans receive: {e}")
            await self.send(text_data=json.dumps({
                'error': 'Erreur serveur'
            }))
    
    async def handle_chat_message(self, data):
        """Traiter un message de chat"""
        message_content = data.get('message', '').strip()
        
        if not message_content:
            return
        
        # Sauvegarder le message
        message = await self.save_message(message_content)
        
        if message:
            # Diffuser le message à tous les participants
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': {
                        'id': message.id,
                        'content': message.content,
                        'user': {
                            'id': message.user.id,
                            'username': message.user.username,
                            'full_name': message.user.get_full_name(),
                            'user_type': getattr(message.user, 'user_type', 'client')
                        },
                        'timestamp': message.created_at.isoformat(),
                        'message_type': message.message_type
                    }
                }
            )
            
            # Logger l'action
            await self.log_chat_action('chat_message', {
                'message_id': message.id,
                'content_length': len(message_content)
            })
    
    async def handle_typing(self, data):
        """Traiter l'indicateur de frappe"""
        is_typing = data.get('is_typing', False)
        
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'typing_indicator',
                'user': {
                    'id': self.user.id,
                    'username': self.user.username,
                    'full_name': self.user.get_full_name()
                },
                'is_typing': is_typing
            }
        )
    
    async def handle_file_upload(self, data):
        """Traiter l'upload de fichier"""
        file_url = data.get('file_url')
        file_name = data.get('file_name')
        file_type = data.get('file_type', 'file')
        
        if file_url and file_name:
            # Sauvegarder le message avec fichier
            message = await self.save_message(
                content=f"Fichier partagé: {file_name}",
                message_type=file_type,
                file_url=file_url
            )
            
            if message:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'chat_message',
                        'message': {
                            'id': message.id,
                            'content': message.content,
                            'user': {
                                'id': message.user.id,
                                'username': message.user.username,
                                'full_name': message.user.get_full_name(),
                                'user_type': getattr(message.user, 'user_type', 'client')
                            },
                            'timestamp': message.created_at.isoformat(),
                            'message_type': message.message_type,
                            'file_url': file_url,
                            'file_name': file_name
                        }
                    }
                )
    
    async def chat_message(self, event):
        """Envoyer un message de chat"""
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message']
        }))
    
    async def typing_indicator(self, event):
        """Envoyer l'indicateur de frappe"""
        # Ne pas renvoyer à l'expéditeur
        if event['user']['id'] != self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'typing_indicator',
                'user': event['user'],
                'is_typing': event['is_typing']
            }))
    
    async def mission_update(self, event):
        """Envoyer une mise à jour de mission"""
        await self.send(text_data=json.dumps({
            'type': 'mission_update',
            'update': event['update']
        }))
    
    @database_sync_to_async
    def check_mission_access(self):
        """Vérifier l'accès à la mission"""
        try:
            mission = Mission.objects.get(id=self.mission_id)
            user_type = getattr(self.user, 'user_type', None)
            
            # Client: peut accéder à ses propres missions
            if user_type == 'client' and mission.client == self.user:
                return True
            
            # Livreur: peut accéder aux missions qui lui sont assignées
            if user_type == 'livreur' and mission.livreur == self.user:
                return True
            
            # Entreprise: peut accéder aux missions de ses clients
            if user_type == 'entreprise':
                # Vérifier si l'entreprise a créé cette mission
                return True  # À affiner selon la logique métier
            
            # Admin: accès total
            if self.user.is_staff or self.user.is_superuser:
                return True
            
            return False
            
        except Mission.DoesNotExist:
            return False
    
    @database_sync_to_async
    def save_message(self, content, message_type='text', file_url=None):
        """Sauvegarder un message"""
        try:
            # Récupérer ou créer la conversation
            mission = Mission.objects.get(id=self.mission_id)
            conversation, created = Conversation.objects.get_or_create(
                mission=mission,
                defaults={'title': f"Chat Mission #{mission.id}"}
            )
            
            # Ajouter l'utilisateur aux participants si nécessaire
            if self.user not in conversation.participants.all():
                conversation.participants.add(self.user)
            
            # Créer le message
            message = Message.objects.create(
                conversation=conversation,
                user=self.user,
                content=content,
                message_type=message_type,
                file_url=file_url
            )
            
            return message
            
        except Exception as e:
            logger.error(f"Erreur sauvegarde message: {e}")
            return None
    
    @database_sync_to_async
    def get_message_history(self):
        """Récupérer l'historique des messages"""
        try:
            mission = Mission.objects.get(id=self.mission_id)
            conversation = Conversation.objects.filter(mission=mission).first()
            
            if not conversation:
                return []
            
            messages = Message.objects.filter(
                conversation=conversation
            ).select_related('user').order_by('created_at')[:50]
            
            return [
                {
                    'id': msg.id,
                    'content': msg.content,
                    'user': {
                        'id': msg.user.id,
                        'username': msg.user.username,
                        'full_name': msg.user.get_full_name(),
                        'user_type': getattr(msg.user, 'user_type', 'client')
                    },
                    'timestamp': msg.created_at.isoformat(),
                    'message_type': msg.message_type,
                    'file_url': msg.file_url
                }
                for msg in messages
            ]
            
        except Exception as e:
            logger.error(f"Erreur récupération historique: {e}")
            return []
    
    async def send_message_history(self):
        """Envoyer l'historique des messages"""
        messages = await self.get_message_history()
        
        await self.send(text_data=json.dumps({
            'type': 'message_history',
            'messages': messages
        }))
    
    @database_sync_to_async
    def log_chat_action(self, action, details=None):
        """Logger les actions du chat"""
        try:
            # Créer une requête factice pour l'audit
            class FakeRequest:
                def __init__(self, user, mission_id):
                    self.user = user
                    self.path = f'/chat/mission/{mission_id}/'
                    self.method = 'WS'
                    self.META = {
                        'REMOTE_ADDR': '127.0.0.1',
                        'HTTP_USER_AGENT': 'WebSocket'
                    }
                    self.session = type('obj', (object,), {'session_key': ''})()
            
            fake_request = FakeRequest(self.user, self.mission_id)
            
            AuditService.log_action(
                request=fake_request,
                action=action,
                object_type='Mission',
                object_id=self.mission_id,
                details=details or {},
                severity='info'
            )
            
        except Exception as e:
            logger.error(f"Erreur logging chat: {e}")


class NotificationConsumer(AsyncWebsocketConsumer):
    """Consumer pour les notifications temps réel"""
    
    async def connect(self):
        """Connexion aux notifications"""
        self.user = self.scope['user']
        
        if not self.user.is_authenticated:
            await self.close()
            return
        
        # Groupe de notifications par type d'utilisateur
        user_type = getattr(self.user, 'user_type', 'client')
        self.notification_group = f'notifications_{user_type}_{self.user.id}'
        
        await self.channel_layer.group_add(
            self.notification_group,
            self.channel_name
        )
        
        await self.accept()
    
    async def disconnect(self, close_code):
        """Déconnexion des notifications"""
        await self.channel_layer.group_discard(
            self.notification_group,
            self.channel_name
        )
    
    async def receive(self, text_data):
        """Recevoir une action de notification"""
        try:
            data = json.loads(text_data)
            action = data.get('action')
            
            if action == 'mark_read':
                notification_id = data.get('notification_id')
                await self.mark_notification_read(notification_id)
                
        except json.JSONDecodeError:
            pass
    
    async def notification_message(self, event):
        """Envoyer une notification"""
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'notification': event['notification']
        }))
    
    async def mission_status_update(self, event):
        """Notification de changement de statut de mission"""
        await self.send(text_data=json.dumps({
            'type': 'mission_status_update',
            'mission_id': event['mission_id'],
            'status': event['status'],
            'message': event['message']
        }))
    
    @database_sync_to_async
    def mark_notification_read(self, notification_id):
        """Marquer une notification comme lue"""
        try:
            from notifications.models import Notification
            Notification.objects.filter(
                id=notification_id,
                user=self.user
            ).update(is_read=True)
        except Exception as e:
            logger.error(f"Erreur marquage notification: {e}")


# Service pour envoyer des notifications
class NotificationService:
    """Service pour envoyer des notifications temps réel"""
    
    @staticmethod
    async def send_mission_chat_notification(mission_id, message, sender):
        """Envoyer notification de nouveau message"""
        from channels.layers import get_channel_layer
        
        channel_layer = get_channel_layer()
        
        # Récupérer les participants de la mission
        participants = await NotificationService.get_mission_participants(mission_id)
        
        for participant in participants:
            if participant.id != sender.id:  # Ne pas notifier l'expéditeur
                user_type = getattr(participant, 'user_type', 'client')
                group_name = f'notifications_{user_type}_{participant.id}'
                
                await channel_layer.group_send(
                    group_name,
                    {
                        'type': 'notification_message',
                        'notification': {
                            'type': 'chat_message',
                            'title': 'Nouveau message',
                            'message': f'Mission #{mission_id}: {message[:50]}...',
                            'mission_id': mission_id,
                            'sender': {
                                'name': sender.get_full_name(),
                                'user_type': getattr(sender, 'user_type', 'client')
                            }
                        }
                    }
                )
    
    @staticmethod
    async def send_mission_status_update(mission_id, new_status, participants):
        """Envoyer notification de changement de statut"""
        from channels.layers import get_channel_layer
        
        channel_layer = get_channel_layer()
        
        status_messages = {
            'pending': 'Mission créée',
            'ready': 'Livreur assigné',
            'in_progress': 'Mission en cours',
            'delivered': 'Mission livrée',
            'cancelled': 'Mission annulée'
        }
        
        message = status_messages.get(new_status, f'Statut mis à jour: {new_status}')
        
        for participant in participants:
            user_type = getattr(participant, 'user_type', 'client')
            group_name = f'notifications_{user_type}_{participant.id}'
            
            await channel_layer.group_send(
                group_name,
                {
                    'type': 'mission_status_update',
                    'mission_id': mission_id,
                    'status': new_status,
                    'message': message
                }
            )
    
    @staticmethod
    @database_sync_to_async
    def get_mission_participants(mission_id):
        """Récupérer les participants d'une mission"""
        try:
            mission = Mission.objects.select_related('client', 'livreur').get(id=mission_id)
            participants = [mission.client]
            
            if mission.livreur:
                participants.append(mission.livreur)
            
            return participants
            
        except Mission.DoesNotExist:
            return []
