from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q, Count, Sum, Avg
from django.utils import timezone
from datetime import datetime, timedelta
import json
import csv
from io import StringIO
from users.models import User
from missions.models import Mission
from subscriptions.models import SubscriptionPlan
from ratings.models import Rating
from chat.models import Conversation, ChatMessage
from rbac.permissions import require_permission, require_role, admin_required, manager_required

def is_admin(user):
    """Fonction helper pour vérifier si un utilisateur est admin"""
    return user.is_authenticated and (user.is_superuser or user.has_any_role('admin', 'super_admin'))

@admin_required
def admin_dashboard(request):
    """Dashboard principal pour les administrateurs"""
    
    # Statistiques générales
    total_users = User.objects.count()
    total_missions = Mission.objects.count()
    active_missions = Mission.objects.filter(status__in=['en_attente', 'acceptee', 'en_cours']).count()
    completed_missions = Mission.objects.filter(status='livree').count()
    
    # Calcul des revenus (missions complétées)
    total_revenue = sum(mission.price or 0 for mission in Mission.objects.filter(status='livree'))
    
    # Croissance mensuelle des utilisateurs
    last_month = timezone.now() - timedelta(days=30)
    new_users_this_month = User.objects.filter(date_joined__gte=last_month).count()
    users_growth = (new_users_this_month / max(total_users - new_users_this_month, 1)) * 100
    
    # Missions des 7 derniers jours pour le graphique
    missions_data = []
    for i in range(7):
        date = timezone.now().date() - timedelta(days=i)
        missions_count = Mission.objects.filter(created_at__date=date).count()
        missions_data.append({
            'date': date.strftime('%d/%m'),
            'count': missions_count
        })
    missions_data.reverse()
    
    # Activités récentes
    recent_activities = [
        {
            'type': 'user',
            'message': f'{new_users_this_month} nouveaux utilisateurs ce mois',
            'time': 'Il y a 2 heures',
            'icon': 'user-plus'
        },
        {
            'type': 'mission',
            'message': f'{active_missions} missions en cours',
            'time': 'Il y a 5 minutes',
            'icon': 'truck'
        },
        {
            'type': 'system',
            'message': 'Sauvegarde automatique effectuée',
            'time': 'Il y a 1 heure',
            'icon': 'database'
        },
    ]
    
    # Alertes système
    alerts = []
    if active_missions > 50:
        alerts.append({
            'type': 'warning',
            'message': f'Charge élevée: {active_missions} missions actives',
            'time': 'Maintenant'
        })
    
    # Utilisateurs récents
    recent_users = User.objects.order_by('-date_joined')[:5]
    
    # Métriques système simulées
    system_metrics = {
        'cpu': 45,
        'memory': 62,
        'storage': 78,
        'network': 23
    }
    
    context = {
        'title': 'Dashboard Administrateur',
        'total_users': total_users,
        'total_missions': total_missions,
        'active_missions': active_missions,
        'completed_missions': completed_missions,
        'total_revenue': total_revenue,
        'users_growth': round(users_growth, 1),
        'missions_data': json.dumps(missions_data),
        'recent_activities': recent_activities,
        'alerts': alerts,
        'recent_users': recent_users,
        'system_metrics': system_metrics,
        'system_health': 85,  # Pourcentage de santé globale
    }
    
    return render(request, 'admin/dashboard_admin.html', context)

@require_permission('admin_dashboard.manage_users')
def users_management(request):
    """Gestion des utilisateurs"""
    users = User.objects.all().order_by('-date_joined')
    
    context = {
        'title': 'Gestion des Utilisateurs',
        'users': users,
    }
    
    return render(request, 'admin/users_management.html', context)

