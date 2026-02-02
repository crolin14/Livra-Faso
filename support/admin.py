from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from django.db.models import Count, Avg
from .models import (
    SupportCategory, SupportTicket, TicketMessage, TicketAttachment,
    TicketTemplate, SupportKnowledgeBase, SupportMetrics
)
from audit.services import AuditService


@admin.register(SupportCategory)
class SupportCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'response_time_hours', 'resolution_time_hours', 'is_active', 'ticket_count')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'ticket_count')
    
    fieldsets = (
        ('Informations de base', {
            'fields': ('name', 'description', 'color', 'icon')
        }),
        ('Configuration SLA', {
            'fields': ('response_time_hours', 'resolution_time_hours')
        }),
        ('Paramètres', {
            'fields': ('is_active', 'auto_assign_to')
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'ticket_count'),
            'classes': ('collapse',)
        })
    )
    
    def ticket_count(self, obj):
        return obj.tickets.count()
    ticket_count.short_description = 'Nombre de tickets'
    
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        
        # Log de l'action
        action = 'update' if change else 'create'
        AuditService.log_admin_action(
            admin_user=request.user,
            category='support_management',
            action=f'{action}_category',
            description=f"Catégorie de support {action}e: {obj.name}",
            target_object_type='SupportCategory',
            target_object_id=str(obj.id),
            request=request
        )


class TicketMessageInline(admin.TabularInline):
    model = TicketMessage
    extra = 0
    readonly_fields = ('created_at', 'ip_address', 'user_agent')
    fields = ('author', 'message_type', 'content', 'is_public', 'created_at')
    
    def has_delete_permission(self, request, obj=None):
        return False


class TicketAttachmentInline(admin.TabularInline):
    model = TicketAttachment
    extra = 0
    readonly_fields = ('uploaded_at', 'file_size')


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = (
        'ticket_number', 'title', 'user', 'category', 'priority', 
        'status', 'assigned_to', 'created_at', 'sla_status'
    )
    list_filter = (
        'status', 'priority', 'category', 'source', 'is_escalated',
        'created_at', 'resolved_at'
    )
    search_fields = (
        'ticket_number', 'title', 'description', 'user__username',
        'user__email', 'user_email'
    )
    readonly_fields = (
        'ticket_number', 'created_at', 'updated_at', 'first_response_at',
        'resolved_at', 'closed_at', 'sla_response_due', 'sla_resolution_due',
        'response_time_display', 'resolution_time_display'
    )
    
    fieldsets = (
        ('Informations du ticket', {
            'fields': (
                'ticket_number', 'title', 'description', 'category',
                'priority', 'status', 'source'
            )
        }),
        ('Utilisateur', {
            'fields': ('user', 'user_email', 'user_phone')
        }),
        ('Assignation', {
            'fields': ('assigned_to', 'assigned_by', 'assigned_at')
        }),
        ('SLA et temps', {
            'fields': (
                'sla_response_due', 'sla_resolution_due',
                'first_response_at', 'response_time_display',
                'resolved_at', 'resolution_time_display'
            ),
            'classes': ('collapse',)
        }),
        ('Résolution', {
            'fields': ('resolved_by', 'resolution_notes', 'closed_by', 'closed_at')
        }),
        ('Satisfaction', {
            'fields': (
                'satisfaction_rating', 'satisfaction_comment',
                'satisfaction_submitted_at'
            ),
            'classes': ('collapse',)
        }),
        ('Métadonnées', {
            'fields': (
                'is_escalated', 'related_mission', 'tags',
                'created_at', 'updated_at'
            ),
            'classes': ('collapse',)
        })
    )
    
    inlines = [TicketMessageInline, TicketAttachmentInline]
    
    actions = ['assign_to_me', 'mark_resolved', 'escalate_tickets']
    
    def sla_status(self, obj):
        now = timezone.now()
        
        if obj.status in ['resolved', 'closed']:
            # Vérifier si les SLA ont été respectés
            response_met = obj.first_response_at and obj.first_response_at <= obj.sla_response_due
            resolution_met = obj.resolved_at and obj.resolved_at <= obj.sla_resolution_due
            
            if response_met and resolution_met:
                return format_html('<span style="color: green;">✓ SLA Respecté</span>')
            else:
                return format_html('<span style="color: orange;">⚠ SLA Dépassé</span>')
        else:
            # Vérifier les SLA en cours
            response_overdue = not obj.first_response_at and now > obj.sla_response_due
            resolution_overdue = now > obj.sla_resolution_due
            
            if response_overdue or resolution_overdue:
                return format_html('<span style="color: red;">🔴 En retard</span>')
            else:
                return format_html('<span style="color: blue;">⏳ En cours</span>')
    
    sla_status.short_description = 'Statut SLA'
    
    def response_time_display(self, obj):
        time = obj.get_response_time()
        return str(time) if time else 'Non répondu'
    response_time_display.short_description = 'Temps de réponse'
    
    def resolution_time_display(self, obj):
        time = obj.get_resolution_time()
        return str(time) if time else 'Non résolu'
    resolution_time_display.short_description = 'Temps de résolution'
    
    def assign_to_me(self, request, queryset):
        updated = 0
        for ticket in queryset:
            if not ticket.assigned_to:
                ticket.assigned_to = request.user
                ticket.assigned_by = request.user
                ticket.assigned_at = timezone.now()
                ticket.save()
                updated += 1
        
        self.message_user(request, f'{updated} ticket(s) assigné(s) à vous.')
        
        # Log de l'action
        AuditService.log_admin_action(
            admin_user=request.user,
            category='support_management',
            action='bulk_assign_tickets',
            description=f"{updated} tickets assignés à {request.user.username}",
            request=request
        )
    
    assign_to_me.short_description = "M'assigner les tickets sélectionnés"
    
    def mark_resolved(self, request, queryset):
        updated = queryset.filter(status__in=['open', 'in_progress']).update(
            status='resolved',
            resolved_at=timezone.now(),
            resolved_by=request.user
        )
        
        self.message_user(request, f'{updated} ticket(s) marqué(s) comme résolu(s).')
        
        # Log de l'action
        AuditService.log_admin_action(
            admin_user=request.user,
            category='support_management',
            action='bulk_resolve_tickets',
            description=f"{updated} tickets marqués comme résolus",
            request=request
        )
    
    mark_resolved.short_description = "Marquer comme résolu"
    
    def escalate_tickets(self, request, queryset):
        updated = queryset.filter(is_escalated=False).update(
            is_escalated=True,
            priority='high'
        )
        
        self.message_user(request, f'{updated} ticket(s) escaladé(s).')
        
        # Log de l'action
        AuditService.log_admin_action(
            admin_user=request.user,
            category='support_management',
            action='bulk_escalate_tickets',
            description=f"{updated} tickets escaladés",
            request=request
        )
    
    escalate_tickets.short_description = "Escalader les tickets"
    
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        
        # Log de l'action
        action = 'update' if change else 'create'
        AuditService.log_admin_action(
            admin_user=request.user,
            category='support_management',
            action=f'{action}_ticket',
            description=f"Ticket {obj.ticket_number} {action}",
            target_object_type='SupportTicket',
            target_object_id=str(obj.id),
            request=request
        )


