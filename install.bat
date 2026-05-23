@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0"

:: 1. Variables & Setup
set "XEON_DIR=%USERPROFILE%\.xeon"
set "BIN_DIR=%USERPROFILE%\.xeon\bin"
set "RUBIDIUM_URL=https://github.com/TomDexterYoutube/Rubidium/archive/refs/heads/main.zip"

echo [1/5] Environment Check...
:: Python Version Check (Must be 3.13+)
python -c "import sys; exit(0 if sys.version_info >= (3,13) else 1)" >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [!] Python 3.13+ not detected. Attempting install...
    winget install Python.Python.3 -e --accept-package-agreements
)

where clang >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [!] Clang not detected. Attempting install...
    winget install LLVM.LLVM -e --accept-package-agreements
)

:: 2. Download
echo [2/5] Fetching Rubidium...
powershell -Command "$wc = New-Object System.Net.WebClient; try { $wc.DownloadFile('%RUBIDIUM_URL%', 'rubidium.zip') } catch { exit 1 }"
if %ERRORLEVEL% neq 0 ( echo [!] Download failed. Check internet/proxy. & pause & exit /b 1 )

echo [3/5] Extracting...
:: -Force ensures it overwrites existing extracted files silently
powershell -Command "Expand-Archive -Path 'rubidium.zip' -DestinationPath '.' -Force"
for /d %%D in (*Rubidium*) do ( if /i not "%%~nxD"=="Rubidium" ren "%%D" "Rubidium" )

:: 3. Installation
echo [4/5] Copying files (overwriting existing)...
if not exist "%XEON_DIR%\Rubidium" mkdir "%XEON_DIR%\Rubidium"
if not exist "%BIN_DIR%" mkdir "%BIN_DIR%"
xcopy /E /I /Y "Rubidium\*" "%XEON_DIR%\Rubidium\" >nul
if exist "xeon.py" copy /Y "xeon.py" "%XEON_DIR%\" >nul
if exist "debug.py" copy /Y "debug.py" "%XEON_DIR%\" >nul

:: 4. Create Wrapper & PATH
echo [5/5] Finalizing...
(
echo @echo off
echo if /I "%%~1"=="update" goto :update
echo python "%XEON_DIR%\xeon.py" %%*
echo exit /b %%ERRORLEVEL%%
echo.
echo :update
echo echo Updating Xeon and Rubidium...
echo set "TEMP_DIR=%%TEMP%%\xeon_update"
echo if not exist "%%TEMP_DIR%%" mkdir "%%TEMP_DIR%%"
echo cd /d "%%TEMP_DIR%%"
echo powershell -Command "$wc = New-Object System.Net.WebClient; $wc.DownloadFile('%RUBIDIUM_URL%', 'rubidium.zip')"
echo powershell -Command "Expand-Archive -Path 'rubidium.zip' -DestinationPath '.' -Force"
echo for /d %%%%D in (*Rubidium*^) do ren "%%%%D" "Rubidium"
echo :: Overwrite without deleting
echo if not exist "%XEON_DIR%\Rubidium" mkdir "%XEON_DIR%\Rubidium"
echo xcopy /E /I /Y "Rubidium\*" "%XEON_DIR%\Rubidium\" ^>nul
echo if exist "Rubidium\xeon.py" copy /Y "Rubidium\xeon.py" "%XEON_DIR%\" ^>nul
echo if exist "Rubidium\debug.py" copy /Y "Rubidium\debug.py" "%XEON_DIR%\" ^>nul
echo cd /d "%%~dp0"
echo rmdir /s /q "%%TEMP_DIR%%"
echo echo Update complete!
echo exit /b 0
) > "%BIN_DIR%\xeon.bat"

powershell -Command "$p = [Environment]::GetEnvironmentVariable('Path', 'User'); if (-not $p.Contains('%BIN_DIR%')) { [Environment]::SetEnvironmentVariable('Path', '%BIN_DIR%;' + $p, 'User') }"

echo Installation complete! Please restart your terminal.
pause
