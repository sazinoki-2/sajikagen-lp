@echo off
rem Sajikagen LP editor: start the local server, then open the editor in the default browser.
cd /d "%~dp0"
start "sajikagen-server" /min python live.py
timeout /t 2 /nobreak >nul
start "" "http://127.0.0.1:8210/__edit"
