from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Count, Sum, Q
from datetime import datetime, timedelta
from users.models import User
from missions.models import Mission
from chat.models import Conversation
from ratings.models import Rating
import json

def is_admin(user):
    """Vérifie si l'utilisateur est un administrateur"""
    return user.is_authenticated and user.user_type == 'admin'

@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    """Dashboard principal de l'administrateur"""
    
    # Calcul des statistiques générales
    stats = calculate_dashboard_stats()
    
    # Métriques système
    system_metrics = get_system_metrics()
    
    # Activités récentes
    recent_activities = get_recent_activities()
    
    # Utilisateurs récents
    recent_users = User.objects.order_by('-date_joined')[:5]
    
    # Alertes récentes
    recent_alerts = get_recent_alerts()
    
    # Données pour les graphiques
    chart_data = get_chart_data()
    
    context = {
        'stats': stats,
        'system_metrics': system_metrics,
        'recent_activities': recent_activities,
        'recent_users': recent_users,
        'recent_alerts': recent_alerts,
        'current_time': timezone.now(),
        'chart_labels': json.dumps(chart_data['labels']),
        'missions_data': json.dumps(chart_data['missions_data']),
        'completed_missions_data': json.dumps(chart_data['completed_missions_data']),
    }
    
    return render(request, 'admin/dashboard_admin.html', context)

def calculate_dashboard_stats():
    """Calcule les statistiques du dashboard"""
    now = timezone.now()
    last_month = now - timedelta(days=30)
    today = now.date()
    
    # Utilisateurs
    total_users = User.objects.count()
    users_this_month = User.objects.filter(date_joined__gte=last_month).count()
    users_last_month = User.objects.filter(
        date_joined__gte=last_month - timedelta(days=30),
        date_joined__lt=last_month
    ).count()
    
    users_growth = calculate_growth_percentage(users_this_month, users_last_month)
    
    # Missions
    active_missions = Mission.objects.filter(
        status__in=['en_attente', 'acceptee', 'en_cours']
    ).count()
    
    missions_today = Mission.objects.filter(created_at__date=today).count()
    missions_yesterday = Mission.objects.filter(
        created_at__date=today - timedelta(days=1)
    ).count()
    
    missions_growth = calculate_growth_percentage(missions_today, missions_yesterday)
    
    # Revenus (simulation)
    total_revenue = Mission.objects.filter(
        status='livree'
    ).aggregate(total=Sum('price'))['total'] or 0
    
    revenue_this_month = Mission.objects.filter(
        status='livree',
        delivery_time__gte=last_month
    ).aggregate(total=Sum('price'))['total'] or 0
    
    revenue_last_month = Mission.objects.filter(
        status='livree',
        delivery_time__gte=last_month - timedelta(days=30),
        delivery_time__lt=last_month
    ).aggregate(total=Sum('price'))['total'] or 0
    
    revenue_growth = calculate_growth_percentage(revenue_this_month, revenue_last_month)
    
    # Santé du système (simulation)
    system_health = 98  # Pourcentage de disponibilité
    
    # Comptage par type d'utilisateur
    user_counts = User.objects.values('user_type').annotate(count=Count('id'))
    user_type_dict = {item['user_type']: item['count'] for item in user_counts}
    
    return {
        'total_users': total_users,
        'users_growth': users_growth,
        'active_missions': active_missions,
        'missions_growth': missions_growth,
        'total_revenue': total_revenue,
        'revenue_growth': revenue_growth,
        'system_health': system_health,
        'clients_count': user_type_dict.get('client', 0),
        'livreurs_count': user_type_dict.get('livreur', 0),
        'entreprises_count': user_type_dict.get('entreprise', 0),
    }

def calculate_growth_percentage(current, previous):
    """Calcule le pourcentage de croissance"""
    if previous == 0:
        return 100 if current > 0 else 0
    return round(((current - previous) / previous) * 100, 1)

def get_system_metrics():
    """Récupère les métriques système (simulation)"""
    import random
    
    return {
        'cpu_usage': random.randint(20, 80),
        'memory_usage': random.randint(30, 70),
        'storage_usage': random.randint(40, 85),
    }

