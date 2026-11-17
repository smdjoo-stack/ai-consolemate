@echo off
title AI ConsoleMate
cd /d "%~dp0"

rem If it is already running, just open the screen again
curl.exe -s -o nul --max-time 2 http://127.0.0.1:8800/api/status && (
  start "" http://localhost:8800
  exit /b
)

rem Find Python (py launcher, or the default user install folder)
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PY="%LOCALAPPDATA%\Programs\Python\Python312\python.exe""
if not defined PY where python >nul 2>nul && set "PY=python"
if not defined PY (
  echo Python is not installed. Please run install.bat first.
  pause
  exit /b 1
)

echo Starting AI ConsoleMate. Closing this window stops the program.
%PY% -m pip install -q --disable-pip-version-check -r requirements.txt
%PY% app.py
pause
