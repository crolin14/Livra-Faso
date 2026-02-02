from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction
from django.db.models import Sum, Count, Q
from decimal import Decimal
from .models import PromotionCampaign, PromoCode, PromotionUsage, PromotionRule, PromotionAnalytics
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


class PromotionService:
    """Service principal pour la gestion des promotions"""
    
    @staticmethod
    def validate_promo_code(code, user, order_amount):
        """
        Valide un code promo pour un utilisateur et montant donnés
        """
        try:
            promo_code = PromoCode.objects.select_related('campaign').get(
                code=code.upper(),
                is_active=True
            )
            
            # Vérifier si le code peut être utilisé
            if not promo_code.can_be_used():
                return {
                    'valid': False,
                    'error': 'Code promo non valide ou expiré',
                    'code': None
                }
            
            # Vérifier si l'utilisateur peut utiliser cette campagne
            if not promo_code.campaign.can_be_used_by_user(user):
                return {
                    'valid': False,
                    'error': 'Ce code promo n\'est pas disponible pour votre profil',
                    'code': None
                }
            
            # Vérifier les règles avancées
            if not PromotionService._check_promotion_rules(promo_code.campaign, user):
                return {
                    'valid': False,
                    'error': 'Conditions d\'utilisation non remplies',
                    'code': None
                }
            
            # Calculer la réduction
            discount = promo_code.campaign.calculate_discount(order_amount)
            
            if discount <= 0:
                return {
                    'valid': False,
                    'error': f'Montant minimum requis: {promo_code.campaign.minimum_order_amount} FCFA',
                    'code': None
                }
            
            return {
                'valid': True,
                'error': None,
                'code': promo_code,
                'discount_amount': discount,
                'final_amount': order_amount - discount,
                'campaign': promo_code.campaign
            }
            
        except PromoCode.DoesNotExist:
            return {
                'valid': False,
                'error': 'Code promo introuvable',
                'code': None
            }
        except Exception as e:
            logger.error(f"Erreur lors de la validation du code promo {code}: {e}")
            return {
                'valid': False,
                'error': 'Erreur lors de la validation du code',
                'code': None
            }
    
    @staticmethod
    def apply_promotion(promo_code, user, mission, original_amount, request=None):
        """
        Applique une promotion et enregistre son utilisation
        """
        try:
            with transaction.atomic():
                # Recalculer la réduction pour s'assurer de la cohérence
                discount = promo_code.campaign.calculate_discount(original_amount)
                final_amount = original_amount - discount
                
                # Créer l'enregistrement d'utilisation
                usage = PromotionUsage.objects.create(
                    campaign=promo_code.campaign,
                    promo_code=promo_code,
                    user=user,
                    mission=mission,
                    original_amount=original_amount,
                    discount_amount=discount,
                    final_amount=final_amount,
                    ip_address=PromotionService._get_client_ip(request) if request else None,
                    user_agent=request.META.get('HTTP_USER_AGENT', '') if request else ''
                )
                
                # Mettre à jour les compteurs
                promo_code.usage_count += 1
                promo_code.save()
                
                promo_code.campaign.current_usage_count += 1
                promo_code.campaign.total_savings_generated += discount
                promo_code.campaign.save()
                
                # Désactiver le code si usage unique et utilisé
                if promo_code.is_single_use:
                    promo_code.is_active = False
                    promo_code.save()
                
                # Enregistrer dans l'audit
                from audit.services import AuditService
                AuditService.log_action(
                    user=user,
                    action_type='promo_used',
                    description=f"Code promo utilisé: {promo_code.code}",
                    content_object=usage,
                    severity='low',
                    request=request,
                    additional_data={
                        'promo_code': promo_code.code,
                        'campaign': promo_code.campaign.name,
                        'discount_amount': float(discount),
                        'original_amount': float(original_amount),
                    }
                )
                
                return usage
                
        except Exception as e:
            logger.error(f"Erreur lors de l'application de la promotion: {e}")
            return None
    
    @staticmethod
    def get_available_promotions(user):
        """
        Récupère les promotions disponibles pour un utilisateur
        """
        now = timezone.now()
        
        # Promotions actives dans la période de validité
        campaigns = PromotionCampaign.objects.filter(
            status='active',
            start_date__lte=now,
            end_date__gte=now
        ).filter(
            Q(total_usage_limit__isnull=True) | 
            Q(current_usage_count__lt=models.F('total_usage_limit'))
        )
        
        available_campaigns = []
        for campaign in campaigns:
            if campaign.can_be_used_by_user(user):
                # Vérifier les règles avancées
                if PromotionService._check_promotion_rules(campaign, user):
                    available_campaigns.append(campaign)
        
        return available_campaigns
    
    @staticmethod
    def generate_bulk_promo_codes(campaign, count, prefix='', length=8, created_by=None):
        """
        Génère des codes promo en lot
        """
        codes = []
        for _ in range(count):
            code = PromoCode.generate_code(length=length, prefix=prefix)
            promo_code = PromoCode.objects.create(
                code=code,
                campaign=campaign,
                generation_type='bulk',
                generated_by=created_by
            )
            codes.append(promo_code)
        
        return codes
    
    @staticmethod
    def get_promotion_analytics(campaign, start_date=None, end_date=None):
        """
        Récupère les analytics d'une campagne
        """
        if not start_date:
            start_date = campaign.start_date.date()
        if not end_date:
            end_date = timezone.now().date()
        
        analytics = PromotionAnalytics.objects.filter(
            campaign=campaign,
            date__range=[start_date, end_date]
        ).order_by('date')
        
        # Calculer les totaux
        totals = analytics.aggregate(
            total_uses=Sum('total_uses'),
            total_unique_users=Sum('unique_users'),
            total_discount=Sum('total_discount_given'),
            total_revenue_impact=Sum('total_revenue_impact'),
            avg_conversion_rate=models.Avg('conversion_rate')
        )
        
        return {
            'daily_analytics': analytics,
            'totals': totals,
            'period': {
                'start': start_date,
                'end': end_date
            }
        }
    
    @staticmethod
    def update_daily_analytics(campaign, date=None):
        """
        Met à jour les analytics quotidiennes d'une campagne
        """
        if not date:
            date = timezone.now().date()
        
        # Récupérer les données du jour
        usages = PromotionUsage.objects.filter(
            campaign=campaign,
            used_at__date=date,
            is_valid=True
        )
        
        analytics, created = PromotionAnalytics.objects.get_or_create(
            campaign=campaign,
            date=date,
            defaults={
                'total_uses': 0,
                'unique_users': 0,
                'total_discount_given': Decimal('0'),
                'total_revenue_impact': Decimal('0'),
            }
        )
        
        # Calculer les métriques
        analytics.total_uses = usages.count()
        analytics.unique_users = usages.values('user').distinct().count()
        analytics.total_discount_given = usages.aggregate(
            total=Sum('discount_amount')
        )['total'] or Decimal('0')
        analytics.total_revenue_impact = usages.aggregate(
            total=Sum('original_amount')
        )['total'] or Decimal('0')
        
        analytics.save()
        
        return analytics
    
    @staticmethod
    def _check_promotion_rules(campaign, user, mission=None):
        """
        Vérifie les règles avancées d'une campagne
        """
        rules = campaign.rules.filter(is_active=True)
        
        for rule in rules:
            if not rule.evaluate(user, mission):
                return False
        
        return True
    
    @staticmethod
    def _get_client_ip(request):
        """Récupère l'IP du client"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    @staticmethod
    def deactivate_expired_campaigns():
        """
        Désactive les campagnes expirées (tâche cron)
        """
        now = timezone.now()
        expired_campaigns = PromotionCampaign.objects.filter(
            status='active',
            end_date__lt=now
        )
        
        count = expired_campaigns.update(status='expired')
        
        if count > 0:
            logger.info(f"{count} campagnes expirées désactivées")
        
        return count
    
    @staticmethod
    def get_user_promotion_history(user, limit=50):
        """
        Récupère l'historique des promotions d'un utilisateur
        """
        return PromotionUsage.objects.filter(
            user=user,
            is_valid=True
        ).select_related(
            'campaign', 'promo_code', 'mission'
        ).order_by('-used_at')[:limit]
    
    @staticmethod
    def calculate_user_savings(user):
        """
        Calcule les économies totales d'un utilisateur
        """
        total_savings = PromotionUsage.objects.filter(
            user=user,
            is_valid=True
        ).aggregate(
            total=Sum('discount_amount')
        )['total'] or Decimal('0')
        
        return total_savings


class PromotionRecommendationService:
    """Service de recommandation de promotions"""
    
    @staticmethod
    def recommend_promotions_for_user(user, order_amount=None):
        """
        Recommande des promotions personnalisées pour un utilisateur
        """
        available_promotions = PromotionService.get_available_promotions(user)
        
        if not available_promotions:
            return []
        
        # Scorer les promotions selon différents critères
        scored_promotions = []
        
        for campaign in available_promotions:
            score = PromotionRecommendationService._calculate_promotion_score(
                campaign, user, order_amount
            )
            scored_promotions.append({
                'campaign': campaign,
                'score': score,
                'potential_discount': campaign.calculate_discount(order_amount) if order_amount else None
            })
        
        # Trier par score décroissant
        scored_promotions.sort(key=lambda x: x['score'], reverse=True)
        
        return scored_promotions[:5]  # Top 5 recommandations
    
    @staticmethod
    def _calculate_promotion_score(campaign, user, order_amount=None):
        """
        Calcule un score de recommandation pour une promotion
        """
        score = 0
        
        # Score basé sur le type de promotion
        if campaign.campaign_type == 'percentage':
            score += 30
        elif campaign.campaign_type == 'fixed_amount':
            score += 25
        elif campaign.campaign_type == 'free_delivery':
            score += 20
        
        # Score basé sur l'audience cible
        if campaign.target_audience == user.user_type:
            score += 20
        elif campaign.target_audience == 'all':
            score += 10
        
        # Score basé sur l'urgence (fin proche)
        days_until_end = (campaign.end_date - timezone.now()).days
        if days_until_end <= 1:
            score += 30  # Urgence élevée
        elif days_until_end <= 7:
            score += 15  # Urgence moyenne
        
        # Score basé sur la rareté (usage limité)
        if campaign.total_usage_limit:
            usage_ratio = campaign.current_usage_count / campaign.total_usage_limit
            if usage_ratio > 0.8:
                score += 25  # Presque épuisé
            elif usage_ratio > 0.5:
                score += 10
        
        # Score basé sur le montant de réduction potentiel
        if order_amount:
            discount = campaign.calculate_discount(order_amount)
            discount_ratio = discount / order_amount if order_amount > 0 else 0
            score += int(discount_ratio * 100)  # Plus la réduction est importante, plus le score est élevé
        
        return score
