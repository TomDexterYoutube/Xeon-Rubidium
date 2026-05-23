@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0"

:: 1. Variables & Setup
set "XEON_DIR=%USERPROFILE%\.xeon"
set "BIN_DIR=%USERPROFILE%\.xeon\bin"
set "RUBIDIUM_URL=https://github.com/TomDexterYoutube/Rubidium/archive/refs/heads/main.zip"

echo [1/6] Environment Check...
:: Python Version Check (Must be 3.8+)
python -c "import sys; exit(0 if sys.version_info >= (3,8) else 1)" >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [!] Python 3.8+ not detected. Attempting install...
    winget install Python.Python.3 -e --accept-package-agreements
)

where clang >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [!] Clang not detected. Attempting install...
    winget install LLVM.LLVM -e --accept-package-agreements
)

:: 2. Cleanup (Stale File Conflict)
echo [2/6] Cleaning previous installation...
if exist "%XEON_DIR%\Rubidium" rmdir /s /q "%XEON_DIR%\Rubidium"
if exist "%XEON_DIR%\xeon.py" del /f /q "%XEON_DIR%\xeon.py"
if exist "%XEON_DIR%\debug.py" del /f /q "%XEON_DIR%\debug.py"

:: 3. Download & Verify
echo [3/6] Fetching Rubidium...
powershell -Command "$wc = New-Object System.Net.WebClient; try { $wc.DownloadFile('%RUBIDIUM_URL%', 'rubidium.zip') } catch { exit 1 }"
if %ERRORLEVEL% neq 0 ( echo [!] Download failed. Check internet/proxy. & pause & exit /b 1 )

:: Verify size (must be > 5kb)
for %%I in (rubidium.zip) do if %%~zI LSS 5000 ( echo [!] Download corrupt. & del rubidium.zip & pause & exit /b 1 )

echo [4/6] Extracting...
powershell -Command "Expand-Archive -Path 'rubidium.zip' -DestinationPath '.' -Force; Remove-Item 'rubidium.zip'"
for /d %%D in (*Rubidium*) do ( if /i not "%%~nxD"=="Rubidium" ren "%%D" "Rubidium" )

:: 4. Installation
echo [5/6] Copying files...
if not exist "%XEON_DIR%" mkdir "%XEON_DIR%"
xcopy /E /I /Y "Rubidium" "%XEON_DIR%\Rubidium\" >nul
if exist "xeon.py" copy /Y "xeon.py" "%XEON_DIR%\" >nul
if exist "debug.py" copy /Y "debug.py" "%XEON_DIR%\" >nul

:: 5. Create Wrapper & PATH
echo [6/6] Finalizing...
( echo @echo off & echo python "%XEON_DIR%\xeon.py" %%* ) > "%BIN_DIR%\xeon.bat"
powershell -Command "$p = [Environment]::GetEnvironmentVariable('Path', 'User'); if (-not $p.Contains('%BIN_DIR%')) { [Environment]::SetEnvironmentVariable('Path', '%BIN_DIR%;' + $p, 'User') }"

echo Installation complete! Please restart your terminal.
pause