@admin.register(TicketMessage)
class TicketMessageAdmin(admin.ModelAdmin):
    list_display = ('ticket', 'author', 'message_type', 'is_public', 'created_at')
    list_filter = ('message_type', 'is_public', 'created_at')
    search_fields = ('ticket__ticket_number', 'author__username', 'content')
    readonly_fields = ('created_at', 'ip_address', 'user_agent')
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(TicketTemplate)
class TicketTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'template_type', 'category', 'is_active', 'usage_count')
    list_filter = ('template_type', 'category', 'is_active')
    search_fields = ('name', 'subject', 'content')
    readonly_fields = ('usage_count', 'created_at')
    
    fieldsets = (
        ('Informations de base', {
            'fields': ('name', 'template_type', 'category', 'is_active')
        }),
        ('Contenu', {
            'fields': ('subject', 'content', 'variables')
        }),
        ('Statistiques', {
            'fields': ('usage_count', 'created_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(SupportKnowledgeBase)
class SupportKnowledgeBaseAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'article_type', 'author', 'is_published', 
        'is_public', 'view_count', 'helpful_percentage'
    )
    list_filter = (
        'article_type', 'is_published', 'is_public', 'categories',
        'created_at', 'updated_at'
    )
    search_fields = ('title', 'content', 'tags')
    readonly_fields = (
        'slug', 'view_count', 'helpful_votes', 'total_votes',
        'created_at', 'updated_at', 'helpful_percentage'
    )
    filter_horizontal = ('categories',)
    
    fieldsets = (
        ('Informations de base', {
            'fields': ('title', 'slug', 'article_type', 'categories')
        }),
        ('Contenu', {
            'fields': ('content', 'tags')
        }),
        ('Publication', {
            'fields': ('is_published', 'is_public', 'author')
        }),
        ('Statistiques', {
            'fields': (
                'view_count', 'helpful_votes', 'total_votes', 'helpful_percentage',
                'created_at', 'updated_at'
            ),
            'classes': ('collapse',)
        })
    )
    
    def helpful_percentage(self, obj):
        if obj.total_votes > 0:
            percentage = (obj.helpful_votes / obj.total_votes) * 100
            return f"{percentage:.1f}%"
        return "0%"
    helpful_percentage.short_description = 'Utilité'


@admin.register(SupportMetrics)
class SupportMetricsAdmin(admin.ModelAdmin):
    list_display = (
        'date', 'tickets_created', 'tickets_resolved', 'tickets_closed',
        'sla_response_percentage', 'sla_resolution_percentage',
        'avg_satisfaction_display'
    )
    list_filter = ('date',)
    readonly_fields = (
        'date', 'tickets_created', 'tickets_resolved', 'tickets_closed',
        'avg_first_response_time', 'avg_resolution_time',
        'sla_response_met', 'sla_resolution_met',
        'avg_satisfaction_rating', 'satisfaction_responses',
        'sla_response_percentage', 'sla_resolution_percentage'
    )
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
    
    def sla_response_percentage(self, obj):
        if obj.tickets_created > 0:
            percentage = (obj.sla_response_met / obj.tickets_created) * 100
            return f"{percentage:.1f}%"
        return "0%"
    sla_response_percentage.short_description = 'SLA Réponse'
    
    def sla_resolution_percentage(self, obj):
        if obj.tickets_resolved > 0:
            percentage = (obj.sla_resolution_met / obj.tickets_resolved) * 100
            return f"{percentage:.1f}%"
        return "0%"
    sla_resolution_percentage.short_description = 'SLA Résolution'
    
    def avg_satisfaction_display(self, obj):
        if obj.avg_satisfaction_rating:
            return f"{obj.avg_satisfaction_rating:.1f}/5"
        return "N/A"
    avg_satisfaction_display.short_description = 'Satisfaction moy.'


# Configuration de l'admin
admin.site.site_header = "LivraFaso - Administration Support"
admin.site.site_title = "Support Admin"
admin.site.index_title = "Gestion du Support"
