# =============================================================================
# LinkedIn Automation Bot - One-click PowerShell bootstrap
# =============================================================================
# This script installs everything you need and gets the project ready to run.
# It is safe to re-run if anything fails partway through.
#
# What it does:
#   1. Verifies PowerShell, winget, and internet are available
#   2. Installs Python 3.12 (silently, via winget) if not already installed
#   3. Downloads the project ZIP from GitHub
#   4. Extracts it to %USERPROFILE%\Documents\linkedin-automation-bot
#   5. Runs setup.bat (creates venv, installs dependencies, downloads Chromium)
#   6. Loads starter templates and sequences via seed.py
#   7. Opens .env in Notepad so you can fill in your credentials
#   8. Prints clear next steps
#
# What you still have to do yourself afterwards:
#   - Sign up at https://console.anthropic.com and get an API key
#   - Fill in LINKEDIN_EMAIL, LINKEDIN_PASSWORD, ANTHROPIC_API_KEY in .env
#   - Double-click start.bat
#   - Allow the Windows Defender firewall popup on first run
#   - Log into LinkedIn in the Chromium window that opens
# =============================================================================

$ErrorActionPreference = "Stop"

# --- Configuration -----------------------------------------------------------
$RepoOwner   = "myonnone01"
$RepoName    = "linkedin-automation-bot"
$RepoBranch  = "claude/linkedin-automation-tool-MGeGK"
$ZipUrl      = "https://github.com/$RepoOwner/$RepoName/archive/refs/heads/$RepoBranch.zip"
$ZipFile     = Join-Path $env:TEMP "linkedin-bot.zip"
$TargetRoot  = Join-Path $env:USERPROFILE "Documents"
$TargetDir   = Join-Path $TargetRoot $RepoName

# --- Helpers -----------------------------------------------------------------

function Write-Banner {
    param([string]$Text)
    Write-Host ""
    Write-Host ("=" * 70) -ForegroundColor Cyan
    Write-Host "  $Text" -ForegroundColor Cyan
    Write-Host ("=" * 70) -ForegroundColor Cyan
    Write-Host ""
}

function Write-Step {
    param([int]$Num, [int]$Total, [string]$Text)
    Write-Host ""
    Write-Host "[$Num/$Total] $Text" -ForegroundColor Yellow
    Write-Host ("-" * 70) -ForegroundColor DarkGray
}

function Write-Ok {
    param([string]$Text)
    Write-Host "  OK  $Text" -ForegroundColor Green
}

function Write-Warn {
    param([string]$Text)
    Write-Host "  !!  $Text" -ForegroundColor Yellow
}

function Write-Err {
    param([string]$Text)
    Write-Host "  XX  $Text" -ForegroundColor Red
}

function Test-CommandExists {
    param([string]$Name)
    $null -ne (Get-Command $Name -ErrorAction SilentlyContinue)
}

function Refresh-Path {
    # After winget installs something, $env:Path in this session is stale.
    # Pull the latest from the registry.
    $machinePath = [System.Environment]::GetEnvironmentVariable("Path", "Machine")
    $userPath    = [System.Environment]::GetEnvironmentVariable("Path", "User")
    $env:Path = "$machinePath;$userPath"
}

# --- Begin ------------------------------------------------------------------

Write-Banner "LinkedIn Automation Bot - Bootstrap"
Write-Host "This will install Python (if needed), download the project," -ForegroundColor Gray
Write-Host "run setup.bat, and open .env for you to fill in." -ForegroundColor Gray
Write-Host ""
Write-Host "Estimated time: 5-10 minutes." -ForegroundColor Gray

$totalSteps = 9

# --- Step 1: PowerShell version check ----------------------------------------
Write-Step 1 $totalSteps "Checking PowerShell version"
if ($PSVersionTable.PSVersion.Major -lt 5) {
    Write-Err "PowerShell 5.1 or newer is required. You have $($PSVersionTable.PSVersion)."
    Write-Host ""
    Write-Host "Update Windows from Settings -> Windows Update, then re-run this script." -ForegroundColor Yellow
    exit 1
}
Write-Ok "PowerShell $($PSVersionTable.PSVersion) - good"

