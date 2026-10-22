@echo off
cd /d "%~dp0"
py -3 run.py terminal %*
if errorlevel 1 pause
