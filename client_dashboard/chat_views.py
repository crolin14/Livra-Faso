from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
import json

from missions.models import Mission
from chat.models import Conversation, ChatMessage
from rbac.decorators import require_any_role


@login_required
@require_any_role('client')
def mission_chat(request, mission_id):
    """Vue pour le chat d'une mission spécifique"""
    mission = get_object_or_404(Mission, id=mission_id, client=request.user)
    
    # Récupérer ou créer la conversation
    conversation, created = Conversation.objects.get_or_create(
        defaults={'is_active': True}
    )
    
    # Ajouter les participants si la conversation vient d'être créée
    if created or not conversation.participants.exists():
        conversation.participants.add(request.user)
        if mission.livreur:
            conversation.participants.add(mission.livreur)
    
    # Récupérer les messages existants
    messages = conversation.messages.select_related('sender').order_by('timestamp')
    
    # Marquer les messages comme lus
    unread_messages = messages.filter(is_read=False).exclude(sender=request.user)
    unread_messages.update(is_read=True)
    
    context = {
        'mission': mission,
        'conversation': conversation,
        'messages': messages,
        'current_user': request.user,
    }
    
    return render(request, 'client_dashboard/mission_chat.html', context)


@login_required
@require_any_role('client')
@require_http_methods(["POST"])
def send_message_api(request, mission_id):
    """API pour envoyer un message dans le chat d'une mission"""
    try:
        mission = get_object_or_404(Mission, id=mission_id, client=request.user)
        data = json.loads(request.body)
        
        message_content = data.get('message', '').strip()
        if not message_content:
            return JsonResponse({
                'success': False,
                'error': 'Message vide'
            })
        
        # Récupérer ou créer la conversation
        conversation, created = Conversation.objects.get_or_create(
            defaults={'is_active': True}
        )
        
        if created or not conversation.participants.exists():
            conversation.participants.add(request.user)
            if mission.livreur:
                conversation.participants.add(mission.livreur)
        
        # Créer le message
        message = Message.objects.create(
            conversation=conversation,
            sender=request.user,
            content=message_content
        )
        
        return JsonResponse({
            'success': True,
            'message': {
                'id': message.id,
                'content': message.content,
                'sender': message.sender.get_full_name() or message.sender.username,
                'timestamp': message.timestamp.isoformat(),
                'is_own': True
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
@require_any_role('client')
def get_messages_api(request, mission_id):
    """API pour récupérer les messages d'une mission"""
    try:
        mission = get_object_or_404(Mission, id=mission_id, client=request.user)
        
        conversation = Conversation.objects.filter().first()
        if not conversation:
            return JsonResponse({
                'success': True,
                'messages': []
            })
        
        messages = conversation.messages.select_related('sender').order_by('timestamp')
        
        # Marquer comme lus les messages non lus
        unread_messages = messages.filter(is_read=False).exclude(sender=request.user)
        unread_messages.update(is_read=True)
        
        messages_data = []
        for message in messages:
            messages_data.append({
                'id': message.id,
                'content': message.content,
                'sender': message.sender.get_full_name() or message.sender.username,
                'timestamp': message.timestamp.isoformat(),
                'is_own': message.sender == request.user,
                'is_read': message.is_read
            })
        
        return JsonResponse({
            'success': True,
            'messages': messages_data
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
@require_any_role('client')
def chat_status_api(request, mission_id):
    """API pour vérifier le statut du chat (nouveau messages, participants en ligne)"""
    try:
        mission = get_object_or_404(Mission, id=mission_id, client=request.user)
        
        conversation = Conversation.objects.filter().first()
        if not conversation:
            return JsonResponse({
                'success': True,
                'unread_count': 0,
                'participants': [],
                'last_message': None
            })
        
        # Compter les messages non lus
        unread_count = conversation.messages.filter(
            is_read=False
        ).exclude(sender=request.user).count()
        
        # Informations sur les participants
        participants = []
        for participant in conversation.participants.all():
            if participant != request.user:
                participants.append({
                    'id': participant.id,
                    'name': participant.get_full_name() or participant.username,
                    'user_type': participant.user_type,
                    'is_online': False  # À implémenter avec Redis pour le statut en ligne
                })
        
        # Dernier message
        last_message = conversation.last_message
        last_message_data = None
        if last_message:
            last_message_data = {
                'content': last_message.content,
                'sender': last_message.sender.get_full_name() or last_message.sender.username,
                'timestamp': last_message.timestamp.isoformat(),
                'is_own': last_message.sender == request.user
            }
        
        return JsonResponse({
            'success': True,
            'unread_count': unread_count,
            'participants': participants,
            'last_message': last_message_data,
            'conversation_active': conversation.is_active
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })
