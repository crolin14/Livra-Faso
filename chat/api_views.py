from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db import models
import json
from .models import ChatMessage, Conversation
from missions.models import Mission


@login_required
@require_http_methods(["GET"])
def mission_chat_messages(request, mission_id):
    """API pour récupérer les messages d'une mission"""
    try:
        mission = Mission.objects.get(id=mission_id)
        
        # Vérifier que l'utilisateur a accès à cette mission
        if not (request.user == mission.client or request.user == mission.livreur or request.user.is_staff):
            return JsonResponse({'success': False, 'error': 'Accès non autorisé'}, status=403)
        
        # Récupérer ou créer la conversation
        conversation, created = Conversation.objects.get_or_create(
            mission=mission,
            defaults={
                'client': mission.client,
                'livreur': mission.livreur
            }
        )
        
        # Récupérer les messages
        messages = ChatMessage.objects.filter(conversation=conversation).order_by('timestamp')
        
        messages_data = []
        for message in messages:
            sender_type = 'client' if message.sender == mission.client else 'livreur'
            if request.user.user_type == 'entreprise' and message.sender == request.user:
                sender_type = 'entreprise'
                
            messages_data.append({
                'id': message.id,
                'message': message.message,
                'sender_name': message.sender.get_full_name(),
                'sender_type': sender_type,
                'timestamp': message.timestamp.strftime('%d/%m/%Y %H:%M'),
                'message_type': message.message_type,
                'is_read': message.is_read
            })
        
        return JsonResponse({
            'success': True,
            'messages': messages_data,
            'conversation_id': conversation.id
        })
        
    except Mission.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Mission non trouvée'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def send_mission_message(request, mission_id):
    """API pour envoyer un message dans le chat d'une mission"""
    try:
        mission = Mission.objects.get(id=mission_id)
        
        # Vérifier que l'utilisateur a accès à cette mission
        if not (request.user == mission.client or request.user == mission.livreur or request.user.is_staff):
            return JsonResponse({'success': False, 'error': 'Accès non autorisé'}, status=403)
        
        data = json.loads(request.body)
        message_text = data.get('message', '').strip()
        
        if not message_text:
            return JsonResponse({'success': False, 'error': 'Message vide'}, status=400)
        
        # Récupérer ou créer la conversation
        conversation, created = Conversation.objects.get_or_create(
            mission=mission,
            defaults={
                'client': mission.client,
                'livreur': mission.livreur
            }
        )
        
        # Créer le message
        chat_message = ChatMessage.objects.create(
            conversation=conversation,
            sender=request.user,
            message=message_text,
            message_type='text'
        )
        
        # Mettre à jour la conversation
        conversation.last_message = chat_message
        conversation.updated_at = timezone.now()
        conversation.save()
        
        return JsonResponse({
            'success': True,
            'message_id': chat_message.id,
            'timestamp': chat_message.timestamp.strftime('%d/%m/%Y %H:%M')
        })
        
    except Mission.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Mission non trouvée'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def user_conversations(request):
    """API pour récupérer toutes les conversations de l'utilisateur"""
    try:
        conversations = Conversation.objects.filter(
            models.Q(client=request.user) | models.Q(livreur=request.user)
        ).select_related('mission', 'client', 'livreur', 'last_message').order_by('-updated_at')
        
        conversations_data = []
        for conversation in conversations:
            # Déterminer l'autre participant
            other_user = conversation.livreur if request.user == conversation.client else conversation.client
            
            conversations_data.append({
                'id': conversation.id,
                'mission_id': conversation.mission.id,
                'mission_title': conversation.mission.title or 'Livraison Express',
                'other_user_name': other_user.get_full_name() if other_user else 'Utilisateur supprimé',
                'last_message': conversation.last_message.message if conversation.last_message else 'Aucun message',
                'last_message_time': conversation.updated_at.strftime('%d/%m/%Y %H:%M'),
                'unread_count': ChatMessage.objects.filter(
                    conversation=conversation,
                    is_read=False
                ).exclude(sender=request.user).count()
            })
        
        return JsonResponse({
            'success': True,
            'conversations': conversations_data
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def mark_messages_read(request, conversation_id):
    """API pour marquer les messages comme lus"""
    try:
        conversation = Conversation.objects.get(id=conversation_id)
        
        # Vérifier l'accès
        if not (request.user == conversation.client or request.user == conversation.livreur):
            return JsonResponse({'success': False, 'error': 'Accès non autorisé'}, status=403)
        
        # Marquer tous les messages non lus comme lus
        ChatMessage.objects.filter(
            conversation=conversation,
            is_read=False
        ).exclude(sender=request.user).update(is_read=True)
        
        return JsonResponse({'success': True})
        
    except Conversation.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Conversation non trouvée'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
