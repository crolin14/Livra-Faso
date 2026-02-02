from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count
from django.utils import timezone
from rbac.permissions import admin_required, manager_required
from .models import PromotionCampaign, PromoCode, PromotionUsage, PromotionAnalytics
from .services import PromotionService, PromotionRecommendationService
from audit.services import AuditService
import json
from decimal import Decimal


# API Endpoints
@require_http_methods(["POST"])
@login_required
@csrf_exempt
def validate_promo_code(request):
    """Valide un code promo via API"""
    try:
        data = json.loads(request.body)
        code = data.get('code', '').strip()
        order_amount = Decimal(str(data.get('order_amount', 0)))
        
        if not code:
            return JsonResponse({
                'valid': False,
                'error': 'Code promo requis'
            })
        
        result = PromotionService.validate_promo_code(code, request.user, order_amount)
        
        # Convertir les objets pour JSON
        if result['valid']:
            result['campaign_name'] = result['campaign'].name
            result['campaign_description'] = result['campaign'].description
            result['discount_amount'] = float(result['discount_amount'])
            result['final_amount'] = float(result['final_amount'])
            # Supprimer les objets non sérialisables
            del result['code']
            del result['campaign']
        
        return JsonResponse(result)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'valid': False,
            'error': 'Format JSON invalide'
        })
    except Exception as e:
        return JsonResponse({
            'valid': False,
            'error': 'Erreur lors de la validation'
        })


@require_http_methods(["POST"])
@login_required
@csrf_exempt
def apply_promo_code(request):
    """Applique un code promo à une mission"""
    try:
        data = json.loads(request.body)
        code = data.get('code', '').strip()
        mission_id = data.get('mission_id')
        original_amount = Decimal(str(data.get('original_amount', 0)))
        
        # Valider d'abord le code
        validation = PromotionService.validate_promo_code(code, request.user, original_amount)
        if not validation['valid']:
            return JsonResponse(validation)
        
        # Récupérer la mission
        from missions.models import Mission
        try:
            mission = Mission.objects.get(id=mission_id, client=request.user)
        except Mission.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Mission introuvable'
            })
        
        # Appliquer la promotion
        promo_code = PromoCode.objects.get(code=code.upper())
        usage = PromotionService.apply_promotion(
            promo_code, request.user, mission, original_amount, request
        )
        
        if usage:
            return JsonResponse({
                'success': True,
                'usage_id': str(usage.id),
                'discount_amount': float(usage.discount_amount),
                'final_amount': float(usage.final_amount),
                'message': f'Code promo appliqué! Vous économisez {usage.discount_amount} FCFA'
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Erreur lors de l\'application du code'
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': 'Erreur lors de l\'application'
        })


@login_required
def get_available_promotions(request):
    """Récupère les promotions disponibles pour l'utilisateur"""
    try:
        order_amount = request.GET.get('order_amount')
        if order_amount:
            order_amount = Decimal(str(order_amount))
        
        # Récupérer les promotions disponibles
        promotions = PromotionService.get_available_promotions(request.user)
        
        # Récupérer les recommandations
        recommendations = PromotionRecommendationService.recommend_promotions_for_user(
            request.user, order_amount
        )
        
        promotions_data = []
        for campaign in promotions:
            discount = campaign.calculate_discount(order_amount) if order_amount else None
            promotions_data.append({
                'id': str(campaign.id),
                'name': campaign.name,
                'description': campaign.description,
                'type': campaign.get_campaign_type_display(),
                'discount_percentage': float(campaign.discount_percentage) if campaign.discount_percentage else None,
                'discount_amount': float(campaign.discount_amount) if campaign.discount_amount else None,
                'minimum_order': float(campaign.minimum_order_amount),
                'potential_discount': float(discount) if discount else None,
                'end_date': campaign.end_date.isoformat(),
            })
        
        return JsonResponse({
            'promotions': promotions_data,
            'recommendations': [
                {
                    'campaign': {
                        'id': str(rec['campaign'].id),
                        'name': rec['campaign'].name,
                        'description': rec['campaign'].description,
                    },
                    'score': rec['score'],
                    'potential_discount': float(rec['potential_discount']) if rec['potential_discount'] else None,
                }
                for rec in recommendations
            ]
        })
        
    except Exception as e:
        return JsonResponse({
            'error': 'Erreur lors de la récupération des promotions'
        })


