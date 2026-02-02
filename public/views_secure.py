"""
Vues publiques sécurisées avec optimisations de performance
"""
import logging
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods
from django.core.exceptions import ValidationError, PermissionDenied
from django.db import models
from django.db.models.functions import TruncMonth, TruncDate
from django.db.models import Sum, Count, Q, Prefetch
from django.utils import timezone
from django.core.validators import validate_email
from django.utils.html import escape
from django.core.paginator import Paginator
from django.core.cache import cache
from datetime import timedelta
import json

from users.models import User, LivreurProfile, EntrepriseProfile
from missions.models import Mission

logger = logging.getLogger(__name__)

def home(request):
    """Page d'accueil avec statistiques en cache"""
    try:
        # Utilisation du cache pour les statistiques d'accueil
        stats = cache.get('home_stats')
        if not stats:
            stats = {
                'total_missions': Mission.objects.count(),
                'active_livreurs': User.objects.filter(
                    user_type='livreur', 
                    is_active=True
                ).count(),
                'entreprises': User.objects.filter(
                    user_type='entreprise', 
                    is_active=True
                ).count(),
            }
            # Cache pour 5 minutes
            cache.set('home_stats', stats, 300)
        
        context = {
            'title': 'Accueil - Livraison Faso',
            'description': 'Plateforme de livraison au Burkina Faso',
            'stats': stats,
        }
        return render(request, 'public/home.html', context)
        
    except Exception as e:
        logger.error(f"Erreur sur la page d'accueil: {e}")
        context = {
            'title': 'Accueil - Livraison Faso',
            'description': 'Plateforme de livraison au Burkina Faso',
        }
        return render(request, 'public/home.html', context)

def about(request):
    """Page à propos"""
    context = {
        'title': 'À propos - Livraison Faso',
        'description': 'Découvrez notre histoire et notre mission',
    }
    return render(request, 'public/about.html', context)

@csrf_protect
@require_http_methods(["GET", "POST"])
def contact(request):
    """Page contact avec validation sécurisée"""
    try:
        if request.method == 'POST':
            # Validation et nettoyage des données
            name = request.POST.get('name', '').strip()
            email = request.POST.get('email', '').strip()
            subject = request.POST.get('subject', '').strip()
            message = request.POST.get('message', '').strip()
            
            # Validations
            errors = []
            
            if not name or len(name) < 2:
                errors.append("Le nom doit contenir au moins 2 caractères.")
            elif len(name) > 100:
                errors.append("Le nom ne peut pas dépasser 100 caractères.")
            
            if not email:
                errors.append("L'adresse email est requise.")
            else:
                try:
                    validate_email(email)
                except ValidationError:
                    errors.append("Adresse email invalide.")
            
            if not subject or len(subject) < 5:
                errors.append("Le sujet doit contenir au moins 5 caractères.")
            elif len(subject) > 200:
                errors.append("Le sujet ne peut pas dépasser 200 caractères.")
            
            if not message or len(message) < 10:
                errors.append("Le message doit contenir au moins 10 caractères.")
            elif len(message) > 2000:
                errors.append("Le message ne peut pas dépasser 2000 caractères.")
            
            if errors:
                for error in errors:
                    messages.error(request, error)
            else:
                # Échappement HTML
                name = escape(name)
                subject = escape(subject)
                message = escape(message)
                
                # Ici vous pouvez ajouter l'envoi d'email ou sauvegarder en base
                logger.info(f"Message de contact reçu de {email}: {subject}")
                messages.success(request, 'Votre message a été envoyé avec succès !')
                return redirect('public:contact')
        
        context = {
            'title': 'Contact - Livraison Faso',
            'description': 'Contactez-nous pour toute question',
        }
        return render(request, 'public/contact.html', context)
        
    except Exception as e:
        logger.error(f"Erreur sur la page de contact: {e}")
        messages.error(request, "Une erreur est survenue. Veuillez réessayer.")
        return render(request, 'public/contact.html', {
            'title': 'Contact - Livraison Faso',
            'description': 'Contactez-nous pour toute question',
        })

