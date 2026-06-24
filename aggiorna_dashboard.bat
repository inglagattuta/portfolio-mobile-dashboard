@echo off
setlocal

cd /d "%~dp0"
set "PYTHON_EXE=C:\Users\franc\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"

echo =========================================
echo  Aggiornamento Portafoglio Mobile
echo =========================================
echo.

if not exist "%PYTHON_EXE%" (
    echo ERRORE: Python non trovato:
    echo %PYTHON_EXE%
    echo.
    pause
    exit /b 1
)

"%PYTHON_EXE%" tools\export_mobile_snapshot.py
if errorlevel 1 (
    echo.
    echo ERRORE: generazione snapshot non riuscita.
    pause
    exit /b 1
)

echo.
if not exist ".dashboard_code" (
    echo.
    echo ERRORE: file .dashboard_code mancante.
    echo Crea il file .dashboard_code in questa cartella con il codice della dashboard.
    pause
    exit /b 1
)

set /p PORTFOLIO_DASHBOARD_CODE=<.dashboard_code
if "%PORTFOLIO_DASHBOARD_CODE%"=="" (
    echo.
    echo ERRORE: .dashboard_code vuoto.
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

del /q portfolio_snapshot.json snapshot.js 2>nul

git rev-parse --is-inside-work-tree >nul 2>&1
if errorlevel 1 (
    echo.
    echo ERRORE: questa cartella non e un repository Git.
    pause
    exit /b 1
)

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
echo Dashboard aggiornata e inviata a GitHub Pages.
pause
