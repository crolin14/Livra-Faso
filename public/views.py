from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm
from django.views.generic import TemplateView
from users.models import User, LivreurProfile, EntrepriseProfile
from users.forms import UserRegistrationForm
from missions.models import Mission
from subscriptions.models import SubscriptionPlan
from django.db import models
from django.db.models.functions import TruncMonth, TruncDate
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta
import json

def home(request):
    """Page d'accueil"""
    import logging
    logger = logging.getLogger(__name__)
    
    # Récupérer les plans d'abonnement actifs avec gestion d'erreur
    try:
        subscription_plans = SubscriptionPlan.objects.filter(is_active=True).order_by('price')[:3]
    except Exception as e:
        logger.error(f"Erreur récupération plans d'abonnement: {e}")
        subscription_plans = []
    
    # Statistiques générales avec gestion d'erreurs
    try:
        total_missions = Mission.objects.count()
    except Exception as e:
        logger.error(f"Erreur comptage missions: {e}")
        total_missions = 0
        
    try:
        total_users = User.objects.count()
    except Exception as e:
        logger.error(f"Erreur comptage utilisateurs: {e}")
        total_users = 0
        
    try:
        active_livreurs = User.objects.filter(user_type='livreur').count()
    except Exception as e:
        logger.error(f"Erreur comptage livreurs: {e}")
        active_livreurs = 0
    
    context = {
        'title': 'Accueil - Livraison Faso',
        'description': 'Plateforme de livraison au Burkina Faso',
        'subscription_plans': subscription_plans,
        'stats': {
            'total_missions': total_missions,
            'total_users': total_users,
            'active_livreurs': active_livreurs,
        }
    }
    return render(request, 'public/home_modern.html', context)

def about(request):
    """Page à propos"""
    context = {
        'title': 'À propos - Livraison Faso',
        'description': 'Découvrez notre histoire et notre mission',
    }
    return render(request, 'public/about_modern.html', context)

def contact(request):
    """Page contact"""
    if request.method == 'POST':
        # Traitement du formulaire de contact
        name = request.POST.get('name')
        email = request.POST.get('email')
        subject = request.POST.get('subject')
        message = request.POST.get('message')
        
        # Ici vous pouvez ajouter l'envoi d'email ou sauvegarder en base
        messages.success(request, 'Votre message a été envoyé avec succès !')
        return redirect('public:contact')
    
    context = {
        'title': 'Contact - Livraison Faso',
        'description': 'Contactez-nous pour toute question',
    }
    return render(request, 'public/contact_modern.html', context)

def faq(request):
    """Page FAQ"""
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
    
    context = {
        'title': 'FAQ - Livraison Faso',
        'description': 'Questions fréquemment posées',
        'faqs': faqs,
    }
    return render(request, 'public/faq_modern.html', context)



@login_required
def client_dashboard(request):
    """Dashboard pour les clients"""
    user = request.user
    
    # Récupérer les missions du client
    missions = Mission.objects.filter(client=user).order_by('-created_at')[:10]
    
    # Statistiques du client
    total_missions = Mission.objects.filter(client=user).count()
    completed_missions = Mission.objects.filter(client=user, status='completed').count()
    pending_missions = Mission.objects.filter(client=user, status='pending').count()
    in_progress_missions = Mission.objects.filter(client=user, status='in_progress').count()
    
    context = {
        'title': 'Dashboard Client',
        'user': user,
        'missions': missions,
        'stats': {
            'total_missions': total_missions,
            'completed_missions': completed_missions,
            'pending_missions': pending_missions,
            'in_progress_missions': in_progress_missions,
        }
    }
    return render(request, 'dashboards/client_dashboard.html', context)

