from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
import uuid

User = get_user_model()

class Role(models.Model):
    """Modèle pour les rôles système avec hiérarchie"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50, unique=True)
    display_name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_system = models.BooleanField(default=False, help_text="Rôle système non modifiable")
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='children')
    level = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['level', 'name']
        verbose_name = 'Rôle'
        verbose_name_plural = 'Rôles'

    def __str__(self):
        return self.display_name

    def save(self, *args, **kwargs):
        if self.parent:
            self.level = self.parent.level + 1
        super().save(*args, **kwargs)

    def get_all_permissions(self):
        """Récupère toutes les permissions du rôle et de ses parents"""
        permissions = set(self.permissions.all())
        if self.parent:
            permissions.update(self.parent.get_all_permissions())
        return permissions

    def has_permission(self, permission_codename):
        """Vérifie si le rôle a une permission spécifique"""
        return self.get_all_permissions().filter(codename=permission_codename).exists()

class Permission(models.Model):
    """Modèle pour les permissions granulaires"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    codename = models.CharField(max_length=50, unique=True)
    module = models.CharField(max_length=50, db_index=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['module', 'name']
        verbose_name = 'Permission'
        verbose_name_plural = 'Permissions'

    def __str__(self):
        return f"{self.module}.{self.codename}"

class RolePermission(models.Model):
    """Association rôles-permissions avec métadonnées"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='role_permissions')
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE, related_name='permission_roles')
    granted_at = models.DateTimeField(auto_now_add=True)
    granted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        unique_together = ['role', 'permission']
        verbose_name = 'Permission de rôle'
        verbose_name_plural = 'Permissions de rôles'

    def __str__(self):
        return f"{self.role.name} -> {self.permission.codename}"

class UserRole(models.Model):
    """Association utilisateurs-rôles avec expiration"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_roles')
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='role_users')
    assigned_at = models.DateTimeField(auto_now_add=True)
    assigned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_roles')
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ['user', 'role']
        verbose_name = 'Rôle utilisateur'
        verbose_name_plural = 'Rôles utilisateurs'

    def __str__(self):
        return f"{self.user.username} -> {self.role.name}"

    def clean(self):
        if self.expires_at and self.expires_at <= self.assigned_at:
            raise ValidationError("La date d'expiration doit être postérieure à la date d'attribution")

    def is_expired(self):
        """Vérifie si le rôle a expiré"""
        if not self.expires_at:
            return False
        from django.utils import timezone
        return timezone.now() > self.expires_at

class PermissionCache(models.Model):
    """Cache des permissions utilisateur pour optimiser les performances"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='permission_cache')
    permissions = models.JSONField(default=list)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Cache de permissions'
        verbose_name_plural = 'Caches de permissions'

    def __str__(self):
        return f"Cache permissions: {self.user.username}"

    def refresh_cache(self):
        """Actualise le cache des permissions"""
        permissions = []
        for user_role in self.user.user_roles.filter(is_active=True):
            if not user_role.is_expired():
                role_permissions = user_role.role.get_all_permissions()
                for perm in role_permissions:
                    permissions.append({
                        'codename': perm.codename,
                        'module': perm.module,
                        'name': perm.name
                    })
        
        self.permissions = permissions
        self.save()
        return permissions

    def has_permission(self, permission_codename):
        """Vérifie rapidement si l'utilisateur a une permission"""
        return any(perm['codename'] == permission_codename for perm in self.permissions)

    def has_module_access(self, module_name):
        """Vérifie si l'utilisateur a accès à un module"""
        return any(perm['module'] == module_name for perm in self.permissions)
