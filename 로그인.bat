@echo off
rem Sign in to Claude with a subscription account
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\login.ps1"
pause
