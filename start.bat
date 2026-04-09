@echo off
REM =============================================================
REM LinkedIn Automation Bot - Start (Windows)
REM Activates the virtual environment and launches the web app.
REM The app will print its LAN URL and auto-open your browser.
REM =============================================================

setlocal

if not exist .venv\Scripts\activate.bat (
    echo [ERROR] .venv not found. Run setup.bat first.
    pause
    exit /b 1
)

if not exist .env (
    echo [ERROR] .env not found. Run setup.bat first, then edit .env with your credentials.
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat
python app.py

REM If python exits (Ctrl+C or error), hold the window so the user can read any output.
pause
endlocal
