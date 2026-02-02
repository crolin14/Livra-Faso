from django.core.management.base import BaseCommand
from django.utils import timezone
from subscriptions.models import SubscriptionPlan
from ratings.models import RatingCategory
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Créer des données d\'exemple pour Livraison Faso'

    def handle(self, *args, **options):
        self.stdout.write('Création des données d\'exemple...')
        
        # Créer des plans d'abonnement
        plans_data = [
            {
                'name': 'Plan Basique',
                'plan_type': 'basic',
                'description': 'Idéal pour les petites entreprises. Inclut 10 missions par mois.',
                'price': 5000.00,
                'duration_days': 30,
                'max_missions_per_month': 10,
                'priority_support': False,
                'advanced_analytics': False,
                'custom_branding': False,
            },
            {
                'name': 'Plan Premium',
                'plan_type': 'premium',
                'description': 'Pour les entreprises en croissance. Inclut 50 missions par mois et support prioritaire.',
                'price': 15000.00,
                'duration_days': 30,
                'max_missions_per_month': 50,
                'priority_support': True,
                'advanced_analytics': True,
                'custom_branding': False,
            },
            {
                'name': 'Plan Entreprise',
                'plan_type': 'enterprise',
                'description': 'Solution complète pour les grandes entreprises. Missions illimitées et personnalisation.',
                'price': 50000.00,
                'duration_days': 30,
                'max_missions_per_month': 999,
                'priority_support': True,
                'advanced_analytics': True,
                'custom_branding': True,
            },
        ]
        
        for plan_data in plans_data:
            plan, created = SubscriptionPlan.objects.get_or_create(
                name=plan_data['name'],
                defaults=plan_data
            )
            if created:
                self.stdout.write(f'Plan créé: {plan.name}')
            else:
                self.stdout.write(f'Plan existant: {plan.name}')
        
        # Créer des catégories d'évaluation
        categories_data = [
            {
                'name': 'Ponctualité',
                'description': 'Respect des délais de livraison',
            },
            {
                'name': 'Qualité du service',
                'description': 'Professionnalisme et courtoisie',
            },
            {
                'name': 'État du colis',
                'description': 'Intégrité des marchandises livrées',
            },
            {
                'name': 'Communication',
                'description': 'Clarté et rapidité des communications',
            },
            {
                'name': 'Prix',
                'description': 'Rapport qualité-prix du service',
            },
        ]
        
        for cat_data in categories_data:
            category, created = RatingCategory.objects.get_or_create(
                name=cat_data['name'],
                defaults=cat_data
            )
            if created:
                self.stdout.write(f'Catégorie créée: {category.name}')
            else:
                self.stdout.write(f'Catégorie existante: {category.name}')
        
        self.stdout.write(
            self.style.SUCCESS('Données d\'exemple créées avec succès !')
        ) 