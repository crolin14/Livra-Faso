"""
WebSocket Consumer sécurisé pour le chat en temps réel
"""
import json
import logging
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.core.exceptions import ValidationError, PermissionDenied
from django.utils.html import escape
from .models import Message, Conversation
from django.contrib.auth import get_user_model
from missions.models import Mission

User = get_user_model()
logger = logging.getLogger(__name__)

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        """Connexion WebSocket sécurisée avec validation d'autorisation"""
        try:
            self.mission_id = self.scope['url_route']['kwargs']['mission_id']
            self.user = self.scope['user']
            
            # Validation de l'utilisateur authentifié
            if not self.user.is_authenticated:
                logger.warning(f"Tentative de connexion WebSocket non authentifiée pour mission {self.mission_id}")
                await self.close(code=4001)
                return
            
            # Validation de l'autorisation d'accès à la mission
            has_access = await self.check_mission_access(self.user.id, self.mission_id)
            if not has_access:
                logger.warning(f"Accès WebSocket refusé: utilisateur {self.user.id} pour mission {self.mission_id}")
                await self.close(code=4003)
                return
            
            # Validation de l'ID de mission
            try:
                mission_id_int = int(self.mission_id)
                if mission_id_int <= 0:
                    raise ValueError("ID de mission invalide")
            except (ValueError, TypeError):
                logger.error(f"ID de mission invalide: {self.mission_id}")
                await self.close(code=4000)
                return
            
            self.mission_group_name = f'chat_{mission_id_int}'
            
            # Rejoindre le groupe de la mission
            await self.channel_layer.group_add(
                self.mission_group_name,
                self.channel_name
            )
            
            await self.accept()
            logger.info(f"Connexion WebSocket établie: utilisateur {self.user.id} pour mission {self.mission_id}")
            
        except Exception as e:
            logger.error(f"Erreur lors de la connexion WebSocket: {e}")
            await self.close(code=4500)

    async def disconnect(self, close_code):
        """Déconnexion sécurisée"""
        try:
            if hasattr(self, 'mission_group_name'):
                await self.channel_layer.group_discard(
                    self.mission_group_name,
                    self.channel_name
                )
            logger.info(f"Déconnexion WebSocket: utilisateur {getattr(self.user, 'id', 'unknown')} (code: {close_code})")
        except Exception as e:
            logger.error(f"Erreur lors de la déconnexion WebSocket: {e}")

    async def receive(self, text_data):
        """Réception de message avec validation et sécurisation"""
        try:
            # Validation de l'utilisateur
            if not self.user.is_authenticated:
                logger.warning("Message reçu d'un utilisateur non authentifié")
                return
            
            # Parse et validation du JSON
            try:
                text_data_json = json.loads(text_data)
            except json.JSONDecodeError:
                logger.warning(f"JSON invalide reçu de l'utilisateur {self.user.id}")
                await self.send_error("Format de message invalide")
                return
            
            # Validation des champs requis
            if 'message' not in text_data_json:
                await self.send_error("Message manquant")
                return
            
            message = text_data_json['message']
            
            # Validation et nettoyage du message
            if not isinstance(message, str):
                await self.send_error("Le message doit être une chaîne de caractères")
                return
            
            message = message.strip()
            
            # Validation de la longueur du message
            if len(message) == 0:
                await self.send_error("Le message ne peut pas être vide")
                return
            
            if len(message) > 1000:  # Limite de 1000 caractères
                await self.send_error("Message trop long (maximum 1000 caractères)")
                return
            
            # Échappement HTML pour prévenir XSS
            message_escaped = escape(message)
            
            # Vérification de l'accès à la mission
            has_access = await self.check_mission_access(self.user.id, self.mission_id)
            if not has_access:
                logger.warning(f"Tentative d'envoi de message non autorisée: utilisateur {self.user.id} pour mission {self.mission_id}")
                await self.send_error("Accès non autorisé à cette conversation")
                return
            
            # Récupération sécurisée de la conversation
            conversation = await self.get_or_create_conversation(self.mission_id)
            if not conversation:
                await self.send_error("Impossible de créer la conversation")
                return
            
            # Sauvegarde du message en base
            saved_message = await self.save_message(conversation, self.user, message_escaped)
            if not saved_message:
                await self.send_error("Erreur lors de la sauvegarde du message")
                return
            
            # Envoi du message au groupe
            await self.channel_layer.group_send(
                self.mission_group_name,
                {
                    'type': 'chat_message',
                    'message': message_escaped,
                    'sender': self.user.username,
                    'sender_id': self.user.id,
                    'timestamp': saved_message.created_at.isoformat()
                }
            )
            
            logger.debug(f"Message envoyé: utilisateur {self.user.id} dans mission {self.mission_id}")
            
        except Exception as e:
            logger.error(f"Erreur lors de la réception du message: {e}")
            await self.send_error("Erreur interne du serveur")

    async def chat_message(self, event):
        """Envoi de message au client avec validation"""
        try:
            message = event['message']
            sender = event['sender']
            sender_id = event['sender_id']
            timestamp = event['timestamp']
            
            # Validation supplémentaire côté envoi
            if not isinstance(message, str) or not isinstance(sender, str):
                logger.error("Données de message invalides lors de l'envoi")
                return
            
            # Envoi sécurisé au WebSocket
            await self.send(text_data=json.dumps({
                'message': message,
                'sender': sender,
                'sender_id': sender_id,
                'timestamp': timestamp,
                'type': 'message'
            }))
            
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi du message au client: {e}")

    async def send_error(self, error_message):
        """Envoi d'un message d'erreur au client"""
        try:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': error_message
            }))
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi du message d'erreur: {e}")

    @database_sync_to_async
    def check_mission_access(self, user_id, mission_id):
        """Vérification sécurisée de l'accès à la mission"""
        try:
            mission = Mission.objects.select_related('client', 'livreur').get(id=mission_id)
            user = User.objects.get(id=user_id)
            
            # L'utilisateur a accès s'il est le client, le livreur ou un candidat
            has_access = (
                user == mission.client or
                user == mission.livreur or
                mission.candidats.filter(id=user.id).exists()
            )
            
            return has_access
            
        except (Mission.DoesNotExist, User.DoesNotExist):
            return False
        except Exception as e:
            logger.error(f"Erreur lors de la vérification d'accès: {e}")
            return False

    @database_sync_to_async
    def get_or_create_conversation(self, mission_id):
        """Création ou récupération sécurisée de la conversation"""
        try:
            # Vérification que la mission existe
            if not Mission.objects.filter(id=mission_id).exists():
                return None
            
            conversation, created = Conversation.objects.get_or_create(
                mission_id=mission_id,
                defaults={'title': f'Mission {mission_id}'}
            )
            return conversation
            
        except Exception as e:
            logger.error(f"Erreur lors de la création/récupération de conversation: {e}")
            return None

    @database_sync_to_async
    def save_message(self, conversation, sender, message):
        """Sauvegarde sécurisée du message"""
        try:
            # Validation supplémentaire avant sauvegarde
            if len(message) > 1000:
                return None
            
            message_obj = Message.objects.create(
                conversation=conversation,
                sender=sender,
                content=message
            )
            return message_obj
            
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde du message: {e}")
            return None
