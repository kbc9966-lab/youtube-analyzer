@echo off
rem Install Python and packages for this PC
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\setup.ps1"
pause
