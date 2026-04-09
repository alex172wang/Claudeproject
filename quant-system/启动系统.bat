@echo off
chcp 65001 >nul 2>&1
title Quant Trading System

echo ========================================
echo    Quant Trading System - Launcher
echo ========================================
echo.

cd /d "%~dp0"

echo [1/2] Starting Django API Server...
start "Django API" python manage.py runserver 8000 --noreload

echo Waiting for Django to be ready...
:wait_loop
timeout /t 1 /nobreak >nul 2>&1
curl -s http://127.0.0.1:8000 >nul 2>&1
if errorlevel 1 (
    echo Waiting...
    goto wait_loop
)
echo Django is ready!

echo [2/2] Starting Dashboard...
start "Dashboard" python run_dashboard.py

echo.
echo ========================================
echo    System Started!
echo ========================================
echo.
echo   Dashboard: http://localhost:8050
echo   API:      http://localhost:8000
echo.
echo   Press any key to close this window...
echo ========================================
pause >nul 2>&1
