@echo off
chcp 65001 > nul
setlocal EnableDelayedExpansion

echo ========================================
echo   MIGRATION AUTOMATIQUE RBAC UUID
echo ========================================

REM Activation de l'environnement virtuel
if exist "venv\Scripts\activate.bat" (
    echo [1/2] Activation de l'environnement virtuel...
    call venv\Scripts\activate.bat
) else (
    echo ERREUR: Environnement virtuel non trouve
    echo Veuillez d'abord executer: create_venv.bat
    pause
    exit /b 1
)

echo.
echo [2/2] Execution du script automatique...
python auto_fix_rbac_uuid.py

if !ERRORLEVEL! EQU 0 (
    echo.
    echo ========================================
    echo   MIGRATION RBAC UUID REUSSIE!
    echo ========================================
    echo.
    echo Prochaines etapes:
    echo 1. python manage.py migrate (autres apps)
    echo 2. python manage.py runserver
    echo.
) else (
    echo.
    echo ========================================
    echo   ERREUR LORS DE LA MIGRATION
    echo ========================================
    echo Consultez les messages d'erreur ci-dessus
)

pause
endlocal