@login_required
def livreur_dashboard(request):
    """Dashboard pour les livreurs"""
    user = request.user
    
    # Récupérer les missions du livreur
    missions = Mission.objects.filter(livreur=user).order_by('-created_at')[:10]
    available_missions = Mission.objects.filter(livreur__isnull=True, status='pending')[:5]
    
    # Statistiques du livreur
    total_missions = Mission.objects.filter(livreur=user).count()
    completed_missions = Mission.objects.filter(livreur=user, status='completed').count()
    pending_missions = Mission.objects.filter(livreur=user, status='pending').count()
    in_progress_missions = Mission.objects.filter(livreur=user, status='in_progress').count()
    
    context = {
        'title': 'Dashboard Livreur',
        'user': user,
        'missions': missions,
        'available_missions': available_missions,
        'stats': {
            'total_missions': total_missions,
            'completed_missions': completed_missions,
            'pending_missions': pending_missions,
            'in_progress_missions': in_progress_missions,
        }
    }
    return render(request, 'dashboards/livreur_dashboard.html', context)

@login_required
def entreprise_dashboard(request):
    """Dashboard pour les entreprises"""
    user = request.user
    
    # Récupérer les missions de l'entreprise (client)
    missions = Mission.objects.filter(client=user).order_by('-created_at')[:10]
    
    # Statistiques de l'entreprise
    total_missions = Mission.objects.filter(client=user).count()
    completed_missions = Mission.objects.filter(client=user, status='livree').count()
    pending_missions = Mission.objects.filter(client=user, status='en_attente').count()
    in_progress_missions = Mission.objects.filter(client=user, status='en_cours').count()
    
    # Calcul du chiffre d'affaires
    total_revenue = Mission.objects.filter(
        client=user, 
        status='livree'
    ).aggregate(total=Sum('price'))['total'] or 0
    
    context = {
        'title': 'Dashboard Entreprise',
        'user': user,
        'missions': missions,
        'stats': {
            'total_missions': total_missions,
            'completed_missions': completed_missions,
            'pending_missions': pending_missions,
            'in_progress_missions': in_progress_missions,
            'total_revenue': total_revenue,
        }
    }
    return render(request, 'dashboards/entreprise_dashboard.html', context)

@login_required
def dashboard(request):
    """Dashboard principal basé sur le type d'utilisateur"""
    user = request.user
    
    if user.user_type == 'client':
        return client_dashboard(request)
    elif user.user_type == 'livreur':
        return livreur_dashboard(request)
    elif user.user_type == 'entreprise':
        return entreprise_dashboard(request)
    elif user.user_type == 'admin':
        # Rediriger vers le dashboard admin
        return redirect('admin_dashboard:dashboard')
    else:
        # Pour les autres types ou utilisateurs sans type défini
        return render(request, 'public/dashboard_modern.html', {
            'title': 'Dashboard',
            'user': user,
        })


@login_required
def statistics_view(request):
    import logging
    logger = logging.getLogger(__name__)
    
    if request.user.user_type != 'entreprise':
        messages.error(request, "Vous n'avez pas l'autorisation d'accéder à cette page.")
        return redirect('public:dashboard')

    user = request.user
    
    try:
        missions = Mission.objects.filter(client=user)
    except Exception as e:
        logger.error(f"Erreur récupération missions utilisateur: {e}")
        missions = Mission.objects.none()

    # Statistiques générales avec gestion d'erreurs
    try:
        total_missions = missions.count()
        completed_missions = missions.filter(status='completed').count()
        pending_missions = missions.filter(status='pending').count()
        in_progress_missions = missions.filter(status='in_progress').count()
        cancelled_missions = missions.filter(status='cancelled').count()
    except Exception as e:
        logger.error(f"Erreur calcul statistiques missions: {e}")
        total_missions = completed_missions = pending_missions = in_progress_missions = cancelled_missions = 0

    # Calcul du taux de satisfaction (exemple simple)
    satisfaction_rate = "N/A"

    # Données pour les graphiques avec gestion d'erreurs
    try:
        missions_per_day = missions.annotate(
            day=TruncDate('created_at')
        ).values('day').annotate(count=models.Count('id')).order_by('day')
        missions_per_day = list(missions_per_day)
    except Exception as e:
        logger.error(f"Erreur génération données par jour: {e}")
        missions_per_day = []
        
    try:
        missions_per_month = missions.annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(count=models.Count('id')).order_by('month')
        missions_per_month = list(missions_per_month)
    except Exception as e:
        logger.error(f"Erreur génération données par mois: {e}")
        missions_per_month = []

    context = {
        'title': 'Statistiques',
        'total_missions': total_missions,
        'completed_missions': completed_missions,
        'pending_missions': pending_missions,
        'in_progress_missions': in_progress_missions,
        'cancelled_missions': cancelled_missions,
        'satisfaction_rate': satisfaction_rate,
        'missions_per_day_json': list(missions_per_day),
        'missions_per_month_json': list(missions_per_month),
    }
    return render(request, 'public/dashboard_statistics.html', context)

