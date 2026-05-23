@echo off
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
echo ✔ Installation complete!
echo.
echo IMPORTANT: Please add "%XEON_DIR%" to your system PATH environment variable to use 'xeon' globally.
echo To update the compiler later, just drop the new .py files into %XEON_DIR%
pause