# --- Step 2: winget check ----------------------------------------------------
Write-Step 2 $totalSteps "Checking for winget (Windows package manager)"
if (-not (Test-CommandExists "winget")) {
    Write-Err "winget is not installed."
    Write-Host ""
    Write-Host "Install 'App Installer' from the Microsoft Store, then re-run:" -ForegroundColor Yellow
    Write-Host "  https://apps.microsoft.com/detail/9NBLGGH4NNS1" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Alternatively, install Python manually from python.org and use the" -ForegroundColor Yellow
    Write-Host "manual setup steps in GETTING_STARTED.md." -ForegroundColor Yellow
    exit 1
}
Write-Ok "winget found"

# --- Step 3: Python ----------------------------------------------------------
Write-Step 3 $totalSteps "Checking for Python 3.11+"
$needPython = $true
if (Test-CommandExists "python") {
    try {
        $pyVerOutput = & python --version 2>&1
        if ($pyVerOutput -match "Python (\d+)\.(\d+)") {
            $major = [int]$Matches[1]
            $minor = [int]$Matches[2]
            $isOk = ($major -gt 3) -or (($major -eq 3) -and ($minor -ge 11))
            if ($isOk) {
                Write-Ok "Found $pyVerOutput"
                $needPython = $false
            } else {
                Write-Warn "Found $pyVerOutput - too old, will install 3.12"
            }
        }
    } catch {
        Write-Warn "Python check failed, will install"
    }
}

if ($needPython) {
    Write-Host "  Installing Python 3.12 via winget (this can take 2-3 minutes)..." -ForegroundColor Gray
    try {
        winget install --id Python.Python.3.12 `
            --accept-package-agreements `
            --accept-source-agreements `
            --silent `
            --disable-interactivity | Out-Host
    } catch {
        Write-Err "Python install failed: $_"
        Write-Host ""
        Write-Host "Try installing Python manually from:" -ForegroundColor Yellow
        Write-Host "  https://www.python.org/downloads/windows/" -ForegroundColor Cyan
        Write-Host "Then re-run this script." -ForegroundColor Yellow
        exit 1
    }
    Refresh-Path
    if (-not (Test-CommandExists "python")) {
        Write-Err "Python installed but not yet on PATH for this session."
        Write-Host ""
        Write-Host "CLOSE THIS WINDOW, open a NEW PowerShell window, and re-run this script." -ForegroundColor Yellow
        Write-Host "(Windows updates the PATH only for new shells.)" -ForegroundColor Yellow
        exit 1
    }
    Write-Ok "Python installed: $(python --version)"
}

# --- Step 4: Download project ZIP --------------------------------------------
Write-Step 4 $totalSteps "Downloading project from GitHub"
Write-Host "  Source: $ZipUrl" -ForegroundColor Gray
try {
    Invoke-WebRequest -Uri $ZipUrl -OutFile $ZipFile -UseBasicParsing
} catch {
    Write-Err "Download failed: $($_.Exception.Message)"
    Write-Host ""
    if ($_.Exception.Response.StatusCode -eq 404) {
        Write-Host "The repo or branch may be private, or the URL is wrong." -ForegroundColor Yellow
        Write-Host "Check that this URL works in your browser:" -ForegroundColor Yellow
        Write-Host "  $ZipUrl" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "If the repo is private, you'll need to download the ZIP manually" -ForegroundColor Yellow
        Write-Host "from GitHub (logged in) and skip this script. See GETTING_STARTED.md." -ForegroundColor Yellow
    }
    exit 1
}
$zipSize = (Get-Item $ZipFile).Length
Write-Ok "Downloaded $([math]::Round($zipSize / 1KB, 1)) KB to $ZipFile"

# --- Step 5: Backup existing folder + extract --------------------------------
Write-Step 5 $totalSteps "Extracting to $TargetDir"

