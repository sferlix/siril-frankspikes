@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

set "VENV_DIR=%~dp0.venv"
set "PY_EXE="

call :find_python
if defined PY_EXE goto :have_python

echo.
echo Python non risulta installato su questo computer.
echo Provo a installarlo automaticamente (serve una connessione a Internet)...
echo.
call :install_python

echo.
echo ============================================================
echo  Installazione di Python avviata/completata.
echo  Chiudi questa finestra e fai doppio click di nuovo su
echo  run_frankspikes.bat per continuare (serve una nuova
echo  finestra perche' Windows aggiorni i percorsi di sistema).
echo ============================================================
pause
exit /b 0

:have_python
echo Uso Python: %PY_EXE%

if not exist "%VENV_DIR%\Scripts\python.exe" (
    echo Creo l'ambiente virtuale in "%VENV_DIR%"...
    "%PY_EXE%" -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo ERRORE nella creazione dell'ambiente virtuale.
        pause
        exit /b 1
    )
)

set "VENV_PY=%VENV_DIR%\Scripts\python.exe"

echo Verifico le dipendenze (la prima volta puo' richiedere qualche minuto)...
"%VENV_PY%" -m pip install --quiet --upgrade pip
"%VENV_PY%" -m pip install --quiet -r "%~dp0requirements.txt"
if errorlevel 1 (
    echo ERRORE nell'installazione delle dipendenze.
    pause
    exit /b 1
)

echo Avvio frankSpikes...
"%VENV_PY%" "%~dp0frankSpikes.py"
if errorlevel 1 (
    echo.
    echo frankSpikes si e' chiuso con un errore - vedi sopra.
    pause
)
exit /b 0

rem ---------------------------------------------------------------
rem Looks for a usable Python 3 interpreter, preferring the official
rem "py" launcher (more reliable than "python" alone, which on a
rem clean Windows install is often just the Microsoft Store stub).
rem ---------------------------------------------------------------
:find_python
set "PY_EXE="
where py >nul 2>nul
if not errorlevel 1 (
    for /f "delims=" %%P in ('py -3 -c "import sys; print(sys.executable)" 2^>nul') do set "PY_EXE=%%P"
    if defined PY_EXE exit /b 0
)
where python >nul 2>nul
if not errorlevel 1 (
    python -c "import sys; exit(0 if sys.version_info[:2] >= (3,9) else 1)" >nul 2>nul
    if not errorlevel 1 (
        for /f "delims=" %%P in ('python -c "import sys; print(sys.executable)" 2^>nul') do set "PY_EXE=%%P"
    )
)
exit /b 0

rem ---------------------------------------------------------------
rem Tries winget first (built into Windows 10 1809+/11), falls back
rem to downloading the official python.org installer and running it
rem silently for the current user only (no admin rights needed).
rem ---------------------------------------------------------------
:install_python
where winget >nul 2>nul
if not errorlevel 1 (
    echo Installo Python tramite winget...
    winget install -e --id Python.Python.3.12 --silent --accept-package-agreements --accept-source-agreements
    exit /b 0
)

echo winget non disponibile - scarico l'installer ufficiale da python.org...
set "PY_INSTALLER=%TEMP%\frankspikes_python_installer.exe"
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "try { Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.7/python-3.12.7-amd64.exe' -OutFile '%PY_INSTALLER%' -UseBasicParsing } catch { exit 1 }"
if not exist "%PY_INSTALLER%" (
    echo Download dell'installer di Python fallito.
    echo Installalo manualmente da https://www.python.org/downloads/ e riesegui questo script.
    exit /b 1
)
echo Eseguo l'installer di Python (solo per l'utente corrente, nessun diritto da amministratore richiesto)...
"%PY_INSTALLER%" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0
exit /b 0
