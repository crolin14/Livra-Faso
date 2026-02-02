"""
Commande personnalisée pour nettoyer les sessions expirées et orphelines
"""
from django.core.management.base import BaseCommand
from django.contrib.sessions.models import Session
from django.utils import timezone
from django.contrib.auth import get_user_model
import logging

logger = logging.getLogger(__name__)
User = get_user_model()

class Command(BaseCommand):
    help = 'Nettoie les sessions expirées et orphelines'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Affiche ce qui serait supprimé sans effectuer la suppression',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Affichage détaillé des opérations',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        verbose = options['verbose']
        
        self.stdout.write(self.style.SUCCESS('=== Nettoyage des sessions ==='))
        
        # Compter les sessions avant nettoyage
        total_sessions_before = Session.objects.count()
        expired_sessions = Session.objects.filter(expire_date__lt=timezone.now())
        expired_count = expired_sessions.count()
        
        if verbose:
            self.stdout.write(f'Sessions totales: {total_sessions_before}')
            self.stdout.write(f'Sessions expirées: {expired_count}')
        
        if dry_run:
            self.stdout.write(self.style.WARNING(f'[DRY RUN] {expired_count} sessions seraient supprimées'))
        else:
            # Supprimer les sessions expirées
            deleted_count = expired_sessions.delete()[0]
            self.stdout.write(self.style.SUCCESS(f'✅ {deleted_count} sessions expirées supprimées'))
            
            # Vérifier les sessions orphelines (utilisateurs supprimés)
            orphaned_count = 0
            for session in Session.objects.all():
                try:
                    session_data = session.get_decoded()
                    user_id = session_data.get('_auth_user_id')
                    if user_id:
                        try:
                            User.objects.get(pk=user_id)
                        except User.DoesNotExist:
                            if verbose:
                                self.stdout.write(f'Session orpheline détectée: {session.session_key}')
                            session.delete()
                            orphaned_count += 1
                except Exception as e:
                    if verbose:
                        self.stdout.write(f'Erreur lors du décodage de session: {e}')
                    session.delete()
                    orphaned_count += 1
            
            if orphaned_count > 0:
                self.stdout.write(self.style.SUCCESS(f'✅ {orphaned_count} sessions orphelines supprimées'))
            
            # Statistiques finales
            total_sessions_after = Session.objects.count()
            total_cleaned = total_sessions_before - total_sessions_after
            
            self.stdout.write(self.style.SUCCESS(f'=== Nettoyage terminé ==='))
            self.stdout.write(f'Sessions avant: {total_sessions_before}')
            self.stdout.write(f'Sessions après: {total_sessions_after}')
            self.stdout.write(f'Total nettoyé: {total_cleaned}')
            
            logger.info(f'Nettoyage des sessions terminé: {total_cleaned} sessions supprimées')
