from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Role, Permission, RolePermission, UserRole, PermissionCache

User = get_user_model()

class PermissionSerializer(serializers.ModelSerializer):
    """Serializer pour les permissions"""
    
    class Meta:
        model = Permission
        fields = ['id', 'name', 'codename', 'module', 'description', 'created_at']
        read_only_fields = ['id', 'created_at']

class RoleSerializer(serializers.ModelSerializer):
    """Serializer pour les rôles avec permissions"""
    permissions = PermissionSerializer(many=True, read_only=True)
    permission_ids = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
        required=False
    )
    users_count = serializers.SerializerMethodField()
    parent_name = serializers.CharField(source='parent.display_name', read_only=True)
    children = serializers.SerializerMethodField()
    
    class Meta:
        model = Role
        fields = [
            'id', 'name', 'display_name', 'description', 'is_system',
            'parent', 'parent_name', 'level', 'permissions', 'permission_ids',
            'users_count', 'children', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'level', 'created_at', 'updated_at']

    def get_users_count(self, obj):
        """Nombre d'utilisateurs ayant ce rôle"""
        return obj.role_users.filter(is_active=True).count()

    def get_children(self, obj):
        """Rôles enfants"""
        children = obj.children.all()
        return RoleSerializer(children, many=True, context=self.context).data

    def create(self, validated_data):
        permission_ids = validated_data.pop('permission_ids', [])
        role = Role.objects.create(**validated_data)
        
        # Assigner les permissions
        if permission_ids:
            permissions = Permission.objects.filter(id__in=permission_ids)
            for permission in permissions:
                RolePermission.objects.create(
                    role=role,
                    permission=permission,
                    granted_by=self.context['request'].user
                )
        
        return role

    def update(self, instance, validated_data):
        permission_ids = validated_data.pop('permission_ids', None)
        
        # Mettre à jour les champs du rôle
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Mettre à jour les permissions si spécifiées
        if permission_ids is not None:
            # Supprimer les anciennes permissions
            instance.role_permissions.all().delete()
            
            # Ajouter les nouvelles permissions
            permissions = Permission.objects.filter(id__in=permission_ids)
            for permission in permissions:
                RolePermission.objects.create(
                    role=instance,
                    permission=permission,
                    granted_by=self.context['request'].user
                )
        
        return instance

class UserRoleSerializer(serializers.ModelSerializer):
    """Serializer pour l'association utilisateur-rôle"""
    role_name = serializers.CharField(source='role.display_name', read_only=True)
    user_name = serializers.CharField(source='user.username', read_only=True)
    assigned_by_name = serializers.CharField(source='assigned_by.username', read_only=True)
    is_expired = serializers.SerializerMethodField()
    
    class Meta:
        model = UserRole
        fields = [
            'id', 'user', 'user_name', 'role', 'role_name',
            'assigned_at', 'assigned_by', 'assigned_by_name',
            'expires_at', 'is_active', 'is_expired'
        ]
        read_only_fields = ['id', 'assigned_at', 'assigned_by']

    def get_is_expired(self, obj):
        """Vérifie si le rôle a expiré"""
        return obj.is_expired()

    def create(self, validated_data):
        validated_data['assigned_by'] = self.context['request'].user
        user_role = UserRole.objects.create(**validated_data)
        
        # Invalider le cache de permissions de l'utilisateur
        PermissionCache.objects.filter(user=user_role.user).delete()
        
        return user_role

    def update(self, instance, validated_data):
        old_user = instance.user
        super().update(instance, validated_data)
        
        # Invalider le cache de permissions si l'utilisateur a changé
        if old_user != instance.user:
            PermissionCache.objects.filter(user__in=[old_user, instance.user]).delete()
        else:
            PermissionCache.objects.filter(user=instance.user).delete()
        
        return instance

class UserWithRolesSerializer(serializers.ModelSerializer):
    """Serializer pour les utilisateurs avec leurs rôles"""
    roles = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField()
    active_roles_count = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'user_type', 'is_active', 'last_login', 'date_joined',
            'roles', 'permissions', 'active_roles_count'
        ]
        read_only_fields = ['id', 'last_login', 'date_joined']

    def get_roles(self, obj):
        """Rôles actifs de l'utilisateur"""
        active_roles = obj.user_roles.filter(is_active=True)
        return UserRoleSerializer(active_roles, many=True).data

    def get_permissions(self, obj):
        """Permissions de l'utilisateur"""
        from .permissions import get_user_permissions
        return get_user_permissions(obj)

    def get_active_roles_count(self, obj):
        """Nombre de rôles actifs"""
        return obj.user_roles.filter(is_active=True).count()

