@echo off
setlocal

cd /d "%~dp0"

echo =========================================
echo  Aggiornamento Portafoglio Mobile
echo =========================================
echo.

py -3 tools\export_mobile_snapshot.py
if errorlevel 1 (
    echo.
    echo ERRORE: generazione snapshot non riuscita.
    pause
    exit /b 1
)

echo.
echo Snapshot aggiornato.
echo.
set /p PORTFOLIO_DASHBOARD_CODE=Codice dashboard: 
if "%PORTFOLIO_DASHBOARD_CODE%"=="" (
    echo.
    echo ERRORE: codice mancante.
    pause
    exit /b 1
)

node tools\encrypt_snapshot.mjs
if errorlevel 1 (
    echo.
    echo ERRORE: cifratura snapshot non riuscita.
    set PORTFOLIO_DASHBOARD_CODE=
    pause
    exit /b 1
)
set PORTFOLIO_DASHBOARD_CODE=

git rev-parse --is-inside-work-tree >nul 2>&1
if errorlevel 1 (
    echo.
    echo Questa cartella non e ancora collegata a GitHub.
    echo Quando creeremo il repository, questo file potra fare anche commit e push.
    pause
    exit /b 0
)

git status --short
git add encrypted_snapshot.json encrypted_snapshot.js
git diff --cached --quiet
if not errorlevel 1 (
    echo.
    echo Nessuna modifica da pubblicare.
    pause
    exit /b 0
)

git commit -m "Update portfolio snapshot"
if errorlevel 1 (
    echo.
    echo ERRORE: commit non riuscito.
    pause
    exit /b 1
)

git push
if errorlevel 1 (
    echo.
    echo ERRORE: push non riuscito.
    pause
    exit /b 1
)

echo.
echo Dashboard aggiornata e inviata a GitHub.
pause
