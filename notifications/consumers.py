import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import Notification
from rbac.models import UserRole

User = get_user_model()


class NotificationConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time notifications"""
    
    async def connect(self):
        """Handle WebSocket connection"""
        self.user = self.scope["user"]
        
        if self.user.is_anonymous:
            await self.close()
            return
        
        # Join user-specific notification group
        self.user_group_name = f"notifications_{self.user.id}"
        await self.channel_layer.group_add(
            self.user_group_name,
            self.channel_name
        )
        
        # Join role-based groups for admin notifications
        user_roles = await self.get_user_roles(self.user)
        for role in user_roles:
            role_group_name = f"role_{role.role.codename}"
            await self.channel_layer.group_add(
                role_group_name,
                self.channel_name
            )
        
        await self.accept()
        
        # Send initial unread notifications count
        unread_count = await self.get_unread_count(self.user)
        await self.send(text_data=json.dumps({
            'type': 'unread_count',
            'count': unread_count
        }))
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        if hasattr(self, 'user_group_name'):
            await self.channel_layer.group_discard(
                self.user_group_name,
                self.channel_name
            )
        
        # Leave role-based groups
        if hasattr(self, 'user') and not self.user.is_anonymous:
            user_roles = await self.get_user_roles(self.user)
            for role in user_roles:
                role_group_name = f"role_{role.role.codename}"
                await self.channel_layer.group_discard(
                    role_group_name,
                    self.channel_name
                )
    
    async def receive(self, text_data):
        """Handle messages from WebSocket"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'mark_read':
                notification_id = data.get('notification_id')
                await self.mark_notification_read(notification_id)
                
            elif message_type == 'mark_all_read':
                await self.mark_all_notifications_read(self.user)
                
            elif message_type == 'get_notifications':
                notifications = await self.get_recent_notifications(self.user)
                await self.send(text_data=json.dumps({
                    'type': 'notifications_list',
                    'notifications': notifications
                }))
                
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON format'
            }))
    
    async def notification_message(self, event):
        """Send notification to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'new_notification',
            'notification': event['notification']
        }))
    
    async def system_alert(self, event):
        """Send system alert to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'system_alert',
            'alert': event['alert']
        }))
    
    async def mission_update(self, event):
        """Send mission update to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'mission_update',
            'mission': event['mission']
        }))
    
    async def user_activity(self, event):
        """Send user activity update to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'user_activity',
            'activity': event['activity']
        }))
    
    @database_sync_to_async
    def get_user_roles(self, user):
        """Get user roles for group membership"""
        return list(UserRole.objects.filter(user=user).select_related('role'))
    
    @database_sync_to_async
    def get_unread_count(self, user):
        """Get unread notifications count"""
        return Notification.objects.filter(
            recipient=user,
            is_read=False
        ).count()
    
    @database_sync_to_async
    def mark_notification_read(self, notification_id):
        """Mark specific notification as read"""
        try:
            notification = Notification.objects.get(
                id=notification_id,
                recipient=self.user
            )
            notification.is_read = True
            notification.save()
            return True
        except Notification.DoesNotExist:
            return False
    
    @database_sync_to_async
    def mark_all_notifications_read(self, user):
        """Mark all notifications as read for user"""
        Notification.objects.filter(
            recipient=user,
            is_read=False
        ).update(is_read=True)
    
    @database_sync_to_async
    def get_recent_notifications(self, user):
        """Get recent notifications for user"""
        notifications = Notification.objects.filter(
            recipient=user
        ).order_by('-created_at')[:20]
        
        return [
            {
                'id': str(notif.id),
                'title': notif.title,
                'message': notif.message,
                'type': notif.type,
                'is_read': notif.is_read,
                'created_at': notif.created_at.isoformat(),
                'data': notif.data
            }
            for notif in notifications
        ]


class AdminDashboardConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for admin dashboard real-time updates"""
    
    async def connect(self):
        """Handle WebSocket connection for admin dashboard"""
        self.user = self.scope["user"]
        
        if self.user.is_anonymous or not await self.is_admin_user(self.user):
            await self.close()
            return
        
        # Join admin dashboard group
        self.group_name = "admin_dashboard"
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send initial dashboard data
        dashboard_data = await self.get_dashboard_data()
        await self.send(text_data=json.dumps({
            'type': 'dashboard_data',
            'data': dashboard_data
        }))
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )
    
    async def receive(self, text_data):
        """Handle messages from WebSocket"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'get_stats':
                stats = await self.get_live_stats()
                await self.send(text_data=json.dumps({
                    'type': 'live_stats',
                    'stats': stats
                }))
                
        except json.JSONDecodeError:
            pass
    
    async def stats_update(self, event):
        """Send stats update to admin dashboard"""
        await self.send(text_data=json.dumps({
            'type': 'stats_update',
            'stats': event['stats']
        }))
    
    async def new_mission(self, event):
        """Send new mission notification to admin dashboard"""
        await self.send(text_data=json.dumps({
            'type': 'new_mission',
            'mission': event['mission']
        }))
    
    async def new_user(self, event):
        """Send new user notification to admin dashboard"""
        await self.send(text_data=json.dumps({
            'type': 'new_user',
            'user': event['user']
        }))
    
    async def system_health(self, event):
        """Send system health update to admin dashboard"""
        await self.send(text_data=json.dumps({
            'type': 'system_health',
            'health': event['health']
        }))
    
    @database_sync_to_async
    def is_admin_user(self, user):
        """Check if user has admin privileges"""
        return UserRole.objects.filter(
            user=user,
            role__codename__in=['super_admin', 'admin', 'manager']
        ).exists()
    
    @database_sync_to_async
    def get_dashboard_data(self):
        """Get initial dashboard data"""
        from missions.models import Mission
        from users.models import User
        
        return {
            'total_missions': Mission.objects.count(),
            'active_missions': Mission.objects.filter(
                status__in=['en_attente', 'acceptee', 'en_cours']
            ).count(),
            'total_users': User.objects.count(),
            'online_users': User.objects.filter(is_active=True).count()
        }
    
    @database_sync_to_async
    def get_live_stats(self):
        """Get live statistics for dashboard"""
        from missions.models import Mission
        from users.models import User
        from django.utils import timezone
        from datetime import timedelta
        
        now = timezone.now()
        today = now.date()
        
        return {
            'missions_today': Mission.objects.filter(
                created_at__date=today
            ).count(),
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
            'pending_missions': Mission.objects.filter(
                status='en_attente'
            ).count()
        }