@login_required
def get_user_savings(request):
    """Récupère les économies totales de l'utilisateur"""
    try:
        total_savings = PromotionService.calculate_user_savings(request.user)
        history = PromotionService.get_user_promotion_history(request.user, limit=10)
        
        history_data = []
        for usage in history:
            history_data.append({
                'campaign_name': usage.campaign.name,
                'promo_code': usage.promo_code.code if usage.promo_code else None,
                'discount_amount': float(usage.discount_amount),
                'used_at': usage.used_at.isoformat(),
                'mission_id': str(usage.mission.id) if usage.mission else None,
            })
        
        return JsonResponse({
            'total_savings': float(total_savings),
            'recent_usage': history_data
        })
        
    except Exception as e:
        return JsonResponse({
            'error': 'Erreur lors de la récupération des économies'
        })


# Admin Views
@admin_required
def admin_campaigns_list(request):
    """Liste des campagnes promotionnelles"""
    campaigns = PromotionCampaign.objects.all().order_by('-created_at')
    
    # Filtres
    status_filter = request.GET.get('status')
    if status_filter:
        campaigns = campaigns.filter(status=status_filter)
    
    search = request.GET.get('search')
    if search:
        campaigns = campaigns.filter(
            Q(name__icontains=search) | Q(description__icontains=search)
        )
    
    paginator = Paginator(campaigns, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'campaigns': page_obj,
        'status_choices': PromotionCampaign.STATUS_CHOICES,
        'current_status': status_filter,
        'search_query': search,
    }
    
    return render(request, 'promotions/admin/campaigns_list.html', context)


@admin_required
def admin_campaign_detail(request, campaign_id):
    """Détail d'une campagne"""
    campaign = get_object_or_404(PromotionCampaign, id=campaign_id)
    
    # Statistiques
    stats = {
        'total_codes': campaign.promo_codes.count(),
        'active_codes': campaign.promo_codes.filter(is_active=True).count(),
        'total_usages': campaign.usages.count(),
        'unique_users': campaign.usages.values('user').distinct().count(),
        'total_discount_given': campaign.usages.aggregate(
            total=Sum('discount_amount')
        )['total'] or Decimal('0'),
    }
    
    # Codes récents
    recent_codes = campaign.promo_codes.order_by('-generated_at')[:10]
    
    # Utilisations récentes
    recent_usages = campaign.usages.select_related('user', 'promo_code').order_by('-used_at')[:10]
    
    context = {
        'campaign': campaign,
        'stats': stats,
        'recent_codes': recent_codes,
        'recent_usages': recent_usages,
    }
    
    return render(request, 'promotions/admin/campaign_detail.html', context)


@admin_required
def admin_campaign_analytics(request, campaign_id):
    """Analytics d'une campagne"""
    campaign = get_object_or_404(PromotionCampaign, id=campaign_id)
    
    # Période d'analyse
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    if start_date:
        start_date = timezone.datetime.strptime(start_date, '%Y-%m-%d').date()
    if end_date:
        end_date = timezone.datetime.strptime(end_date, '%Y-%m-%d').date()
    
    analytics_data = PromotionService.get_promotion_analytics(
        campaign, start_date, end_date
    )
    
    context = {
        'campaign': campaign,
        'analytics': analytics_data,
    }
    
    return render(request, 'promotions/admin/campaign_analytics.html', context)


@admin_required
@require_http_methods(["POST"])
def admin_generate_codes(request, campaign_id):
    """Génère des codes promo en lot"""
    campaign = get_object_or_404(PromotionCampaign, id=campaign_id)
    
    try:
        count = int(request.POST.get('count', 10))
        prefix = request.POST.get('prefix', '').upper()
        length = int(request.POST.get('length', 8))
        
        if count > 1000:
            messages.error(request, 'Maximum 1000 codes par génération')
            return redirect('promotions:admin_campaign_detail', campaign_id=campaign_id)
        
        codes = PromotionService.generate_bulk_promo_codes(
            campaign, count, prefix, length, request.user
        )
        
        # Log de l'action
        AuditService.log_admin_action(
            admin_user=request.user,
            category='content_management',
            action='generate_promo_codes',
            description=f'Génération de {count} codes promo pour {campaign.name}',
            target_object_type='PromotionCampaign',
            target_object_id=str(campaign.id),
            request=request,
            reason=f'Génération en lot de {count} codes'
        )
        
        messages.success(request, f'{len(codes)} codes générés avec succès')
        
    except ValueError:
        messages.error(request, 'Paramètres invalides')
    except Exception as e:
        messages.error(request, f'Erreur lors de la génération: {str(e)}')
    
    return redirect('promotions:admin_campaign_detail', campaign_id=campaign_id)


