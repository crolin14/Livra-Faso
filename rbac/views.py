from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.db.models import Q, Count
from django.utils import timezone
from .models import Role, Permission, RolePermission, UserRole, PermissionCache
from .serializers import (
    RoleSerializer, PermissionSerializer, UserRoleSerializer,
    UserWithRolesSerializer, RoleAssignmentSerializer,
    PermissionCacheSerializer, RoleHierarchySerializer,
    BulkRoleAssignmentSerializer
)
from .permissions import (
    api_require_permission, PermissionManager,
    has_permission, has_module_access
)
from utils.pagination import StandardResultsSetPagination
from utils.filters import SearchFilter, DateRangeFilter

User = get_user_model()

class RoleViewSet(viewsets.ModelViewSet):
    """ViewSet pour la gestion des rôles"""
    queryset = Role.objects.all().order_by('level', 'name')
    serializer_class = RoleSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [SearchFilter]
    search_fields = ['name', 'display_name', 'description']

    def get_permissions(self):
        """Permissions requises selon l'action"""
        permission_classes = [permissions.IsAuthenticated]
        
        if self.action in ['list', 'retrieve']:
            self.required_permission = 'roles.view'
        elif self.action == 'create':
            self.required_permission = 'roles.create'
        elif self.action in ['update', 'partial_update']:
            self.required_permission = 'roles.edit'
        elif self.action == 'destroy':
            self.required_permission = 'roles.delete'
        
        return [permission() for permission in permission_classes]

    @api_require_permission('roles.view')
    def list(self, request):
        """Liste des rôles avec filtres"""
        queryset = self.get_queryset()
        
        # Filtres
        if request.GET.get('is_system'):
            is_system = request.GET.get('is_system').lower() == 'true'
            queryset = queryset.filter(is_system=is_system)
        
        if request.GET.get('parent_id'):
            queryset = queryset.filter(parent_id=request.GET.get('parent_id'))
        
        if request.GET.get('level'):
            queryset = queryset.filter(level=request.GET.get('level'))

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @api_require_permission('roles.create')
    def create(self, request):
        """Créer un nouveau rôle"""
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            role = serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @api_require_permission('roles.edit')
    def update(self, request, pk=None):
        """Modifier un rôle"""
        role = self.get_object()
        
        if role.is_system and not request.user.is_superuser:
            return Response(
                {'error': 'Les rôles système ne peuvent pas être modifiés'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = self.get_serializer(role, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @api_require_permission('roles.delete')
    def destroy(self, request, pk=None):
        """Supprimer un rôle"""
        role = self.get_object()
        
        if role.is_system:
            return Response(
                {'error': 'Les rôles système ne peuvent pas être supprimés'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if role.role_users.filter(is_active=True).exists():
            return Response(
                {'error': 'Ce rôle est encore assigné à des utilisateurs'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        role.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'])
    @api_require_permission('roles.view')
    def hierarchy(self, request):
        """Hiérarchie des rôles"""
        root_roles = Role.objects.filter(parent=None).order_by('name')
        serializer = RoleHierarchySerializer(root_roles, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    @api_require_permission('roles.view')
    def users(self, request, pk=None):
        """Utilisateurs ayant ce rôle"""
        role = self.get_object()
        user_roles = role.role_users.filter(is_active=True)
        
        # Pagination
        page = self.paginate_queryset(user_roles)
        if page is not None:
            serializer = UserRoleSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = UserRoleSerializer(user_roles, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    @api_require_permission('roles.assign')
    def clone(self, request, pk=None):
        """Cloner un rôle avec ses permissions"""
        original_role = self.get_object()
        
        data = request.data.copy()
        data['name'] = f"{original_role.name}_copy"
        data['display_name'] = f"{original_role.display_name} (Copie)"
        
        # Récupérer les IDs des permissions
        permission_ids = [str(perm.id) for perm in original_role.permissions.all()]
        data['permission_ids'] = permission_ids
        
        serializer = self.get_serializer(data=data)
        if serializer.is_valid():
            new_role = serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class PermissionViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet pour les permissions (lecture seule)"""
    queryset = Permission.objects.all().order_by('module', 'name')
    serializer_class = PermissionSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [SearchFilter]
    search_fields = ['name', 'codename', 'module']

    @api_require_permission('roles.view')
    def list(self, request):
        """Liste des permissions avec filtres"""
        queryset = self.get_queryset()
        
        if request.GET.get('module'):
            queryset = queryset.filter(module=request.GET.get('module'))
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    @api_require_permission('roles.view')
    def by_module(self, request):
        """Permissions groupées par module"""
        permissions = Permission.objects.all().order_by('module', 'name')
        grouped = {}
        
        for perm in permissions:
            if perm.module not in grouped:
                grouped[perm.module] = []
            grouped[perm.module].append(PermissionSerializer(perm).data)
        
        return Response(grouped)

    @action(detail=False, methods=['post'])
    @api_require_permission('settings.edit')
    def sync(self, request):
        """Synchroniser les permissions avec le code"""
        PermissionManager.sync_permissions()
        return Response({'message': 'Permissions synchronisées avec succès'})

class UserRoleViewSet(viewsets.ModelViewSet):
    """ViewSet pour la gestion des rôles utilisateurs"""
    queryset = UserRole.objects.all().order_by('-assigned_at')
    serializer_class = UserRoleSerializer
    pagination_class = StandardResultsSetPagination

    @api_require_permission('roles.assign')
    def list(self, request):
        """Liste des assignations de rôles"""
        queryset = self.get_queryset()
        
        # Filtres
        if request.GET.get('user_id'):
            queryset = queryset.filter(user_id=request.GET.get('user_id'))
        
        if request.GET.get('role_id'):
            queryset = queryset.filter(role_id=request.GET.get('role_id'))
        
        if request.GET.get('is_active'):
            is_active = request.GET.get('is_active').lower() == 'true'
            queryset = queryset.filter(is_active=is_active)
        
        if request.GET.get('expired'):
            expired = request.GET.get('expired').lower() == 'true'
            if expired:
                queryset = queryset.filter(
                    expires_at__lt=timezone.now()
                ).exclude(expires_at=None)
            else:
                queryset = queryset.filter(
                    Q(expires_at__gte=timezone.now()) | Q(expires_at=None)
                )

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    @api_require_permission('roles.assign')
    def assign_role(self, request):
        """Assigner un rôle à un utilisateur"""
        serializer = RoleAssignmentSerializer(
            data=request.data,
            context={'request': request}
        )
        if serializer.is_valid():
            user_role = serializer.save()
            if user_role:
                return Response(
                    UserRoleSerializer(user_role).data,
                    status=status.HTTP_201_CREATED
                )
            return Response({'message': 'Rôle révoqué avec succès'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    @api_require_permission('roles.assign')
    def bulk_assign(self, request):
        """Assignation en masse de rôles"""
        serializer = BulkRoleAssignmentSerializer(
            data=request.data,
            context={'request': request}
        )
        if serializer.is_valid():
            results = serializer.save()
            return Response({
                'message': f'{len(results)} assignations effectuées',
                'count': len(results)
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserPermissionViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet pour les permissions utilisateurs"""
    queryset = User.objects.all()
    serializer_class = UserWithRolesSerializer
    pagination_class = StandardResultsSetPagination

    @api_require_permission('users.view')
    def list(self, request):
        """Liste des utilisateurs avec leurs permissions"""
        queryset = self.get_queryset()
        
        # Filtres
        if request.GET.get('user_type'):
            queryset = queryset.filter(user_type=request.GET.get('user_type'))
        
        if request.GET.get('has_role'):
            role_name = request.GET.get('has_role')
            queryset = queryset.filter(
                user_roles__role__name=role_name,
                user_roles__is_active=True
            )

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    @api_require_permission('users.view')
    def permissions(self, request, pk=None):
        """Permissions détaillées d'un utilisateur"""
        user = self.get_object()
        
        from .permissions import get_user_permissions, get_user_modules
        
        permissions = get_user_permissions(user)
        modules = get_user_modules(user)
        
        return Response({
            'user': user.username,
            'permissions': permissions,
            'modules': modules,
            'is_superuser': user.is_superuser
        })

    @action(detail=True, methods=['post'])
    @api_require_permission('users.edit')
    def refresh_cache(self, request, pk=None):
        """Actualiser le cache de permissions d'un utilisateur"""
        user = self.get_object()
        
        cache, created = PermissionCache.objects.get_or_create(user=user)
        permissions = cache.refresh_cache()
        
        return Response({
            'message': 'Cache actualisé',
            'permissions_count': len(permissions),
            'last_updated': cache.last_updated
        })

    @action(detail=False, methods=['post'])
    @api_require_permission('users.edit')
    def refresh_all_caches(self, request):
        """Actualiser tous les caches de permissions"""
        caches = PermissionCache.objects.all()
        updated_count = 0
        
        for cache in caches:
            cache.refresh_cache()
            updated_count += 1
        
        return Response({
            'message': f'{updated_count} caches actualisés'
        })

    @action(detail=True, methods=['post'])
    @api_require_permission('users.view')
    def check_permission(self, request, pk=None):
        """Vérifier si un utilisateur a une permission"""
        user = self.get_object()
        permission_codename = request.data.get('permission')
        
        if not permission_codename:
            return Response(
                {'error': 'Permission codename required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        has_perm = has_permission(user, permission_codename)
        
        return Response({
            'user': user.username,
            'permission': permission_codename,
            'has_permission': has_perm
        })

    @action(detail=True, methods=['post'])
    @api_require_permission('users.view')
    def check_module_access(self, request, pk=None):
        """Vérifier l'accès d'un utilisateur à un module"""
        user = self.get_object()
        module_name = request.data.get('module')
        
        if not module_name:
            return Response(
                {'error': 'Module name required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        has_access = has_module_access(user, module_name)
        
        return Response({
            'user': user.username,
            'module': module_name,
            'has_access': has_access
        })

class PermissionCacheViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet pour le cache de permissions"""
    queryset = PermissionCache.objects.all().order_by('-last_updated')
    serializer_class = PermissionCacheSerializer
    pagination_class = StandardResultsSetPagination

    @api_require_permission('audit.view')
    def list(self, request):
        """Liste des caches de permissions"""
        queryset = self.get_queryset()
        
        if request.GET.get('user_id'):
            queryset = queryset.filter(user_id=request.GET.get('user_id'))

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    @api_require_permission('audit.view')
    def stats(self, request):
        """Statistiques des caches de permissions"""
        total_caches = PermissionCache.objects.count()
        avg_permissions = PermissionCache.objects.aggregate(
            avg_perms=Count('permissions')
        )['avg_perms'] or 0
        
        return Response({
            'total_caches': total_caches,
            'average_permissions_per_user': round(avg_permissions, 2),
            'last_refresh': PermissionCache.objects.first().last_updated if total_caches > 0 else None
        })