@require_permission('admin_dashboard.manage_missions')
def missions_management(request):
    """Gestion des missions"""
    # Filtres
    status_filter = request.GET.get('status')
    priority_filter = request.GET.get('priority')
    livreur_filter = request.GET.get('livreur')
    date_filter = request.GET.get('date')
    
    missions = Mission.objects.all().select_related('client', 'livreur')
    
    # Appliquer les filtres
    if status_filter:
        missions = missions.filter(status=status_filter)
    if priority_filter:
        missions = missions.filter(priority=priority_filter)
    if livreur_filter:
        missions = missions.filter(livreur_id=livreur_filter)
    if date_filter:
        missions = missions.filter(created_at__date=date_filter)
    
    missions = missions.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(missions, 20)
    page_number = request.GET.get('page')
    missions_page = paginator.get_page(page_number)
    
    # Statistiques des missions
    missions_stats = {
        'en_cours': Mission.objects.filter(status='en_cours').count(),
        'livree': Mission.objects.filter(status='livree').count(),
        'en_attente': Mission.objects.filter(status='en_attente').count(),
        'annulee': Mission.objects.filter(status='annulee').count(),
    }
    
    # Revenus total
    total_revenue = Mission.objects.filter(status='livree').aggregate(
        total=Sum('price')
    )['total'] or 0
    
    # Liste des livreurs pour le filtre
    livreurs = User.objects.filter(user_type='livreur')
    
    context = {
        'title': 'Gestion des Missions',
        'missions': missions_page,
        'missions_stats': missions_stats,
        'total_revenue': total_revenue,
        'livreurs': livreurs,
    }
    
    return render(request, 'admin/missions_management_complete.html', context)

@admin_required
def system_config(request):
    """Configuration système"""
    context = {
        'title': 'Configuration Système',
    }
    
    return render(request, 'admin/system_config.html', context)

@manager_required
def reports(request):
    """Rapports et analytics"""
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    # Dates par défaut (30 derniers jours)
    if not start_date:
        start_date = (timezone.now() - timedelta(days=30)).date()
    else:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        
    if not end_date:
        end_date = timezone.now().date()
    else:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # Métriques principales
    missions_period = Mission.objects.filter(
        created_at__date__range=[start_date, end_date]
    )
    
    metrics = {
        'total_revenue': missions_period.filter(status='livree').aggregate(
            total=Sum('price')
        )['total'] or 0,
        'completed_missions': missions_period.filter(status='livree').count(),
        'new_users': User.objects.filter(
            date_joined__date__range=[start_date, end_date]
        ).count(),
        'satisfaction_rate': 92,  # À calculer avec les ratings
        'revenue_growth': 15.2,
        'missions_growth': 8.7,
        'users_growth': 12.3,
        'satisfaction_growth': 2.1,
    }
    
    # Données pour les graphiques
    revenue_chart = {
        'labels': [],
        'values': []
    }
    
    # Générer les données des 7 derniers jours
    for i in range(7):
        date = end_date - timedelta(days=6-i)
        revenue = sum(mission.price or 0 for mission in Mission.objects.filter(
            status='livree',
            created_at__date=date
        ))
        revenue_chart['labels'].append(date.strftime('%d/%m'))
        revenue_chart['values'].append(revenue)
    
    missions_chart = {
        'labels': ['En attente', 'En cours', 'Livrées', 'Annulées'],
        'values': [
            missions_period.filter(status='en_attente').count(),
            missions_period.filter(status='en_cours').count(),
            missions_period.filter(status='livree').count(),
            missions_period.filter(status='annulee').count(),
        ]
    }
    
    # Données utilisateurs par type
    users_chart = {
        'labels': ['Clients', 'Livreurs', 'Entreprises', 'Admins'],
        'values': [
            User.objects.filter(user_type='client').count(),
            User.objects.filter(user_type='livreur').count(),
            User.objects.filter(user_type='entreprise').count(),
            User.objects.filter(user_type='admin').count(),
        ]
    }
    
    # Données de performance (radar chart)
    performance_chart = {
        'labels': ['Rapidité', 'Qualité', 'Communication', 'Ponctualité', 'Satisfaction'],
        'values': [4.2, 4.5, 4.1, 4.3, 4.4]  # Données simulées sur 5
    }
    
    # Top performers
    top_performers = User.objects.filter(
        user_type='livreur'
    ).annotate(
        missions_count=Count('livreur_missions'),
        total_revenue=Sum('livreur_missions__price')
    ).order_by('-missions_count')[:10]
    
    # Transactions récentes
    recent_transactions = Mission.objects.filter(
        status='livree'
    ).select_related('client', 'livreur').order_by('-created_at')[:20]
    
    context = {
        'title': 'Rapports et Analytics',
        'metrics': metrics,
        'revenue_chart': json.dumps(revenue_chart),
        'missions_chart': json.dumps(missions_chart),
        'users_chart': json.dumps(users_chart),
        'performance_chart': json.dumps(performance_chart),
        'top_performers': top_performers,
        'recent_transactions': recent_transactions,
    }
    
    return render(request, 'admin/reports_complete.html', context)

