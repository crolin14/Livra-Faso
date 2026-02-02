from django.core.management.base import BaseCommand
from django.utils import timezone
from audit.services import AuditService
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Collecte les métriques système pour le monitoring'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--interval',
            type=int,
            default=300,
            help='Intervalle en secondes entre les collectes (défaut: 300s)'
        )
        parser.add_argument(
            '--continuous',
            action='store_true',
            help='Collecte continue des métriques'
        )
    
    def handle(self, *args, **options):
        interval = options['interval']
        continuous = options['continuous']
        
        self.stdout.write(
            self.style.SUCCESS(f'Démarrage de la collecte de métriques (intervalle: {interval}s)')
        )
        
        if continuous:
            import time
            while True:
                try:
                    metrics = AuditService.collect_system_metrics()
                    if metrics:
                        self.stdout.write(
                            f'{timezone.now()}: Métriques collectées - Status: {metrics.system_status}'
                        )
                    else:
                        self.stdout.write(
                            self.style.ERROR(f'{timezone.now()}: Erreur lors de la collecte')
                        )
                    
                    time.sleep(interval)
                    
                except KeyboardInterrupt:
                    self.stdout.write(
                        self.style.SUCCESS('\nArrêt de la collecte de métriques')
                    )
                    break
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'Erreur: {e}')
                    )
                    time.sleep(interval)
        else:
            # Collecte unique
            metrics = AuditService.collect_system_metrics()
            if metrics:
                self.stdout.write(
                    self.style.SUCCESS(f'Métriques collectées - Status: {metrics.system_status}')
                )
            else:
                self.stdout.write(
                    self.style.ERROR('Erreur lors de la collecte des métriques')
                )
