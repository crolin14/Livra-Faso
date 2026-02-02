from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Sum, Avg
from django.utils import timezone
from datetime import datetime, timedelta
import json

from missions.models import Mission
from users.models import User, LivreurProfile
# from rbac.decorators import require_any_role, api_require_permission


@login_required
@require_http_methods(["GET"])
def livreur_available_missions(request):
    """API endpoint for available missions for livreurs"""
    try:
        # Get available missions (not assigned or in candidacy phase)
        missions = Mission.objects.filter(
            status__in=['pending', 'confirmed'],
            livreur__isnull=True
        ).select_related('client').order_by('-created_at')[:20]
        
        missions_data = []
        for mission in missions:
            missions_data.append({
                'id': mission.id,
                'title': f"Livraison vers {mission.destination_address[:50]}..." if mission.destination_address else "Mission sans destination",
                'pickup_address': mission.pickup_address or "Adresse non définie",
                'destination_address': mission.destination_address or "Destination non définie",
                'price': float(mission.price) if mission.price else 0,
                'distance': f"{mission.distance_km:.1f} km" if hasattr(mission, 'distance_km') and mission.distance_km else "N/A",
                'created_at': mission.created_at.strftime('%H:%M'),
                'priority': getattr(mission, 'priority', 'normal'),
                'client_name': mission.client.get_full_name() if mission.client else "Client",
                'description': getattr(mission, 'description', '') or "Aucune description",
            })
        
        return JsonResponse({
            'success': True,
            'missions': missions_data,
            'count': len(missions_data)
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["GET"])
def livreur_profile(request):
    """API endpoint for livreur profile data"""
    try:
        if request.user.user_type != 'livreur':
            return JsonResponse({'error': 'Access denied'}, status=403)
        
        profile, created = LivreurProfile.objects.get_or_create(user=request.user)
        
        return JsonResponse({
            'success': True,
            'profile': {
                'name': request.user.get_full_name(),
                'phone': request.user.phone,
                'email': request.user.email,
                'vehicle_type': profile.vehicle_type,
                'vehicle_registration': profile.vehicle_registration,
                'is_available': profile.is_available,
                'rating': float(profile.rating) if profile.rating else 0,
                'total_deliveries': profile.total_deliveries,
            }
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["GET"])
def livreur_stats(request):
    """API endpoint for livreur statistics"""
    try:
        if request.user.user_type != 'livreur':
            return JsonResponse({'error': 'Access denied'}, status=403)
        
        # Get missions statistics
        total_missions = Mission.objects.filter(livreur=request.user).count()
        completed_missions = Mission.objects.filter(
            livreur=request.user, 
            status='delivered'
        ).count()
        pending_missions = Mission.objects.filter(
            livreur=request.user, 
            status__in=['accepted', 'in_progress']
        ).count()
        
        # Calculate real earnings from completed missions
        total_earnings = Mission.objects.filter(
            livreur=request.user,
            status='delivered'
        ).aggregate(total=Sum('price'))['total'] or 0
        
        # Get livreur profile for additional stats
        try:
            profile = LivreurProfile.objects.get(user=request.user)
            rating = float(profile.rating) if profile.rating else 0
            total_deliveries = profile.total_deliveries or 0
        except LivreurProfile.DoesNotExist:
            rating = 0
            total_deliveries = 0
        
        return JsonResponse({
            'success': True,
            'stats': {
                'total_missions': total_missions,
                'completed_missions': completed_missions,
                'pending_missions': pending_missions,
                'total_earnings': float(total_earnings),
                'success_rate': round((completed_missions / total_missions * 100) if total_missions > 0 else 0, 1),
                'rating': rating,
                'total_deliveries': total_deliveries,
            }
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["GET"])
def livreur_earnings(request):
    """API endpoint for livreur earnings data"""
    try:
        if request.user.user_type != 'livreur':
            return JsonResponse({'error': 'Access denied'}, status=403)
        
        # Get earnings for the last 7 days based on delivery date
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=6)
        
        daily_earnings = []
        for i in range(7):
            date = start_date + timedelta(days=i)
            # Use delivered_at field if available, otherwise created_at
            earnings = Mission.objects.filter(
                livreur=request.user,
                status='delivered'
            ).filter(
                **{
                    f"{'delivered_at' if hasattr(Mission, 'delivered_at') else 'updated_at'}__date": date
                }
            ).aggregate(total=Sum('price'))['total'] or 0
            
            daily_earnings.append({
                'date': date.strftime('%Y-%m-%d'),
                'day': date.strftime('%a'),
                'earnings': float(earnings),
                'missions_count': Mission.objects.filter(
                    livreur=request.user,
                    status='delivered'
                ).filter(
                    **{
                        f"{'delivered_at' if hasattr(Mission, 'delivered_at') else 'updated_at'}__date": date
                    }
                ).count()
            })
        
        # Calculate weekly total
        weekly_total = sum(day['earnings'] for day in daily_earnings)
        
        return JsonResponse({
            'success': True,
            'daily_earnings': daily_earnings,
            'weekly_total': weekly_total,
            'period': f"{start_date.strftime('%d/%m')} - {end_date.strftime('%d/%m')}"
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def accept_mission(request, mission_id):
    """API endpoint to accept a mission"""
    try:
        if request.user.user_type != 'livreur':
            return JsonResponse({'error': 'Access denied'}, status=403)
        
        mission = Mission.objects.get(id=mission_id)
        
        if mission.status not in ['pending', 'confirmed']:
            return JsonResponse({
                'success': False,
                'error': 'Mission not available'
            }, status=400)
        
        mission.livreur = request.user
        mission.status = 'accepted'
        mission.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Mission acceptée avec succès'
        })
    except Mission.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Mission not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def complete_mission(request, mission_id):
    """API endpoint to complete a mission"""
    try:
        if request.user.user_type != 'livreur':
            return JsonResponse({'error': 'Access denied'}, status=403)
        
        mission = Mission.objects.get(id=mission_id, livreur=request.user)
        
        if mission.status != 'in_progress':
            return JsonResponse({
                'success': False,
                'error': 'Mission cannot be completed'
            }, status=400)
        
        mission.status = 'delivered'
        mission.delivered_at = timezone.now()
        mission.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Mission terminée avec succès'
        })
    except Mission.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Mission not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@csrf_exempt