class RoleAssignmentSerializer(serializers.Serializer):
    """Serializer pour assigner/révoquer des rôles"""
    user_id = serializers.UUIDField()
    role_id = serializers.UUIDField()
    expires_at = serializers.DateTimeField(required=False, allow_null=True)
    action = serializers.ChoiceField(choices=['assign', 'revoke'])

    def validate(self, data):
        """Validation des données"""
        try:
            user = User.objects.get(id=data['user_id'])
            role = Role.objects.get(id=data['role_id'])
        except User.DoesNotExist:
            raise serializers.ValidationError("Utilisateur introuvable")
        except Role.DoesNotExist:
            raise serializers.ValidationError("Rôle introuvable")

        data['user'] = user
        data['role'] = role
        return data

    def save(self):
        """Exécuter l'action d'assignation/révocation"""
        user = self.validated_data['user']
        role = self.validated_data['role']
        action = self.validated_data['action']
        expires_at = self.validated_data.get('expires_at')

        if action == 'assign':
            user_role, created = UserRole.objects.get_or_create(
                user=user,
                role=role,
                defaults={
                    'assigned_by': self.context['request'].user,
                    'expires_at': expires_at,
                    'is_active': True
                }
            )
            if not created:
                user_role.is_active = True
                user_role.expires_at = expires_at
                user_role.save()
        
        elif action == 'revoke':
            UserRole.objects.filter(user=user, role=role).update(is_active=False)

        # Invalider le cache de permissions
        PermissionCache.objects.filter(user=user).delete()
        
        return user_role if action == 'assign' else None

class PermissionCacheSerializer(serializers.ModelSerializer):
    """Serializer pour le cache de permissions"""
    user_name = serializers.CharField(source='user.username', read_only=True)
    permissions_count = serializers.SerializerMethodField()
    
    class Meta:
        model = PermissionCache
        fields = ['user', 'user_name', 'permissions', 'permissions_count', 'last_updated']
        read_only_fields = ['last_updated']

    def get_permissions_count(self, obj):
        """Nombre de permissions en cache"""
        return len(obj.permissions)

class RoleHierarchySerializer(serializers.ModelSerializer):
    """Serializer pour la hiérarchie des rôles"""
    children = serializers.SerializerMethodField()
    permissions_count = serializers.SerializerMethodField()
    users_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Role
        fields = [
            'id', 'name', 'display_name', 'description', 'level',
            'children', 'permissions_count', 'users_count'
        ]

    def get_children(self, obj):
        """Rôles enfants récursifs"""
        children = obj.children.all()
        return RoleHierarchySerializer(children, many=True).data

    def get_permissions_count(self, obj):
        """Nombre de permissions du rôle"""
        return obj.permissions.count()

    def get_users_count(self, obj):
        """Nombre d'utilisateurs avec ce rôle"""
        return obj.role_users.filter(is_active=True).count()

class BulkRoleAssignmentSerializer(serializers.Serializer):
    """Serializer pour l'assignation en masse de rôles"""
    user_ids = serializers.ListField(child=serializers.UUIDField())
    role_ids = serializers.ListField(child=serializers.UUIDField())
    expires_at = serializers.DateTimeField(required=False, allow_null=True)
    action = serializers.ChoiceField(choices=['assign', 'revoke'])

    def validate(self, data):
        """Validation des données en masse"""
        users = User.objects.filter(id__in=data['user_ids'])
        roles = Role.objects.filter(id__in=data['role_ids'])
        
        if users.count() != len(data['user_ids']):
            raise serializers.ValidationError("Certains utilisateurs sont introuvables")
        
        if roles.count() != len(data['role_ids']):
            raise serializers.ValidationError("Certains rôles sont introuvables")

        data['users'] = users
        data['roles'] = roles
        return data

    def save(self):
        """Exécuter l'assignation/révocation en masse"""
        users = self.validated_data['users']
        roles = self.validated_data['roles']
        action = self.validated_data['action']
        expires_at = self.validated_data.get('expires_at')
        assigned_by = self.context['request'].user

        results = []
        
        for user in users:
            for role in roles:
                if action == 'assign':
                    user_role, created = UserRole.objects.get_or_create(
                        user=user,
                        role=role,
                        defaults={
                            'assigned_by': assigned_by,
                            'expires_at': expires_at,
                            'is_active': True
                        }
                    )
                    if not created:
                        user_role.is_active = True
                        user_role.expires_at = expires_at
                        user_role.save()
                    results.append(user_role)
                
                elif action == 'revoke':
                    UserRole.objects.filter(user=user, role=role).update(is_active=False)

        # Invalider les caches de permissions
        PermissionCache.objects.filter(user__in=users).delete()
        
        return results
