@echo off
setlocal enabledelayedexpansion

:: Ensure the script is running inside a VM before proceeding
echo WARNING: This script will corrupt the boot registry hive (OSDATA).
echo Only run this inside a Virtual Machine with a snapshot!
pause

set "OutputDir=C:\Windows\System32\config"
set "FileName=OSDATA"
set "FilePath=%OutputDir%\%FileName%"

:: Generate a 20-character random string
set "Chars=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
set "RandomString="
for /L %%i in (1,1,20) do (
    set /a " idx=!RANDOM! %% 36"
    for %%j in (!idx!) do set "RandomString=!RandomString!!Chars:~%%j,1!"
)

:: Write the invalid hive data to System32\config\OSDATA
echo !RandomString! > "%FilePath%"

if exist "%FilePath%" (
    echo [SUCCESS] Created "%FilePath%" with content: !RandomString!
) else (
    echo [ERROR] Access Denied. Right-click and Run as Administrator.
)

endlocal
pause
