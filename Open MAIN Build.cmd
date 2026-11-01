@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\Open-LiveWorkspace.ps1" -BuiltRelease ".next-release-main-20261101-065003-150442" %*
if errorlevel 1 pause