if (Test-Path $TargetDir) {
    $contents = Get-ChildItem $TargetDir -Force -ErrorAction SilentlyContinue
    if ($contents.Count -gt 0) {
        Write-Warn "$TargetDir already exists and is not empty."
        Write-Host ""
        Write-Host "  [O] Overwrite (existing folder will be backed up to ...backup-<timestamp>)" -ForegroundColor White
        Write-Host "  [S] Skip extract (use existing folder as-is, just re-run setup)" -ForegroundColor White
        Write-Host "  [A] Abort" -ForegroundColor White
        Write-Host ""
        $choice = Read-Host "Your choice [O/S/A]"
        switch -Wildcard ($choice.ToUpper()) {
            "O*" {
                $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
                $backup = "$TargetDir.backup-$stamp"
                Write-Host "  Moving existing folder to $backup ..." -ForegroundColor Gray
                Move-Item -Path $TargetDir -Destination $backup
                Write-Ok "Backed up existing folder"
            }
            "S*" {
                Write-Host "  Skipping extract; will re-run setup on existing folder." -ForegroundColor Gray
            }
            default {
                Write-Host "  Aborted." -ForegroundColor Yellow
                exit 0
            }
        }
    }
}

if (-not (Test-Path $TargetDir)) {
    if (-not (Test-Path $TargetRoot)) {
        New-Item -ItemType Directory -Path $TargetRoot | Out-Null
    }
    Write-Host "  Expanding archive..." -ForegroundColor Gray
    $tempExtract = Join-Path $env:TEMP "linkedin-bot-extract"
    if (Test-Path $tempExtract) { Remove-Item -Recurse -Force $tempExtract }
    Expand-Archive -Path $ZipFile -DestinationPath $tempExtract -Force
    # GitHub names extracted folders with branch name; find the one folder inside
    $extractedRoot = Get-ChildItem $tempExtract -Directory | Select-Object -First 1
    if (-not $extractedRoot) {
        Write-Err "ZIP appears empty - something went wrong with the download."
        exit 1
    }
    Move-Item -Path $extractedRoot.FullName -Destination $TargetDir
    Remove-Item -Recurse -Force $tempExtract
    Write-Ok "Extracted to $TargetDir"

    # Migrate old .env if present in a backup folder
    $latestBackup = Get-ChildItem -Path $TargetRoot -Directory -Filter "$RepoName.backup-*" -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
    if ($latestBackup) {
        $oldEnv = Join-Path $latestBackup.FullName ".env"
        if (Test-Path $oldEnv) {
            Copy-Item -Path $oldEnv -Destination (Join-Path $TargetDir ".env")
            Write-Ok "Migrated .env from previous install (your credentials are preserved)"
        }
    }
}

# --- Step 6: Run setup.bat ---------------------------------------------------
Write-Step 6 $totalSteps "Running setup.bat (this takes 3-5 minutes)"
Push-Location $TargetDir
try {
    Write-Host "  Creating Python venv, installing packages, downloading Chromium..." -ForegroundColor Gray
    Write-Host "  (You will see a wall of pip and Playwright output below. This is normal.)" -ForegroundColor Gray
    Write-Host ""
    & cmd /c "setup.bat"
    if ($LASTEXITCODE -ne 0) {
        Write-Err "setup.bat exited with code $LASTEXITCODE"
        Write-Host ""
        Write-Host "Scroll up in this window to find the actual error." -ForegroundColor Yellow
        Write-Host "Common causes:" -ForegroundColor Yellow
        Write-Host "  - corporate VPN blocking pypi.org" -ForegroundColor Yellow
        Write-Host "  - antivirus blocking the venv folder" -ForegroundColor Yellow
        Write-Host "  - out of disk space" -ForegroundColor Yellow
        exit 1
    }
    Write-Ok "setup.bat completed"
} finally {
    Pop-Location
}

# --- Step 7: Ensure .env exists ----------------------------------------------
Write-Step 7 $totalSteps "Preparing .env settings file"
$envFile  = Join-Path $TargetDir ".env"
$envSample = Join-Path $TargetDir ".env.example"
if (-not (Test-Path $envFile)) {
    if (Test-Path $envSample) {
        Copy-Item -Path $envSample -Destination $envFile
        Write-Ok "Created .env from .env.example"
    } else {
        Write-Warn ".env.example not found - you'll need to create .env manually"
    }
} else {
    Write-Ok ".env already exists (will not overwrite)"
}

