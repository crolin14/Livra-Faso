"""
Services d'analytics et tableaux de bord pour LivraFaso
Génère les métriques et statistiques pour entreprises
"""
import logging
from datetime import datetime, timedelta
from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone
from django.contrib.auth import get_user_model
from missions.models import Mission
from ratings.models import Rating

User = get_user_model()
logger = logging.getLogger(__name__)

class AnalyticsService:
    """Service principal d'analytics"""
    
    def get_enterprise_dashboard_data(self, user, period='month'):
        """
        Génère les données du tableau de bord entreprise
        
        Args:
            user: Utilisateur entreprise
            period: 'day', 'week', 'month', 'year'
        """
        end_date = timezone.now()
        start_date = self._get_period_start_date(end_date, period)
        
        # Missions de la période
        missions = Mission.objects.filter(
            client=user,
            created_at__range=[start_date, end_date]
        )
        
        # Statistiques générales
        stats = {
            'total_missions': missions.count(),
            'completed_missions': missions.filter(status='livree').count(),
            'pending_missions': missions.filter(status__in=['en_attente', 'acceptee', 'en_cours']).count(),
            'cancelled_missions': missions.filter(status='annulee').count(),
            'total_amount': missions.aggregate(total=Sum('price'))['total'] or 0,
            'average_rating': self._get_average_rating(user, start_date, end_date),
            'success_rate': self._calculate_success_rate(missions),
        }
        
        # Données pour graphiques
        charts_data = {
            'missions_by_day': self._get_missions_by_day(missions, start_date, end_date),
            'missions_by_status': self._get_missions_by_status(missions),
            'revenue_by_day': self._get_revenue_by_day(missions, start_date, end_date),
            'top_routes': self._get_top_routes(missions),
            'delivery_times': self._get_delivery_time_stats(missions),
        }
        
        # Comparaison période précédente
        previous_period_stats = self._get_previous_period_comparison(user, start_date, end_date, period)
        
        return {
            'period': period,
            'stats': stats,
            'charts': charts_data,
            'comparison': previous_period_stats,
            'subscription_info': self._get_subscription_info(user),
        }
    
    def get_livreur_dashboard_data(self, user, period='month'):
        """
        Génère les données du tableau de bord livreur
        """
        end_date = timezone.now()
        start_date = self._get_period_start_date(end_date, period)
        
        # Missions du livreur
        missions = Mission.objects.filter(
            livreur=user,
            created_at__range=[start_date, end_date]
        )
        
        # Calcul des gains
        total_earnings = 0
        commission_paid = 0
        
        for mission in missions.filter(status='livree'):
            from location.utils import calculate_commission
            commission_data = calculate_commission(
                mission.price, 
                'premium' if hasattr(user, 'livreur_profile') and user.livreur_profile.is_premium else 'gratuit'
            )
            total_earnings += commission_data['livreur_amount']
            commission_paid += commission_data['commission']
        
        stats = {
            'total_missions': missions.count(),
            'completed_missions': missions.filter(status='delivered').count(),
            'total_earnings': total_earnings,
            'commission_paid': commission_paid,
            'average_rating': self._get_livreur_average_rating(user, start_date, end_date),
            'total_distance': self._calculate_total_distance(missions),
            'average_delivery_time': self._calculate_average_delivery_time(missions),
        }
        
        charts_data = {
            'earnings_by_day': self._get_earnings_by_day(missions, start_date, end_date),
            'missions_by_status': self._get_missions_by_status(missions),
            'delivery_zones': self._get_delivery_zones_stats(missions),
            'performance_trends': self._get_performance_trends(user, start_date, end_date),
        }
        
        return {
            'period': period,
            'stats': stats,
            'charts': charts_data,
            'profile_completion': self._get_profile_completion(user),
        }
    
    def get_admin_dashboard_data(self, period='month'):
        """
        Génère les données du tableau de bord administrateur
        """
        end_date = timezone.now()
        start_date = self._get_period_start_date(end_date, period)
        
        # Statistiques globales
        all_missions = Mission.objects.filter(created_at__range=[start_date, end_date])
        all_users = User.objects.filter(date_joined__range=[start_date, end_date])
        
        stats = {
            'total_missions': all_missions.count(),
            'total_revenue': all_missions.aggregate(total=Sum('price'))['total'] or 0,
            'new_users': all_users.count(),
            'active_livreurs': User.objects.filter(
                user_type='livreur',
                livreur_profile__is_available=True
            ).count(),
            'enterprise_clients': User.objects.filter(user_type='entreprise').count(),
            'average_mission_value': all_missions.aggregate(avg=Avg('price'))['avg'] or 0,
        }
        
        charts_data = {
            'revenue_by_day': self._get_revenue_by_day(all_missions, start_date, end_date),
            'missions_by_city': self._get_missions_by_city(all_missions),
            'user_growth': self._get_user_growth(start_date, end_date),
            'top_livreurs': self._get_top_livreurs(start_date, end_date),
            'service_type_distribution': self._get_service_type_distribution(all_missions),
        }
        
        return {
            'period': period,
            'stats': stats,
            'charts': charts_data,
        }
    
    def _get_period_start_date(self, end_date, period):
        """Calcule la date de début selon la période"""
        if period == 'day':
            return end_date.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == 'week':
            return end_date - timedelta(days=7)
        elif period == 'month':
            return end_date - timedelta(days=30)
        elif period == 'year':
            return end_date - timedelta(days=365)
        return end_date - timedelta(days=30)
    
    def _calculate_success_rate(self, missions):
        """Calcule le taux de réussite des missions"""
        total = missions.count()
        if total == 0:
            return 0
        completed = missions.filter(status='livree').count()
        return round((completed / total) * 100, 1)
    
    def _get_average_rating(self, user, start_date, end_date):
        """Récupère la note moyenne d'un utilisateur"""
        ratings = Rating.objects.filter(
            rated_user=user,
            created_at__range=[start_date, end_date]
        )
        avg_rating = ratings.aggregate(avg=Avg('rating'))['avg']
        return round(avg_rating, 1) if avg_rating else 0
    
    def _get_livreur_average_rating(self, user, start_date, end_date):
        """Récupère la note moyenne d'un livreur"""
        missions = Mission.objects.filter(
            livreur=user,
            status='livree',
            created_at__range=[start_date, end_date]
        )
        ratings = Rating.objects.filter(
            mission__in=missions,
            rater_type='client'
        )
        avg_rating = ratings.aggregate(avg=Avg('rating'))['avg']
        return round(avg_rating, 1) if avg_rating else 0
    
    def _get_missions_by_day(self, missions, start_date, end_date):
        """Données missions par jour pour graphique"""
        data = []
        current_date = start_date.date()
        end_date_only = end_date.date()
        
        while current_date <= end_date_only:
            count = missions.filter(created_at__date=current_date).count()
            data.append({
                'date': current_date.strftime('%Y-%m-%d'),
                'count': count
            })
            current_date += timedelta(days=1)
        
        return data
    
    def _get_missions_by_status(self, missions):
        """Distribution des missions par statut"""
        status_counts = missions.values('status').annotate(count=Count('id'))
        return [{'status': item['status'], 'count': item['count']} for item in status_counts]
    
    def _get_revenue_by_day(self, missions, start_date, end_date):
        """Revenus par jour pour graphique"""
        data = []
        current_date = start_date.date()
        end_date_only = end_date.date()
        
        while current_date <= end_date_only:
            revenue = missions.filter(
                created_at__date=current_date,
                status='livree'
            ).aggregate(total=Sum('price'))['total'] or 0
            
            data.append({
                'date': current_date.strftime('%Y-%m-%d'),
                'revenue': revenue
            })
            current_date += timedelta(days=1)
        
        return data
    
    def _get_top_routes(self, missions):
        """Top 5 des routes les plus utilisées"""
        routes = missions.values('pickup_address', 'delivery_address').annotate(
            count=Count('id')
        ).order_by('-count')[:5]
        
        return [
            {
                'route': f"{route['pickup_address']} → {route['delivery_address']}",
                'count': route['count']
            }
            for route in routes
        ]
    
    def _get_delivery_time_stats(self, missions):
        """Statistiques des temps de livraison"""
        completed_missions = missions.filter(status='livree')
        times = []
        
        for mission in completed_missions:
            if mission.delivered_at and mission.created_at:
                duration = mission.delivered_at - mission.created_at
                times.append(duration.total_seconds() / 3600)  # En heures
        
        if not times:
            return {'average': 0, 'min': 0, 'max': 0}
        
        return {
            'average': round(sum(times) / len(times), 1),
            'min': round(min(times), 1),
            'max': round(max(times), 1)
        }
    
    def _get_previous_period_comparison(self, user, start_date, end_date, period):
        """Comparaison avec la période précédente"""
        period_duration = end_date - start_date
        previous_start = start_date - period_duration
        previous_end = start_date
        
        previous_missions = Mission.objects.filter(
            client=user,
            created_at__range=[previous_start, previous_end]
        )
        
        current_count = Mission.objects.filter(
            client=user,
            created_at__range=[start_date, end_date]
        ).count()
        
        previous_count = previous_missions.count()
        
        if previous_count > 0:
            growth = round(((current_count - previous_count) / previous_count) * 100, 1)
        else:
            growth = 100 if current_count > 0 else 0
        
        return {
            'previous_missions': previous_count,
            'growth_percentage': growth
        }
    
    def _get_subscription_info(self, user):
        """Informations sur l'abonnement utilisateur"""
        if hasattr(user, 'entreprise_profile'):
            profile = user.entreprise_profile
            return {
                'type': getattr(profile, 'subscription_type', 'none'),
                'missions_limit': 50 if getattr(profile, 'subscription_type', None) == 'starter' else None,
                'current_month_missions': Mission.objects.filter(
                    client=user,
                    created_at__month=timezone.now().month
                ).count()
            }
        return {'type': 'none'}
    
    def _calculate_total_distance(self, missions):
        """Calcule la distance totale parcourue"""
        total_distance = 0
        for mission in missions.filter(status='livree'):
            if hasattr(mission, 'distance_km'):
                total_distance += mission.distance_km
        return round(total_distance, 1)
    
    def _calculate_average_delivery_time(self, missions):
        """Calcule le temps moyen de livraison"""
        times = []
        for mission in missions.filter(status='livree'):
            if mission.delivered_at and mission.accepted_at:
                duration = mission.delivered_at - mission.accepted_at
                times.append(duration.total_seconds() / 60)  # En minutes
        
        return round(sum(times) / len(times), 0) if times else 0
    
    def _get_earnings_by_day(self, missions, start_date, end_date):
        """Gains par jour pour livreur"""
        data = []
        current_date = start_date.date()
        end_date_only = end_date.date()
        
        while current_date <= end_date_only:
            daily_missions = missions.filter(
                created_at__date=current_date,
                status='livree'
            )
            
            daily_earnings = 0
            for mission in daily_missions:
                from location.utils import calculate_commission
                commission_data = calculate_commission(mission.price, 'premium')  # À adapter
                daily_earnings += commission_data['livreur_amount']
            
            data.append({
                'date': current_date.strftime('%Y-%m-%d'),
                'earnings': daily_earnings
            })
            current_date += timedelta(days=1)
        
        return data
    
    def _get_delivery_zones_stats(self, missions):
        """Statistiques par zones de livraison"""
        # Simplification - grouper par quartiers/zones
        zones = missions.values('delivery_address').annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        
        return [
            {
                'zone': zone['delivery_address'][:50] + '...' if len(zone['delivery_address']) > 50 else zone['delivery_address'],
                'count': zone['count']
            }
            for zone in zones
        ]
    
    def _get_performance_trends(self, user, start_date, end_date):
        """Tendances de performance du livreur"""
        # Évolution des notes sur la période
        ratings = Rating.objects.filter(
            rated_user=user,
            created_at__range=[start_date, end_date]
        ).order_by('created_at')
        
        data = []
        for rating in ratings:
            data.append({
                'date': rating.created_at.strftime('%Y-%m-%d'),
                'rating': rating.rating
            })
        
        return data
    
    def _get_profile_completion(self, user):
        """Pourcentage de complétion du profil"""
        completion = 0
        total_fields = 10
        
        if user.first_name:
            completion += 1
        if user.last_name:
            completion += 1
        if user.email:
            completion += 1
        if user.phone_number:
            completion += 1
        
        if hasattr(user, 'livreur_profile'):
            profile = user.livreur_profile
            if profile.vehicle_type:
                completion += 1
            if profile.license_number:
                completion += 1
            if profile.vehicle_plate:
                completion += 1
            if profile.service_zones.exists():
                completion += 1
            if hasattr(profile, 'profile_photo') and profile.profile_photo:
                completion += 1
            if hasattr(profile, 'bio') and profile.bio:
                completion += 1
        
        return round((completion / total_fields) * 100)
    
    def _get_missions_by_city(self, missions):
        """Missions par ville"""
        # Simplification - extraire la ville de l'adresse
        cities = {}
        for mission in missions:
            # Logique simplifiée - à améliorer avec géocodage
            if 'Ouagadougou' in mission.pickup_address:
                cities['Ouagadougou'] = cities.get('Ouagadougou', 0) + 1
            elif 'Bobo-Dioulasso' in mission.pickup_address:
                cities['Bobo-Dioulasso'] = cities.get('Bobo-Dioulasso', 0) + 1
            else:
                cities['Autres'] = cities.get('Autres', 0) + 1
        
        return [{'city': city, 'count': count} for city, count in cities.items()]
    
    def _get_user_growth(self, start_date, end_date):
        """Croissance des utilisateurs"""
        data = []
        current_date = start_date.date()
        end_date_only = end_date.date()
        
        while current_date <= end_date_only:
            new_users = User.objects.filter(date_joined__date=current_date).count()
            data.append({
                'date': current_date.strftime('%Y-%m-%d'),
                'new_users': new_users
            })
            current_date += timedelta(days=1)
        
        return data
    
    def _get_top_livreurs(self, start_date, end_date):
        """Top livreurs de la période"""
        livreurs = User.objects.filter(
            user_type='livreur',
            missions_assigned__created_at__range=[start_date, end_date]
        ).annotate(
            mission_count=Count('missions_assigned'),
            avg_rating=Avg('ratings_received__rating')
        ).order_by('-mission_count')[:10]
        
        return [
            {
                'name': livreur.get_full_name(),
                'missions': livreur.mission_count,
                'rating': round(livreur.avg_rating, 1) if livreur.avg_rating else 0
            }
            for livreur in livreurs
        ]
    
    def _get_service_type_distribution(self, missions):
        """Distribution par type de service"""
        services = missions.values('service_type').annotate(count=Count('id'))
        return [{'service': item['service_type'], 'count': item['count']} for item in services]


# Instance globale du service
analytics_service = AnalyticsService()
