@echo off
title AI ConsoleMate - Install
cd /d "%~dp0"
echo ============================================
echo   AI ConsoleMate - install
echo ============================================
echo.

rem 1) Python
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PY="%LOCALAPPDATA%\Programs\Python\Python312\python.exe""
if not defined PY (
  echo [1/3] Python is not installed. It will be installed now with winget ^(free, official python.org build^).
  echo       Press any key to continue, or close this window to cancel.
  pause >nul
  winget install --id Python.Python.3.12 -e --scope user --accept-package-agreements --accept-source-agreements
  if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PY="%LOCALAPPDATA%\Programs\Python\Python312\python.exe""
)
if not defined PY (
  echo Python install failed. Please install Python 3.12 from https://www.python.org/downloads/ and run install.bat again.
  pause
  exit /b 1
)
echo [1/3] Python OK

rem 2) Packages
echo [2/3] Installing packages...
%PY% -m pip install -q --disable-pip-version-check -r requirements.txt
if errorlevel 1 (
  echo Package install failed. Check the internet connection and run install.bat again.
  pause
  exit /b 1
)
echo [2/3] Packages OK

rem 3) Desktop shortcut "AI 콘솔메이트" (Korean name built from character codes so this file stays plain ASCII)
powershell -NoProfile -ExecutionPolicy Bypass -Command "$n = 'AI ' + [string]::new([char[]](0xCF58,0xC194,0xBA54,0xC774,0xD2B8)); $p = Join-Path ([Environment]::GetFolderPath('Desktop')) ($n + '.lnk'); $s = (New-Object -ComObject WScript.Shell).CreateShortcut($p); $s.TargetPath = '%~dp0start.bat'; $s.WorkingDirectory = '%~dp0'; $s.IconLocation = $env:SystemRoot + '\System32\SndVol.exe,0'; $s.WindowStyle = 7; $s.Save()"
echo [3/3] Desktop shortcut created
echo.
echo Done! Starting AI ConsoleMate. The setup wizard will open in the browser.
echo.
call "%~dp0start.bat"
