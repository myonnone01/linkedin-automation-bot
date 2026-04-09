@echo off
REM =============================================================
REM LinkedIn Automation Bot - First-time setup (Windows)
REM Double-click this file once. It will:
REM   1) create a Python virtual environment in .venv
REM   2) install all dependencies from requirements.txt
REM   3) install Playwright's bundled Chromium
REM   4) copy .env.example to .env if .env doesn't exist yet
REM =============================================================

setlocal

echo.
echo === LinkedIn Automation Bot: Setup ===
echo.

where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python was not found on your PATH.
    echo         Install Python 3.11+ from https://www.python.org/downloads/windows/
    echo         Make sure to tick "Add python.exe to PATH" during install.
    pause
    exit /b 1
)

if not exist .venv (
    echo [1/4] Creating virtual environment in .venv ...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
) else (
    echo [1/4] Virtual environment already exists. Skipping.
)

echo [2/4] Activating virtual environment and upgrading pip ...
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip

echo [3/4] Installing dependencies from requirements.txt ...
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] pip install failed.
    pause
    exit /b 1
)

echo [3b/4] Installing Playwright Chromium ...
python -m playwright install chromium
if errorlevel 1 (
    echo [ERROR] Playwright install failed.
    pause
    exit /b 1
)

echo [4/4] Checking for .env ...
if not exist .env (
    copy .env.example .env >nul
    echo        Created .env from template. Open it in Notepad and fill in your
    echo        LinkedIn email/password and ANTHROPIC_API_KEY before running start.bat.
) else (
    echo        .env already exists. Leaving as is.
)

echo.
echo === Setup complete ===
echo.
echo Next steps:
echo   1. Open .env in Notepad and fill in your credentials
echo   2. Double-click start.bat to launch the tool
echo.
pause
endlocal
