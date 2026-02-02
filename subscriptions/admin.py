from django.contrib import admin
from .models import SubscriptionPlan, UserSubscription, Payment, PaymentNotification

@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'plan_type', 'price', 'duration', 'is_active', 'created_at']
    list_filter = ['plan_type', 'is_active', 'created_at']
    search_fields = ['name', 'features']
    list_editable = ['is_active']
    ordering = ['plan_type', 'price']
    
    fieldsets = (
        ('Informations de base', {
            'fields': ('name', 'plan_type', 'price', 'duration', 'features', 'is_active')
        }),
        ('Fonctionnalités', {
            'fields': ('max_missions_per_month', 'priority_support', 'advanced_analytics', 'multi_user_management'),
            'classes': ('collapse',)
        }),
    )

@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = ['user', 'plan', 'status', 'payment_status', 'start_date', 'end_date', 'days_remaining_display']
    list_filter = ['status', 'payment_status', 'plan', 'created_at']
    search_fields = ['user__username', 'user__email', 'plan__name']
    readonly_fields = ['created_at', 'updated_at', 'days_remaining_display']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Abonnement', {
            'fields': ('user', 'plan', 'status')
        }),
        ('Dates', {
            'fields': ('start_date', 'end_date', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
        ('Paiement', {
            'fields': ('payment_status', 'amount_paid', 'payment_method')
        }),
        ('Informations', {
            'fields': ('days_remaining_display',),
            'classes': ('collapse',)
        }),
    )
    
    def days_remaining_display(self, obj):
        days = obj.days_remaining
        if days > 0:
            return f"{days} jours"
        return "Expiré"
    days_remaining_display.short_description = "Jours restants"
    
    actions = ['activate_subscriptions', 'cancel_subscriptions']
    
    def activate_subscriptions(self, request, queryset):
        for subscription in queryset:
            subscription.activate()
        self.message_user(request, f"{queryset.count()} abonnements activés.")
    activate_subscriptions.short_description = "Activer les abonnements sélectionnés"
    
    def cancel_subscriptions(self, request, queryset):
        for subscription in queryset:
            subscription.cancel()
        self.message_user(request, f"{queryset.count()} abonnements annulés.")
    cancel_subscriptions.short_description = "Annuler les abonnements sélectionnés"

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['user', 'amount', 'currency', 'status', 'payment_method', 'created_at']
    list_filter = ['status', 'payment_method', 'operator', 'created_at']
    search_fields = ['user__username', 'transaction_id', 'reference', 'phone_number']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'created_at'

@admin.register(PaymentNotification)
class PaymentNotificationAdmin(admin.ModelAdmin):
    list_display = ['payment', 'notification_type', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['message']
    readonly_fields = ['created_at']
