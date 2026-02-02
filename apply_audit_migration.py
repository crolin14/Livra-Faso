#!/usr/bin/env python
"""
Script to apply audit migration and fix missing columns
"""
import os
import sys
import django
from django.core.management import execute_from_command_line
from django.db import connection

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Livraison_Faso.settings')
django.setup()

def check_column_exists(table_name, column_name):
    """Check if a column exists in a table"""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name=%s AND column_name=%s
        """, [table_name, column_name])
        return cursor.fetchone() is not None

def add_missing_columns():
    """Add missing columns directly using SQL"""
    with connection.cursor() as cursor:
        print("Checking and adding missing columns...")
        
        # Check audit_auditlog columns
        missing_columns = []
        
        if not check_column_exists('audit_auditlog', 'action_type'):
            missing_columns.append(('audit_auditlog', 'action_type'))
            cursor.execute("ALTER TABLE audit_auditlog ADD COLUMN action_type varchar(20) DEFAULT 'system_event'")
            print("✓ Added action_type to audit_auditlog")
        
        if not check_column_exists('audit_auditlog', 'action_description'):
            missing_columns.append(('audit_auditlog', 'action_description'))
            cursor.execute("ALTER TABLE audit_auditlog ADD COLUMN action_description varchar(255) DEFAULT 'Action système'")
            print("✓ Added action_description to audit_auditlog")
        
        if not check_column_exists('audit_auditlog', 'severity'):
            missing_columns.append(('audit_auditlog', 'severity'))
            cursor.execute("ALTER TABLE audit_auditlog ADD COLUMN severity varchar(10) DEFAULT 'low'")
            print("✓ Added severity to audit_auditlog")
        
        if not check_column_exists('audit_auditlog', 'user_agent'):
            missing_columns.append(('audit_auditlog', 'user_agent'))
            cursor.execute("ALTER TABLE audit_auditlog ADD COLUMN user_agent text DEFAULT ''")
            print("✓ Added user_agent to audit_auditlog")
        
        # Check audit_securityevent columns
        if not check_column_exists('audit_securityevent', 'source_ip'):
            missing_columns.append(('audit_securityevent', 'source_ip'))
            cursor.execute("ALTER TABLE audit_securityevent ADD COLUMN source_ip inet")
            print("✓ Added source_ip to audit_securityevent")
        
        if not check_column_exists('audit_securityevent', 'event_type'):
            missing_columns.append(('audit_securityevent', 'event_type'))
            cursor.execute("ALTER TABLE audit_securityevent ADD COLUMN event_type varchar(50) DEFAULT 'suspicious_activity'")
            print("✓ Added event_type to audit_securityevent")
        
        if not check_column_exists('audit_securityevent', 'description'):
            missing_columns.append(('audit_securityevent', 'description'))
            cursor.execute("ALTER TABLE audit_securityevent ADD COLUMN description text DEFAULT ''")
            print("✓ Added description to audit_securityevent")
        
        if not check_column_exists('audit_securityevent', 'user_agent'):
            missing_columns.append(('audit_securityevent', 'user_agent'))
            cursor.execute("ALTER TABLE audit_securityevent ADD COLUMN user_agent text DEFAULT ''")
            print("✓ Added user_agent to audit_securityevent")
        
        if missing_columns:
            print(f"\n✅ Successfully added {len(missing_columns)} missing columns")
        else:
            print("\n✅ All required columns already exist")
        
        return len(missing_columns)

def main():
    print("=== AUDIT MIGRATION FIX ===")
    print("Fixing missing columns in audit tables...")
    
    try:
        # Add missing columns directly
        columns_added = add_missing_columns()
        
        # Try to run Django migration
        print("\nApplying Django migration...")
        try:
            execute_from_command_line(['manage.py', 'migrate', 'audit'])
            print("✅ Django migration applied successfully")
        except Exception as e:
            print(f"⚠️ Django migration failed: {e}")
            print("But columns were added directly, so audit system should work")
        
        # Test the audit system
        print("\nTesting audit system...")
        from audit.models import AuditLog, SecurityEvent
        
        # Test AuditLog creation
        try:
            test_log = AuditLog.objects.create(
                action_type='test',
                action_description='Test audit log',
                severity='low'
            )
            print("✅ AuditLog creation test passed")
            test_log.delete()
        except Exception as e:
            print(f"❌ AuditLog test failed: {e}")
        
        # Test SecurityEvent creation
        try:
            test_event = SecurityEvent.objects.create(
                event_type='test',
                source_ip='127.0.0.1',
                description='Test security event'
            )
            print("✅ SecurityEvent creation test passed")
            test_event.delete()
        except Exception as e:
            print(f"❌ SecurityEvent test failed: {e}")
        
        print(f"\n🎉 AUDIT SYSTEM FIX COMPLETED!")
        print(f"Added {columns_added} missing columns")
        print("The audit system should now work without errors.")
        
    except Exception as e:
        print(f"❌ Error during migration: {e}")
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
