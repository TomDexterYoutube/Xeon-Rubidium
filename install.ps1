```powershell
$ErrorActionPreference = "Stop"

# ============================================================
# Xeon / Rubidium Windows Installer
# ============================================================

# ------------------------------------------------------------
# Prevent Administrator execution
# ------------------------------------------------------------

$isAdmin = (
    [Security.Principal.WindowsPrincipal](
        [Security.Principal.WindowsIdentity]::GetCurrent()
    )
).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator
)

if ($isAdmin) {
    Write-Host "[!] Please run this script as a normal user, not as Administrator." -ForegroundColor Yellow
    exit 1
}

# ------------------------------------------------------------
# Configuration
# ------------------------------------------------------------

$XEON_DIR       = Join-Path $HOME ".xeon"
$VIRE_DIR       = Join-Path $XEON_DIR "vire"

# Use a proper Windows user bin directory.
$BIN_DIR        = Join-Path $HOME ".local\bin"

$REPO_URL       = "https://github.com/TomDexterYoutube/Rubidium/archive/refs/heads/main.zip"
$VIRE_REPO_URL  = "https://github.com/TomDexterYoutube/Rubidium-Vire/archive/refs/heads/main.zip"
$XEON_RAW_URL   = "https://raw.githubusercontent.com/TomDexterYoutube/Xeon-Rubidium/main/xeon.py"

# ------------------------------------------------------------
# Helper functions
# ------------------------------------------------------------

function Write-Step {
    param(
        [string]$Number,
        [string]$Message
    )

    Write-Host "[$Number] $Message" -ForegroundColor Cyan
}

function Write-ErrorMessage {
    param(
        [string]$Message
    )

    Write-Host "[!] $Message" -ForegroundColor Red
}

function Download-File {
    param(
        [string]$Url,
        [string]$Destination
    )

    try {
        Invoke-WebRequest `
            -Uri $Url `
            -OutFile $Destination `
            -UseBasicParsing

        return $true
    }
    catch {
        Write-ErrorMessage "Failed to download:"
        Write-Host "    $Url" -ForegroundColor DarkGray
        Write-Host "    $($_.Exception.Message)" -ForegroundColor DarkGray

        return $false
    }
}

