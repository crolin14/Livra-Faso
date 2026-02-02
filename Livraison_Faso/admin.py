from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth import get_user_model
from users.models import LivreurProfile, EntrepriseProfile
from missions.models import Mission, MissionTracking, MissionDocument
from chat.models import Conversation, ChatMessage, MessageNotification
from ratings.models import Rating, RatingCategory, CategoryRating, RatingResponse
from subscriptions.models import SubscriptionPlan, UserSubscription, Payment, PaymentNotification
from location.models import UserLocation, MissionLocation, LocationHistory, Geofence, LocationAlert

User = get_user_model()

# Configuration de l'administration pour l'utilisateur personnalisé
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'user_type', 'is_verified', 'is_active')
    list_filter = ('user_type', 'is_verified', 'is_active', 'date_joined')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('-date_joined',)
    
    fieldsets = UserAdmin.fieldsets + (
        ('Informations Livraison Faso', {
            'fields': ('user_type', 'phone_number', 'is_verified')
        }),
    )
    
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Informations Livraison Faso', {
            'fields': ('user_type', 'phone_number')
        }),
    )

# Administration des profils livreurs
@admin.register(LivreurProfile)
class LivreurProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'vehicle_type', 'is_available', 'rating', 'total_missions')
    list_filter = ('vehicle_type', 'is_available', 'experience_years')
    search_fields = ('user__username', 'user__first_name', 'user__last_name')
    readonly_fields = ('rating', 'total_missions')

# Administration des profils entreprises
@admin.register(EntrepriseProfile)
class EntrepriseProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'company_name', 'business_type', 'rating', 'total_orders')
    list_filter = ('business_type',)
    search_fields = ('company_name', 'user__username')
    readonly_fields = ('rating', 'total_orders')

# Administration des missions
@admin.register(Mission)
class MissionAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'client', 'livreur', 'status', 'priority', 'price', 'created_at')
    list_filter = ('status', 'priority', 'is_fragile', 'requires_signature', 'created_at')
    search_fields = ('title', 'client__username', 'livreur__username')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'

# Administration du suivi des missions
@admin.register(MissionTracking)
class MissionTrackingAdmin(admin.ModelAdmin):
    list_display = ('mission', 'status', 'location', 'timestamp')
    list_filter = ('status', 'timestamp')
    search_fields = ('mission__title', 'description')
    readonly_fields = ('timestamp',)

# Administration des documents de mission
@admin.register(MissionDocument)
class MissionDocumentAdmin(admin.ModelAdmin):
    list_display = ('mission', 'document_type', 'uploaded_at')
    list_filter = ('document_type', 'uploaded_at')
    search_fields = ('mission__title', 'description')

# Administration des conversations
@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('id', 'participants_display', 'is_active', 'created_at', 'updated_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('participants__username',)
    readonly_fields = ('created_at', 'updated_at')
    
    def participants_display(self, obj):
        return ", ".join([user.username for user in obj.participants.all()])
    participants_display.short_description = "Participants"

# Administration des messages
@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'conversation', 'message_type', 'is_read', 'timestamp')
    list_filter = ('message_type', 'is_read', 'timestamp')
    search_fields = ('content', 'sender__username')
    readonly_fields = ('timestamp',)

# Administration des notifications de messages
@admin.register(MessageNotification)
class MessageNotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'message', 'is_read', 'created_at')
    list_filter = ('is_read', 'created_at')
    search_fields = ('user__username', 'message__content')

# Administration des évaluations
@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ('rater', 'rated_user', 'rating', 'mission', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('rater__username', 'rated_user__username', 'comment')
    readonly_fields = ('created_at', 'updated_at')

# Administration des catégories d'évaluation
@admin.register(RatingCategory)
class RatingCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'description')

# Administration des évaluations par catégorie
@admin.register(CategoryRating)
class CategoryRatingAdmin(admin.ModelAdmin):
    list_display = ('rating', 'category', 'score')
    list_filter = ('category', 'score')
    search_fields = ('rating__rater__username', 'category__name')

# Administration des réponses aux évaluations
@admin.register(RatingResponse)
class RatingResponseAdmin(admin.ModelAdmin):
    list_display = ('rating', 'created_at')
    search_fields = ('content', 'rating__rater__username')
    readonly_fields = ('created_at',)

# Administration des plans d'abonnement
@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'plan_type', 'price', 'duration_days', 'is_active')
    list_filter = ('plan_type', 'is_active', 'priority_support', 'advanced_analytics')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at',)

# Administration des abonnements utilisateurs
@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan', 'status', 'start_date', 'end_date', 'amount_paid')
    list_filter = ('status', 'plan', 'payment_method', 'start_date')
    search_fields = ('user__username', 'plan__name')
    readonly_fields = ('created_at', 'updated_at')

# Administration des paiements
@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'currency', 'status', 'payment_method', 'created_at')
    list_filter = ('status', 'payment_method', 'operator', 'created_at')
    search_fields = ('user__username', 'transaction_id', 'reference')
    readonly_fields = ('created_at', 'updated_at')

# Administration des notifications de paiement
@admin.register(PaymentNotification)
class PaymentNotificationAdmin(admin.ModelAdmin):
    list_display = ('payment', 'notification_type', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read', 'created_at')
    search_fields = ('message', 'payment__user__username')
    readonly_fields = ('created_at',)

# Administration de la géolocalisation
@admin.register(UserLocation)
class UserLocationAdmin(admin.ModelAdmin):
    list_display = ('user', 'latitude', 'longitude', 'city', 'is_active', 'last_updated')
    list_filter = ('is_active', 'city', 'country', 'last_updated')
    search_fields = ('user__username', 'address')
    readonly_fields = ('created_at', 'last_updated')

@admin.register(MissionLocation)
class MissionLocationAdmin(admin.ModelAdmin):
    list_display = ('mission', 'location_type', 'latitude', 'longitude', 'city')
    list_filter = ('location_type', 'city', 'country')
    search_fields = ('mission__title', 'address')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(LocationHistory)
class LocationHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'latitude', 'longitude', 'speed', 'timestamp')
    list_filter = ('timestamp',)
    search_fields = ('user__username',)
    readonly_fields = ('timestamp',)
    date_hierarchy = 'timestamp'

@admin.register(Geofence)
class GeofenceAdmin(admin.ModelAdmin):
    list_display = ('name', 'geofence_type', 'center_latitude', 'center_longitude', 'radius', 'is_active')
    list_filter = ('geofence_type', 'is_active', 'created_at')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at',)

@admin.register(LocationAlert)
class LocationAlertAdmin(admin.ModelAdmin):
    list_display = ('user', 'alert_type', 'geofence', 'is_read', 'created_at')
    list_filter = ('alert_type', 'is_read', 'created_at')
    search_fields = ('user__username', 'message')
    readonly_fields = ('created_at',)

# Enregistrement des modèles
admin.site.register(User, CustomUserAdmin)

# Configuration du site d'administration
admin.site.site_header = "Administration Livraison Faso"
admin.site.site_title = "Livraison Faso Admin"
admin.site.index_title = "Tableau de bord Livraison Faso" 