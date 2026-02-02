from django.core.management.base import BaseCommand
from subscriptions.models import SubscriptionPlan

class Command(BaseCommand):
    help = 'Crée les plans d\'abonnement de base pour LivraFaso'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🎯 CRÉATION DES PLANS D\'ABONNEMENT LIVRAFASO'))
        self.stdout.write('=' * 60)
        
        # Supprimer les plans existants
        SubscriptionPlan.objects.all().delete()
        self.stdout.write(self.style.SUCCESS('✅ Plans existants supprimés'))
        
        # Plan Basic
        basic_plan = SubscriptionPlan.objects.create(
            name="Basic",
            plan_type="basic",
            price=10000.00,
            duration=30,
            features="Livraison standard,Support par email,Suivi des missions,Interface simple",
            max_missions_per_month=20,
            priority_support=False,
            advanced_analytics=False,
            multi_user_management=False,
            is_active=True
        )
        self.stdout.write(self.style.SUCCESS('✅ Plan Basic créé: 10 000 FCFA/mois'))
        
        # Plan Premium
        premium_plan = SubscriptionPlan.objects.create(
            name="Premium",
            plan_type="premium",
            price=20000.00,
            duration=30,
            features="Livraison prioritaire,Support 24h/7j,Suivi temps réel,Analytics de base,Notifications SMS",
            max_missions_per_month=100,
            priority_support=True,
            advanced_analytics=False,
            multi_user_management=False,
            is_active=True
        )
        self.stdout.write(self.style.SUCCESS('✅ Plan Premium créé: 20 000 FCFA/mois'))
        
        # Plan Pro
        pro_plan = SubscriptionPlan.objects.create(
            name="Pro",
            plan_type="pro",
            price=50000.00,
            duration=30,
            features="Tout illimité,Support dédié,Analytics avancées,API access,Gestion équipe,Rapports personnalisés",
            max_missions_per_month=999,
            priority_support=True,
            advanced_analytics=True,
            multi_user_management=True,
            is_active=True
        )
        self.stdout.write(self.style.SUCCESS('✅ Plan Pro créé: 50 000 FCFA/mois'))
        
        total_plans = SubscriptionPlan.objects.count()
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('🎉 PLANS D\'ABONNEMENT CRÉÉS AVEC SUCCÈS'))
        self.stdout.write('=' * 60)
        self.stdout.write(f'\n📊 Total plans créés: {total_plans}')
        self.stdout.write('\n💰 TARIFICATION:')
        self.stdout.write('• Basic: 10 000 FCFA/mois (20 missions)')
        self.stdout.write('• Premium: 20 000 FCFA/mois (100 missions)')
        self.stdout.write('• Pro: 50 000 FCFA/mois (illimité)')
