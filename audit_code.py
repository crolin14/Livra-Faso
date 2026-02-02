import os
import sys
import re

# ============================================
# 1. RÉCUPÉRATION DES ARGUMENTS
# ============================================
if len(sys.argv) > 1:
    project_root = sys.argv[1].strip('"')
else:
    project_root = os.getcwd()  # Par défaut : répertoire courant

if len(sys.argv) > 2:
    out_dir = sys.argv[2].strip('"')
else:
    out_dir = os.path.join(project_root, "audit_report")  # Par défaut : dossier audit_report

# Normalisation des chemins Windows
project_root = os.path.normpath(project_root)
out_dir = os.path.normpath(out_dir)

# Création du répertoire de sortie si inexistant
os.makedirs(out_dir, exist_ok=True)
report_path = os.path.join(out_dir, "code_analysis.txt")

issues = []

# ============================================
# 2. VÉRIFICATION STRUCTURE DJANGO
# ============================================
def check_django_structure():
    critical_files = ["settings.py", "urls.py", "wsgi.py", "asgi.py"]
    for f in critical_files:
        found = False
        for root, _, files in os.walk(project_root):
            if f in files:
                found = True
                break
        if not found:
            issues.append(f"[CRITIQUE] Fichier manquant : {f}")

# ============================================
# 3. ANALYSE DES URLS ET VUES (TEMPLATES)
# ============================================
def analyze_urls_and_views():
    views_templates = []
    for root, _, files in os.walk(project_root):
        for f in files:
            if f == "views.py":
                path = os.path.join(root, f)
                with open(path, encoding="utf-8", errors="ignore") as file:
                    content = file.read()
                    views_templates.extend(re.findall(r"render\(.*?,\s*['\"](.*?)['\"]", content))

    # Vérifier si les templates existent vraiment
    for tpl in views_templates:
        tpl_path = os.path.join(project_root, tpl.replace("/", os.sep))
        if not os.path.exists(tpl_path):
            issues.append(f"[LOGIQUE] Template manquant pour la view : {tpl}")

# ============================================
# 4. ANALYSE DES FORMULAIRES (UI)
# ============================================
def check_html_buttons():
    for root, _, files in os.walk(project_root):
        for f in files:
            if f.endswith(".html"):
                with open(os.path.join(root, f), encoding="utf-8", errors="ignore") as file:
                    content = file.read()
                    if "<form" in content and "type=\"submit\"" not in content:
                        issues.append(f"[UI] Formulaire sans bouton submit : {f}")

# ============================================
# 5. MIGRATIONS DJANGO
# ============================================
def check_migrations():
    migrations_found = False
    for root, _, files in os.walk(project_root):
        if "migrations" in root and any(f.endswith(".py") for f in files):
            migrations_found = True
            break
    if not migrations_found:
        issues.append("[CRITIQUE] Aucune migration trouvée !")

# ============================================
# 6. ANALYSE FRONT-END (CSS/JS vides)
# ============================================
def check_empty_frontend_files():
    for root, _, files in os.walk(project_root):
        for f in files:
            if f.endswith((".css", ".js", ".scss", ".sass")):
                path = os.path.join(root, f)
                if os.path.getsize(path) == 0:
                    issues.append(f"[FRONT] Fichier vide détecté : {f}")

# ============================================
# 7. LANCEMENT DES ANALYSES
# ============================================
check_django_structure()
analyze_urls_and_views()
check_html_buttons()
check_migrations()
check_empty_frontend_files()

# ============================================
# 8. ÉCRITURE DU RAPPORT
# ============================================
with open(report_path, "w", encoding="utf-8") as report:
    report.write("=== RAPPORT ANALYSE CODE ===\n")
    report.write(f"Projet : {project_root}\n\n")
    if issues:
        for issue in issues:
            report.write(f"- {issue}\n")
    else:
        report.write("✅ Aucun problème majeur détecté.\n")

print(f"\n✅ Analyse terminée.\nRapport disponible ici : {report_path}")