# --- Step 8: Seed starter templates and sequences ----------------------------
Write-Step 8 $totalSteps "Loading starter templates and sequences"
$venvPython = Join-Path $TargetDir ".venv\Scripts\python.exe"
$seedScript = Join-Path $TargetDir "seed.py"
if ((Test-Path $venvPython) -and (Test-Path $seedScript)) {
    Push-Location $TargetDir
    try {
        & $venvPython seed.py
        if ($LASTEXITCODE -eq 0) {
            Write-Ok "Starter templates and sequences loaded"
        } else {
            Write-Warn "seed.py exited with code $LASTEXITCODE - you can run it manually later"
        }
    } finally {
        Pop-Location
    }
} else {
    Write-Warn "Could not find venv or seed.py - skipping starter data"
}

# --- Step 9: Open .env in Notepad and print next steps -----------------------
Write-Step 9 $totalSteps "Opening .env in Notepad for you to fill in"
if (Test-Path $envFile) {
    Start-Process notepad.exe -ArgumentList $envFile
    Write-Ok "Notepad opened with .env"
} else {
    Write-Warn ".env not found - cannot open it"
}

# --- Final next-steps banner -------------------------------------------------
Write-Banner "ALMOST DONE - 4 things you still need to do"

Write-Host "1. GET AN ANTHROPIC API KEY (one-time, ~3 minutes)" -ForegroundColor Yellow
Write-Host "   - Open: https://console.anthropic.com" -ForegroundColor White
Write-Host "   - Sign up or log in (Google sign-in works)" -ForegroundColor White
Write-Host "   - Settings -> Billing -> add a card -> prepay `$5" -ForegroundColor White
Write-Host "   - API Keys -> Create Key -> name it 'linkedin-bot' -> copy the key" -ForegroundColor White
Write-Host "     (it starts with sk-ant-... you only see it once, save it!)" -ForegroundColor White
Write-Host ""

Write-Host "2. FILL IN .env (the Notepad window that just opened)" -ForegroundColor Yellow
Write-Host "   Replace the blank values for these three lines:" -ForegroundColor White
Write-Host "     LINKEDIN_EMAIL=your-linkedin-email@example.com" -ForegroundColor Cyan
Write-Host "     LINKEDIN_PASSWORD=your-linkedin-password" -ForegroundColor Cyan
Write-Host "     ANTHROPIC_API_KEY=sk-ant-..." -ForegroundColor Cyan
Write-Host "   No quotes. No spaces around '='. Save (Ctrl+S) and close Notepad." -ForegroundColor White
Write-Host ""

Write-Host "3. START THE TOOL" -ForegroundColor Yellow
Write-Host "   Open File Explorer and go to:" -ForegroundColor White
Write-Host "     $TargetDir" -ForegroundColor Cyan
Write-Host "   Double-click start.bat" -ForegroundColor White
Write-Host "   Your browser will open to http://localhost:5000" -ForegroundColor White
Write-Host ""

Write-Host "4. FIRST-RUN ONLY - LinkedIn login + firewall popup" -ForegroundColor Yellow
Write-Host "   When you click Start in the dashboard:" -ForegroundColor White
Write-Host "   - Windows asks 'allow Python through firewall?' -> tick Private, Allow" -ForegroundColor White
Write-Host "   - A Chromium browser window opens -> log into LinkedIn manually" -ForegroundColor White
Write-Host "     (email, password, any 2FA code on your phone)" -ForegroundColor White
Write-Host "   - After login the tool takes over. Future runs reuse your session." -ForegroundColor White
Write-Host ""

Write-Banner "Bootstrap complete - good luck!"
Write-Host "Project location: $TargetDir" -ForegroundColor Gray
Write-Host ""
Read-Host "Press Enter to close this window"
