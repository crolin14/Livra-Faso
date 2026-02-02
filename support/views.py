from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator
from django.db.models import Q, Count, Avg
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import (
    SupportTicket, TicketMessage, SupportCategory, TicketTemplate,
    SupportKnowledgeBase, SupportMetrics
)
from .services import SupportTicketService, SupportAnalyticsService, KnowledgeBaseService
from rbac.decorators import require_role
from audit.services import AuditService
import json
from datetime import datetime, timedelta

User = get_user_model()


# ===== VUES PRINCIPALES =====

@login_required
def ticket_list(request):
    """Liste des tickets de l'utilisateur"""
    tickets = SupportTicket.objects.filter(user=request.user).select_related(
        'category', 'assigned_to'
    ).order_by('-created_at')
    
    # Filtres
    status_filter = request.GET.get('status')
    category_filter = request.GET.get('category')
    
    if status_filter:
        tickets = tickets.filter(status=status_filter)
    if category_filter:
        tickets = tickets.filter(category_id=category_filter)
    
    # Pagination
    paginator = Paginator(tickets, 20)
    page_number = request.GET.get('page')
    tickets_page = paginator.get_page(page_number)
    
    # Données pour les filtres
    categories = SupportCategory.objects.filter(is_active=True)
    
    context = {
        'tickets': tickets_page,
        'categories': categories,
        'current_status': status_filter,
        'current_category': category_filter,
        'status_choices': SupportTicket.STATUS_CHOICES,
    }
    
    return render(request, 'support/ticket_list.html', context)


@login_required
def ticket_detail(request, ticket_id):
    """Détail d'un ticket"""
    ticket = get_object_or_404(
        SupportTicket.objects.select_related('category', 'assigned_to', 'user'),
        id=ticket_id
    )
    
    # Vérifier les permissions
    if ticket.user != request.user and not request.user.has_perm('support.view_supportticket'):
        return HttpResponseForbidden("Vous n'avez pas accès à ce ticket.")
    
    # Messages du ticket
    messages_list = ticket.messages.select_related('author').order_by('created_at')
    
    # Templates de réponse (pour les agents)
    templates = []
    if request.user.has_perm('support.change_supportticket'):
        templates = TicketTemplate.objects.filter(
            is_active=True,
            template_type='response'
        )
    
    context = {
        'ticket': ticket,
        'messages': messages_list,
        'templates': templates,
        'can_manage': request.user.has_perm('support.change_supportticket'),
    }
    
    return render(request, 'support/ticket_detail.html', context)


@login_required
def create_ticket(request):
    """Création d'un nouveau ticket"""
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        category_id = request.POST.get('category')
        priority = request.POST.get('priority', 'medium')
        
        if not all([title, description, category_id]):
            messages.error(request, "Tous les champs obligatoires doivent être remplis.")
            return redirect('support:create_ticket')
        
        try:
            category = SupportCategory.objects.get(id=category_id, is_active=True)
            
            ticket = SupportTicketService.create_ticket(
                user=request.user,
                title=title,
                description=description,
                category=category,
                priority=priority,
                source='web',
                request=request
            )
            
            if ticket:
                messages.success(
                    request, 
                    f"Votre ticket #{ticket.ticket_number} a été créé avec succès."
                )
                return redirect('support:ticket_detail', ticket_id=ticket.id)
            else:
                messages.error(request, "Erreur lors de la création du ticket.")
                
        except SupportCategory.DoesNotExist:
            messages.error(request, "Catégorie invalide.")
    
    # GET request
    categories = SupportCategory.objects.filter(is_active=True).order_by('name')
    
    context = {
        'categories': categories,
        'priority_choices': SupportTicket.PRIORITY_CHOICES,
    }
    
    return render(request, 'support/create_ticket.html', context)


