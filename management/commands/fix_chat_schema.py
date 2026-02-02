from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = 'Fix chat_conversation table schema by adding missing columns'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            try:
                self.stdout.write("🔧 Fixing chat_conversation table schema...")
                
                # Check if table exists
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.tables 
                        WHERE table_name = 'chat_conversation'
                    );
                """)
                table_exists = cursor.fetchone()[0]
                
                if not table_exists:
                    self.stdout.write(self.style.ERROR("❌ Table chat_conversation does not exist"))
                    return
                
                # Check existing columns
                cursor.execute("""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name = 'chat_conversation' 
                    ORDER BY ordinal_position;
                """)
                columns = [row[0] for row in cursor.fetchall()]
                self.stdout.write(f"Current columns: {columns}")
                
                # Add missing columns
                columns_to_add = [
                    ('mission_id', 'UUID'),
                    ('client_id', 'UUID'),
                    ('livreur_id', 'UUID'),
                    ('last_message_id', 'BIGINT')
                ]
                
                for col_name, col_type in columns_to_add:
                    if col_name not in columns:
                        cursor.execute(f"""
                            ALTER TABLE chat_conversation 
                            ADD COLUMN {col_name} {col_type};
                        """)
                        self.stdout.write(self.style.SUCCESS(f"✅ Added {col_name} column"))
                    else:
                        self.stdout.write(f"ℹ️ {col_name} already exists")
                
                # Verify final schema
                cursor.execute("""
                    SELECT column_name, data_type FROM information_schema.columns 
                    WHERE table_name = 'chat_conversation' 
                    ORDER BY ordinal_position;
                """)
                final_schema = cursor.fetchall()
                
                self.stdout.write("\n📋 Final schema:")
                for col_name, col_type in final_schema:
                    self.stdout.write(f"  - {col_name}: {col_type}")
                
                self.stdout.write(self.style.SUCCESS("✅ Schema fix completed successfully!"))
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Error fixing schema: {e}"))
                raise
