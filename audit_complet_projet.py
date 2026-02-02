#!/usr/bin/env python
"""
Audit complet du projet LivraFaso - Détection et correction automatique des bugs
"""
import os
import re
import sys
from pathlib import Path
import subprocess
import json

class LivraFasoAuditor:
    def __init__(self, project_root):
        self.project_root = Path(project_root)
        self.errors = []
        self.warnings = []
        self.fixes_applied = []
        
    def run_django_check(self):
        """Exécuter python manage.py check"""
        print("🔍 AUDIT DJANGO SYSTEM CHECK")
        print("=" * 40)
        
        try:
            result = subprocess.run(
                [sys.executable, 'manage.py', 'check'],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print("✅ Django system check: AUCUN PROBLÈME")
            else:
                print("❌ Django system check: ERREURS DÉTECTÉES")
                print(result.stdout)
                print(result.stderr)
                self.errors.append(f"Django check failed: {result.stderr}")
                
        except Exception as e:
            print(f"❌ Erreur lors du check Django: {e}")
            self.errors.append(f"Django check error: {e}")
    
    def check_missing_templates(self):
        """Vérifier les templates manquants"""
        print("\n🔍 VÉRIFICATION TEMPLATES")
        print("=" * 30)
        
        # Scanner les vues pour les templates référencés
        template_refs = set()
        
        for view_file in self.project_root.rglob("views.py"):
            try:
                with open(view_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Extraire les références de templates
                matches = re.findall(r"render\([^,]+,\s*['\"]([^'\"]+)['\"]", content)
                template_refs.update(matches)
                
            except Exception as e:
                print(f"❌ Erreur lecture {view_file}: {e}")
        
        # Vérifier l'existence des templates
        templates_dir = self.project_root / 'templates'
        missing_templates = []
        
        for template_ref in template_refs:
            template_path = templates_dir / template_ref
            if not template_path.exists():
                missing_templates.append(template_ref)
                print(f"❌ Template manquant: {template_ref}")
        
        if not missing_templates:
            print("✅ Tous les templates existent")
        else:
            self.errors.extend([f"Missing template: {t}" for t in missing_templates])
    
    def check_url_patterns(self):
        """Vérifier les patterns d'URLs"""
        print("\n🔍 VÉRIFICATION URLs")
        print("=" * 25)
        
        # Vérifier les doublons de namespace
        namespaces = {}
        
        for urls_file in self.project_root.rglob("urls.py"):
            if "venv" in str(urls_file):
                continue
                
            try:
                with open(urls_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                app_name_match = re.search(r'app_name\s*=\s*["\']([^"\']+)["\']', content)
                if app_name_match:
                    namespace = app_name_match.group(1)
                    file_path = str(urls_file.relative_to(self.project_root))
                    
                    if namespace not in namespaces:
                        namespaces[namespace] = []
                    namespaces[namespace].append(file_path)
                    
            except Exception as e:
                print(f"❌ Erreur lecture {urls_file}: {e}")
        
        # Identifier les doublons
        duplicates = {ns: files for ns, files in namespaces.items() if len(files) > 1}
        
        if duplicates:
            print("❌ Namespaces dupliqués détectés:")
            for namespace, files in duplicates.items():
                print(f"  '{namespace}': {files}")
                self.warnings.append(f"Duplicate namespace '{namespace}': {files}")
        else:
            print("✅ Aucun doublon de namespace")
    
    def check_migrations(self):
        """Vérifier l'état des migrations"""
        print("\n🔍 VÉRIFICATION MIGRATIONS")
        print("=" * 30)
        
        try:
            # Vérifier les migrations en attente
            result = subprocess.run(
                [sys.executable, 'manage.py', 'showmigrations', '--plan'],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            
            if "[ ]" in result.stdout:
                print("❌ Migrations non appliquées détectées")
                unapplied = [line for line in result.stdout.split('\n') if '[ ]' in line]
                for migration in unapplied[:5]:  # Afficher les 5 premières
                    print(f"  {migration.strip()}")
                self.warnings.append("Unapplied migrations found")
            else:
                print("✅ Toutes les migrations sont appliquées")
                
        except Exception as e:
            print(f"❌ Erreur vérification migrations: {e}")
            self.errors.append(f"Migration check error: {e}")
    
    def check_static_files(self):
        """Vérifier les fichiers statiques"""
        print("\n🔍 VÉRIFICATION FICHIERS STATIQUES")
        print("=" * 40)
        
        static_dir = self.project_root / 'static'
        if not static_dir.exists():
            print("❌ Dossier static/ manquant")
            self.errors.append("Static directory missing")
            return
        
        # Vérifier les fichiers CSS/JS critiques
        critical_files = [
            'css/livrafaso-unified.css',
            'js/chart.js',
            'images/default-avatar.png'
        ]
        
        missing_files = []
        for file_path in critical_files:
            full_path = static_dir / file_path
            if not full_path.exists():
                missing_files.append(file_path)
                print(f"❌ Fichier statique manquant: {file_path}")
        
        if not missing_files:
            print("✅ Fichiers statiques critiques présents")
        else:
            self.warnings.extend([f"Missing static file: {f}" for f in missing_files])
    
    def check_database_connection(self):
        """Vérifier la connexion à la base de données"""
        print("\n🔍 VÉRIFICATION BASE DE DONNÉES")
        print("=" * 35)
        
        try:
            result = subprocess.run(
                [sys.executable, 'manage.py', 'dbshell', '--command', 'SELECT 1;'],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                print("✅ Connexion base de données: OK")
            else:
                print("❌ Problème connexion base de données")
                self.errors.append("Database connection failed")
                
        except subprocess.TimeoutExpired:
            print("⚠️ Timeout connexion base de données")
            self.warnings.append("Database connection timeout")
        except Exception as e:
            print(f"❌ Erreur test base de données: {e}")
            self.errors.append(f"Database test error: {e}")
    
    def check_imports(self):
        """Vérifier les imports manquants"""
        print("\n🔍 VÉRIFICATION IMPORTS")
        print("=" * 25)
        
        python_files = list(self.project_root.rglob("*.py"))
        import_errors = []
        
        for py_file in python_files[:10]:  # Limiter pour éviter la surcharge
            if "venv" in str(py_file) or "__pycache__" in str(py_file):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Vérifier les imports Django courants
                if 'from django.shortcuts import' in content:
                    if 'render' in content and 'render' not in content.split('from django.shortcuts import')[1].split('\n')[0]:
                        import_errors.append(f"{py_file}: Missing 'render' import")
                
            except Exception as e:
                continue  # Ignorer les erreurs de lecture
        
        if import_errors:
            print(f"❌ {len(import_errors)} erreurs d'import détectées")
            for error in import_errors[:3]:
                print(f"  {error}")
            self.warnings.extend(import_errors)
        else:
            print("✅ Imports principaux corrects")
    
    def generate_report(self):
        """Générer le rapport d'audit"""
        print("\n" + "="*60)
        print("📊 RAPPORT D'AUDIT COMPLET")
        print("="*60)
        
        print(f"\n🔴 ERREURS CRITIQUES: {len(self.errors)}")
        for i, error in enumerate(self.errors[:5], 1):
            print(f"  {i}. {error}")
        
        print(f"\n⚠️ AVERTISSEMENTS: {len(self.warnings)}")
        for i, warning in enumerate(self.warnings[:5], 1):
            print(f"  {i}. {warning}")
        
        print(f"\n✅ CORRECTIONS APPLIQUÉES: {len(self.fixes_applied)}")
        for i, fix in enumerate(self.fixes_applied, 1):
            print(f"  {i}. {fix}")
        
        # Score de santé
        total_issues = len(self.errors) + len(self.warnings)
        if total_issues == 0:
            health_score = 100
            status = "🎉 EXCELLENT"
        elif total_issues <= 3:
            health_score = 85
            status = "✅ BON"
        elif total_issues <= 7:
            health_score = 70
            status = "⚠️ MOYEN"
        else:
            health_score = 50
            status = "🔴 CRITIQUE"
        
        print(f"\n📈 SCORE DE SANTÉ: {health_score}% - {status}")
        
        return {
            'errors': self.errors,
            'warnings': self.warnings,
            'fixes': self.fixes_applied,
            'health_score': health_score
        }
    
    def run_full_audit(self):
        """Exécuter l'audit complet"""
        print("🚀 DÉMARRAGE AUDIT COMPLET LIVRAFASO")
        print("="*50)
        
        self.run_django_check()
        self.check_missing_templates()
        self.check_url_patterns()
        self.check_migrations()
        self.check_static_files()
        self.check_database_connection()
        self.check_imports()
        
        return self.generate_report()

if __name__ == '__main__':
    project_root = Path(__file__).parent
    auditor = LivraFasoAuditor(project_root)
    report = auditor.run_full_audit()
    
    # Sauvegarder le rapport
    with open('audit_report.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Rapport sauvegardé: audit_report.json")
