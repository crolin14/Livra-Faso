it@echo off
echo Creation d'un utilisateur administrateur LivraFaso...
echo.

REM S'assurer que l'environnement virtuel est actif
if not defined VIRTUAL_ENV (
    echo Activation de l'environnement virtuel...
    call venv\Scripts\activate.bat
)

echo Verification de Django...
python manage.py check --deploy

echo.
echo Creation de l'utilisateur administrateur...
python create_admin_user.py

echo.
echo ✅ Script termine!
echo.
echo Prochaines etapes:
echo   1. python manage.py migrate
echo   2. python manage.py runserver
echo   3. Acceder au dashboard: http://127.0.0.1:8000/admin-dashboard/

pause