def is_admin(user):
    return user.is_superuser or user.is_staff

@user_passes_test(is_admin)
def admin_dashboard(request):
    import logging
    logger = logging.getLogger(__name__)
    
    today = timezone.now().date()
    
    # Livraisons aujourd'hui avec gestion d'erreur
    try:
        deliveries_today = Mission.objects.filter(created_at__date=today).count()
    except Exception as e:
        logger.error(f"Erreur comptage livraisons aujourd'hui: {e}")
        deliveries_today = 0
        
    # Revenus aujourd'hui avec gestion d'erreur
    try:
        revenue_today = Mission.objects.filter(created_at__date=today, status='completed').aggregate(total=Sum('price'))['total'] or 0
    except Exception as e:
        logger.error(f"Erreur calcul revenus aujourd'hui: {e}")
        revenue_today = 0
        
    # Livreurs actifs - requête simplifiée
    try:
        active_drivers = User.objects.filter(user_type='livreur').count()
    except Exception as e:
        logger.error(f"Erreur comptage livreurs actifs: {e}")
        active_drivers = 0
        
    # Entreprises avec gestion d'erreur
    try:
        companies_count = User.objects.filter(user_type='entreprise').count()
    except Exception as e:
        logger.error(f"Erreur comptage entreprises: {e}")
        companies_count = 0
    # Dernières livraisons avec gestion d'erreur
    try:
        recent_deliveries = Mission.objects.select_related('client').order_by('-created_at')[:4]
    except Exception as e:
        logger.error(f"Erreur récupération livraisons récentes: {e}")
        recent_deliveries = []

    # Graphique activité des livraisons avec gestion d'erreur
    try:
        days = [today - timedelta(days=i) for i in range(6, -1, -1)]
        deliveries_labels = [d.strftime('%a %d/%m') for d in days]
        deliveries_data = []
        for d in days:
            try:
                count = Mission.objects.filter(created_at__date=d).count()
                deliveries_data.append(count)
            except Exception:
                deliveries_data.append(0)
    except Exception as e:
        logger.error(f"Erreur génération graphique livraisons: {e}")
        deliveries_labels = []
        deliveries_data = []

    # Graphique répartition des revenus avec gestion d'erreur
    try:
        revenue_labels = ['Livraisons', 'Abonnements', 'Commissions', 'Extras']
        total_revenue = Mission.objects.filter(status='completed').aggregate(total=Sum('price'))['total'] or 0
        revenue_data = [total_revenue, 0, 0, 0]
    except Exception as e:
        logger.error(f"Erreur calcul répartition revenus: {e}")
        revenue_labels = ['Livraisons', 'Abonnements', 'Commissions', 'Extras']
        revenue_data = [0, 0, 0, 0]

    context = {
        'deliveries_today': deliveries_today,
        'revenue_today': revenue_today,
        'active_drivers': active_drivers,
        'companies_count': companies_count,
        'recent_deliveries': recent_deliveries,
        'deliveries_labels': json.dumps(deliveries_labels),
        'deliveries_data': json.dumps(deliveries_data),
        'revenue_labels': json.dumps(revenue_labels),
        'revenue_data': json.dumps(revenue_data),
    }
    # Rediriger vers le nouveau dashboard admin
    from django.shortcuts import redirect
    return redirect('admin_dashboard:dashboard')