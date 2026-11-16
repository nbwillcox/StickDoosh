@echo off
cd /d "%~dp0..\.."
"C:\Users\nicho\Documents\ComfyUI\.venv\Scripts\python.exe" tools\vocal\mg_voice2.py H1
python tools\make_audiolist.py
echo.
echo Done. Hard-refresh the game (Ctrl+F5).
pause
