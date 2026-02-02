"""
Django Management Command for Performance Optimization
Usage: python manage.py optimize_performance
"""

from django.core.management.base import BaseCommand
from django.db import connection
from django.contrib.auth import get_user_model
from missions.models import Mission
from chat.models import Conversation, ChatMessage
from ratings.models import Rating
from subscriptions.models import SubscriptionPlan, UserSubscription

User = get_user_model()

class Command(BaseCommand):
    help = 'Apply performance optimizations to LivraFaso database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--indexes-only',
            action='store_true',
            help='Only create database indexes',
        )
        parser.add_argument(
            '--analyze-only',
            action='store_true',
            help='Only analyze database performance',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🚀 LivraFaso Performance Optimization Tool\n')
        )
        
        if options['analyze_only']:
            self.analyze_performance()
        elif options['indexes_only']:
            self.create_database_indexes()
        else:
            self.create_database_indexes()
            self.optimize_queries()
            self.analyze_performance()
        
        self.stdout.write(
            self.style.SUCCESS('\n✅ Performance optimization completed!')
        )

    def create_database_indexes(self):
        """Create database indexes for better query performance"""
        self.stdout.write('📊 Creating database indexes...')
        
        indexes = [
            # User indexes
            ("idx_users_user_type", "users_user", "user_type"),
            ("idx_users_is_active", "users_user", "is_active"),
            ("idx_users_location", "users_user", "latitude, longitude", 
             "WHERE latitude IS NOT NULL AND longitude IS NOT NULL"),
            
            # Mission indexes
            ("idx_missions_status_created", "missions_mission", "status, created_at DESC"),
            ("idx_missions_client_status", "missions_mission", "client_id, status"),
            ("idx_missions_livreur_status", "missions_mission", "livreur_id, status", 
             "WHERE livreur_id IS NOT NULL"),
            ("idx_missions_pickup_location", "missions_mission", "pickup_latitude, pickup_longitude"),
            ("idx_missions_delivery_location", "missions_mission", "delivery_latitude, delivery_longitude"),
            
            # Chat indexes
            ("idx_conversations_participants", "chat_conversation", "client_id, livreur_id"),
            ("idx_messages_conversation_created", "chat_message", "conversation_id, created_at DESC"),
            ("idx_messages_sender_read", "chat_message", "sender_id, is_read"),
            
            # Rating indexes
            ("idx_ratings_mission_rater", "ratings_rating", "mission_id, rater_id"),
            ("idx_ratings_rated_user_score", "ratings_rating", "rated_user_id, score"),
            
            # Subscription indexes
            ("idx_user_subscriptions_active", "subscriptions_usersubscription", 
             "user_id, is_active, end_date"),
        ]
        
        with connection.cursor() as cursor:
            for index_data in indexes:
                index_name = index_data[0]
                table_name = index_data[1]
                columns = index_data[2]
                condition = index_data[3] if len(index_data) > 3 else ""
                
                try:
                    sql = f"""
                        CREATE INDEX CONCURRENTLY IF NOT EXISTS {index_name} 
                        ON {table_name}({columns}) {condition};
                    """
                    cursor.execute(sql)
                    self.stdout.write(f'  ✅ Created index: {index_name}')
                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(f'  ⚠️ Index {index_name}: {str(e)}')
                    )

    def optimize_queries(self):
        """Optimize database configuration"""
        self.stdout.write('🔍 Optimizing database configuration...')
        
        with connection.cursor() as cursor:
            try:
                # Update table statistics
                cursor.execute("ANALYZE;")
                self.stdout.write('  ✅ Updated table statistics')
                
                # Check current configuration
                cursor.execute("SHOW work_mem;")
                work_mem = cursor.fetchone()[0]
                self.stdout.write(f'  📊 Current work_mem: {work_mem}')
                
                cursor.execute("SHOW random_page_cost;")
                random_page_cost = cursor.fetchone()[0]
                self.stdout.write(f'  📊 Current random_page_cost: {random_page_cost}')
                
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f'  ⚠️ Query optimization: {str(e)}')
                )

    def analyze_performance(self):
        """Analyze current database performance"""
        self.stdout.write('📈 Analyzing database performance...')
        
        with connection.cursor() as cursor:
            try:
                # Table sizes
                cursor.execute("""
                    SELECT 
                        schemaname,
                        tablename,
                        n_live_tup as live_tuples,
                        n_dead_tup as dead_tuples,
                        pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
                    FROM pg_stat_user_tables 
                    ORDER BY n_live_tup DESC
                    LIMIT 10;
                """)
                
                results = cursor.fetchall()
                if results:
                    self.stdout.write('\n  📊 Top Tables by Size:')
                    for row in results:
                        schema, table, live, dead, size = row
                        self.stdout.write(f'    {table}: {live:,} rows, {size}')
                
                # Index usage
                cursor.execute("""
                    SELECT 
                        schemaname,
                        tablename,
                        indexname,
                        idx_tup_read,
                        idx_tup_fetch
                    FROM pg_stat_user_indexes 
                    WHERE idx_tup_read > 0
                    ORDER BY idx_tup_read DESC
                    LIMIT 10;
                """)
                
                results = cursor.fetchall()
                if results:
                    self.stdout.write('\n  📊 Most Used Indexes:')
                    for row in results:
                        schema, table, index, reads, fetches = row
                        self.stdout.write(f'    {index}: {reads:,} reads')
                
                # Connection stats
                cursor.execute("""
                    SELECT count(*) as total_connections,
                           count(*) FILTER (WHERE state = 'active') as active_connections
                    FROM pg_stat_activity;
                """)
                
                total, active = cursor.fetchone()
                self.stdout.write(f'\n  📊 Connections: {active}/{total} active')
                
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f'  ⚠️ Performance analysis: {str(e)}')
                )
