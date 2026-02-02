from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from .models import Conversation, ChatMessage, MessageNotification

@login_required
def conversation_list(request):
    """Liste des conversations de l'utilisateur"""
    user = request.user
    conversations = user.conversations.filter(is_active=True)
    
    # Ajouter les informations de messages non lus
    for conversation in conversations:
        conversation.has_unread_messages = conversation.has_unread_messages(user)
        conversation.unread_count = conversation.unread_count(user)
    
    context = {
        'title': 'Messages',
        'conversations': conversations,
    }
    return render(request, 'chat/dashboard_chat.html', context)

@login_required
def conversation_detail(request, conversation_id):
    """Détails d'une conversation"""
    conversation = get_object_or_404(Conversation, id=conversation_id, participants=request.user)
    
    # Marquer les messages comme lus
    unread_messages = conversation.messages.filter(is_read=False).exclude(sender=request.user)
    unread_messages.update(is_read=True)
    
    context = {
        'title': 'Conversation',
        'conversation': conversation,
        'messages': conversation.messages.all(),
    }
    return render(request, 'chat/conversation_detail.html', context)

@login_required
def send_message(request, conversation_id):
    """Envoyer un message"""
    conversation = get_object_or_404(Conversation, id=conversation_id, participants=request.user)
    
    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        message_type = request.POST.get('message_type', 'text')
        
        if content:
            message = ChatMessage.objects.create(
                conversation=conversation,
                sender=request.user,
                message=content,
                message_type=message_type
            )
            
            # Créer des notifications pour les autres participants
            for participant in conversation.participants.exclude(id=request.user.id):
                MessageNotification.objects.create(
                    user=participant,
                    message=message
                )
            
            # Mettre à jour la date de modification de la conversation
            conversation.save()
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message_id': message.id,
                    'timestamp': message.timestamp.isoformat()
                })
            
            messages.success(request, 'Message envoyé !')
        else:
            messages.error(request, 'Le message ne peut pas être vide.')
    
    return redirect('chat:detail', conversation_id=conversation_id)

@login_required
def start_conversation(request, user_id):
    """Démarrer une nouvelle conversation"""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    other_user = get_object_or_404(User, id=user_id)
    
    if other_user == request.user:
        messages.error(request, 'Vous ne pouvez pas démarrer une conversation avec vous-même.')
        return redirect('chat:list')
    
    # Vérifier si une conversation existe déjà
    existing_conversation = Conversation.objects.filter(
        participants=request.user
    ).filter(
        participants=other_user
    ).filter(
        is_active=True
    ).first()
    
    if existing_conversation:
        return redirect('chat:detail', conversation_id=existing_conversation.id)
    
    # Créer une nouvelle conversation
    conversation = Conversation.objects.create()
    conversation.participants.add(request.user, other_user)
    
    messages.success(request, f'Nouvelle conversation créée avec {other_user.username}')
    return redirect('chat:detail', conversation_id=conversation.id)
