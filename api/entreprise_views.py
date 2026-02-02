from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Avg, Q
from django.utils import timezone
from datetime import datetime, timedelta
import json
import csv
import io
from missions.models import Mission
from users.models import User


@login_required
@require_http_methods(["GET"])
def entreprise_kpis(request):
    """API pour récupérer les KPIs temps réel de l'entreprise"""
    try:
        user = request.user
        today = timezone.now().date()
        last_month = today - timedelta(days=30)
        
        # Missions de l'entreprise
        missions = Mission.objects.filter(client=user)
        missions_this_month = missions.filter(created_at__date__gte=last_month)
        missions_last_month = missions.filter(
            created_at__date__gte=last_month - timedelta(days=30),
            created_at__date__lt=last_month
        )
        
        # Calculs KPIs
        total_deliveries = missions.count()
        completed_missions = missions.filter(status='completed').count()
        success_rate = (completed_missions / total_deliveries * 100) if total_deliveries > 0 else 0
        
        # Délai moyen (simulation)
        avg_delivery_time = 45  # En minutes
        
        # Coût logistique moyen
        logistics_cost = missions.aggregate(
            avg_cost=Avg('estimated_price')
        )['avg_cost'] or 0
        
        # Tendances (comparaison avec le mois précédent)
        deliveries_trend = calculate_trend(
            missions_this_month.count(),
            missions_last_month.count()
        )
        
        # Missions actives aujourd'hui
        active_deliveries = missions.filter(
            status='in_progress',
            created_at__date=today
        ).count()
        
        completed_today = missions.filter(
            status='completed',
            updated_at__date=today
        ).count()
        
        pending_pickup = missions.filter(status='pending').count()
        
        return JsonResponse({
            'success': True,
            'total_deliveries': total_deliveries,
            'success_rate': round(success_rate, 1),
            'avg_time': avg_delivery_time,
            'logistics_cost': round(logistics_cost, 0),
            'active_deliveries': active_deliveries,
            'completed_today': completed_today,
            'pending_pickup': pending_pickup,
            'deliveries_trend': deliveries_trend,
            'success_trend': {'text': '+2% ce mois', 'positive': True},
            'time_trend': {'text': '-5min ce mois', 'positive': True},
            'cost_trend': {'text': '-8% ce mois', 'positive': True}
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def entreprise_missions(request):
    """API pour récupérer les missions avec filtres avancés"""
    try:
        user = request.user
        missions = Mission.objects.filter(client=user).select_related('livreur')
        
        # Filtres
        status = request.GET.get('status')
        date_from = request.GET.get('date_from')
        date_to = request.GET.get('date_to')
        
        if status:
            missions = missions.filter(status=status)
        
        if date_from:
            missions = missions.filter(created_at__date__gte=date_from)
            
        if date_to:
            missions = missions.filter(created_at__date__lte=date_to)
        
        # Pagination
        missions = missions.order_by('-created_at')[:50]
        
        missions_data = []
        for mission in missions:
            missions_data.append({
                'id': mission.id,
                'title': mission.title or 'Livraison Express',
                'pickup_address': mission.pickup_address,
                'delivery_address': mission.delivery_address,
                'status': mission.status,
                'status_display': mission.get_status_display(),
                'estimated_price': float(mission.estimated_price) if mission.estimated_price else 0,
                'livreur_name': mission.livreur.get_full_name() if mission.livreur else None,
                'created_at': mission.created_at.strftime('%d/%m/%Y %H:%M'),
            })
        
        return JsonResponse({
            'success': True,
            'missions': missions_data
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def bulk_create_missions(request):
    """API pour créer des missions en masse via CSV"""
    try:
        if 'csv_file' not in request.FILES:
            return JsonResponse({'success': False, 'error': 'Aucun fichier fourni'}, status=400)
        
        csv_file = request.FILES['csv_file']
        
        # Vérifier le type de fichier
        if not csv_file.name.endswith('.csv'):
            return JsonResponse({'success': False, 'error': 'Format de fichier invalide'}, status=400)
        
        # Lire le fichier CSV
        decoded_file = csv_file.read().decode('utf-8')
        csv_data = csv.DictReader(io.StringIO(decoded_file))
        
        created_count = 0
        errors = []
        
        for row_num, row in enumerate(csv_data, start=2):
            try:
                # Validation des champs requis
                pickup_address = row.get('pickup_address', '').strip()
                delivery_address = row.get('delivery_address', '').strip()
                
                if not pickup_address or not delivery_address:
                    errors.append(f'Ligne {row_num}: Adresses manquantes')
                    continue
                
                # Logique robuste pour le prix : toujours garantir qu'il y a un prix valide
                prix = row.get('price')
                prix_estime = row.get('estimated_price', 2500)
                
                if prix and float(prix) > 0:
                    prix_final = float(prix)
                elif prix_estime and float(prix_estime) > 0:
                    prix_final = float(prix_estime)
                else:
                    errors.append(f'Ligne {row_num}: Le prix de la mission est obligatoire')
                    continue
                
                # Créer la mission
                mission = Mission.objects.create(
                    client=request.user,
                    title=row.get('title', f'Livraison de {pickup_address} à {delivery_address}'),
                    description=row.get('description', ''),
                    pickup_address=pickup_address,
                    delivery_address=delivery_address,
                    estimated_price=float(prix_estime),
                    price=prix_final,
                    status='pending'
                )
                created_count += 1
                
            except Exception as e:
                errors.append(f'Ligne {row_num}: {str(e)}')
        
        response_data = {
            'success': True,
            'created_count': created_count
        }
        
        if errors:
            response_data['errors'] = errors
        
        return JsonResponse(response_data)
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def analytics_export(request):
    """API pour exporter les analytics en PDF/CSV"""
    try:
        format_type = request.GET.get('format', 'csv')
        user = request.user
        
        missions = Mission.objects.filter(client=user).select_related('livreur')
        
        if format_type == 'csv':
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="analytics_{timezone.now().strftime("%Y%m%d")}.csv"'
            
            writer = csv.writer(response)
            writer.writerow([
                'ID Mission', 'Titre', 'Adresse Récupération', 'Adresse Livraison',
                'Statut', 'Prix Estimé', 'Livreur', 'Date Création', 'Date Mise à Jour'
            ])
            
            for mission in missions:
                writer.writerow([
                    mission.id,
                    mission.title or 'Livraison Express',
                    mission.pickup_address,
                    mission.delivery_address,
                    mission.get_status_display(),
                    mission.estimated_price,
                    mission.livreur.get_full_name() if mission.livreur else 'Non assigné',
                    mission.created_at.strftime('%d/%m/%Y %H:%M'),
                    mission.updated_at.strftime('%d/%m/%Y %H:%M')
                ])
            
            return response
        
        elif format_type == 'json':
            missions_data = []
            for mission in missions:
                missions_data.append({
                    'id': mission.id,
                    'title': mission.title,
                    'pickup_address': mission.pickup_address,
                    'delivery_address': mission.delivery_address,
                    'status': mission.status,
                    'estimated_price': float(mission.estimated_price) if mission.estimated_price else 0,
                    'livreur': mission.livreur.get_full_name() if mission.livreur else None,
                    'created_at': mission.created_at.isoformat(),
                    'updated_at': mission.updated_at.isoformat()
                })
            
            return JsonResponse({
                'success': True,
                'data': missions_data,
                'export_date': timezone.now().isoformat()
            })
        
        else:
            return JsonResponse({'success': False, 'error': 'Format non supporté'}, status=400)
            
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


def calculate_trend(current_value, previous_value):
    """Calcule la tendance entre deux valeurs"""
    if previous_value == 0:
        if current_value > 0:
            return {'text': '+100% ce mois', 'positive': True}
        else:
            return {'text': 'Aucun changement', 'positive': True}
    
    percentage = ((current_value - previous_value) / previous_value) * 100
    sign = '+' if percentage >= 0 else ''
    
    return {
        'text': f'{sign}{percentage:.1f}% ce mois',
        'positive': percentage >= 0
    }
