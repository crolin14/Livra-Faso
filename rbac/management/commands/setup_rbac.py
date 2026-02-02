from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from rbac.models import Role, Permission, RolePermission

User = get_user_model()

class Command(BaseCommand):
    help = 'Configure le système RBAC avec les 7 rôles et permissions par défaut'

    def handle(self, *args, **options):
        self.stdout.write('Configuration du système RBAC...')
        
        # Créer les permissions
        self.create_permissions()
        
        # Créer les rôles avec hiérarchie
        self.create_roles()
        
        # Assigner les permissions aux rôles
        self.assign_permissions()
        
        self.stdout.write(
            self.style.SUCCESS('Système RBAC configuré avec succès!')
        )

    def create_permissions(self):
        """Créer toutes les permissions du système"""
        permissions_data = [
            # Permissions Admin Dashboard
            ('admin.view_dashboard', 'admin', 'Voir le dashboard admin'),
            ('admin.manage_users', 'admin', 'Gérer les utilisateurs'),
            ('admin.manage_missions', 'admin', 'Gérer les missions'),
            ('admin.view_reports', 'admin', 'Voir les rapports'),
            ('admin.system_config', 'admin', 'Configuration système'),
            ('admin.security_logs', 'admin', 'Logs de sécurité'),
            ('admin.export_data', 'admin', 'Exporter les données'),
            
            # Permissions Missions
            ('missions.create', 'missions', 'Créer une mission'),
            ('missions.view_own', 'missions', 'Voir ses propres missions'),
            ('missions.view_all', 'missions', 'Voir toutes les missions'),
            ('missions.edit_own', 'missions', 'Modifier ses missions'),
            ('missions.edit_all', 'missions', 'Modifier toutes les missions'),
            ('missions.delete_own', 'missions', 'Supprimer ses missions'),
            ('missions.delete_all', 'missions', 'Supprimer toutes les missions'),
            ('missions.assign_livreur', 'missions', 'Assigner un livreur'),
            ('missions.accept', 'missions', 'Accepter une mission'),
            ('missions.complete', 'missions', 'Compléter une mission'),
            ('missions.cancel', 'missions', 'Annuler une mission'),
            
            # Permissions Utilisateurs
            ('users.view_profile', 'users', 'Voir son profil'),
            ('users.edit_profile', 'users', 'Modifier son profil'),
            ('users.view_all_profiles', 'users', 'Voir tous les profils'),
            ('users.edit_all_profiles', 'users', 'Modifier tous les profils'),
            ('users.delete_users', 'users', 'Supprimer des utilisateurs'),
            ('users.manage_roles', 'users', 'Gérer les rôles'),
            
            # Permissions Paiements
            ('payments.view_own', 'payments', 'Voir ses paiements'),
            ('payments.view_all', 'payments', 'Voir tous les paiements'),
            ('payments.process', 'payments', 'Traiter les paiements'),
            ('payments.refund', 'payments', 'Effectuer des remboursements'),
            
            # Permissions Entreprise
            ('enterprise.manage_team', 'enterprise', 'Gérer son équipe'),
            ('enterprise.view_analytics', 'enterprise', 'Voir les analytics'),
            ('enterprise.manage_subscription', 'enterprise', 'Gérer l\'abonnement'),
            ('enterprise.bulk_missions', 'enterprise', 'Missions en lot'),
            
            # Permissions Chat
            ('chat.send_message', 'chat', 'Envoyer des messages'),
            ('chat.view_conversations', 'chat', 'Voir les conversations'),
            ('chat.moderate', 'chat', 'Modérer les conversations'),
            
            # Permissions Notifications
            ('notifications.send', 'notifications', 'Envoyer des notifications'),
            ('notifications.broadcast', 'notifications', 'Diffusion générale'),
            
            # Permissions Support
            ('support.create_ticket', 'support', 'Créer un ticket'),
            ('support.view_tickets', 'support', 'Voir les tickets'),
            ('support.manage_tickets', 'support', 'Gérer les tickets'),
            
            # Permissions Ratings
            ('ratings.give', 'ratings', 'Donner une note'),
            ('ratings.view', 'ratings', 'Voir les notes'),
            ('ratings.moderate', 'ratings', 'Modérer les notes'),
        ]
        
        for codename, module, name in permissions_data:
            permission, created = Permission.objects.get_or_create(
                codename=codename,
                defaults={
                    'name': name,
                    'module': module,
                    'description': f'Permission pour {name.lower()}'
                }
            )
            if created:
                self.stdout.write(f'  Permission créée: {codename}')

    def create_roles(self):
        """Créer les 7 rôles avec hiérarchie"""
        roles_data = [
            # Niveau 0 - Super Admin
            ('super_admin', 'Super Administrateur', 'Accès complet au système', None, 0, True),
            
            # Niveau 1 - Admin
            ('admin', 'Administrateur', 'Administration générale', 'super_admin', 1, True),
            
            # Niveau 2 - Gestionnaires
            ('manager', 'Gestionnaire', 'Gestion opérationnelle', 'admin', 2, True),
            ('support_manager', 'Gestionnaire Support', 'Gestion du support client', 'admin', 2, True),
            
            # Niveau 3 - Utilisateurs métier
            ('enterprise', 'Entreprise', 'Compte entreprise avec équipe', None, 3, True),
            ('livreur', 'Livreur', 'Livreur professionnel', None, 3, True),
            ('client', 'Client', 'Client standard', None, 3, True),
        ]
        
        created_roles = {}
        
        for name, display_name, description, parent_name, level, is_system in roles_data:
            parent = created_roles.get(parent_name) if parent_name else None
            
            role, created = Role.objects.get_or_create(
                name=name,
                defaults={
                    'display_name': display_name,
                    'description': description,
                    'parent': parent,
                    'level': level,
                    'is_system': is_system
                }
            )
            created_roles[name] = role
            
            if created:
                self.stdout.write(f'  Rôle créé: {display_name} (niveau {level})')

    def assign_permissions(self):
        """Assigner les permissions aux rôles"""
        role_permissions = {
            'super_admin': [
                # Toutes les permissions (héritage)
            ],
            'admin': [
                'admin.view_dashboard', 'admin.manage_users', 'admin.manage_missions',
                'admin.view_reports', 'admin.system_config', 'admin.security_logs',
                'admin.export_data', 'missions.view_all', 'missions.edit_all',
                'missions.delete_all', 'missions.assign_livreur', 'missions.cancel',
                'users.view_all_profiles', 'users.edit_all_profiles', 'users.delete_users',
                'users.manage_roles', 'payments.view_all', 'payments.process',
                'payments.refund', 'chat.moderate', 'notifications.broadcast',
                'support.manage_tickets', 'ratings.moderate'
            ],
            'manager': [
                'missions.view_all', 'missions.edit_all', 'missions.assign_livreur',
                'users.view_all_profiles', 'payments.view_all', 'support.manage_tickets',
                'chat.moderate', 'notifications.send', 'ratings.view'
            ],
            'support_manager': [
                'support.manage_tickets', 'support.view_tickets', 'chat.moderate',
                'users.view_all_profiles', 'notifications.send'
            ],
            'enterprise': [
                'missions.create', 'missions.view_own', 'missions.edit_own',
                'missions.delete_own', 'enterprise.manage_team', 'enterprise.view_analytics',
                'enterprise.manage_subscription', 'enterprise.bulk_missions',
                'users.view_profile', 'users.edit_profile', 'payments.view_own',
                'chat.send_message', 'chat.view_conversations', 'support.create_ticket',
                'ratings.give', 'ratings.view'
            ],
            'livreur': [
                'missions.view_all', 'missions.accept', 'missions.complete',
                'users.view_profile', 'users.edit_profile', 'payments.view_own',
                'chat.send_message', 'chat.view_conversations', 'support.create_ticket',
                'ratings.give', 'ratings.view'
            ],
            'client': [
                'missions.create', 'missions.view_own', 'missions.edit_own',
                'missions.cancel', 'users.view_profile', 'users.edit_profile',
                'payments.view_own', 'chat.send_message', 'chat.view_conversations',
                'support.create_ticket', 'ratings.give', 'ratings.view'
            ]
        }
        
        for role_name, permission_codenames in role_permissions.items():
            try:
                role = Role.objects.get(name=role_name)
                
                for codename in permission_codenames:
                    try:
                        permission = Permission.objects.get(codename=codename)
                        role_permission, created = RolePermission.objects.get_or_create(
                            role=role,
                            permission=permission
                        )
                        if created:
                            self.stdout.write(f'    {role_name} -> {codename}')
                    except Permission.DoesNotExist:
                        self.stdout.write(
                            self.style.WARNING(f'Permission {codename} non trouvée')
                        )
                        
            except Role.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Rôle {role_name} non trouvé')
                )

        # Super Admin hérite de toutes les permissions
        super_admin = Role.objects.get(name='super_admin')
        all_permissions = Permission.objects.all()
        
        for permission in all_permissions:
            RolePermission.objects.get_or_create(
                role=super_admin,
                permission=permission
            )
        
        self.stdout.write('  Super Admin: toutes les permissions assignées')
