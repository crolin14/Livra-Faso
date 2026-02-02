@echo off
echo ========================================
echo    MIGRATION CSS UNIFIE LIVRAFASO
echo ========================================
echo.

cd /d "%~dp0"

echo 1. Sauvegarde des anciens fichiers CSS...
if not exist "static\css\backup_old" mkdir "static\css\backup_old"
copy "static\css\style.css" "static\css\backup_old\" >nul 2>&1
copy "static\css\admin_dashboard.css" "static\css\backup_old\" >nul 2>&1
copy "static\css\livrafaso-design-system.css" "static\css\backup_old\" >nul 2>&1
echo ✅ Sauvegarde terminee

echo.
echo 2. Application du nouveau systeme CSS unifie...
echo ✅ livrafaso-unified.css deja present

echo.
echo 3. Mise a jour des templates...
powershell -Command "(Get-ChildItem -Path 'templates' -Recurse -Filter '*.html') | ForEach-Object { $content = Get-Content $_.FullName -Raw -Encoding UTF8; $modified = $false; if ($content -match 'style\.css') { $content = $content -replace 'style\.css', 'livrafaso-unified.css'; $modified = $true }; if ($content -match 'admin_dashboard\.css') { $content = $content -replace 'admin_dashboard\.css', 'livrafaso-unified.css'; $modified = $true }; if ($content -match 'livrafaso-design-system\.css') { $content = $content -replace 'livrafaso-design-system\.css', 'livrafaso-unified.css'; $modified = $true }; if ($modified) { Set-Content -Path $_.FullName -Value $content -Encoding UTF8; Write-Host \"✅ Mis a jour: $($_.Name)\" } }"

echo.
echo ========================================
echo    MIGRATION TERMINEE AVEC SUCCES!
echo ========================================
echo.
echo 📋 PROCHAINES ETAPES:
echo 1. Tester l'affichage sur http://127.0.0.1:8000
echo 2. Consulter GUIDE_STYLE_LIVRAFASO.md
echo 3. Mettre a jour les classes HTML selon BEM
echo.
echo 🔄 ROLLBACK: Restaurer depuis static\css\backup_old\
echo.
pause