function Find-ExtractedFolder {
    param(
        [string]$Directory,
        [string]$Pattern,
        [string]$ExcludePattern = ""
    )

    $folders = Get-ChildItem `
        -Path $Directory `
        -Directory `
        -ErrorAction SilentlyContinue |
        Where-Object {
            $_.Name -like $Pattern
        }

    if ($ExcludePattern -ne "") {
        $folders = $folders | Where-Object {
            $_.Name -notlike $ExcludePattern
        }
    }

    return $folders | Select-Object -First 1
}

# ------------------------------------------------------------
# Create directories
# ------------------------------------------------------------

New-Item -ItemType Directory -Force -Path $XEON_DIR | Out-Null
New-Item -ItemType Directory -Force -Path $VIRE_DIR | Out-Null
New-Item -ItemType Directory -Force -Path $BIN_DIR | Out-Null

# ------------------------------------------------------------
# Check Python
# ------------------------------------------------------------

Write-Step "1/6" "Checking system..."

$pythonCommand = Get-Command "python" -ErrorAction SilentlyContinue

if (-not $pythonCommand) {
    Write-ErrorMessage "Python is not installed or is not available in PATH."
    Write-Host "Install Python 3.13+ and make sure 'Add Python to PATH' is enabled." -ForegroundColor Yellow
    exit 1
}

# Get Python version safely.
try {
    $pyVersionText = & python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"

    if ($LASTEXITCODE -ne 0) {
        throw "Python returned exit code $LASTEXITCODE"
    }

    $pyVersion = [version]$pyVersionText.Trim()
}
catch {
    Write-ErrorMessage "Could not determine the installed Python version."
    exit 1
}

Write-Host "    Python: $pyVersion" -ForegroundColor Gray
Write-Host "    Path:   $($pythonCommand.Source)" -ForegroundColor Gray

if ($pyVersion -lt [version]"3.13") {
    Write-ErrorMessage "Python 3.13+ is required."
    Write-Host "    Current version: $pyVersion" -ForegroundColor Yellow
    exit 1
}

# ------------------------------------------------------------
# Temporary directory
# ------------------------------------------------------------

$TMP_DIR = Join-Path `
    ([System.IO.Path]::GetTempPath()) `
    ("xeon-" + [System.Guid]::NewGuid().ToString())

New-Item -ItemType Directory -Path $TMP_DIR | Out-Null

try {

    # --------------------------------------------------------
    # Copy local xeon.py if available
    # --------------------------------------------------------

    if (Test-Path ".\xeon.py" -PathType Leaf) {
        Copy-Item `
            ".\xeon.py" `
            (Join-Path $XEON_DIR "xeon.py") `
            -Force

        Write-Host "    Installed local xeon.py" -ForegroundColor Gray
    }
    else {
        Write-Host "    Local xeon.py not found." -ForegroundColor Yellow
    }

    # --------------------------------------------------------
    # Fetch Rubidium
    # --------------------------------------------------------

    Write-Step "2/6" "Fetching Rubidium source..."

    $rubidiumZip = Join-Path $TMP_DIR "rubidium.zip"

    if (-not (Download-File $REPO_URL $rubidiumZip)) {
        throw "Rubidium download failed."
    }

    # --------------------------------------------------------
    # Extract Rubidium
    # --------------------------------------------------------

    Write-Step "3/6" "Extracting Rubidium..."

    Expand-Archive `
        -Path $rubidiumZip `
        -DestinationPath $TMP_DIR `
        -Force

    $rubidiumFolder = Find-ExtractedFolder `
        -Directory $TMP_DIR `
        -Pattern "*Rubidium*" `
        -ExcludePattern "*Vire*"

    if (-not $rubidiumFolder) {
        throw "Could not find the extracted Rubidium directory."
    }

    Write-Host "    Found: $($rubidiumFolder.Name)" -ForegroundColor Gray

    # --------------------------------------------------------
    # Copy Rubidium
    # --------------------------------------------------------

    Write-Host "    Installing Rubidium..." -ForegroundColor Gray

    Copy-Item `
        -Path (Join-Path $rubidiumFolder.FullName "*") `
        -Destination $XEON_DIR `
        -Recurse `
        -Force

    # --------------------------------------------------------
    # Fetch Vire
    # --------------------------------------------------------

    Write-Step "4/6" "Fetching Vire..."

    $vireZip = Join-Path $TMP_DIR "vire.zip"

    if (Download-File $VIRE_REPO_URL $vireZip) {

        Expand-Archive `
            -Path $vireZip `
            -DestinationPath $TMP_DIR `
            -Force

        $vireFolder = Find-ExtractedFolder `
            -Directory $TMP_DIR `
            -Pattern "*Rubidium-Vire*"

        if (-not $vireFolder) {
            # Fallback in case GitHub changes the archive name.
            $vireFolder = Find-ExtractedFolder `
                -Directory $TMP_DIR `
                -Pattern "*Vire*"
        }

        if ($vireFolder) {

            Write-Host "    Found: $($vireFolder.Name)" -ForegroundColor Gray

            Copy-Item `
                -Path (Join-Path $vireFolder.FullName "*") `
                -Destination $VIRE_DIR `
                -Recurse `
                -Force

            Write-Host "    Vire installed." -ForegroundColor Green
        }
        else {
            Write-Host "[!] Could not locate extracted Vire files." -ForegroundColor Yellow
        }
    }
    else {
        Write-Host "[!] Vire download failed. Continuing without Vire." -ForegroundColor Yellow
    }

    # --------------------------------------------------------
    # Verify xeon.py
    # --------------------------------------------------------

    if (-not (Test-Path (Join-Path $XEON_DIR "xeon.py") -PathType Leaf)) {

        Write-Host "    Local xeon.py was not available." -ForegroundColor Yellow
        Write-Host "    Downloading official Xeon launcher..." -ForegroundColor Yellow

        $xeonPath = Join-Path $XEON_DIR "xeon.py"

        if (-not (Download-File $XEON_RAW_URL $xeonPath)) {
            throw "Could not install xeon.py."
        }
    }

    # --------------------------------------------------------
    # Clean temporary files
    # --------------------------------------------------------

    Write-Step "5/6" "Cleaning temporary files..."

}
finally {

    if (Test-Path $TMP_DIR) {
        Remove-Item `
            -Path $TMP_DIR `
            -Recurse `
            -Force `
            -ErrorAction SilentlyContinue
    }
}

# ------------------------------------------------------------
# Create command wrapper
# ------------------------------------------------------------

Write-Step "6/6" "Creating xeon command..."

$wrapperPath = Join-Path $BIN_DIR "xeon.cmd"

$xeonPython = Join-Path $XEON_DIR "xeon.py"

# CMD only needs to launch Python.
# Everything else belongs inside xeon.py.
$wrapperContent = @"
@echo off
python "$xeonPython" %*
"@

Set-Content `
    -Path $wrapperPath `
    -Value $wrapperContent `
    -Encoding ASCII

# ------------------------------------------------------------
# Add .local\bin to User PATH
# ------------------------------------------------------------

$userPath = [Environment]::GetEnvironmentVariable(
    "PATH",
    "User"
)

if ([string]::IsNullOrWhiteSpace($userPath)) {
    $userPath = ""
}

# Split PATH into actual entries instead of doing a substring search.
$pathEntries = $userPath -split ";" |
    Where-Object { -not [string]::IsNullOrWhiteSpace($_) }

$alreadyInPath = $false

foreach ($entry in $pathEntries) {
    try {
        if (
            [System.IO.Path]::GetFullPath($entry).TrimEnd("\") -ieq
            [System.IO.Path]::GetFullPath($BIN_DIR).TrimEnd("\")
        ) {
            $alreadyInPath = $true
            break
        }
    }
    catch {
        # Ignore malformed PATH entries.
    }
}

if (-not $alreadyInPath) {

    if ([string]::IsNullOrWhiteSpace($userPath)) {
        $newPath = $BIN_DIR
    }
    else {
        $newPath = "$userPath;$BIN_DIR"
    }

    [Environment]::SetEnvironmentVariable(
        "PATH",
        $newPath,
        "User"
    )

    Write-Host "    Added $BIN_DIR to User PATH." -ForegroundColor Green
}
else {
    Write-Host "    $BIN_DIR is already in User PATH." -ForegroundColor Gray
}

# ------------------------------------------------------------
# Finished
# ------------------------------------------------------------

Write-Host ""
Write-Host "========================================================" -ForegroundColor Green
Write-Host " Installation complete!" -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Xeon installed to:" -ForegroundColor Gray
Write-Host "    $XEON_DIR" -ForegroundColor White
Write-Host ""
Write-Host "Command wrapper:" -ForegroundColor Gray
Write-Host "    $wrapperPath" -ForegroundColor White
Write-Host ""
Write-Host "IMPORTANT: Restart your terminal/PowerShell window." -ForegroundColor Yellow
Write-Host ""
Write-Host "Then run:" -ForegroundColor Gray
Write-Host "    xeon" -ForegroundColor Green
Write-Host ""
```