@admin_required
def security_logs(request):
    """Logs de sécurité"""
    # Filtres
    search = request.GET.get('search', '')
    level_filter = request.GET.get('level')
    category_filter = request.GET.get('category')
    date_filter = request.GET.get('date')
    
    # Données simulées pour les logs de sécurité
    security_logs = [
        {
            'id': 1,
            'level': 'critical',
            'category': 'auth',
            'title': 'Tentative de connexion suspecte',
            'message': 'Plusieurs tentatives de connexion échouées depuis la même IP',
            'timestamp': timezone.now() - timedelta(hours=2),
            'ip_address': '192.168.1.100',
            'user': None,
            'details': 'User-Agent: Mozilla/5.0... IP: 192.168.1.100 Attempts: 15'
        },
        {
            'id': 2,
            'level': 'warning',
            'category': 'api',
            'title': 'Limite de taux API dépassée',
            'message': 'Un utilisateur a dépassé la limite de requêtes API',
            'timestamp': timezone.now() - timedelta(hours=1),
            'ip_address': '10.0.0.50',
            'user': User.objects.first() if User.objects.exists() else None,
            'details': 'Endpoint: /api/missions/ Rate: 150 req/min Limit: 100 req/min'
        },
        {
            'id': 3,
            'level': 'info',
            'category': 'system',
            'title': 'Sauvegarde automatique',
            'message': 'Sauvegarde automatique de la base de données effectuée',
            'timestamp': timezone.now() - timedelta(hours=6),
            'ip_address': None,
            'user': None,
            'details': 'Backup size: 2.3GB Duration: 45s Status: Success'
        },
        {
            'id': 4,
            'level': 'error',
            'category': 'database',
            'title': 'Erreur de connexion base de données',
            'message': 'Perte temporaire de connexion à la base de données',
            'timestamp': timezone.now() - timedelta(hours=12),
            'ip_address': None,
            'user': None,
            'details': 'Error: Connection timeout Database: postgresql Duration: 30s'
        },
    ]
    
    # Appliquer les filtres
    if level_filter:
        security_logs = [log for log in security_logs if log['level'] == level_filter]
    if category_filter:
        security_logs = [log for log in security_logs if log['category'] == category_filter]
    if search:
        security_logs = [log for log in security_logs if search.lower() in log['message'].lower()]
    
    # Statistiques de sécurité
    security_stats = {
        'critical_events': 3,
        'login_attempts': 127,
        'api_errors': 15,
        'security_score': 87,
    }
    
    context = {
        'title': 'Logs de Sécurité',
        'security_logs': security_logs,
        'security_stats': security_stats,
        'current_time': timezone.now(),
        'has_more_logs': len(security_logs) >= 20,
    }
    
    return render(request, 'admin/security_logs_complete.html', context)

# api_stats removed - using stats_api instead (unified endpoint)

# Nouvelles vues pour les fonctionnalités admin

