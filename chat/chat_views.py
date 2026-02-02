"""
Vues pour le chat temps réel - LivraFaso
"""

from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.utils import timezone
from rbac.new_decorators import client_required, livreur_required, entreprise_required, admin_required
from missions.models import Mission
from .models import Conversation, Message
from .realtime_consumers import NotificationService
import json
import logging

logger = logging.getLogger(__name__)

@login_required
def mission_chat_view(request, mission_id):
    """Vue pour le chat d'une mission"""
    mission = get_object_or_404(Mission, id=mission_id)
    
    # Vérifier les permissions
    user_type = getattr(request.user, 'user_type', None)
    has_access = False
    
    if user_type == 'client' and mission.client == request.user:
        has_access = True
    elif user_type == 'livreur' and mission.livreur == request.user:
        has_access = True
    elif user_type == 'entreprise':
        has_access = True  # À affiner selon la logique métier
    elif request.user.is_staff or request.user.is_superuser:
        has_access = True
    
    if not has_access:
        return JsonResponse({'error': 'Accès non autorisé'}, status=403)
    
    # Récupérer ou créer la conversation
    conversation, created = Conversation.objects.get_or_create(
        mission=mission,
        defaults={'title': f"Chat Mission #{mission.id}"}
    )
    
    # Ajouter l'utilisateur aux participants
    if request.user not in conversation.participants.all():
        conversation.participants.add(request.user)
    
    context = {
        'mission': mission,
        'conversation': conversation,
        'user_type': user_type,
        'websocket_url': f'ws/chat/mission/{mission_id}/'
    }
    
    return render(request, 'chat/mission_chat.html', context)

@login_required
@require_http_methods(["GET"])
def conversation_messages(request, conversation_id):
    """API pour récupérer les messages d'une conversation"""
    conversation = get_object_or_404(Conversation, id=conversation_id)
    
    # Vérifier l'accès
    if request.user not in conversation.participants.all() and not request.user.is_staff:
        return JsonResponse({'error': 'Accès non autorisé'}, status=403)
    
    # Pagination
    page = request.GET.get('page', 1)
    messages = Message.objects.filter(
        conversation=conversation
    ).select_related('user').order_by('-created_at')
    
    paginator = Paginator(messages, 20)
    page_obj = paginator.get_page(page)
    
    messages_data = []
    for message in page_obj:
        messages_data.append({
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
            'file_url': message.file_url,
            'is_read': message.is_read
        })
    
    return JsonResponse({
        'messages': messages_data,
        'has_next': page_obj.has_next(),
        'has_previous': page_obj.has_previous(),
        'current_page': page_obj.number,
        'total_pages': paginator.num_pages
    })

