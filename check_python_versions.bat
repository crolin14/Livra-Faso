@echo off
echo Verification des versions Python installees...
echo.

echo === VERSIONS PYTHON DISPONIBLES ===
python --version 2>nul && echo Python (defaut): && python --version
python3 --version 2>nul && echo Python3: && python3 --version
py --version 2>nul && echo Py launcher: && py --version
py -3 --version 2>nul && echo Py -3: && py -3 --version
py -3.11 --version 2>nul && echo Python 3.11: && py -3.11 --version
py -3.12 --version 2>nul && echo Python 3.12: && py -3.12 --version

echo.
echo === EMPLACEMENTS PYTHON ===
where python 2>nul
where python3 2>nul
where py 2>nul

echo.
echo === ENVIRONNEMENT VIRTUEL ACTUEL ===
if defined VIRTUAL_ENV (
    echo Environnement virtuel actif: %VIRTUAL_ENV%
    echo Version Python dans venv:
    python --version
) else (
    echo Aucun environnement virtuel actif
)

echo.
echo === RECOMMANDATIONS ===
echo 1. Utilisez 'py -3.11' ou 'py -3.12' pour Django
echo 2. Recreez votre environnement virtuel avec la bonne version
echo 3. Evitez Python 3.13 (problemes avec psycopg2)

pause
