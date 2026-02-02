import json
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from .models import Message, Conversation
from django.contrib.auth import get_user_model

User = get_user_model()

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.mission_id = self.scope['url_route']['kwargs']['mission_id']
        self.mission_group_name = 'chat_%s' % self.mission_id

        # Join room group
        await self.channel_layer.group_add(
            self.mission_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.mission_group_name,
            self.channel_name
        )

    # Receive message from WebSocket
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json['message']
        sender_id = text_data_json['sender']

        sender = await self.get_user(sender_id)
        conversation = await self.get_or_create_conversation(self.mission_id)

        # Save message to database
        await self.save_message(conversation, sender, message)

        # Send message to room group
        await self.channel_layer.group_send(
            self.mission_group_name,
            {
                'type': 'chat_message',
                'message': message,
                'sender': sender.username
            }
        )

    # Receive message from room group
    async def chat_message(self, event):
        message = event['message']
        sender = event['sender']

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'message': message,
            'sender': sender
        }))

    @database_sync_to_async
    def get_user(self, user_id):
        return User.objects.get(id=user_id)

    @database_sync_to_async
    def get_or_create_conversation(self, mission_id):
        from missions.models import Mission
        try:
            mission = Mission.objects.get(id=mission_id)
            conversation, _ = Conversation.objects.get_or_create(
                defaults={'is_active': True}
            )
            # Ajouter les participants (client et livreur)
            if mission.client:
                conversation.participants.add(mission.client)
            if mission.livreur:
                conversation.participants.add(mission.livreur)
            return conversation
        except Mission.DoesNotExist:
            # Créer une conversation générique si la mission n'existe pas
            conversation, _ = Conversation.objects.get_or_create(id=mission_id)
            return conversation

    @database_sync_to_async
    def save_message(self, conversation, sender, message):
        Message.objects.create(conversation=conversation, sender=sender, content=message)


class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        if self.user.is_anonymous:
            await self.close()
            return
        
        self.user_group_name = f'notifications_{self.user.id}'
        
        # Join user notification group
        await self.channel_layer.group_add(
            self.user_group_name,
            self.channel_name
        )
        
        await self.accept()
    
    async def disconnect(self, close_code):
        if hasattr(self, 'user_group_name'):
            await self.channel_layer.group_discard(
                self.user_group_name,
                self.channel_name
            )
    
    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'ping':
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'timestamp': data.get('timestamp')
                }))
        except json.JSONDecodeError:
            pass
    
    async def notification_message(self, event):
        """Send notification to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'title': event['title'],
            'message': event['message'],
            'notification_type': event.get('notification_type', 'info'),
            'timestamp': event.get('timestamp')
        }))
