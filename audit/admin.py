from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import AuditLog, SecurityEvent, SystemMetrics, AdminAction, DataExport


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'user', 'action_type', 'action_description', 'severity', 'requires_review', 'is_reviewed']
    list_filter = ['action_type', 'severity', 'requires_review', 'is_reviewed', 'timestamp']
    search_fields = ['action_description', 'user__username', 'user__email']
    readonly_fields = ['id', 'timestamp', 'user', 'action_type', 'action_description', 'content_type', 'object_id', 'old_values', 'new_values', 'additional_data', 'user_ip', 'user_agent', 'session_key', 'request_path', 'request_method']
    
    fieldsets = (
        ('Information de base', {
            'fields': ('id', 'timestamp', 'user', 'action_type', 'action_description', 'severity')
        }),
        ('Objet concerné', {
            'fields': ('content_type', 'object_id'),
            'classes': ('collapse',)
        }),
        ('Données', {
            'fields': ('old_values', 'new_values', 'additional_data'),
            'classes': ('collapse',)
        }),
        ('Métadonnées de requête', {
            'fields': ('user_ip', 'user_agent', 'session_key', 'request_path', 'request_method'),
            'classes': ('collapse',)
        }),
        ('Révision', {
            'fields': ('requires_review', 'is_reviewed', 'reviewed_by', 'reviewed_at'),
        }),
    )
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        # Only allow marking as reviewed
        return request.user.is_superuser
    
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(SecurityEvent)
class SecurityEventAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'event_type', 'source_ip', 'risk_level', 'user', 'is_blocked', 'is_investigated']
    list_filter = ['event_type', 'risk_level', 'is_blocked', 'is_investigated', 'timestamp']
    search_fields = ['description', 'source_ip', 'user__username']
    readonly_fields = ['id', 'timestamp', 'event_type', 'source_ip', 'description', 'user', 'user_agent', 'request_path', 'request_method', 'request_data']
    
    fieldsets = (
        ('Événement', {
            'fields': ('id', 'timestamp', 'event_type', 'risk_level', 'description')
        }),
        ('Source', {
            'fields': ('source_ip', 'user', 'user_agent')
        }),
        ('Requête', {
            'fields': ('request_path', 'request_method', 'request_data'),
            'classes': ('collapse',)
        }),
        ('Réponse', {
            'fields': ('is_blocked', 'action_taken')
        }),
        ('Investigation', {
            'fields': ('is_investigated', 'investigated_by', 'investigated_at', 'investigation_notes')
        }),
    )
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(SystemMetrics)
class SystemMetricsAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'system_status', 'cpu_usage', 'memory_usage', 'active_users', 'missions_created_today']
    list_filter = ['system_status', 'timestamp']
    readonly_fields = ['id', 'timestamp', 'cpu_usage', 'memory_usage', 'disk_usage', 'active_users', 'active_sessions', 'api_requests_per_minute', 'database_connections', 'missions_created_today', 'missions_completed_today', 'revenue_today', 'new_users_today', 'error_rate', 'failed_requests', 'system_status']
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('id', 'timestamp', 'system_status')
        }),
        ('Métriques système', {
            'fields': ('cpu_usage', 'memory_usage', 'disk_usage', 'database_connections')
        }),
        ('Métriques applicatives', {
            'fields': ('active_users', 'active_sessions', 'api_requests_per_minute')
        }),
        ('Métriques métier', {
            'fields': ('missions_created_today', 'missions_completed_today', 'revenue_today', 'new_users_today')
        }),
        ('Métriques d\'erreur', {
            'fields': ('error_rate', 'failed_requests')
        }),
    )
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(AdminAction)
class AdminActionAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'admin_user', 'category', 'action', 'target_user', 'is_critical', 'is_approved']
    list_filter = ['category', 'is_critical', 'is_approved', 'requires_approval', 'timestamp']
    search_fields = ['action', 'description', 'admin_user__username', 'target_user__username']
    readonly_fields = ['id', 'timestamp', 'admin_user', 'category', 'action', 'description', 'target_user', 'target_object_type', 'target_object_id', 'before_state', 'after_state', 'ip_address', 'user_agent']
    
    fieldsets = (
        ('Action', {
            'fields': ('id', 'timestamp', 'admin_user', 'category', 'action', 'description')
        }),
        ('Cible', {
            'fields': ('target_user', 'target_object_type', 'target_object_id')
        }),
        ('États', {
            'fields': ('before_state', 'after_state'),
            'classes': ('collapse',)
        }),
        ('Métadonnées', {
            'fields': ('ip_address', 'user_agent', 'reason'),
            'classes': ('collapse',)
        }),
        ('Validation', {
            'fields': ('is_critical', 'requires_approval', 'is_approved', 'approved_by', 'approved_at')
        }),
    )
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(DataExport)
class DataExportAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'user', 'export_type', 'format', 'records_count', 'contains_sensitive_data', 'is_completed']
    list_filter = ['export_type', 'format', 'contains_sensitive_data', 'is_completed', 'timestamp']
    search_fields = ['user__username', 'access_reason']
    readonly_fields = ['id', 'timestamp', 'user', 'export_type', 'format', 'filters_applied', 'date_range_start', 'date_range_end', 'records_count', 'file_size', 'file_path']
    
    fieldsets = (
        ('Export', {
            'fields': ('id', 'timestamp', 'user', 'export_type', 'format')
        }),
        ('Filtres', {
            'fields': ('filters_applied', 'date_range_start', 'date_range_end'),
            'classes': ('collapse',)
        }),
        ('Résultats', {
            'fields': ('records_count', 'file_size', 'file_path', 'is_completed', 'error_message')
        }),
        ('Sécurité', {
            'fields': ('contains_sensitive_data', 'access_reason')
        }),
    )
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
