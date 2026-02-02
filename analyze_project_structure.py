#!/usr/bin/env python3
"""
Analyseur complet de structure de projet LivraFaso
Analyse backend Django, frontend, assets et génère un rapport détaillé
"""

import os
import re
from pathlib import Path
import json
from collections import defaultdict

class ProjectAnalyzer:
    def __init__(self, project_root):
        self.project_root = Path(project_root)
        self.analysis = {
            'backend': {
                'apps': {},
                'models': {},
                'views': {},
                'urls': {},
                'forms': {},
                'services': {}
            },
            'frontend': {
                'templates': {},
                'static_files': {},
                'components': {},
                'forms': {}
            },
            'files': {
                'total': 0,
                'by_type': defaultdict(int),
                'by_directory': defaultdict(int),
                'unused': [],
                'duplicates': []
            },
            'dependencies': {
                'backend_frontend': [],
                'internal': []
            }
        }
    
    def analyze_django_apps(self):
        """Analyse les applications Django"""
        apps = {}
        
        # Identifier les apps Django
        for item in self.project_root.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                app_path = item
                if (app_path / 'apps.py').exists() or (app_path / 'models.py').exists():
                    apps[item.name] = {
                        'path': str(app_path),
                        'models': self._analyze_models(app_path),
                        'views': self._analyze_views(app_path),
                        'urls': self._analyze_urls(app_path),
                        'forms': self._analyze_forms(app_path),
                        'admin': self._analyze_admin(app_path),
                        'migrations': self._count_migrations(app_path)
                    }
        
        return apps
    
    def _analyze_models(self, app_path):
        """Analyse les modèles Django"""
        models_file = app_path / 'models.py'
        models = []
        
        if models_file.exists():
            try:
                content = models_file.read_text(encoding='utf-8')
                # Rechercher les classes de modèles
                model_pattern = r'class\s+(\w+)\s*\([^)]*Model[^)]*\):'
                matches = re.findall(model_pattern, content)
                
                for model_name in matches:
                    # Analyser les champs du modèle
                    model_section = self._extract_class_content(content, model_name)
                    fields = self._extract_model_fields(model_section)
                    
                    models.append({
                        'name': model_name,
                        'fields': fields,
                        'methods': self._extract_methods(model_section)
                    })
            except Exception as e:
                print(f"Erreur analyse models {app_path}: {e}")
        
        return models
    
    def _analyze_views(self, app_path):
        """Analyse les vues Django"""
        views = []
        
        for view_file in app_path.glob('views*.py'):
            try:
                content = view_file.read_text(encoding='utf-8')
                
                # Vues basées sur des fonctions
                func_pattern = r'def\s+(\w+)\s*\([^)]*request[^)]*\):'
                func_views = re.findall(func_pattern, content)
                
                # Vues basées sur des classes
                class_pattern = r'class\s+(\w+)\s*\([^)]*View[^)]*\):'
                class_views = re.findall(class_pattern, content)
                
                views.extend([{'name': v, 'type': 'function', 'file': view_file.name} for v in func_views])
                views.extend([{'name': v, 'type': 'class', 'file': view_file.name} for v in class_views])
                
            except Exception as e:
                print(f"Erreur analyse views {view_file}: {e}")
        
        return views
    
    def _analyze_urls(self, app_path):
        """Analyse les URLs Django"""
        urls_file = app_path / 'urls.py'
        urls = []
        
        if urls_file.exists():
            try:
                content = urls_file.read_text(encoding='utf-8')
                
                # Patterns URL
                url_pattern = r"path\s*\(\s*['\"]([^'\"]*)['\"]"
                matches = re.findall(url_pattern, content)
                
                for match in matches:
                    urls.append({
                        'pattern': match,
                        'name': self._extract_url_name(content, match)
                    })
                    
            except Exception as e:
                print(f"Erreur analyse URLs {urls_file}: {e}")
        
        return urls
    
    def _analyze_forms(self, app_path):
        """Analyse les formulaires Django"""
        forms_file = app_path / 'forms.py'
        forms = []
        
        if forms_file.exists():
            try:
                content = forms_file.read_text(encoding='utf-8')
                
                # Classes de formulaires
                form_pattern = r'class\s+(\w+)\s*\([^)]*Form[^)]*\):'
                matches = re.findall(form_pattern, content)
                
                for form_name in matches:
                    form_section = self._extract_class_content(content, form_name)
                    fields = self._extract_form_fields(form_section)
                    
                    forms.append({
                        'name': form_name,
                        'fields': fields
                    })
                    
            except Exception as e:
                print(f"Erreur analyse forms {forms_file}: {e}")
        
        return forms
    
    def analyze_templates(self):
        """Analyse les templates HTML"""
        templates_dir = self.project_root / 'templates'
        templates = {}
        
        if templates_dir.exists():
            for template_file in templates_dir.rglob('*.html'):
                try:
                    content = template_file.read_text(encoding='utf-8')
                    relative_path = template_file.relative_to(templates_dir)
                    
                    templates[str(relative_path)] = {
                        'path': str(template_file),
                        'size': len(content),
                        'forms': self._extract_html_forms(content),
                        'static_refs': self._extract_static_references(content),
                        'extends': self._extract_template_extends(content),
                        'includes': self._extract_template_includes(content)
                    }
                    
                except Exception as e:
                    print(f"Erreur analyse template {template_file}: {e}")
        
        return templates
    
    def analyze_static_files(self):
        """Analyse les fichiers statiques"""
        static_dir = self.project_root / 'static'
        static_files = {
            'css': [],
            'js': [],
            'images': [],
            'other': []
        }
        
        if static_dir.exists():
            for static_file in static_dir.rglob('*'):
                if static_file.is_file():
                    ext = static_file.suffix.lower()
                    file_info = {
                        'name': static_file.name,
                        'path': str(static_file.relative_to(static_dir)),
                        'size': static_file.stat().st_size
                    }
                    
                    if ext in ['.css']:
                        static_files['css'].append(file_info)
                    elif ext in ['.js']:
                        static_files['js'].append(file_info)
                    elif ext in ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico']:
                        static_files['images'].append(file_info)
                    else:
                        static_files['other'].append(file_info)
        
        return static_files
    
    def detect_unused_files(self):
        """Détecte les fichiers potentiellement inutilisés"""
        unused = []
        
        # Analyser les références dans les templates
        templates = self.analyze_templates()
        all_static_refs = set()
        
        for template_info in templates.values():
            all_static_refs.update(template_info['static_refs'])
        
        # Vérifier les fichiers statiques
        static_files = self.analyze_static_files()
        for category, files in static_files.items():
            for file_info in files:
                if file_info['path'] not in all_static_refs:
                    unused.append({
                        'file': file_info['path'],
                        'type': 'static',
                        'reason': 'Non référencé dans les templates'
                    })
        
        return unused
    
    def detect_duplicates(self):
        """Détecte les fichiers dupliqués"""
        duplicates = []
        file_hashes = defaultdict(list)
        
        # Analyser les fichiers CSS pour détecter du contenu similaire
        css_files = (self.project_root / 'static' / 'css').glob('*.css') if (self.project_root / 'static' / 'css').exists() else []
        
        for css_file in css_files:
            try:
                content = css_file.read_text(encoding='utf-8')
                # Simplifier le contenu pour comparaison
                simplified = re.sub(r'\s+', ' ', content).strip()
                if len(simplified) > 100:  # Ignorer les fichiers très petits
                    file_hashes[hash(simplified)].append(str(css_file))
            except:
                pass
        
        for file_hash, files in file_hashes.items():
            if len(files) > 1:
                duplicates.append({
                    'files': files,
                    'type': 'content_similar'
                })
        
        return duplicates
    
    def analyze_backend_frontend_dependencies(self):
        """Analyse les dépendances backend ↔ frontend"""
        dependencies = []
        
        # Analyser les vues et leurs templates
        apps = self.analyze_django_apps()
        templates = self.analyze_templates()
        
        for app_name, app_info in apps.items():
            for view in app_info['views']:
                # Chercher le template utilisé par cette vue
                template_name = self._find_view_template(app_name, view['name'])
                if template_name and template_name in templates:
                    dependencies.append({
                        'backend': f"{app_name}.views.{view['name']}",
                        'frontend': template_name,
                        'type': 'view_template'
                    })
        
        return dependencies
    
    def _extract_class_content(self, content, class_name):
        """Extrait le contenu d'une classe"""
        pattern = rf'class\s+{class_name}\s*\([^)]*\):(.*?)(?=\nclass|\nif\s+__name__|\Z)'
        match = re.search(pattern, content, re.DOTALL)
        return match.group(1) if match else ""
    
    def _extract_model_fields(self, model_content):
        """Extrait les champs d'un modèle Django"""
        fields = []
        field_pattern = r'(\w+)\s*=\s*models\.(\w+Field)'
        matches = re.findall(field_pattern, model_content)
        
        for field_name, field_type in matches:
            fields.append({
                'name': field_name,
                'type': field_type
            })
        
        return fields
    
    def _extract_methods(self, class_content):
        """Extrait les méthodes d'une classe"""
        methods = []
        method_pattern = r'def\s+(\w+)\s*\('
        matches = re.findall(method_pattern, class_content)
        
        for method_name in matches:
            if not method_name.startswith('_'):  # Ignorer les méthodes privées
                methods.append(method_name)
        
        return methods
    
    def _extract_form_fields(self, form_content):
        """Extrait les champs d'un formulaire Django"""
        fields = []
        field_pattern = r'(\w+)\s*=\s*forms\.(\w+Field)'
        matches = re.findall(field_pattern, form_content)
        
        for field_name, field_type in matches:
            fields.append({
                'name': field_name,
                'type': field_type
            })
        
        return fields
    
    def _extract_html_forms(self, content):
        """Extrait les formulaires HTML"""
        forms = []
        form_pattern = r'<form[^>]*>(.*?)</form>'
        matches = re.findall(form_pattern, content, re.DOTALL | re.IGNORECASE)
        
        for i, form_content in enumerate(matches):
            inputs = re.findall(r'<input[^>]*name=["\']([^"\']*)["\']', form_content)
            forms.append({
                'id': i,
                'inputs': inputs
            })
        
        return forms
    
    def _extract_static_references(self, content):
        """Extrait les références aux fichiers statiques"""
        refs = []
        
        # Références {% static %}
        static_pattern = r'{%\s*static\s+["\']([^"\']*)["\']'
        refs.extend(re.findall(static_pattern, content))
        
        # Références directes
        direct_pattern = r'(?:src|href)=["\']/?static/([^"\']*)["\']'
        refs.extend(re.findall(direct_pattern, content))
        
        return refs
    
    def _extract_template_extends(self, content):
        """Extrait les extends de template"""
        pattern = r'{%\s*extends\s+["\']([^"\']*)["\']'
        matches = re.findall(pattern, content)
        return matches[0] if matches else None
    
    def _extract_template_includes(self, content):
        """Extrait les includes de template"""
        pattern = r'{%\s*include\s+["\']([^"\']*)["\']'
        return re.findall(pattern, content)
    
    def _extract_url_name(self, content, pattern):
        """Extrait le nom d'une URL"""
        name_pattern = rf"path\s*\(\s*['\"]({re.escape(pattern)})['\"].*?name\s*=\s*['\"]([^'\"]*)['\"]"
        match = re.search(name_pattern, content)
        return match.group(2) if match else None
    
    def _find_view_template(self, app_name, view_name):
        """Trouve le template utilisé par une vue"""
        # Logique simplifiée - à améliorer selon les conventions du projet
        possible_templates = [
            f"{app_name}/{view_name}.html",
            f"{app_name}/{view_name}_detail.html",
            f"{app_name}/{view_name}_list.html"
        ]
        
        templates = self.analyze_templates()
        for template in possible_templates:
            if template in templates:
                return template
        
        return None
    
    def _count_migrations(self, app_path):
        """Compte les migrations d'une app"""
        migrations_dir = app_path / 'migrations'
        if migrations_dir.exists():
            return len([f for f in migrations_dir.glob('*.py') if f.name != '__init__.py'])
        return 0
    
    def _analyze_admin(self, app_path):
        """Analyse le fichier admin.py"""
        admin_file = app_path / 'admin.py'
        if admin_file.exists():
            try:
                content = admin_file.read_text(encoding='utf-8')
                # Rechercher les registrations admin
                register_pattern = r'admin\.site\.register\s*\(\s*(\w+)'
                return re.findall(register_pattern, content)
            except:
                pass
        return []
    
    def generate_full_analysis(self):
        """Génère l'analyse complète du projet"""
        print("🔍 Analyse complète du projet LivraFaso...")
        
        # Backend
        self.analysis['backend']['apps'] = self.analyze_django_apps()
        
        # Frontend
        self.analysis['frontend']['templates'] = self.analyze_templates()
        self.analysis['frontend']['static_files'] = self.analyze_static_files()
        
        # Fichiers et structure
        self.analysis['files']['unused'] = self.detect_unused_files()
        self.analysis['files']['duplicates'] = self.detect_duplicates()
        
        # Dépendances
        self.analysis['dependencies']['backend_frontend'] = self.analyze_backend_frontend_dependencies()
        
        # Statistiques
        self._calculate_statistics()
        
        return self.analysis
    
    def _calculate_statistics(self):
        """Calcule les statistiques du projet"""
        total_files = 0
        by_type = defaultdict(int)
        
        # Compter tous les fichiers
        for root, dirs, files in os.walk(self.project_root):
            # Ignorer certains dossiers
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'node_modules']]
            
            for file in files:
                if not file.startswith('.'):
                    total_files += 1
                    ext = Path(file).suffix.lower()
                    by_type[ext if ext else 'no_extension'] += 1
        
        self.analysis['files']['total'] = total_files
        self.analysis['files']['by_type'] = dict(by_type)