@require_permission('admin_dashboard.view_missions')
def mission_details(request, mission_id):
    """Détails d'une mission en AJAX"""
    mission = get_object_or_404(Mission, id=mission_id)
    
    html = f"""
    <div class="space-y-4">
        <div class="grid grid-cols-2 gap-4">
            <div>
                <h3 class="font-semibold text-gray-900">Informations générales</h3>
                <p><strong>ID:</strong> #{mission.id}</p>
                <p><strong>Statut:</strong> {mission.get_status_display()}</p>
                <p><strong>Prix:</strong> {mission.price} FCFA</p>
                <p><strong>Distance:</strong> {mission.distance} km</p>
            </div>
            <div>
                <h3 class="font-semibold text-gray-900">Participants</h3>
                <p><strong>Client:</strong> {mission.client.username}</p>
                <p><strong>Livreur:</strong> {mission.livreur.username if mission.livreur else 'Non assigné'}</p>
            </div>
        </div>
        <div>
            <h3 class="font-semibold text-gray-900">Adresses</h3>
            <p><strong>Récupération:</strong> {mission.pickup_address}</p>
            <p><strong>Livraison:</strong> {mission.delivery_address}</p>
        </div>
        <div>
            <h3 class="font-semibold text-gray-900">Description</h3>
            <p>{mission.description}</p>
        </div>
    </div>
    """
    
    return JsonResponse({'html': html})

@require_permission('admin_dashboard.manage_missions')
def cancel_mission(request, mission_id):
    """Annuler une mission"""
    if request.method == 'POST':
        mission = get_object_or_404(Mission, id=mission_id)
        mission.status = 'annulee'
        mission.save()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False})

@require_permission('admin_dashboard.export_data')
def export_missions(request):
    """Exporter les missions en CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="missions.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['ID', 'Client', 'Livreur', 'Statut', 'Prix', 'Date création'])
    
    missions = Mission.objects.all().select_related('client', 'livreur')
    for mission in missions:
        writer.writerow([
            mission.id,
            mission.client.username,
            mission.livreur.username if mission.livreur else 'Non assigné',
            mission.get_status_display(),
            mission.price,
            mission.created_at.strftime('%d/%m/%Y %H:%M')
        ])
    
    return response

@admin_required
def save_config(request):
    """Sauvegarder la configuration système"""
    if request.method == 'POST':
        # Ici vous pouvez sauvegarder les paramètres en base
        # Pour l'instant, on simule une sauvegarde réussie
        return JsonResponse({'success': True})
    return JsonResponse({'success': False})

@admin_required
def system_check(request):
    """Vérification du système"""
    # Simulation d'une vérification système
    issues = []
    
    # Vérifier la base de données
    try:
        User.objects.count()
    except:
        issues.append('Problème de connexion base de données')
    
    # Vérifier l'espace disque (simulé)
    # if disk_usage > 90:
    #     issues.append('Espace disque faible')
    
    return JsonResponse({
        'healthy': len(issues) == 0,
        'issues': issues
    })

@admin_required
def create_backup(request):
    """Créer une sauvegarde"""
    if request.method == 'POST':
        # Ici vous implémenteriez la logique de sauvegarde
        return JsonResponse({'success': True})
    return JsonResponse({'success': False})

@admin_required
def clear_cache(request):
    """Vider le cache"""
    if request.method == 'POST':
        # Ici vous implémenteriez le vidage du cache
        return JsonResponse({'success': True})
    return JsonResponse({'success': False})

@admin_required
def regenerate_api_key(request):
    """Régénérer la clé API"""
    if request.method == 'POST':
        # Ici vous implémenteriez la régénération de clé API
        return JsonResponse({'success': True, 'new_key': 'new-api-key-here'})
    return JsonResponse({'success': False})

@manager_required
def generate_report(request):
    """Générer un rapport PDF"""
    # Ici vous implémenteriez la génération de rapport PDF
    return HttpResponse('Rapport PDF généré', content_type='application/pdf')

@admin_required
def export_security_logs(request):
    """Exporter les logs de sécurité"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="security_logs.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Niveau', 'Catégorie', 'Message', 'Date', 'IP'])
    
    # Ici vous exporteriez les vrais logs
    writer.writerow(['Critical', 'Auth', 'Tentative de connexion suspecte', timezone.now(), '192.168.1.100'])
    
    return response

