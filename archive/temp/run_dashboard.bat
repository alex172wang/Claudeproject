@echo off
chcp 65001 >nul
title 量化交易系统 - 仪表板

:: 设置颜色
color 0A

:: 检查是否已有实例在运行
netstat -ano | findstr ":8050" >nul
if %errorlevel% equ 0 (
    echo.
    echo [错误] 仪表板已经在运行！
    echo.
    echo 访问地址: http://127.0.0.1:8050
    echo.
    echo 如果无法访问，请检查任务管理器中的 Python 进程。
    echo.
    pause
    exit /b 1
)

:: 检查是否存在锁文件
if exist ".dashboard.lock" (
    echo.
    echo [警告] 检测到锁文件，可能上次运行未正常退出。
    echo.
    set /p choice="是否强制启动? (y/n): "
    if /i not "%choice%"=="y" (
        echo 已取消启动。
        pause
        exit /b 0
    )
    del /f ".dashboard.lock" 2>nul
)

:: 创建锁文件
echo %date% %time% > ".dashboard.lock"
echo PID=%random% >> ".dashboard.lock"

echo.
echo ============================================
echo    量化交易系统 - 实时监控仪表板
echo ============================================
echo.
echo 正在启动服务...
echo.

:: 检查 Python 是否可用
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到 Python，请确保 Python 已安装并添加到 PATH。
    del /f ".dashboard.lock" 2>nul
    pause
    exit /b 1
)

:: 检查 run_dashboard.py 是否存在
if not exist "run_dashboard.py" (
    echo [错误] 未找到 run_dashboard.py 文件。
    del /f ".dashboard.lock" 2>nul
    pause
    exit /b 1
)

echo 启动时间: %date% %time%
echo 访问地址: http://127.0.0.1:8050
echo.
echo 按 Ctrl+C 停止服务
echo.
echo ============================================
echo.

:: 启动服务
python run_dashboard.py

:: 清理锁文件
del /f ".dashboard.lock" 2>nul

echo.
echo 服务已停止。
echo.
pause
