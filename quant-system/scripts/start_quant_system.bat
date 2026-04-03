@echo off
chcp 65001 >nul
title 量化交易系统启动器

:: 设置颜色
color 0A

echo.
echo ============================================
echo     量化交易系统 - 启动器
echo ============================================
echo.

:: 设置工作目录（脚本所在目录的上级目录，即 quant-system）
cd /d "%~dp0.."
echo [1/5] 工作目录: %CD%

:: 检查Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到Python！
    echo 请确保Python 3.8+ 已安装并添加到PATH。
    pause
    exit /b 1
)
for /f "tokens=2" %%a in ('python --version 2^>^&1') do set PYTHON_VERSION=%%a
echo [2/5] Python版本: %PYTHON_VERSION%

:: 检查虚拟环境（项目根目录的venv）
if not exist "..\venv" (
    echo.
    echo 正在创建虚拟环境...
    cd ..
    python -m venv venv
    cd quant-system
    echo 虚拟环境创建完成。
)

:: 激活虚拟环境
echo [3/5] 激活虚拟环境...
call ..\venv\Scripts\activate.bat

:: 检查依赖
echo [4/5] 检查依赖项...
pip list | findstr /i "django" >nul 2>&1
if %errorlevel% neq 0 (
    echo 正在安装依赖项...
    pip install -r ..\requirements.txt
    if %errorlevel% neq 0 (
        echo [错误] 依赖安装失败！
        pause
        exit /b 1
    )
)
echo 依赖项检查完成。

:: 检查数据库
echo [5/5] 检查数据库...
if not exist "db.sqlite3" (
    echo 正在初始化数据库...
    python manage.py makemigrations
    python manage.py migrate
    echo 正在创建管理员用户...
    echo from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.filter(username='admin').exists() or User.objects.create_superuser('admin', '', 'admin123') | python manage.py shell
)

echo.
echo ============================================
echo     启动服务
echo ============================================
echo.
echo 正在启动 Django 服务器...
start "Django Server" cmd /k "python manage.py runserver 0.0.0.0:8000"

timeout /t 3 /nobreak >nul

echo.
echo 正在启动 Dashboard 服务...
start "Dashboard" cmd /k "python run_dashboard.py --port 8050"

timeout /t 3 /nobreak >nul

echo.
echo ============================================
echo     服务已启动
echo ============================================
echo.
echo 访问地址:
echo   - Django Admin: http://localhost:8000/admin/
echo   - Dashboard:    http://localhost:8050
echo   - API:          http://localhost:8000/api/
echo.
echo 默认管理员账号:
echo   用户名: admin
echo   密码:   admin123
echo.
echo 正在打开浏览器访问 Dashboard...
timeout /t 2 /nobreak >nul

:: 打开浏览器
start http://localhost:8050

echo.
echo 提示: 关闭此窗口不会停止服务。
echo       请手动关闭 Django Server 和 Dashboard 窗口来停止服务。
echo.
pause