def get_recent_activities():
    """Récupère les activités récentes"""
    activities = []
    
    # Nouvelles missions
    recent_missions = Mission.objects.order_by('-created_at')[:3]
    for mission in recent_missions:
        activities.append({
            'description': f'Nouvelle mission créée: {mission.title}',
            'timestamp': mission.created_at,
            'icon': 'truck',
            'color': 'blue',
            'status': 'active'
        })
    
    # Nouveaux utilisateurs
    recent_users = User.objects.order_by('-date_joined')[:3]
    for user in recent_users:
        activities.append({
            'description': f'Nouvel utilisateur inscrit: {user.username}',
            'timestamp': user.date_joined,
            'icon': 'user-plus',
            'color': 'green',
            'status': 'active'
        })
    
    # Missions complétées
    completed_missions = Mission.objects.filter(
        status='livree'
    ).order_by('-delivery_time')[:2]
    for mission in completed_missions:
        activities.append({
            'description': f'Mission complétée: {mission.title}',
            'timestamp': mission.delivery_time,
            'icon': 'check-circle',
            'color': 'green',
            'status': 'active'
        })
    
    # Trier par timestamp décroissant
    activities.sort(key=lambda x: x['timestamp'], reverse=True)
    
    return activities[:8]

def get_recent_alerts():
    """Récupère les alertes récentes (simulation)"""
    alerts = [
        {
            'title': 'Pic de trafic détecté',
            'message': 'Augmentation de 150% des connexions',
            'timestamp': timezone.now() - timedelta(minutes=15),
            'type': 'yellow',
            'icon': 'trending-up'
        },
        {
            'title': 'Maintenance programmée',
            'message': 'Redémarrage du serveur dans 2h',
            'timestamp': timezone.now() - timedelta(hours=1),
            'type': 'blue',
            'icon': 'clock'
        },
        {
            'title': 'Nouveau livreur vérifié',
            'message': 'Livreur ID #1234 approuvé',
            'timestamp': timezone.now() - timedelta(hours=3),
            'type': 'green',
            'icon': 'user-check'
        }
    ]
    
    return alerts

def get_chart_data():
    """Prépare les données pour les graphiques"""
    # Derniers 7 jours
    labels = []
    missions_data = []
    completed_missions_data = []
    
    for i in range(6, -1, -1):
        date = timezone.now().date() - timedelta(days=i)
        labels.append(date.strftime('%d/%m'))
        
        # Missions créées ce jour
        missions_count = Mission.objects.filter(created_at__date=date).count()
        missions_data.append(missions_count)
        
        # Missions complétées ce jour
        completed_count = Mission.objects.filter(
            delivery_time__date=date,
            status='livree'
        ).count()
        completed_missions_data.append(completed_count)
    
    return {
        'labels': labels,
        'missions_data': missions_data,
        'completed_missions_data': completed_missions_data
    }

@login_required
@user_passes_test(is_admin)
def admin_users_management(request):
    """Gestion des utilisateurs"""
    users = User.objects.all().order_by('-date_joined')
    
    context = {
        'users': users,
        'title': 'Gestion des Utilisateurs'
    }
    
    return render(request, 'admin/users_management.html', context)

@login_required
@user_passes_test(is_admin)
def admin_missions_management(request):
    """Gestion des missions"""
    missions = Mission.objects.all().order_by('-created_at')
    
    context = {
        'missions': missions,
        'title': 'Gestion des Missions'
    }
    
    return render(request, 'admin/missions_management.html', context)

@login_required
@user_passes_test(is_admin)
def admin_system_config(request):
    """Configuration du système"""
    context = {
        'title': 'Configuration Système'
    }
    
    return render(request, 'admin/system_config.html', context)

@login_required
@user_passes_test(is_admin)
def admin_reports(request):
    """Rapports et analytics"""
    context = {
        'title': 'Rapports et Analytics'
    }
    
    return render(request, 'admin/reports.html', context)

@login_required
@user_passes_test(is_admin)
def admin_security(request):
    """Sécurité et logs"""
    context = {
        'title': 'Sécurité et Logs'
    }
    
    return render(request, 'admin/security.html', context)

@login_required
@user_passes_test(is_admin)
def api_dashboard_stats(request):
    """API pour récupérer les stats en temps réel"""
    stats = calculate_dashboard_stats()
    system_metrics = get_system_metrics()
    
    return JsonResponse({
        'stats': stats,
        'system_metrics': system_metrics,
        'timestamp': timezone.now().isoformat()
    })