@login_required
@require_http_methods(["POST"])
def add_message(request, ticket_id):
    """Ajouter un message à un ticket"""
    ticket = get_object_or_404(SupportTicket, id=ticket_id)
    
    # Vérifier les permissions
    if ticket.user != request.user and not request.user.has_perm('support.change_supportticket'):
        return HttpResponseForbidden("Vous n'avez pas accès à ce ticket.")
    
    content = request.POST.get('content')
    is_internal = request.POST.get('is_internal') == 'on'
    
    if not content:
        messages.error(request, "Le message ne peut pas être vide.")
        return redirect('support:ticket_detail', ticket_id=ticket_id)
    
    # Déterminer le type de message
    message_type = 'agent' if request.user.has_perm('support.change_supportticket') else 'user'
    
    message = SupportTicketService.add_message(
        ticket=ticket,
        author=request.user,
        content=content,
        message_type=message_type,
        is_internal=is_internal,
        request=request
    )
    
    if message:
        messages.success(request, "Votre message a été ajouté.")
    else:
        messages.error(request, "Erreur lors de l'ajout du message.")
    
    return redirect('support:ticket_detail', ticket_id=ticket_id)


# ===== VUES ADMIN =====

@login_required
@require_role(['admin', 'manager', 'support_agent'])
def admin_ticket_list(request):
    """Liste des tickets pour l'administration"""
    tickets = SupportTicket.objects.select_related(
        'category', 'assigned_to', 'user'
    ).order_by('-created_at')
    
    # Filtres
    status_filter = request.GET.get('status')
    priority_filter = request.GET.get('priority')
    category_filter = request.GET.get('category')
    assigned_filter = request.GET.get('assigned')
    
    if status_filter:
        tickets = tickets.filter(status=status_filter)
    if priority_filter:
        tickets = tickets.filter(priority=priority_filter)
    if category_filter:
        tickets = tickets.filter(category_id=category_filter)
    if assigned_filter == 'me':
        tickets = tickets.filter(assigned_to=request.user)
    elif assigned_filter == 'unassigned':
        tickets = tickets.filter(assigned_to__isnull=True)
    
    # Recherche
    search = request.GET.get('search')
    if search:
        tickets = tickets.filter(
            Q(ticket_number__icontains=search) |
            Q(title__icontains=search) |
            Q(user__username__icontains=search) |
            Q(user__email__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(tickets, 25)
    page_number = request.GET.get('page')
    tickets_page = paginator.get_page(page_number)
    
    # Données pour les filtres
    categories = SupportCategory.objects.filter(is_active=True)
    agents = User.objects.filter(
        groups__name__in=['support_agent', 'manager', 'admin']
    ).distinct()
    
    context = {
        'tickets': tickets_page,
        'categories': categories,
        'agents': agents,
        'status_choices': SupportTicket.STATUS_CHOICES,
        'priority_choices': SupportTicket.PRIORITY_CHOICES,
        'filters': {
            'status': status_filter,
            'priority': priority_filter,
            'category': category_filter,
            'assigned': assigned_filter,
            'search': search,
        }
    }
    
    return render(request, 'support/admin/ticket_list.html', context)


@login_required
@require_role(['admin', 'manager', 'support_agent'])
def admin_dashboard(request):
    """Tableau de bord du support"""
    now = timezone.now()
    today = now.date()
    
    # Statistiques générales
    stats = {
        'total_tickets': SupportTicket.objects.count(),
        'open_tickets': SupportTicket.objects.filter(status='open').count(),
        'in_progress_tickets': SupportTicket.objects.filter(status='in_progress').count(),
        'resolved_today': SupportTicket.objects.filter(
            resolved_at__date=today
        ).count(),
        'my_tickets': SupportTicket.objects.filter(assigned_to=request.user).count(),
    }
    
    # Tickets en retard
    overdue = SupportTicketService.get_overdue_tickets()
    stats['overdue_response'] = overdue['response'].count()
    stats['overdue_resolution'] = overdue['resolution'].count()
    
    # Tickets récents
    recent_tickets = SupportTicket.objects.select_related(
        'category', 'user', 'assigned_to'
    ).order_by('-created_at')[:10]
    
    # Métriques des 7 derniers jours
    week_ago = today - timedelta(days=7)
    recent_metrics = SupportMetrics.objects.filter(
        date__gte=week_ago
    ).order_by('date')
    
    # Satisfaction moyenne
    avg_satisfaction = SupportTicket.objects.filter(
        satisfaction_rating__isnull=False,
        resolved_at__date__gte=week_ago
    ).aggregate(avg=Avg('satisfaction_rating'))['avg']
    
    context = {
        'stats': stats,
        'recent_tickets': recent_tickets,
        'recent_metrics': recent_metrics,
        'avg_satisfaction': avg_satisfaction,
        'overdue_response_tickets': overdue['response'][:5],
        'overdue_resolution_tickets': overdue['resolution'][:5],
    }
    
    return render(request, 'support/admin/dashboard.html', context)


# ===== API ENDPOINTS =====

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_assign_ticket(request, ticket_id):
    """API pour assigner un ticket"""
    if not request.user.has_perm('support.change_supportticket'):
        return Response(
            {'error': 'Permission refusée'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    ticket = get_object_or_404(SupportTicket, id=ticket_id)
    assigned_to_id = request.data.get('assigned_to')
    
    if assigned_to_id:
        try:
            assigned_to = User.objects.get(id=assigned_to_id)
            success = SupportTicketService.assign_ticket(
                ticket=ticket,
                assigned_to=assigned_to,
                assigned_by=request.user,
                request=request
            )
            
            if success:
                return Response({
                    'success': True,
                    'message': f'Ticket assigné à {assigned_to.get_full_name()}'
                })
            else:
                return Response(
                    {'error': 'Erreur lors de l\'assignation'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
                
        except User.DoesNotExist:
            return Response(
                {'error': 'Utilisateur introuvable'},
                status=status.HTTP_404_NOT_FOUND
            )
    else:
        return Response(
            {'error': 'ID utilisateur requis'},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_resolve_ticket(request, ticket_id):
    """API pour résoudre un ticket"""
    if not request.user.has_perm('support.change_supportticket'):
        return Response(
            {'error': 'Permission refusée'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    ticket = get_object_or_404(SupportTicket, id=ticket_id)
    resolution_notes = request.data.get('resolution_notes', '')
    
    success = SupportTicketService.resolve_ticket(
        ticket=ticket,
        resolved_by=request.user,
        resolution_notes=resolution_notes,
        request=request
    )
    
    if success:
        return Response({
            'success': True,
            'message': 'Ticket marqué comme résolu'
        })
    else:
        return Response(
            {'error': 'Erreur lors de la résolution'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_escalate_ticket(request, ticket_id):
    """API pour escalader un ticket"""
    if not request.user.has_perm('support.change_supportticket'):
        return Response(
            {'error': 'Permission refusée'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    ticket = get_object_or_404(SupportTicket, id=ticket_id)
    reason = request.data.get('reason', '')
    
    success = SupportTicketService.escalate_ticket(
        ticket=ticket,
        escalated_by=request.user,
        reason=reason,
        request=request
    )
    
    if success:
        return Response({
            'success': True,
            'message': 'Ticket escaladé avec succès'
        })
    else:
        return Response(
            {'error': 'Erreur lors de l\'escalade'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_ticket_stats(request):
    """API pour les statistiques des tickets"""
    if not request.user.has_perm('support.view_supportticket'):
        return Response(
            {'error': 'Permission refusée'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Statistiques par statut
    status_stats = SupportTicket.objects.values('status').annotate(
        count=Count('id')
    )
    
    # Statistiques par priorité
    priority_stats = SupportTicket.objects.values('priority').annotate(
        count=Count('id')
    )
    
    # Statistiques par catégorie
    category_stats = SupportTicket.objects.values(
        'category__name'
    ).annotate(count=Count('id')).order_by('-count')[:10]
    
    # Évolution sur 30 jours
    thirty_days_ago = timezone.now().date() - timedelta(days=30)
    daily_stats = SupportMetrics.objects.filter(
        date__gte=thirty_days_ago
    ).order_by('date').values('date', 'tickets_created', 'tickets_resolved')
    
    return Response({
        'status_stats': list(status_stats),
        'priority_stats': list(priority_stats),
        'category_stats': list(category_stats),
        'daily_stats': list(daily_stats),
    })


# ===== BASE DE CONNAISSANCES =====

def knowledge_base(request):
    """Page principale de la base de connaissances"""
    query = request.GET.get('q', '')
    article_type = request.GET.get('type', '')
    category_id = request.GET.get('category', '')
    
    category = None
    if category_id:
        try:
            category = SupportCategory.objects.get(id=category_id, is_active=True)
        except SupportCategory.DoesNotExist:
            pass
    
    articles = KnowledgeBaseService.search_articles(
        query=query,
        article_type=article_type,
        category=category
    )
    
    # Pagination
    paginator = Paginator(articles, 20)
    page_number = request.GET.get('page')
    articles_page = paginator.get_page(page_number)
    
    # Articles populaires
    popular_articles = SupportKnowledgeBase.objects.filter(
        is_published=True, is_public=True
    ).order_by('-view_count')[:5]
    
    # Catégories
    categories = SupportCategory.objects.filter(is_active=True)
    
    context = {
        'articles': articles_page,
        'popular_articles': popular_articles,
        'categories': categories,
        'query': query,
        'current_type': article_type,
        'current_category': category,
        'article_types': SupportKnowledgeBase.ARTICLE_TYPES,
    }
    
    return render(request, 'support/knowledge_base.html', context)


def knowledge_article(request, slug):
    """Détail d'un article de la base de connaissances"""
    article = get_object_or_404(
        SupportKnowledgeBase,
        slug=slug,
        is_published=True,
        is_public=True
    )
    
    # Incrémenter le compteur de vues
    KnowledgeBaseService.increment_view_count(article)
    
    # Articles similaires
    similar_articles = SupportKnowledgeBase.objects.filter(
        categories__in=article.categories.all(),
        is_published=True,
        is_public=True
    ).exclude(id=article.id).distinct()[:5]
    
    context = {
        'article': article,
        'similar_articles': similar_articles,
    }
    
    return render(request, 'support/knowledge_article.html', context)


@api_view(['POST'])
def api_vote_article(request, article_id):
    """API pour voter sur l'utilité d'un article"""
    article = get_object_or_404(SupportKnowledgeBase, id=article_id)
    is_helpful = request.data.get('helpful', True)
    
    KnowledgeBaseService.vote_helpful(article, is_helpful)
    
    return Response({
        'success': True,
        'helpful_votes': article.helpful_votes,
        'total_votes': article.total_votes,
    })


# ===== SATISFACTION =====

@login_required
@require_http_methods(["POST"])
def submit_satisfaction(request, ticket_id):
    """Soumettre une évaluation de satisfaction"""
    ticket = get_object_or_404(SupportTicket, id=ticket_id, user=request.user)
    
    if ticket.status != 'resolved':
        messages.error(request, "Vous ne pouvez évaluer que les tickets résolus.")
        return redirect('support:ticket_detail', ticket_id=ticket_id)
    
    rating = request.POST.get('rating')
    comment = request.POST.get('comment', '')
    
    if not rating or not rating.isdigit() or not (1 <= int(rating) <= 5):
        messages.error(request, "Veuillez sélectionner une note entre 1 et 5.")
        return redirect('support:ticket_detail', ticket_id=ticket_id)
    
    success = SupportTicketService.submit_satisfaction_rating(
        ticket=ticket,
        rating=int(rating),
        comment=comment
    )
    
    if success:
        messages.success(request, "Merci pour votre évaluation !")
    else:
        messages.error(request, "Erreur lors de la soumission de l'évaluation.")
    
    return redirect('support:ticket_detail', ticket_id=ticket_id)
