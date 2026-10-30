@echo off
cd /d "%~dp0"
python -m venv .venv
if errorlevel 1 goto failed
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto failed
.venv\Scripts\python.exe ..\dinov3_standard_seed42_9061fbac4697_WebApp_Bundle\dinov3_standard_seed42_9061fbac4697\check_bundle.py --device cpu
if errorlevel 1 goto failed
echo Setup complete. Open Start_SpiceScope.cmd.
pause
exit /b 0
:failed
echo Setup did not complete. Check the error above and retry.
pause
exit /b 1
