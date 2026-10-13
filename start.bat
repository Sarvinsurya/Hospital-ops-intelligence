@echo off
REM Hospital Operations Intelligence System - Windows launcher
REM Double-click this file or run:  start.bat
cd /d "%~dp0"

REM Find a usable Python launcher
where py >nul 2>nul
if %ERRORLEVEL%==0 (
    py -3 launch.py %*
    goto :eof
)
where python >nul 2>nul
if %ERRORLEVEL%==0 (
    python launch.py %*
    goto :eof
)
echo Python 3 not found. Install Python 3.12 from https://www.python.org/downloads/
echo Make sure to tick "Add Python to PATH" during installation.
pause
