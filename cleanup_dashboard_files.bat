@echo off
echo Nettoyage des fichiers dashboard temporaires...

REM Supprimer les fichiers temporaires
del /q *.pyc 2>nul
del /q __pycache__ 2>nul

REM Redemarrer le serveur Django
echo Redemarrage du serveur Django...
taskkill /f /im python.exe 2>nul
timeout /t 2 /nobreak >nul

echo Serveur pret pour redemarrage
echo Executez: python manage.py runserver
pause