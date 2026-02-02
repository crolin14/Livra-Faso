#!/usr/bin/env python3
"""
Script d'analyse complète des URLs et templates Django
Détecte toutes les erreurs NoReverseMatch et autres problèmes d'URLs
Compatible Django >= 4.2 et Windows 11
"""

import os
import re
import json
from pathlib import Path
from collections import defaultdict
import ast

class DjangoURLAnalyzer:
    def __init__(self, project_root):
        self.project_root = Path(project_root)
        self.url_patterns = {}
        self.namespaces = {}
        self.template_urls = {}
        self.errors = []
        self.warnings = []
        
    def find_urls_files(self):
        """Trouve tous les fichiers urls.py du projet"""
        urls_files = []
        for root, dirs, files in os.walk(self.project_root):
            # Ignorer les environnements virtuels
            if 'venv' in root or 'env' in root or '__pycache__' in root:
                continue
            if 'urls.py' in files:
                urls_files.append(Path(root) / 'urls.py')
        return urls_files
    
    def parse_urls_file(self, file_path):
        """Parse un fichier urls.py et extrait les patterns"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extraire app_name (namespace)
            app_name_match = re.search(r"app_name\s*=\s*['\"]([^'\"]+)['\"]", content)
            namespace = app_name_match.group(1) if app_name_match else None
            
            # Extraire les patterns d'URL
            patterns = []
            
            # Patterns path() simples
            path_patterns = re.findall(
                r"path\s*\(\s*['\"]([^'\"]*)['\"],\s*[^,]+,?\s*(?:name\s*=\s*['\"]([^'\"]+)['\"])?\s*\)",
                content
            )
            
            for pattern, name in path_patterns:
                if name:
                    patterns.append({
                        'pattern': pattern,
                        'name': name,
                        'namespace': namespace,
                        'file': str(file_path)
                    })
            
            # Patterns include()
            include_patterns = re.findall(
                r"path\s*\(\s*['\"]([^'\"]*)['\"],\s*include\s*\(\s*['\"]([^'\"]+)['\"](?:,\s*namespace\s*=\s*['\"]([^'\"]+)['\"])?\s*\)\s*\)",
                content
            )
            
            for pattern, include_path, include_namespace in include_patterns:
                if include_namespace:
                    self.namespaces[include_namespace] = {
                        'pattern': pattern,
                        'include': include_path,
                        'file': str(file_path)
                    }
            
            return patterns, namespace
            
        except Exception as e:
            self.errors.append(f"Erreur lors du parsing de {file_path}: {str(e)}")
            return [], None
    
    def find_template_files(self):
        """Trouve tous les fichiers template"""
        template_files = []
        template_dirs = [
            self.project_root / 'templates',
            self.project_root / 'template',
        ]
        
        # Chercher aussi dans les apps
        for root, dirs, files in os.walk(self.project_root):
            if 'templates' in dirs and 'venv' not in root:
                template_dirs.append(Path(root) / 'templates')
        
        for template_dir in template_dirs:
            if template_dir.exists():
                for root, dirs, files in os.walk(template_dir):
                    for file in files:
                        if file.endswith(('.html', '.htm')):
                            template_files.append(Path(root) / file)
        
        return template_files
    
    def parse_template_urls(self, template_file):
        """Parse un template et extrait toutes les références {% url %}"""
        try:
            with open(template_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Pattern pour {% url 'name' %} et {% url "name" %}
            url_patterns = re.findall(
                r"{%\s*url\s+['\"]([^'\"]+)['\"](?:\s+[^%]*)?\s*%}",
                content
            )
            
            urls_found = []
            for line_num, line in enumerate(content.split('\n'), 1):
                for match in re.finditer(r"{%\s*url\s+['\"]([^'\"]+)['\"]", line):
                    urls_found.append({
                        'url_name': match.group(1),
                        'line': line_num,
                        'content': line.strip()
                    })
            
            return urls_found
            
        except Exception as e:
            self.errors.append(f"Erreur lors du parsing du template {template_file}: {str(e)}")
            return []
    
    def analyze_project(self):
        """Analyse complète du projet"""
        print("🔍 Analyse des fichiers URLs...")
        
        # 1. Analyser tous les fichiers urls.py
        urls_files = self.find_urls_files()
        all_patterns = []
        
        for urls_file in urls_files:
            patterns, namespace = self.parse_urls_file(urls_file)
            all_patterns.extend(patterns)
            
            if namespace:
                self.namespaces[namespace] = {
                    'file': str(urls_file),
                    'patterns': patterns
                }
        
        # Créer un index des URLs disponibles
        for pattern in all_patterns:
            name = pattern['name']
            namespace = pattern.get('namespace')
            
            if namespace:
                full_name = f"{namespace}:{name}"
                self.url_patterns[full_name] = pattern
            
            self.url_patterns[name] = pattern
        
        print(f"✅ Trouvé {len(all_patterns)} patterns d'URL dans {len(urls_files)} fichiers")
        
        # 2. Analyser tous les templates
        print("🔍 Analyse des templates...")
        template_files = self.find_template_files()
        
        for template_file in template_files:
            urls_found = self.parse_template_urls(template_file)
            if urls_found:
                self.template_urls[str(template_file)] = urls_found
        
        print(f"✅ Analysé {len(template_files)} templates")
        
        # 3. Vérifier les correspondances
        self.check_url_matches()
        
        return self.generate_report()
    
    def check_url_matches(self):
        """Vérifie que toutes les URLs des templates existent"""
        print("🔍 Vérification des correspondances URL...")
        
        for template_path, urls in self.template_urls.items():
            for url_ref in urls:
                url_name = url_ref['url_name']
                
                # Vérifier si l'URL existe
                if url_name not in self.url_patterns:
                    self.errors.append({
                        'type': 'NoReverseMatch',
                        'template': template_path,
                        'line': url_ref['line'],
                        'url_name': url_name,
                        'content': url_ref['content'],
                        'message': f"URL '{url_name}' introuvable"
                    })
    
    def generate_report(self):
        """Génère un rapport complet"""
        report = {
            'summary': {
                'total_url_patterns': len(self.url_patterns),
                'total_namespaces': len(self.namespaces),
                'total_templates': len(self.template_urls),
                'total_errors': len(self.errors),
                'total_warnings': len(self.warnings)
            },
            'url_patterns': self.url_patterns,
            'namespaces': self.namespaces,
            'errors': self.errors,
            'warnings': self.warnings,
            'suggestions': self.generate_suggestions()
        }
        
        return report
    
    def generate_suggestions(self):
        """Génère des suggestions de correction"""
        suggestions = []
        
        for error in self.errors:
            if error['type'] == 'NoReverseMatch':
                url_name = error['url_name']
                
                # Chercher des URLs similaires
                similar_urls = []
                for existing_url in self.url_patterns.keys():
                    if url_name.lower() in existing_url.lower() or existing_url.lower() in url_name.lower():
                        similar_urls.append(existing_url)
                
                suggestion = {
                    'error': error,
                    'possible_fixes': []
                }
                
                if similar_urls:
                    suggestion['possible_fixes'].append({
                        'type': 'similar_names',
                        'message': f"URLs similaires trouvées: {', '.join(similar_urls[:3])}"
                    })
                
                # Vérifier si c'est un problème de namespace
                if ':' not in url_name:
                    for namespace in self.namespaces.keys():
                        potential_url = f"{namespace}:{url_name}"
                        if potential_url in self.url_patterns:
                            suggestion['possible_fixes'].append({
                                'type': 'missing_namespace',
                                'message': f"Essayez '{potential_url}' au lieu de '{url_name}'"
                            })
                
                suggestions.append(suggestion)
        
        return suggestions
    
    def print_report(self, report):
        """Affiche le rapport de manière lisible"""
        print("\n" + "="*80)
        print("📊 RAPPORT D'ANALYSE DES URLs ET TEMPLATES")
        print("="*80)
        
        # Résumé
        summary = report['summary']
        print(f"\n📈 RÉSUMÉ:")
        print(f"   • Patterns d'URL trouvés: {summary['total_url_patterns']}")
        print(f"   • Namespaces: {summary['total_namespaces']}")
        print(f"   • Templates analysés: {summary['total_templates']}")
        print(f"   • Erreurs détectées: {summary['total_errors']}")
        print(f"   • Avertissements: {summary['total_warnings']}")
        
        # Namespaces
        if report['namespaces']:
            print(f"\n🏷️  NAMESPACES DÉTECTÉS:")
            for namespace, info in report['namespaces'].items():
                print(f"   • {namespace} -> {info.get('file', 'N/A')}")
        
        # Erreurs
        if report['errors']:
            print(f"\n❌ ERREURS DÉTECTÉES:")
            for i, error in enumerate(report['errors'], 1):
                print(f"\n   {i}. {error['type']}")
                print(f"      Template: {error['template']}")
                print(f"      Ligne {error['line']}: {error['content']}")
                print(f"      Problème: {error['message']}")
        
        # Suggestions
        if report['suggestions']:
            print(f"\n💡 SUGGESTIONS DE CORRECTION:")
            for i, suggestion in enumerate(report['suggestions'], 1):
                error = suggestion['error']
                print(f"\n   {i}. Pour l'erreur '{error['url_name']}' dans {Path(error['template']).name}:")
                
                for fix in suggestion['possible_fixes']:
                    print(f"      → {fix['message']}")
        
        # URLs disponibles (échantillon)
        print(f"\n📋 ÉCHANTILLON D'URLs DISPONIBLES:")
        url_sample = list(report['url_patterns'].keys())[:10]
        for url in url_sample:
            print(f"   • {url}")
        
        if len(report['url_patterns']) > 10:
            print(f"   ... et {len(report['url_patterns']) - 10} autres")

def main():
    project_root = Path(__file__).parent
    analyzer = DjangoURLAnalyzer(project_root)
    
    print("🚀 Démarrage de l'analyse Django URLs et Templates")
    print(f"📁 Projet: {project_root}")
    
    try:
        report = analyzer.analyze_project()
        analyzer.print_report(report)
        
        # Sauvegarder le rapport
        report_file = project_root / 'url_analysis_report.json'
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"\n💾 Rapport sauvegardé dans: {report_file}")
        
        # Retourner le code de sortie approprié
        return 1 if report['errors'] else 0
        
    except Exception as e:
        print(f"❌ Erreur critique: {str(e)}")
        return 1

if __name__ == "__main__":
    exit(main())