def main():
    """Fonction principale"""
    project_root = Path.cwd()
    analyzer = ProjectAnalyzer(project_root)
    
    print("🚀 ANALYSE COMPLÈTE DU PROJET LIVRAFASO")
    print("=" * 50)
    
    analysis = analyzer.generate_full_analysis()
    
    # Sauvegarder l'analyse
    with open('PROJECT_ANALYSIS_COMPLETE.json', 'w', encoding='utf-8') as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False)
    
    print("✅ Analyse terminée - Résultats sauvegardés dans PROJECT_ANALYSIS_COMPLETE.json")
    
    # Afficher un résumé
    print("\n📊 RÉSUMÉ:")
    print(f"• Applications Django: {len(analysis['backend']['apps'])}")
    print(f"• Templates HTML: {len(analysis['frontend']['templates'])}")
    print(f"• Fichiers CSS: {len(analysis['frontend']['static_files']['css'])}")
    print(f"• Fichiers JS: {len(analysis['frontend']['static_files']['js'])}")
    print(f"• Total fichiers: {analysis['files']['total']}")
    print(f"• Fichiers inutilisés détectés: {len(analysis['files']['unused'])}")
    print(f"• Doublons détectés: {len(analysis['files']['duplicates'])}")
    
    return analysis

if __name__ == "__main__":
    main()
