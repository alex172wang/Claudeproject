@echo off
chcp 65001 >nul
title 量化交易系统 - Dashboard

echo.
echo ╔═══════════════════════════════════════════════════════════╗
echo ║                                                           ║
echo ║              量化交易系统 - Dashboard                      ║
echo ║                                                           ║
echo ╚═══════════════════════════════════════════════════════════╝
echo.

cd /d "%~dp0"

echo 正在启动 Dashboard...
echo.
echo 访问地址: http://localhost:8050
echo.
echo 按 Ctrl+C 停止服务
echo.

python run_dashboard.py

pause