@admin_required
def admin_codes_list(request):
    """Liste des codes promo"""
    codes = PromoCode.objects.select_related('campaign').order_by('-generated_at')
    
    # Filtres
    campaign_filter = request.GET.get('campaign')
    if campaign_filter:
        codes = codes.filter(campaign_id=campaign_filter)
    
    active_filter = request.GET.get('active')
    if active_filter == 'true':
        codes = codes.filter(is_active=True)
    elif active_filter == 'false':
        codes = codes.filter(is_active=False)
    
    search = request.GET.get('search')
    if search:
        codes = codes.filter(code__icontains=search.upper())
    
    paginator = Paginator(codes, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    campaigns = PromotionCampaign.objects.filter(status='active')
    
    context = {
        'codes': page_obj,
        'campaigns': campaigns,
        'current_campaign': campaign_filter,
        'current_active': active_filter,
        'search_query': search,
    }
    
    return render(request, 'promotions/admin/codes_list.html', context)


@admin_required
def admin_usage_list(request):
    """Liste des utilisations de promotions"""
    usages = PromotionUsage.objects.select_related(
        'user', 'campaign', 'promo_code', 'mission'
    ).order_by('-used_at')
    
    # Filtres
    campaign_filter = request.GET.get('campaign')
    if campaign_filter:
        usages = usages.filter(campaign_id=campaign_filter)
    
    user_filter = request.GET.get('user')
    if user_filter:
        usages = usages.filter(user__username__icontains=user_filter)
    
    paginator = Paginator(usages, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    campaigns = PromotionCampaign.objects.all()
    
    context = {
        'usages': page_obj,
        'campaigns': campaigns,
        'current_campaign': campaign_filter,
        'current_user': user_filter,
    }
    
    return render(request, 'promotions/admin/usage_list.html', context)


@admin_required
def admin_analytics_dashboard(request):
    """Dashboard analytics des promotions"""
    # Statistiques générales
    total_campaigns = PromotionCampaign.objects.count()
    active_campaigns = PromotionCampaign.objects.filter(status='active').count()
    total_codes = PromoCode.objects.count()
    total_usages = PromotionUsage.objects.count()
    
    # Statistiques de la période
    today = timezone.now().date()
    this_month = today.replace(day=1)
    
    monthly_stats = {
        'usages': PromotionUsage.objects.filter(used_at__date__gte=this_month).count(),
        'discount_given': PromotionUsage.objects.filter(
            used_at__date__gte=this_month
        ).aggregate(total=Sum('discount_amount'))['total'] or Decimal('0'),
        'unique_users': PromotionUsage.objects.filter(
            used_at__date__gte=this_month
        ).values('user').distinct().count(),
    }
    
    # Top campagnes
    top_campaigns = PromotionCampaign.objects.annotate(
        usage_count=Count('usages'),
        total_discount=Sum('usages__discount_amount')
    ).order_by('-usage_count')[:5]
    
    context = {
        'total_campaigns': total_campaigns,
        'active_campaigns': active_campaigns,
        'total_codes': total_codes,
        'total_usages': total_usages,
        'monthly_stats': monthly_stats,
        'top_campaigns': top_campaigns,
    }
    
    return render(request, 'promotions/admin/analytics_dashboard.html', context)


@admin_required
@require_http_methods(["POST"])
def admin_code_toggle(request, code_id):
    """Active/désactive un code promo"""
    code = get_object_or_404(PromoCode, id=code_id)
    
    code.is_active = not code.is_active
    if not code.is_active:
        code.deactivated_at = timezone.now()
        code.deactivated_by = request.user
    code.save()
    
    action = 'activé' if code.is_active else 'désactivé'
    messages.success(request, f'Code {code.code} {action}')
    
    # Log de l'action
    AuditService.log_admin_action(
        admin_user=request.user,
        category='content_management',
        action='toggle_promo_code',
        description=f'Code promo {code.code} {action}',
        target_object_type='PromoCode',
        target_object_id=str(code.id),
        request=request
    )
    
    return redirect('promotions:admin_codes')


@admin_required
def admin_campaign_create(request):
    """Créer une nouvelle campagne"""
    if request.method == 'POST':
        # Traitement du formulaire (à implémenter)
        pass
    
    return render(request, 'promotions/admin/campaign_form.html')


@admin_required
def admin_campaign_edit(request, campaign_id):
    """Modifier une campagne"""
    campaign = get_object_or_404(PromotionCampaign, id=campaign_id)
    
    if request.method == 'POST':
        # Traitement du formulaire (à implémenter)
        pass
    
    context = {'campaign': campaign}
    return render(request, 'promotions/admin/campaign_form.html', context)


@admin_required
def admin_code_create(request):
    """Créer un nouveau code promo"""
    if request.method == 'POST':
        # Traitement du formulaire (à implémenter)
        pass
    
    campaigns = PromotionCampaign.objects.filter(status='active')
    context = {'campaigns': campaigns}
    return render(request, 'promotions/admin/code_form.html', context)
