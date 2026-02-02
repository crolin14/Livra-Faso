from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction
from django.db.models import Avg, Count, Q
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from .models import (
    SupportTicket, TicketMessage, SupportCategory, TicketTemplate, 
    SupportMetrics, SupportKnowledgeBase
)
from notifications.websocket_service import send_notification, send_role_notification
from audit.services import AuditService
import logging
from datetime import timedelta

User = get_user_model()
logger = logging.getLogger(__name__)


class SupportTicketService:
    """Service principal pour la gestion des tickets de support"""
    
    @staticmethod
    def create_ticket(user, title, description, category, priority='medium', 
                     source='web', user_email=None, user_phone='', 
                     related_mission=None, request=None):
        """Crée un nouveau ticket de support"""
        try:
            with transaction.atomic():
                if not user_email:
                    user_email = user.email
                
                ticket = SupportTicket.objects.create(
                    title=title,
                    description=description,
                    category=category,
                    user=user,
                    user_email=user_email,
                    user_phone=user_phone,
                    priority=priority,
                    source=source,
                    related_mission=related_mission
                )
                
                # Créer le premier message
                TicketMessage.objects.create(
                    ticket=ticket,
                    author=user,
                    author_name=user.get_full_name() or user.username,
                    author_email=user_email,
                    message_type='user',
                    content=description,
                    ip_address=SupportTicketService._get_client_ip(request) if request else None,
                    user_agent=request.META.get('HTTP_USER_AGENT', '') if request else ''
                )
                
                # Notifier les agents de support
                SupportTicketService._notify_new_ticket(ticket)
                
                # Envoyer email de confirmation
                SupportTicketService._send_ticket_confirmation_email(ticket)
                
                # Log de l'action
                AuditService.log_action(
                    user=user,
                    action_type='create',
                    description=f"Ticket de support créé: {ticket.ticket_number}",
                    content_object=ticket,
                    severity='low',
                    request=request,
                    additional_data={
                        'ticket_number': ticket.ticket_number,
                        'category': category.name,
                        'priority': priority,
                    }
                )
                
                return ticket
                
        except Exception as e:
            logger.error(f"Erreur lors de la création du ticket: {e}")
            return None
    
    @staticmethod
    def add_message(ticket, author, content, message_type='user', is_internal=False, request=None):
        """Ajoute un message à un ticket"""
        try:
            with transaction.atomic():
                message = TicketMessage.objects.create(
                    ticket=ticket,
                    author=author,
                    author_name=author.get_full_name() or author.username,
                    author_email=author.email,
                    message_type=message_type,
                    content=content,
                    is_public=not is_internal,
                    ip_address=SupportTicketService._get_client_ip(request) if request else None,
                    user_agent=request.META.get('HTTP_USER_AGENT', '') if request else ''
                )
                
                # Mettre à jour le ticket
                ticket.updated_at = timezone.now()
                if message_type == 'agent' and ticket.status == 'open':
                    ticket.status = 'in_progress'
                ticket.save()
                
                # Notifier les parties concernées
                SupportTicketService._notify_message_added(ticket, message, author)
                
                return message
                
        except Exception as e:
            logger.error(f"Erreur lors de l'ajout du message: {e}")
            return None
    
    @staticmethod
    def assign_ticket(ticket, assigned_to, assigned_by, request=None):
        """Assigne un ticket à un agent"""
        try:
            old_assignee = ticket.assigned_to
            
            ticket.assigned_to = assigned_to
            ticket.assigned_at = timezone.now()
            ticket.assigned_by = assigned_by
            ticket.save()
            
            # Créer un message système
            if old_assignee != assigned_to:
                content = f"Ticket assigné à {assigned_to.get_full_name()}"
                TicketMessage.objects.create(
                    ticket=ticket,
                    author=assigned_by,
                    author_name=assigned_by.get_full_name() or assigned_by.username,
                    author_email=assigned_by.email,
                    message_type='system',
                    content=content,
                    is_public=False
                )
            
            # Notifier le nouvel assigné
            send_notification(
                assigned_to,
                "Nouveau ticket assigné",
                f"Le ticket #{ticket.ticket_number} vous a été assigné",
                'ticket_assigned',
                {
                    'ticket_id': str(ticket.id),
                    'ticket_number': ticket.ticket_number,
                    'priority': ticket.priority,
                }
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de l'assignation du ticket: {e}")
            return False
    
    @staticmethod
    def resolve_ticket(ticket, resolved_by, resolution_notes='', request=None):
        """Marque un ticket comme résolu"""
        try:
            with transaction.atomic():
                ticket.status = 'resolved'
                ticket.resolved_at = timezone.now()
                ticket.resolved_by = resolved_by
                ticket.resolution_notes = resolution_notes
                ticket.save()
                
                # Créer un message de résolution
                if resolution_notes:
                    TicketMessage.objects.create(
                        ticket=ticket,
                        author=resolved_by,
                        author_name=resolved_by.get_full_name() or resolved_by.username,
                        author_email=resolved_by.email,
                        message_type='agent',
                        content=f"Ticket résolu.\n\nNotes de résolution:\n{resolution_notes}"
                    )
                
                # Notifier l'utilisateur
                send_notification(
                    ticket.user,
                    "Ticket résolu",
                    f"Votre ticket #{ticket.ticket_number} a été résolu",
                    'ticket_resolved',
                    {'ticket_id': str(ticket.id), 'ticket_number': ticket.ticket_number}
                )
                
                return True
                
        except Exception as e:
            logger.error(f"Erreur lors de la résolution du ticket: {e}")
            return False
    
    @staticmethod
    def get_overdue_tickets():
        """Récupère les tickets en retard"""
        now = timezone.now()
        
        overdue_response = SupportTicket.objects.filter(
            first_response_at__isnull=True,
            sla_response_due__lt=now
        )
        
        overdue_resolution = SupportTicket.objects.filter(
            resolved_at__isnull=True,
            sla_resolution_due__lt=now,
            status__in=['open', 'in_progress', 'waiting_customer']
        )
        
        return {
            'response': overdue_response,
            'resolution': overdue_resolution
        }
    
    @staticmethod
    def _notify_new_ticket(ticket):
        """Notifie la création d'un nouveau ticket"""
        send_role_notification(
            'support_agent',
            "Nouveau ticket de support",
            f"Ticket #{ticket.ticket_number}: {ticket.title}",
            'new_ticket',
            {
                'ticket_id': str(ticket.id),
                'ticket_number': ticket.ticket_number,
                'priority': ticket.priority,
                'category': ticket.category.name,
            }
        )
    
    @staticmethod
    def _notify_message_added(ticket, message, author):
        """Notifie l'ajout d'un message"""
        if message.message_type == 'user':
            # Notifier l'agent assigné
            if ticket.assigned_to:
                send_notification(
                    ticket.assigned_to,
                    f"Nouvelle réponse - Ticket #{ticket.ticket_number}",
                    f"L'utilisateur a répondu au ticket {ticket.ticket_number}",
                    'ticket_reply',
                    {'ticket_id': str(ticket.id), 'ticket_number': ticket.ticket_number}
                )
        elif message.message_type == 'agent':
            # Notifier l'utilisateur
            send_notification(
                ticket.user,
                f"Réponse à votre ticket #{ticket.ticket_number}",
                "Un agent a répondu à votre ticket de support",
                'ticket_response',
                {'ticket_id': str(ticket.id), 'ticket_number': ticket.ticket_number}
            )
    
    @staticmethod
    def _send_ticket_confirmation_email(ticket):
        """Envoie un email de confirmation de création de ticket"""
        try:
            subject = f"Ticket #{ticket.ticket_number} créé - LivraFaso Support"
            context = {'ticket': ticket}
            message = render_to_string('support/emails/ticket_created.html', context)
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[ticket.user_email],
                html_message=message,
                fail_silently=True
            )
        except Exception as e:
            logger.error(f"Erreur envoi email confirmation ticket: {e}")
    
    @staticmethod
    def _get_client_ip(request):
        """Récupère l'IP du client"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class SupportAnalyticsService:
    """Service pour les analytics de support"""
    
    @staticmethod
    def calculate_daily_metrics(date=None):
        """Calcule les métriques quotidiennes"""
        if not date:
            date = timezone.now().date()
        
        # Tickets créés ce jour
        tickets_created = SupportTicket.objects.filter(
            created_at__date=date
        ).count()
        
        # Tickets résolus ce jour
        tickets_resolved = SupportTicket.objects.filter(
            resolved_at__date=date
        ).count()
        
        # Tickets fermés ce jour
        tickets_closed = SupportTicket.objects.filter(
            closed_at__date=date
        ).count()
        
        # Temps de réponse moyen
        resolved_tickets = SupportTicket.objects.filter(
            resolved_at__date=date,
            first_response_at__isnull=False
        )
        
        avg_response_time = None
        if resolved_tickets.exists():
            response_times = []
            for ticket in resolved_tickets:
                if ticket.get_response_time():
                    response_times.append(ticket.get_response_time())
            
            if response_times:
                avg_response_time = sum(response_times, timedelta()) / len(response_times)
        
        # Temps de résolution moyen
        avg_resolution_time = None
        if resolved_tickets.exists():
            resolution_times = []
            for ticket in resolved_tickets:
                if ticket.get_resolution_time():
                    resolution_times.append(ticket.get_resolution_time())
            
            if resolution_times:
                avg_resolution_time = sum(resolution_times, timedelta()) / len(resolution_times)
        
        # SLA
        total_tickets = SupportTicket.objects.filter(created_at__date=date)
        sla_response_met = total_tickets.filter(
            first_response_at__isnull=False
        ).filter(
            first_response_at__lt=models.F('sla_response_due')
        ).count()
        
        sla_resolution_met = SupportTicket.objects.filter(
            resolved_at__date=date,
            resolved_at__lt=models.F('sla_resolution_due')
        ).count()
        
        # Satisfaction
        satisfaction_tickets = SupportTicket.objects.filter(
            resolved_at__date=date,
            satisfaction_rating__isnull=False
        )
        
        avg_satisfaction = satisfaction_tickets.aggregate(
            avg=Avg('satisfaction_rating')
        )['avg']
        
        # Créer ou mettre à jour les métriques
        metrics, created = SupportMetrics.objects.get_or_create(
            date=date,
            defaults={
                'tickets_created': tickets_created,
                'tickets_resolved': tickets_resolved,
                'tickets_closed': tickets_closed,
                'avg_first_response_time': avg_response_time,
                'avg_resolution_time': avg_resolution_time,
                'sla_response_met': sla_response_met,
                'sla_resolution_met': sla_resolution_met,
                'avg_satisfaction_rating': avg_satisfaction,
                'satisfaction_responses': satisfaction_tickets.count(),
            }
        )
        
        if not created:
            # Mettre à jour les métriques existantes
            metrics.tickets_created = tickets_created
            metrics.tickets_resolved = tickets_resolved
            metrics.tickets_closed = tickets_closed
            metrics.avg_first_response_time = avg_response_time
            metrics.avg_resolution_time = avg_resolution_time
            metrics.sla_response_met = sla_response_met
            metrics.sla_resolution_met = sla_resolution_met
            metrics.avg_satisfaction_rating = avg_satisfaction
            metrics.satisfaction_responses = satisfaction_tickets.count()
            metrics.save()
        
        return metrics
    
    @staticmethod
    def get_agent_performance(agent, start_date=None, end_date=None):
        """Calcule les performances d'un agent"""
        tickets = SupportTicket.objects.filter(assigned_to=agent)
        
        if start_date:
            tickets = tickets.filter(created_at__date__gte=start_date)
        if end_date:
            tickets = tickets.filter(created_at__date__lte=end_date)
        
        total_tickets = tickets.count()
        resolved_tickets = tickets.filter(status='resolved').count()
        
        # Temps de réponse moyen
        response_times = []
        for ticket in tickets.filter(first_response_at__isnull=False):
            if ticket.get_response_time():
                response_times.append(ticket.get_response_time())
        
        avg_response_time = None
        if response_times:
            avg_response_time = sum(response_times, timedelta()) / len(response_times)
        
        # Satisfaction moyenne
        avg_satisfaction = tickets.filter(
            satisfaction_rating__isnull=False
        ).aggregate(avg=Avg('satisfaction_rating'))['avg']
        
        return {
            'total_tickets': total_tickets,
            'resolved_tickets': resolved_tickets,
            'resolution_rate': (resolved_tickets / total_tickets * 100) if total_tickets > 0 else 0,
            'avg_response_time': avg_response_time,
            'avg_satisfaction': avg_satisfaction,
        }
    
    @staticmethod
    def get_category_stats(start_date=None, end_date=None):
        """Statistiques par catégorie"""
        tickets = SupportTicket.objects.all()
        
        if start_date:
            tickets = tickets.filter(created_at__date__gte=start_date)
        if end_date:
            tickets = tickets.filter(created_at__date__lte=end_date)
        
        return tickets.values('category__name').annotate(
            total=Count('id'),
            resolved=Count('id', filter=Q(status='resolved')),
            avg_satisfaction=Avg('satisfaction_rating')
        ).order_by('-total')


class KnowledgeBaseService:
    """Service pour la base de connaissances"""
    
    @staticmethod
    def search_articles(query, article_type=None, category=None):
        """Recherche dans la base de connaissances"""
        articles = SupportKnowledgeBase.objects.filter(
            is_published=True,
            is_public=True
        )
        
        if query:
            articles = articles.filter(
                Q(title__icontains=query) |
                Q(content__icontains=query) |
                Q(tags__icontains=query)
            )
        
        if article_type:
            articles = articles.filter(article_type=article_type)
        
        if category:
            articles = articles.filter(categories=category)
        
        return articles.order_by('-view_count', '-updated_at')
    
    @staticmethod
    def increment_view_count(article):
        """Incrémente le compteur de vues"""
        article.view_count += 1
        article.save(update_fields=['view_count'])
    
    @staticmethod
    def vote_helpful(article, is_helpful=True):
        """Vote pour l'utilité d'un article"""
        if is_helpful:
            article.helpful_votes += 1
        article.total_votes += 1
        article.save(update_fields=['helpful_votes', 'total_votes'])
