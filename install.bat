@echo off
setlocal

echo Checking system dependencies...

:: 1. Dependency Check (Python)
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo Python not found. Installing via winget...
    winget install Python.Python.3 -e --accept-package-agreements --accept-source-agreements
) else (
    echo Python is installed.
)

:: 2. Dependency Check (Clang/LLVM)
where clang >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo Clang not found. Installing via winget...
    winget install LLVM.LLVM -e --accept-package-agreements --accept-source-agreements
) else (
    echo Clang is installed.
)

:: 3. Installation
echo Installing Xeon and Rubidium...
set XEON_DIR=%USERPROFILE%\.xeon
set BIN_DIR=%USERPROFILE%\.xeon\bin

if not exist "%XEON_DIR%" mkdir "%XEON_DIR%"
if not exist "%BIN_DIR%" mkdir "%BIN_DIR%"

:: Copy compiler files
xcopy /E /I /Y rubidium\* "%XEON_DIR%\"
copy /Y xeon.py "%XEON_DIR%\"

:: 4. Create Wrapper
echo @echo off > "%BIN_DIR%\xeon.bat"
echo python "%XEON_DIR%\xeon.py" %%* >> "%BIN_DIR%\xeon.bat"

:: 5. Smart Path Configuration
:: Check if BIN_DIR is already in PATH
echo Checking PATH configuration...
echo "%PATH%" | findstr /C:"%BIN_DIR%" >nul
if %ERRORLEVEL% neq 0 (
    :: Permanently add to User PATH
    setx PATH "%PATH%;%BIN_DIR%"
    echo ✔ Added %BIN_DIR% to User PATH.
) else (
    echo ✔ %BIN_DIR% is already in your PATH.
)

echo --------------------------------------------------------
echo Installation complete! 
echo Please restart your command prompt or PowerShell to use the 'xeon' command.
pause
