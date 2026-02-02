from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse, path
from django.shortcuts import redirect
from django.contrib import messages
from django.utils import timezone
from .models import PromotionCampaign, PromoCode, PromotionUsage, PromotionRule, PromotionAnalytics
from .services import PromotionService


@admin.register(PromotionCampaign)
class PromotionCampaignAdmin(admin.ModelAdmin):
    list_display = ['name', 'campaign_type', 'status', 'start_date', 'end_date', 'current_usage_count', 'total_savings_generated']
    list_filter = ['status', 'campaign_type', 'target_audience', 'start_date', 'end_date']
    search_fields = ['name', 'description']
    readonly_fields = ['id', 'current_usage_count', 'total_savings_generated', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('name', 'description', 'status')
        }),
        ('Type de promotion', {
            'fields': ('campaign_type', 'discount_percentage', 'discount_amount')
        }),
        ('Conditions', {
            'fields': ('minimum_order_amount', 'maximum_discount_amount')
        }),
        ('Période de validité', {
            'fields': ('start_date', 'end_date')
        }),
        ('Audience cible', {
            'fields': ('target_audience', 'specific_users')
        }),
        ('Limites d\'utilisation', {
            'fields': ('usage_limit_per_user', 'total_usage_limit', 'current_usage_count')
        }),
        ('Métadonnées', {
            'fields': ('id', 'created_by', 'created_at', 'updated_at', 'total_savings_generated'),
            'classes': ('collapse',)
        }),
    )
    
    filter_horizontal = ['specific_users']
    
    def save_model(self, request, obj, form, change):
        if not change:  # Nouvelle campagne
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<path:object_id>/generate-codes/', self.admin_site.admin_view(self.generate_codes_view), name='promotions_promotioncampaign_generate_codes'),
            path('<path:object_id>/analytics/', self.admin_site.admin_view(self.analytics_view), name='promotions_promotioncampaign_analytics'),
        ]
        return custom_urls + urls
    
    def generate_codes_view(self, request, object_id):
        # Vue pour générer des codes en lot
        campaign = self.get_object(request, object_id)
        if request.method == 'POST':
            count = int(request.POST.get('count', 10))
            prefix = request.POST.get('prefix', '')
            codes = PromotionService.generate_bulk_promo_codes(
                campaign, count, prefix, created_by=request.user
            )
            messages.success(request, f'{len(codes)} codes générés avec succès')
        return redirect('admin:promotions_promotioncampaign_change', object_id)
    
    def analytics_view(self, request, object_id):
        # Vue pour les analytics (à implémenter)
        return redirect('admin:promotions_promotioncampaign_change', object_id)


@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    list_display = ['code', 'campaign', 'generation_type', 'usage_count', 'max_uses', 'is_active']
    list_filter = ['generation_type', 'is_active', 'is_single_use', 'generated_at']
    search_fields = ['code', 'campaign__name']
    readonly_fields = ['id', 'generated_at', 'usage_count']
    
    fieldsets = (
        ('Code promo', {
            'fields': ('code', 'campaign', 'is_active')
        }),
        ('Génération', {
            'fields': ('generation_type', 'generated_by', 'generated_at')
        }),
        ('Utilisation', {
            'fields': ('is_single_use', 'max_uses', 'usage_count')
        }),
        ('Désactivation', {
            'fields': ('deactivated_at', 'deactivated_by'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:  # Nouveau code
            obj.generated_by = request.user
            if not obj.code:
                obj.code = PromoCode.generate_code()
        super().save_model(request, obj, form, change)


@admin.register(PromotionUsage)
class PromotionUsageAdmin(admin.ModelAdmin):
    list_display = ['user', 'campaign', 'promo_code', 'discount_amount', 'used_at', 'is_valid']
    list_filter = ['is_valid', 'used_at', 'campaign']
    search_fields = ['user__username', 'user__email', 'promo_code__code', 'campaign__name']
    readonly_fields = ['id', 'used_at', 'ip_address', 'user_agent']
    
    fieldsets = (
        ('Utilisation', {
            'fields': ('campaign', 'promo_code', 'user', 'mission')
        }),
        ('Montants', {
            'fields': ('original_amount', 'discount_amount', 'final_amount')
        }),
        ('Métadonnées', {
            'fields': ('used_at', 'ip_address', 'user_agent'),
            'classes': ('collapse',)
        }),
        ('Statut', {
            'fields': ('is_valid', 'invalidated_at', 'invalidation_reason')
        }),
    )
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        # Permettre seulement l'invalidation
        return request.user.has_perm('promotions.change_promotionusage')


@admin.register(PromotionRule)
class PromotionRuleAdmin(admin.ModelAdmin):
    list_display = ['campaign', 'rule_type', 'field_name', 'operator', 'value', 'is_active']
    list_filter = ['rule_type', 'operator', 'is_active']
    search_fields = ['campaign__name', 'field_name', 'value']
    
    fieldsets = (
        ('Règle', {
            'fields': ('campaign', 'rule_type', 'field_name', 'operator', 'value')
        }),
        ('Statut', {
            'fields': ('is_active',)
        }),
    )


@admin.register(PromotionAnalytics)
class PromotionAnalyticsAdmin(admin.ModelAdmin):
    list_display = ['campaign', 'date', 'total_uses', 'unique_users', 'total_discount_given', 'conversion_rate']
    list_filter = ['date', 'campaign']
    search_fields = ['campaign__name']
    readonly_fields = ['id', 'created_at']
    
    fieldsets = (
        ('Campagne et date', {
            'fields': ('campaign', 'date')
        }),
        ('Métriques d\'utilisation', {
            'fields': ('total_uses', 'unique_users', 'total_discount_given', 'total_revenue_impact')
        }),
        ('Métriques de conversion', {
            'fields': ('views', 'clicks', 'conversions', 'conversion_rate')
        }),
    )
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