def faq(request):
    """Page FAQ avec contenu en cache"""
    try:
        faqs = cache.get('faq_content')
        if not faqs:
            faqs = [
                {
                    'question': 'Comment fonctionne la livraison ?',
                    'answer': 'Notre plateforme met en relation les entreprises avec des livreurs qualifiés pour assurer des livraisons rapides et sécurisées.'
                },
                {
                    'question': 'Comment devenir livreur ?',
                    'answer': 'Inscrivez-vous en tant que livreur, complétez votre profil et commencez à accepter des missions de livraison.'
                },
                {
                    'question': 'Comment créer une mission de livraison ?',
                    'answer': 'Connectez-vous à votre compte entreprise, remplissez le formulaire de mission et un livreur acceptera votre demande.'
                },
                {
                    'question': 'Quels sont les moyens de paiement ?',
                    'answer': 'Nous acceptons Mobile Money (Moov, Orange, Telecel), cartes bancaires et paiements en espèces.'
                },
                {
                    'question': 'Comment suivre ma livraison ?',
                    'answer': 'Vous recevrez des notifications en temps réel sur l\'état de votre livraison via notre application.'
                },
            ]
            # Cache pour 1 heure
            cache.set('faq_content', faqs, 3600)
        
        context = {
            'title': 'FAQ - Livraison Faso',
            'description': 'Questions fréquemment posées',
            'faqs': faqs,
        }
        return render(request, 'public/faq.html', context)
        
    except Exception as e:
        logger.error(f"Erreur sur la page FAQ: {e}")
        return render(request, 'public/faq.html', {
            'title': 'FAQ - Livraison Faso',
            'description': 'Questions fréquemment posées',
            'faqs': [],
        })

@login_required
def dashboard(request):
    """Tableau de bord utilisateur avec requêtes optimisées"""
    try:
        user = request.user
        
        if user.user_type == 'livreur':
            # Requêtes optimisées pour livreur
            missions_assigned = user.missions_assigned.count()
            missions_completed = user.missions_assigned.filter(status='livree').count()
            
            # Optimisation: utiliser aggregate au lieu de sum() en Python
            earnings_result = user.missions_assigned.filter(status='livree').aggregate(
                total=Sum('price')
            )
            total_earnings = earnings_result['total'] or 0
            
            # Requête optimisée avec select_related
            recent_missions = user.missions_assigned.select_related('client').order_by('-created_at')[:5]
            
            context = {
                'title': 'Tableau de bord - Livreur',
                'missions_assigned': missions_assigned,
                'missions_completed': missions_completed,
                'total_earnings': total_earnings,
                'recent_missions': recent_missions,
            }
            return render(request, 'users/livreur_dashboard.html', context)
        
        elif user.user_type == 'entreprise':
            # Requêtes optimisées pour entreprise
            missions_qs = Mission.objects.filter(client=user)
            
            missions_created = missions_qs.count()
            missions_completed = missions_qs.filter(status='livree').count()
            
            # Optimisation: utiliser aggregate
            spent_result = missions_qs.filter(status='livree').aggregate(
                total=Sum('price')
            )
            total_spent = spent_result['total'] or 0
            
            # Requête optimisée avec select_related
            recent_missions = missions_qs.select_related('livreur').order_by('-created_at')[:5]

            context = {
                'title': 'Tableau de bord - Entreprise',
                'missions_created': missions_created,
                'missions_completed': missions_completed,
                'total_spent': total_spent,
                'recent_missions': recent_missions,
            }
            return render(request, 'users/entreprise_dashboard.html', context)
        
        # Redirection par défaut pour types d'utilisateurs non reconnus
        logger.warning(f"Type d'utilisateur non reconnu: {user.user_type}")
        return redirect('public:home')
        
    except Exception as e:
        logger.error(f"Erreur sur le tableau de bord: {e}")
        messages.error(request, "Erreur lors du chargement du tableau de bord.")
        return redirect('public:home')