@login_required
@csrf_exempt
@require_http_methods(["POST"])
def send_message(request):
    """API pour envoyer un message"""
    try:
        data = json.loads(request.body)
        conversation_id = data.get('conversation_id')
        content = data.get('content', '').strip()
        message_type = data.get('message_type', 'text')
        file_url = data.get('file_url')
        
        if not conversation_id or not content:
            return JsonResponse({'error': 'Données manquantes'}, status=400)
        
        conversation = get_object_or_404(Conversation, id=conversation_id)
        
        # Vérifier l'accès
        if request.user not in conversation.participants.all():
            return JsonResponse({'error': 'Accès non autorisé'}, status=403)
        
        # Créer le message
        message = Message.objects.create(
            conversation=conversation,
            user=request.user,
            content=content,
            message_type=message_type,
            file_url=file_url
        )
        
        # Envoyer notification temps réel
        if conversation.mission:
            NotificationService.send_mission_chat_notification(
                conversation.mission.id,
                content,
                request.user
            )
        
        return JsonResponse({
            'success': True,
            'message': {
                'id': message.id,
                'content': message.content,
                'timestamp': message.created_at.isoformat(),
                'user': {
                    'id': request.user.id,
                    'username': request.user.username,
                    'full_name': request.user.get_full_name()
                }
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Format JSON invalide'}, status=400)
    except Exception as e:
        logger.error(f"Erreur envoi message: {e}")
        return JsonResponse({'error': 'Erreur serveur'}, status=500)

@login_required
@require_http_methods(["GET"])
def user_conversations(request):
    """API pour récupérer les conversations de l'utilisateur"""
    conversations = Conversation.objects.filter(
        participants=request.user
    ).select_related('mission').prefetch_related('participants').annotate(
        unread_count=Count('messages', filter=Q(messages__is_read=False) & ~Q(messages__user=request.user))
    ).order_by('-updated_at')
    
    # Pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(conversations, 10)
    page_obj = paginator.get_page(page)
    
    conversations_data = []
    for conv in page_obj:
        # Dernier message
        last_message = conv.messages.order_by('-created_at').first()
        
        conversations_data.append({
            'id': conv.id,
            'title': conv.title,
            'mission': {
                'id': conv.mission.id if conv.mission else None,
                'title': str(conv.mission) if conv.mission else None,
                'status': conv.mission.status if conv.mission else None
            } if conv.mission else None,
            'participants': [
                {
                    'id': p.id,
                    'username': p.username,
                    'full_name': p.get_full_name(),
                    'user_type': getattr(p, 'user_type', 'client')
                }
                for p in conv.participants.all()
            ],
            'last_message': {
                'content': last_message.content if last_message else None,
                'timestamp': last_message.created_at.isoformat() if last_message else None,
                'user': last_message.user.get_full_name() if last_message else None
            } if last_message else None,
            'unread_count': conv.unread_count,
            'updated_at': conv.updated_at.isoformat()
        })
    
    return JsonResponse({
        'conversations': conversations_data,
        'has_next': page_obj.has_next(),
        'has_previous': page_obj.has_previous(),
        'current_page': page_obj.number,
        'total_pages': paginator.num_pages
    })

@login_required
@csrf_exempt
@require_http_methods(["POST"])
def mark_messages_read(request):
    """API pour marquer les messages comme lus"""
    try:
        data = json.loads(request.body)
        conversation_id = data.get('conversation_id')
        
        if not conversation_id:
            return JsonResponse({'error': 'ID conversation manquant'}, status=400)
        
        conversation = get_object_or_404(Conversation, id=conversation_id)
        
        # Vérifier l'accès
        if request.user not in conversation.participants.all():
            return JsonResponse({'error': 'Accès non autorisé'}, status=403)
        
        # Marquer les messages comme lus
        updated_count = Message.objects.filter(
            conversation=conversation,
            is_read=False
        ).exclude(user=request.user).update(
            is_read=True,
            read_at=timezone.now()
        )
        
        return JsonResponse({
            'success': True,
            'updated_count': updated_count
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Format JSON invalide'}, status=400)
    except Exception as e:
        logger.error(f"Erreur marquage messages lus: {e}")
        return JsonResponse({'error': 'Erreur serveur'}, status=500)

@admin_required
def chat_moderation_view(request):
    """Vue de modération du chat pour les admins"""
    # Statistiques
    total_conversations = Conversation.objects.count()
    total_messages = Message.objects.count()
    active_conversations = Conversation.objects.filter(
        updated_at__gte=timezone.now() - timezone.timedelta(days=7)
    ).count()
    
    # Messages récents
    recent_messages = Message.objects.select_related(
        'user', 'conversation', 'conversation__mission'
    ).order_by('-created_at')[:20]
    
    # Conversations avec le plus de messages
    top_conversations = Conversation.objects.annotate(
        message_count=Count('messages')
    ).order_by('-message_count')[:10]
    
    context = {
        'stats': {
            'total_conversations': total_conversations,
            'total_messages': total_messages,
            'active_conversations': active_conversations,
        },
        'recent_messages': recent_messages,
        'top_conversations': top_conversations,
    }
    
    return render(request, 'chat/moderation.html', context)

@admin_required
@csrf_exempt
@require_http_methods(["POST"])
def moderate_message(request):
    """API pour modérer un message"""
    try:
        data = json.loads(request.body)
        message_id = data.get('message_id')
        action = data.get('action')  # 'hide', 'delete', 'flag'
        reason = data.get('reason', '')
        
        if not message_id or not action:
            return JsonResponse({'error': 'Données manquantes'}, status=400)
        
        message = get_object_or_404(Message, id=message_id)
        
        if action == 'hide':
            message.is_hidden = True
            message.moderation_reason = reason
            message.moderated_by = request.user
            message.moderated_at = timezone.now()
            message.save()
            
        elif action == 'delete':
            message.delete()
            
        elif action == 'flag':
            message.is_flagged = True
            message.moderation_reason = reason
            message.moderated_by = request.user
            message.moderated_at = timezone.now()
            message.save()
        
        return JsonResponse({'success': True})
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Format JSON invalide'}, status=400)
    except Exception as e:
        logger.error(f"Erreur modération message: {e}")
        return JsonResponse({'error': 'Erreur serveur'}, status=500)

@login_required
@require_http_methods(["GET"])
def chat_search(request):
    """API pour rechercher dans les messages"""
    query = request.GET.get('q', '').strip()
    conversation_id = request.GET.get('conversation_id')
    
    if not query:
        return JsonResponse({'messages': []})
    
    # Base queryset
    messages = Message.objects.filter(
        content__icontains=query,
        is_hidden=False
    ).select_related('user', 'conversation')
    
    # Filtrer par conversation si spécifié
    if conversation_id:
        messages = messages.filter(conversation_id=conversation_id)
    
    # Filtrer par accès utilisateur
    if not request.user.is_staff:
        messages = messages.filter(
            conversation__participants=request.user
        )
    
    # Pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(messages.order_by('-created_at'), 10)
    page_obj = paginator.get_page(page)
    
    messages_data = []
    for message in page_obj:
        messages_data.append({
            'id': message.id,
            'content': message.content,
            'user': {
                'id': message.user.id,
                'username': message.user.username,
                'full_name': message.user.get_full_name()
            },
            'conversation': {
                'id': message.conversation.id,
                'title': message.conversation.title
            },
            'timestamp': message.created_at.isoformat()
        })
    
    return JsonResponse({
        'messages': messages_data,
        'has_next': page_obj.has_next(),
        'has_previous': page_obj.has_previous(),
        'current_page': page_obj.number,
        'total_pages': paginator.num_pages,
        'total_results': paginator.count
    })