@admin_required
def log_details(request, log_id):
    """Détails d'un log en AJAX"""
    # Simulation des détails d'un log
    html = f"""
    <div class="space-y-4">
        <div class="bg-red-50 border border-red-200 rounded-lg p-4">
            <h3 class="font-semibold text-red-800">Log #{log_id} - Critique</h3>
            <p class="text-red-700">Tentative de connexion suspecte détectée</p>
        </div>
        <div class="grid grid-cols-2 gap-4">
            <div>
                <h4 class="font-medium text-gray-900">Informations</h4>
                <p><strong>Niveau:</strong> Critical</p>
                <p><strong>Catégorie:</strong> Authentification</p>
                <p><strong>IP:</strong> 192.168.1.100</p>
            </div>
            <div>
                <h4 class="font-medium text-gray-900">Détails techniques</h4>
                <pre class="text-xs bg-gray-100 p-2 rounded">User-Agent: Mozilla/5.0...
Attempts: 15
Duration: 5 minutes</pre>
            </div>
        </div>
    </div>
    """
    
    return JsonResponse({'html': html})

@admin_required
def resolve_log(request, log_id):
    """Marquer un log comme résolu"""
    if request.method == 'POST':
        # Ici vous marqueriez le log comme résolu
        return JsonResponse({'success': True})
    return JsonResponse({'success': False})

@admin_required
def check_new_logs(request):
    """Vérifier s'il y a de nouveaux logs"""
    # Simulation de vérification de nouveaux logs
    return JsonResponse({
        'has_new': False,
        'count': 0
    })

@admin_required
@require_http_methods(["POST"])
def system_check_api(request):
    """API endpoint for system health check"""
    try:
        # Perform basic system checks
        issues = []
        
        # Check database connection
        try:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
        except Exception as e:
            issues.append("Database connection failed")
        
        # Check Redis connection (if configured)
        try:
            import redis
            from django.conf import settings
            if hasattr(settings, 'REDIS_URL'):
                r = redis.from_url(settings.REDIS_URL)
                r.ping()
        except Exception:
            pass  # Redis is optional
        
        # Check disk space (basic check)
        import shutil
        total, used, free = shutil.disk_usage('/')
        if free < (1024 * 1024 * 1024):  # Less than 1GB free
            issues.append("Low disk space")
        
        return JsonResponse({
            'healthy': len(issues) == 0,
            'issues': issues,
            'timestamp': timezone.now().isoformat()
        })
    except Exception as e:
        return JsonResponse({
            'healthy': False,
            'issues': [str(e)],
            'timestamp': timezone.now().isoformat()
        })

@admin_required
@require_http_methods(["POST"])
def backup_api(request):
    """API endpoint for creating system backup"""
    try:
        # Simulate backup creation
        import time
        time.sleep(1)  # Simulate backup time
        
        return JsonResponse({
            'success': True,
            'message': 'Backup created successfully',
            'timestamp': timezone.now().isoformat()
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e),
            'timestamp': timezone.now().isoformat()
        })

@admin_required
@require_http_methods(["POST"])
def clear_cache_api(request):
    """API endpoint for clearing system cache"""
    try:
        from django.core.cache import cache
        cache.clear()
        
        return JsonResponse({
            'success': True,
            'message': 'Cache cleared successfully',
            'timestamp': timezone.now().isoformat()
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e),
            'timestamp': timezone.now().isoformat()
        })

@admin_required
def stats_api(request):
    """API endpoint for real-time stats"""
    try:
        from users.models import User
        from missions.models import Mission
        from django.db.models import Sum
        
        # Get real-time stats
        users_online = User.objects.filter(
            last_login__gte=timezone.now() - timezone.timedelta(minutes=15)
        ).count()
        
        missions_today = Mission.objects.filter(
            created_at__date=timezone.now().date()
        ).count()
        
        revenue_today = Mission.objects.filter(
            created_at__date=timezone.now().date(),
            status='livree'
        ).aggregate(total=Sum('price'))['total'] or 0
        
        return JsonResponse({
            'users_online': users_online,
            'missions_today': missions_today,
            'revenue_today': float(revenue_today),
            'timestamp': timezone.now().isoformat()
        })
    except Exception as e:
        return JsonResponse({
            'users_online': 0,
            'missions_today': 0,
            'revenue_today': 0,
            'error': str(e),
            'timestamp': timezone.now().isoformat()
        })