@require_http_methods(["GET", "POST"])
def client_missions(request):
    """API endpoint for client missions"""
    try:
        if request.method == 'POST':
            # Créer une nouvelle mission
            data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
            
            # Validation des champs requis
            pickup_address = data.get('pickup_address', '').strip()
            delivery_address = data.get('delivery_address', '').strip()
            description = data.get('description', '').strip()
            
            if not pickup_address or not delivery_address:
                return JsonResponse({
                    'success': False,
                    'error': 'Adresses de récupération et de livraison requises'
                }, status=400)
            
            # Logique robuste pour le prix : toujours garantir qu'il y a un prix valide
            prix = data.get('price')
            prix_estime = data.get('estimated_price', 2097)  # Prix par défaut si non fourni
            
            if prix and float(prix) > 0:
                prix_final = float(prix)
            elif prix_estime and float(prix_estime) > 0:
                prix_final = float(prix_estime)
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'Le prix de la mission est obligatoire'
                }, status=400)
            
            # Créer la mission
            mission = Mission.objects.create(
                client=request.user,
                title=f"Livraison de {pickup_address} à {delivery_address}",
                description=description,
                pickup_address=pickup_address,
                delivery_address=delivery_address,
                estimated_price=prix_estime,
                price=prix_final,
                status='pending'
            )
            
            return JsonResponse({
                'success': True,
                'mission_id': mission.id,
                'message': 'Mission créée avec succès!'
            })
        
        else:
            # GET - Récupérer les missions
            missions = Mission.objects.filter(
                client=request.user
            ).select_related('livreur').order_by('-created_at')[:20]
            
            missions_data = []
            for mission in missions:
                missions_data.append({
                    'id': mission.id,
                    'pickup_address': mission.pickup_address,
                    'delivery_address': mission.delivery_address,
                    'status': mission.status,
                    'estimated_price': float(mission.estimated_price) if mission.estimated_price else 0,
                    'livreur_name': mission.livreur.get_full_name() if mission.livreur else None,
                    'created_at': mission.created_at.strftime('%d/%m/%Y %H:%M'),
                })
            
            return JsonResponse({
                'success': True,
                'missions': missions_data
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def create_mission_api(request):
    """API endpoint to create a new mission"""
    try:
        if request.user.user_type != 'client':
            return JsonResponse({'error': 'Access denied'}, status=403)
        
        data = json.loads(request.body)
        
        # Logique robuste pour le prix : toujours garantir qu'il y a un prix valide
        prix = data.get('price')
        prix_estime = data.get('estimated_price')
        
        if prix and float(prix) > 0:
            prix_final = float(prix)
        elif prix_estime and float(prix_estime) > 0:
            prix_final = float(prix_estime)
        else:
            return JsonResponse({
                'success': False,
                'error': 'Le prix de la mission est obligatoire'
            }, status=400)
        
        mission = Mission.objects.create(
            client=request.user,
            pickup_address=data.get('pickup_address'),
            delivery_address=data.get('destination_address') or data.get('delivery_address'),
            description=data.get('description', ''),
            estimated_price=prix_estime if prix_estime else prix_final,
            price=prix_final,
            status='pending'
        )
        
        return JsonResponse({
            'success': True,
            'mission_id': mission.id,
            'message': 'Mission créée avec succès'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["GET"])
def mission_status(request, mission_id):
    """API endpoint to get mission status"""
    try:
        mission = Mission.objects.get(id=mission_id)
        
        # Check if user has access to this mission
        if mission.client != request.user and mission.livreur != request.user:
            return JsonResponse({'error': 'Access denied'}, status=403)
        
        return JsonResponse({
            'success': True,
            'status': mission.status,
            'livreur': mission.livreur.get_full_name() if mission.livreur else None,
            'updated_at': mission.updated_at.strftime('%d/%m/%Y %H:%M')
        })
    except Mission.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Mission not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["GET"])
def entreprise_missions(request):
    """API endpoint for entreprise missions"""
    try:
        if request.user.user_type != 'entreprise':
            return JsonResponse({'error': 'Access denied'}, status=403)
        
        missions = Mission.objects.filter(
            client__user_type='entreprise'
        ).select_related('client', 'livreur').order_by('-created_at')[:20]
        
        missions_data = []
        for mission in missions:
            missions_data.append({
                'id': mission.id,
                'client_name': mission.client.get_full_name(),
                'pickup_address': mission.pickup_address,
                'destination_address': mission.destination_address,
                'status': mission.status,
                'price': float(mission.price) if mission.price else 0,
                'livreur_name': mission.livreur.get_full_name() if mission.livreur else None,
                'created_at': mission.created_at.strftime('%d/%m/%Y %H:%M'),
            })
        
        return JsonResponse({
            'success': True,
            'missions': missions_data
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["GET"])
def entreprise_analytics(request):
    """API endpoint for entreprise analytics"""
    try:
        if request.user.user_type != 'entreprise':
            return JsonResponse({'error': 'Access denied'}, status=403)
        
        # Real analytics data for entreprise
        total_missions = Mission.objects.filter(client__user_type='entreprise').count()
        completed_missions = Mission.objects.filter(
            client__user_type='entreprise',
            status='delivered'
        ).count()
        
        # Revenue calculation
        revenue = Mission.objects.filter(
            client__user_type='entreprise',
            status='delivered'
        ).aggregate(total=Sum('price'))['total'] or 0
        
        # Average delivery time (mock for now - needs tracking implementation)
        avg_delivery_time = 28.5  # Will be calculated from real data later
        
        # Customer satisfaction (mock for now - needs rating system)
        customer_satisfaction = 4.7  # Will be calculated from ratings later
        
        # Monthly breakdown (last 6 months)
        monthly_data = []
        for i in range(6):
            month_start = timezone.now().replace(day=1) - timedelta(days=30*i)
            month_missions = Mission.objects.filter(
                client__user_type='entreprise',
                created_at__month=month_start.month,
                created_at__year=month_start.year
            ).count()
            monthly_data.append({
                'month': month_start.strftime('%b'),
                'missions': month_missions
            })
        
        return JsonResponse({
            'success': True,
            'analytics': {
                'total_missions': total_missions,
                'completed_missions': completed_missions,
                'revenue': float(revenue),
                'avg_delivery_time': avg_delivery_time,
                'customer_satisfaction': customer_satisfaction,
                'success_rate': round((completed_missions / total_missions * 100) if total_missions > 0 else 0, 1),
                'monthly_data': monthly_data[::-1]  # Reverse to show oldest first
            }
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["GET"])
def available_livreurs(request):
    """API endpoint for available livreurs"""
    try:
        if request.user.user_type != 'entreprise':
            return JsonResponse({'error': 'Access denied'}, status=403)
        
        livreurs = User.objects.filter(
            user_type='livreur',
            livreurprofile__is_available=True
        ).select_related('livreurprofile')[:20]
        
        livreurs_data = []
        for livreur in livreurs:
            profile = getattr(livreur, 'livreurprofile', None)
            livreurs_data.append({
                'id': livreur.id,
                'name': livreur.get_full_name(),
                'phone': livreur.phone,
                'vehicle_type': profile.vehicle_type if profile else 'N/A',
                'rating': float(profile.rating) if profile and profile.rating else 0,
                'total_deliveries': profile.total_deliveries if profile else 0,
            })
        
        return JsonResponse({
            'success': True,
            'livreurs': livreurs_data
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
# @require_any_role('admin', 'superuser')
@require_http_methods(["GET"])
def admin_stats(request):
    """API endpoint for admin statistics"""
    try:
        # Real user statistics
        total_users = User.objects.count()
        clients_count = User.objects.filter(user_type='client').count()
        livreurs_count = User.objects.filter(user_type='livreur').count()
        entreprises_count = User.objects.filter(user_type='entreprise').count()
        
        # Real mission statistics
        total_missions = Mission.objects.count()
        completed_missions = Mission.objects.filter(status='delivered').count()
        pending_missions = Mission.objects.filter(status='pending').count()
        in_progress_missions = Mission.objects.filter(status='in_progress').count()
        
        # Active livreurs (with profiles and available)
        try:
            active_livreurs = User.objects.filter(
                user_type='livreur',
                livreurprofile__is_available=True
            ).count()
        except:
            active_livreurs = livreurs_count  # Fallback if profile doesn't exist
        
        # Revenue calculation
        total_revenue = Mission.objects.filter(
            status='delivered'
        ).aggregate(total=Sum('price'))['total'] or 0
        
        # Recent activity (last 30 days)
        thirty_days_ago = timezone.now() - timedelta(days=30)
        recent_missions = Mission.objects.filter(
            created_at__gte=thirty_days_ago
        ).count()
        
        return JsonResponse({
            'success': True,
            'stats': {
                'total_users': total_users,
                'clients_count': clients_count,
                'livreurs_count': livreurs_count,
                'entreprises_count': entreprises_count,
                'total_missions': total_missions,
                'completed_missions': completed_missions,
                'pending_missions': pending_missions,
                'in_progress_missions': in_progress_missions,
                'active_livreurs': active_livreurs,
                'total_revenue': float(total_revenue),
                'recent_missions': recent_missions,
                'success_rate': round((completed_missions / total_missions * 100) if total_missions > 0 else 0, 1),
            }
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
# @require_any_role('admin', 'superuser')
@require_http_methods(["GET"])
def admin_users(request):
    """API endpoint for admin user management"""
    try:
        users = User.objects.all().order_by('-date_joined')[:50]
        
        users_data = []
        for user in users:
            users_data.append({
                'id': user.id,
                'name': user.get_full_name(),
                'email': user.email,
                'user_type': user.user_type,
                'is_active': user.is_active,
                'date_joined': user.date_joined.strftime('%d/%m/%Y'),
            })
        
        return JsonResponse({
            'success': True,
            'users': users_data
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
# @require_any_role('admin', 'superuser')
@require_http_methods(["GET"])
def admin_missions(request):
    """API endpoint for admin mission management"""
    try:
        missions = Mission.objects.all().select_related(
            'client', 'livreur'
        ).order_by('-created_at')[:100]
        
        missions_data = []
        for mission in missions:
            missions_data.append({
                'id': mission.id,
                'client_name': mission.client.get_full_name(),
                'livreur_name': mission.livreur.get_full_name() if mission.livreur else None,
                'pickup_address': mission.pickup_address,
                'destination_address': mission.destination_address,
                'status': mission.status,
                'price': float(mission.price) if mission.price else 0,
                'created_at': mission.created_at.strftime('%d/%m/%Y %H:%M'),
            })
        
        return JsonResponse({
            'success': True,
            'missions': missions_data
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
# @require_any_role('admin', 'superuser')
@require_http_methods(["GET"])
def admin_reports(request):
    """API endpoint for admin reports"""
    try:
        # Mock report data
        return JsonResponse({
            'success': True,
            'reports': {
                'daily_missions': [
                    {'date': '2024-01-01', 'count': 25},
                    {'date': '2024-01-02', 'count': 32},
                    {'date': '2024-01-03', 'count': 28},
                ],
                'revenue_by_month': [
                    {'month': 'Jan', 'revenue': 15600},
                    {'month': 'Feb', 'revenue': 18200},
                    {'month': 'Mar', 'revenue': 21400},
                ]
            }
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["GET"])
def get_notifications(request):
    """API endpoint to get user notifications"""
    try:
        # Real notifications based on user missions and activities
        notifications = []
        
        if request.user.user_type == 'livreur':
            # Get available missions for livreur
            available_missions = Mission.objects.filter(
                status__in=['pending', 'confirmed'],
                livreur__isnull=True
            ).count()
            
            if available_missions > 0:
                notifications.append({
                    'id': f'missions_{available_missions}',
                    'title': f'{available_missions} nouvelle(s) mission(s)',
                    'message': f'{available_missions} mission(s) disponible(s) dans votre zone',
                    'type': 'info',
                    'created_at': timezone.now().strftime('%H:%M'),
                    'is_read': False
                })
            
            # Check for completed missions today
            today_completed = Mission.objects.filter(
                livreur=request.user,
                status='delivered',
                updated_at__date=timezone.now().date()
            ).count()
            
            if today_completed > 0:
                notifications.append({
                    'id': f'completed_{today_completed}',
                    'title': 'Missions terminées',
                    'message': f'Vous avez terminé {today_completed} mission(s) aujourd\'hui',
                    'type': 'success',
                    'created_at': timezone.now().strftime('%H:%M'),
                    'is_read': False
                })
        
        elif request.user.user_type == 'client':
            # Get user's pending missions
            pending_missions = Mission.objects.filter(
                client=request.user,
                status__in=['pending', 'confirmed']
            ).count()
            
            if pending_missions > 0:
                notifications.append({
                    'id': f'pending_{pending_missions}',
                    'title': 'Missions en attente',
                    'message': f'Vous avez {pending_missions} mission(s) en attente d\'attribution',
                    'type': 'warning',
                    'created_at': timezone.now().strftime('%H:%M'),
                    'is_read': False
                })
        
        # Fallback notification if no specific ones
        if not notifications:
            notifications.append({
                'id': 'welcome',
                'title': 'Bienvenue sur LivraFaso',
                'message': 'Votre tableau de bord est prêt à l\'utilisation',
                'type': 'info',
                'created_at': timezone.now().strftime('%H:%M'),
                'is_read': False
            })
        
        return JsonResponse({
            'success': True,
            'notifications': notifications
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def mark_notifications_read(request):
    """API endpoint to mark notifications as read"""
    try:
        data = json.loads(request.body)
        notification_ids = data.get('notification_ids', [])
        
        # Mock implementation - in real app, update notification status
        return JsonResponse({
            'success': True,
            'message': f'{len(notification_ids)} notifications marquées comme lues'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