@login_required
def statistics_view(request):
    """Statistiques avec contrôles de sécurité et optimisations"""
    try:
        if request.user.user_type != 'entreprise':
            logger.warning(f"Accès non autorisé aux statistiques par {request.user.id}")
            messages.error(request, "Vous n'avez pas l'autorisation d'accéder à cette page.")
            return redirect('public:dashboard')

        user = request.user
        
        # Requête de base optimisée
        missions = Mission.objects.filter(client=user).select_related('livreur')

        # Statistiques générales avec une seule requête
        stats = missions.aggregate(
            total=Count('id'),
            completed=Count('id', filter=Q(status='livree')),
            pending=Count('id', filter=Q(status='en_attente')),
            in_progress=Count('id', filter=Q(status='en_cours')),
            cancelled=Count('id', filter=Q(status='annulee'))
        )

        # Données pour les graphiques optimisées
        missions_per_day = missions.annotate(
            day=TruncDate('created_at')
        ).values('day').annotate(
            count=Count('id')
        ).order_by('day')

        missions_per_month = missions.annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(
            count=Count('id')
        ).order_by('month')

        context = {
            'title': 'Statistiques',
            'total_missions': stats['total'],
            'completed_missions': stats['completed'],
            'pending_missions': stats['pending'],
            'in_progress_missions': stats['in_progress'],
            'cancelled_missions': stats['cancelled'],
            'satisfaction_rate': "N/A",  # À implémenter avec un système de notation
            'missions_per_day_json': list(missions_per_day),
            'missions_per_month_json': list(missions_per_month),
        }
        return render(request, 'public/dashboard_statistics.html', context)
        
    except Exception as e:
        logger.error(f"Erreur sur les statistiques: {e}")
        messages.error(request, "Erreur lors du chargement des statistiques.")
        return redirect('public:dashboard')

def is_admin(user):
    """Vérification sécurisée des droits administrateur"""
    return user.is_authenticated and (user.is_superuser or user.is_staff)

@user_passes_test(is_admin)
def admin_dashboard(request):
    """Tableau de bord administrateur avec sécurité renforcée"""
    try:
        today = timezone.now().date()
        
        # Requêtes optimisées avec cache
        cache_key = f'admin_stats_{today}'
        admin_stats = cache.get(cache_key)
        
        if not admin_stats:
            # Livraisons aujourd'hui
            deliveries_today = Mission.objects.filter(created_at__date=today).count()
            
            # Revenus aujourd'hui (missions livrées aujourd'hui)
            revenue_result = Mission.objects.filter(
                created_at__date=today, 
                status='livree'
            ).aggregate(total=Sum('price'))
            revenue_today = revenue_result['total'] or 0
            
            # Livreurs actifs (ayant une mission en cours)
            active_drivers = User.objects.filter(
                user_type='livreur', 
                missions_assigned__status='en_cours'
            ).distinct().count()
            
            # Entreprises
            companies_count = User.objects.filter(user_type='entreprise').count()
            
            admin_stats = {
                'deliveries_today': deliveries_today,
                'revenue_today': revenue_today,
                'active_drivers': active_drivers,
                'companies_count': companies_count,
            }
            
            # Cache pour 10 minutes
            cache.set(cache_key, admin_stats, 600)
        
        # Dernières livraisons avec requête optimisée
        recent_deliveries = Mission.objects.select_related(
            'client', 'livreur'
        ).order_by('-created_at')[:4]

        # Graphique activité des livraisons (7 derniers jours)
        days = [today - timedelta(days=i) for i in range(6, -1, -1)]
        deliveries_labels = [d.strftime('%a %d/%m') for d in days]
        
        # Optimisation: une seule requête pour tous les jours
        deliveries_by_day = {}
        missions_by_day = Mission.objects.filter(
            created_at__date__in=days
        ).extra(
            select={'day': 'DATE(created_at)'}
        ).values('day').annotate(count=Count('id'))
        
        for item in missions_by_day:
            deliveries_by_day[item['day']] = item['count']
        
        deliveries_data = [
            deliveries_by_day.get(d.strftime('%Y-%m-%d'), 0) 
            for d in days
        ]

        # Graphique répartition des revenus
        revenue_result = Mission.objects.filter(status='livree').aggregate(
            total=Sum('price')
        )
        total_revenue = revenue_result['total'] or 0
        
        revenue_labels = ['Livraisons', 'Abonnements', 'Commissions', 'Extras']
        revenue_data = [total_revenue, 0, 0, 0]

        context = {
            **admin_stats,
            'recent_deliveries': recent_deliveries,
            'deliveries_labels': json.dumps(deliveries_labels),
            'deliveries_data': json.dumps(deliveries_data),
            'revenue_labels': json.dumps(revenue_labels),
            'revenue_data': json.dumps(revenue_data),
        }
        
        logger.info(f"Accès au tableau de bord admin par {request.user.id}")
        return render(request, 'admin_dashboard.html', context)
        
    except Exception as e:
        logger.error(f"Erreur sur le tableau de bord admin: {e}")
        messages.error(request, "Erreur lors du chargement du tableau de bord.")
        return redirect('public:home')
