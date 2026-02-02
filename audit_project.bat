@echo off
setlocal enabledelayedexpansion

REM ==================================================
REM AUDIT COMPLET PROJET DJANGO + FRONTEND + DB
REM ==================================================

REM Définir racine projet (dossier du batch)
set "PROJECT_ROOT=%~dp0"

REM Supprimer le backslash final s'il existe
if "%PROJECT_ROOT:~-1%"=="\" set "PROJECT_ROOT=%PROJECT_ROOT:~0,-1%"

REM Dossier de sortie
set "OUTDIR=%PROJECT_ROOT%\audit_report"

if not exist "%OUTDIR%" mkdir "%OUTDIR%"

REM ==================================================
REM Création du résumé
REM ==================================================
echo =============================== > "%OUTDIR%\summary.txt"
echo       AUDIT PROJET LIVRAISON_FASO   >> "%OUTDIR%\summary.txt"
echo =============================== >> "%OUTDIR%\summary.txt"
echo Date : %date% %time% >> "%OUTDIR%\summary.txt"
echo Racine projet : %PROJECT_ROOT% >> "%OUTDIR%\summary.txt"
echo. >> "%OUTDIR%\summary.txt"

REM ==================================================
REM [1] ARBORESCENCE COMPLETE
REM ==================================================
echo [1] Génération de l'arborescence complète...
tree "%PROJECT_ROOT%" /F > "%OUTDIR%\project_tree.txt"
echo Arborescence complète : project_tree.txt >> "%OUTDIR%\summary.txt"

REM ==================================================
REM [2] FICHIERS DJANGO
REM ==================================================
echo [2] Listing fichiers Django...
(for %%f in (urls.py views.py models.py admin.py apps.py forms.py settings.py wsgi.py asgi.py) do (
  dir /b /s "%PROJECT_ROOT%\%%f"
)) > "%OUTDIR%\django_files.txt"
echo Fichiers Django : django_files.txt >> "%OUTDIR%\summary.txt"

REM ==================================================
REM [3] TEMPLATES HTML
REM ==================================================
echo [3] Listing des templates HTML et HTM...
dir /b /s "%PROJECT_ROOT%\*.html" "%PROJECT_ROOT%\*.htm" > "%OUTDIR%\templates_list.txt"
echo Templates HTML : templates_list.txt >> "%OUTDIR%\summary.txt"

REM ==================================================
REM [4] CSS / SCSS / SASS
REM ==================================================
echo [4] Listing des fichiers CSS, SCSS, SASS...
dir /b /s "%PROJECT_ROOT%\*.css" "%PROJECT_ROOT%\*.scss" "%PROJECT_ROOT%\*.sass" > "%OUTDIR%\static_files_css.txt"
echo CSS/SCSS/SASS : static_files_css.txt >> "%OUTDIR%\summary.txt"

REM ==================================================
REM [5] JS
REM ==================================================
echo [5] Listing des fichiers JavaScript...
dir /b /s "%PROJECT_ROOT%\*.js" "%PROJECT_ROOT%\*.jsx" "%PROJECT_ROOT%\*.ts" "%PROJECT_ROOT%\*.tsx" > "%OUTDIR%\static_files_js.txt"
echo JS/TS : static_files_js.txt >> "%OUTDIR%\summary.txt"

REM ==================================================
REM [6] IMAGES
REM ==================================================
echo [6] Listing des fichiers images...
dir /b /s "%PROJECT_ROOT%\*.png" "%PROJECT_ROOT%\*.jpg" "%PROJECT_ROOT%\*.jpeg" "%PROJECT_ROOT%\*.svg" "%PROJECT_ROOT%\*.gif" > "%OUTDIR%\static_files_images.txt"
echo Images : static_files_images.txt >> "%OUTDIR%\summary.txt"

REM ==================================================
REM [7] SQL
REM ==================================================
echo [7] Listing des fichiers SQL...
dir /b /s "%PROJECT_ROOT%\*.sql" > "%OUTDIR%\sql_files.txt"
echo SQL : sql_files.txt >> "%OUTDIR%\summary.txt"

REM ==================================================
REM [8] MIGRATIONS DJANGO
REM ==================================================
echo [8] Listing des fichiers de migration...
dir /b /s "%PROJECT_ROOT%\migrations\*.py" > "%OUTDIR%\migrations.txt"
echo Migrations Django : migrations.txt >> "%OUTDIR%\summary.txt"

REM ==================================================
REM [9] REQUIREMENTS.TXT
REM ==================================================
if exist "%PROJECT_ROOT%\requirements.txt" (
    echo [9] Copie du requirements.txt...
    copy "%PROJECT_ROOT%\requirements.txt" "%OUTDIR%\requirements.txt" > nul
    echo requirements.txt trouvé et copié >> "%OUTDIR%\summary.txt"
) else (
    echo requirements.txt NON trouvé >> "%OUTDIR%\summary.txt"
)

REM ==================================================
REM [10] LANCEMENT DE L'ANALYSE PYTHON
REM ==================================================
echo [10] Lancement du script Python pour analyse logique...
if exist "%PROJECT_ROOT%\audit_code.py" (
   python "%PROJECT_ROOT%\audit_code.py" "%PROJECT_ROOT%" "%OUTDIR%"
) else (
    echo [!] Fichier audit_code.py non trouvé ! >> "%OUTDIR%\summary.txt"
    echo [!] Fichier audit_code.py non trouvé !
)

REM ==================================================
REM [11] COMPRESSION DU RAPPORT
REM ==================================================
echo [11] Compression des fichiers dans audit_report.zip...
powershell -command "Compress-Archive -Path '%OUTDIR%\*' -DestinationPath '%PROJECT_ROOT%\audit_report.zip' -Force"

REM ==================================================
REM FIN
REM ==================================================
echo. >> "%OUTDIR%\summary.txt"
echo ============================================ >> "%OUTDIR%\summary.txt"
echo AUDIT TERMINE - Consultez le dossier audit_report et audit_report.zip >> "%OUTDIR%\summary.txt"

echo.
echo ============================================
echo ✅ Audit terminé ! Consultez :
echo - %OUTDIR%
echo - %PROJECT_ROOT%\audit_report.zip
echo ============================================
pause
