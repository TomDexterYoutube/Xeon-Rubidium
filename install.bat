@echo off
echo Checking system dependencies...

:: Check for Python
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo Python not found. Installing via winget...
    winget install Python.Python.3 -e --accept-package-agreements --accept-source-agreements
) else (
    echo Python is installed.
)

:: Check for Clang/LLVM
where clang >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo Clang not found. Installing via winget...
    winget install LLVM.LLVM -e --accept-package-agreements --accept-source-agreements
) else (
    echo Clang is installed.
)

echo Installing Xeon and Rubidium...

set XEON_DIR=%USERPROFILE%\.xeon

:: Create the target directory if it doesn't exist
if not exist "%XEON_DIR%" mkdir "%XEON_DIR%"

:: Copy the compiler files and the build tool
xcopy /E /I /Y rubidium\* "%XEON_DIR%"
copy /Y xeon.py "%XEON_DIR%"

:: Create the executable wrapper
echo @echo off > "%XEON_DIR%\xeon.bat"
echo python "%XEON_DIR%\xeon.py" %%* >> "%XEON_DIR%\xeon.bat"

echo.
echo Installation complete.
echo.
echo IMPORTANT: If dependencies were just installed, you may need to restart your terminal.
echo Please add "%XEON_DIR%" to your system PATH environment variable to use 'xeon' globally.
echo To update the compiler later, place the new .py files into %XEON_DIR%
pause
