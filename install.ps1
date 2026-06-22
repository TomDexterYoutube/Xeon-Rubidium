$ErrorActionPreference = "Stop"

# Prevent running as Administrator (mimicking the non-root check)
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if ($isAdmin) {
    Write-Host "[!] Please run this script as a normal user, not as Administrator." -ForegroundColor Yellow
    Exit
}

# Define Paths
$XEON_DIR = Join-Path $HOME ".xeon"
$BIN_DIR = Join-Path $HOME ".local\bin"
$REPO_URL = "https://github.com/TomDexterYoutube/Rubidium/archive/refs/heads/main.zip"

# Create directories if they don't exist
New-Item -ItemType Directory -Force -Path $XEON_DIR | Out-Null
New-Item -ItemType Directory -Force -Path $BIN_DIR | Out-Null

# Copy local xeon.py to the setup folder
if (Test-Path "xeon.py") {
    Copy-Item "xeon.py" -Destination $XEON_DIR -Force
} else {
    Write-Host "[!] xeon.py not found in current directory. Proceeding anyway..." -ForegroundColor Yellow
}

Write-Host "[1/5] Checking system..."
# Check for Python
if (-not (Get-Command "python" -ErrorAction SilentlyContinue)) {
    Write-Host "[!] Python is not installed or not in your PATH." -ForegroundColor Red
    Exit
}

# Check Python Version (Requires 3.13+)
$pyVersion = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
if ([version]$pyVersion -lt [version]"3.13") {
    Write-Host "[!] Python 3.13+ required. Your current version is $pyVersion. Please update Python." -ForegroundColor Red
    Exit
}

# Create a temporary directory
$TMP_DIR = Join-Path [System.IO.Path]::GetTempPath() ([System.IO.Path]::GetRandomFileName())
New-Item -ItemType Directory -Path $TMP_DIR | Out-Null

Write-Host "[2/5] Fetching source..."
$zipPath = Join-Path $TMP_DIR "rubidium.zip"
try {
    Invoke-WebRequest -Uri $REPO_URL -OutFile $zipPath -UseBasicParsing
} catch {
    Write-Host "[!] Download failed. Check connection." -ForegroundColor Red
    Remove-Item -Recurse -Force $TMP_DIR
    Exit
}

Write-Host "[3/5] Extracting..."
Expand-Archive -Path $zipPath -DestinationPath $TMP_DIR -Force

# Locate the extracted folder (handling variable naming)
$extractedFolder = Get-ChildItem -Path $TMP_DIR -Directory | Where-Object { $_.Name -like "*Rubidium*" } | Select-Object -First 1

Write-Host "[4/5] Copying files..."
if ($extractedFolder) {
    # Copy all files inside the extracted folder to .xeon
    Copy-Item -Path "$($extractedFolder.FullName)\*" -Destination $XEON_DIR -Recurse -Force
}

# Clean up temp folder
Remove-Item -Recurse -Force $TMP_DIR

Write-Host "[5/5] Creating wrapper script..."
# Windows uses .cmd or .ps1 files for command wrappers in PATH. We'll create a cmd batch file.
$wrapperPath = Join-Path $BIN_DIR "xeon.cmd"
$wrapperContent = @"
@echo off
if "%~1"=="update" (
    echo Updating Rubidium...
    powershell -Command "Invoke-WebRequest -Uri 'https://github.com/TomDexterYoutube/Xeon-Rubidium/main/xeon.py' -OutFile '$XEON_DIR\xeon.py' -UseBasicParsing"
    powershell -Command "`$tmp = Join-Path [System.IO.Path]::GetTempPath() ([System.IO.Path]::GetRandomFileName()); Invoke-WebRequest -Uri '$REPO_URL' -OutFile (Join-Path `$tmp 'rubidium.zip') -UseBasicParsing; Expand-Archive -Path (Join-Path `$tmp 'rubidium.zip') -DestinationPath `$tmp -Force; `$ext = Get-ChildItem `$tmp -Directory | Where-Object { `$_.Name -like '*Rubidium*' } | Select-Object -First 1; Copy-Item -Path '`$(`$ext.FullName)\*' -Destination '$XEON_DIR' -Recurse -Force; Remove-Item -Recurse -Force `$tmp"
    echo Update complete!
    goto :eof
)

python "$XEON_DIR\xeon.py" %*
"@

Set-Content -Path $wrapperPath -Value $wrapperContent

# Add $BIN_DIR to User PATH if it isn't already there
$userPath = [Environment]::GetEnvironmentVariable("PATH", "User")
if ($userPath -notlike "*$BIN_DIR*") {
    [Environment]::SetEnvironmentVariable("PATH", "$userPath;$BIN_DIR", "User")
    Write-Host "✔ Added $BIN_DIR to your User PATH environment variable." -ForegroundColor Green
}

Write-Host "`n========================================================" -ForegroundColor Green
Write-Host "Installation complete!" -ForegroundColor Green
Write-Host "Please RESTART your terminal/PowerShell window to apply PATH changes." -ForegroundColor Yellow
Write-Host "Run 'xeon' to start!" -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Green
