@echo off
setlocal enabledelayedexpansion

:: 1. Variables & Setup
set "XEON_DIR=%USERPROFILE%\.xeon"
set "BIN_DIR=%USERPROFILE%\.xeon\bin"
set "RUBIDIUM_URL=https://github.com/TomDexterYoutube/Rubidium/archive/refs/heads/main.zip"

echo [1/5] Environment Check...

python -c "import sys; sys.exit(0 if sys.version_info >= (3,13) else 1)" >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [!] Python 3.13+ not detected. Attempting install...
    winget install Python.Python.3 -e --accept-package-agreements
)

where clang >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [!] Clang not detected. Attempting install...
    winget install LLVM.LLVM -e --accept-package-agreements
)

set "TMP_DIR=%TEMP%\xeon_install_tmp"
if exist "%TMP_DIR%" rmdir /s /q "%TMP_DIR%"
mkdir "%TMP_DIR%"
cd /d "%TMP_DIR%"

:: 2. Download
echo [2/5] Fetching Rubidium...
curl.exe -L -f -s "%RUBIDIUM_URL%" -o rubidium.zip
if %ERRORLEVEL% neq 0 ( 
    echo [!] Download failed. Check internet/proxy. 
    pause 
    exit /b 1 
)

echo [3/5] Extracting...
powershell -Command "Expand-Archive -Path 'rubidium.zip' -DestinationPath '.' -Force"

if exist "Rubidium" rmdir /s /q "Rubidium"
for /d %%D in (*Rubidium*) do (
    if /i not "%%~nxD"=="Rubidium" ren "%%D" "Rubidium"
)

:: 3. Installation
echo [4/5] Copying files...
if not exist "%XEON_DIR%" mkdir "%XEON_DIR%"
if not exist "%BIN_DIR%" mkdir "%BIN_DIR%"

:: Copy everything directly into the root of ~/.xeon/
xcopy /E /I /Y "Rubidium\*" "%XEON_DIR%\" >nul

cd /d "%~dp0"
rmdir /s /q "%TMP_DIR%"

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
echo set "UPDATE_TMP=%%TEMP%%\xeon_update"
echo if exist "%%UPDATE_TMP%%" rmdir /s /q "%%UPDATE_TMP%%"
echo mkdir "%%UPDATE_TMP%%"
echo cd /d "%%UPDATE_TMP%%"
echo curl.exe -L -f -s "%RUBIDIUM_URL%" -o rubidium.zip
echo powershell -Command "Expand-Archive -Path 'rubidium.zip' -DestinationPath '.' -Force"
echo if exist "Rubidium" rmdir /s /q "Rubidium"
echo for /d %%%%D in (*Rubidium*^) do ren "%%%%D" "Rubidium"
echo :: Overwrite without deleting directly into the root of ~/.xeon/
echo if not exist "%XEON_DIR%" mkdir "%XEON_DIR%"
echo xcopy /E /I /Y "Rubidium\*" "%XEON_DIR%\" ^>nul
echo cd /d "%USERPROFILE%"
echo rmdir /s /q "%%UPDATE_TMP%%"
echo echo Update complete!
echo exit /b 0
) > "%BIN_DIR%\xeon.bat"

powershell -Command "$p = [Environment]::GetEnvironmentVariable('Path', 'User'); if (-not $p.Contains('%BIN_DIR%')) { [Environment]::SetEnvironmentVariable('Path', '%BIN_DIR%;' + $p, 'User') }"

echo.
echo ========================================================
echo Installation complete! 
echo Please RESTART your terminal for the PATH to take effect.
echo Run 'xeon' to start or 'xeon update' to update.
echo ========================================================
pause
