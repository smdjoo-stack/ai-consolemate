@echo off
cd /d "%~dp0"
echo Practice mode: starting the FAKE WING console. Set "wing_ip" to "127.0.0.1" in config.json first.
start "FAKE WING" py -3 wing_simulator.py
py -3 -m pip install -q -r requirements.txt
py -3 app.py
pause
