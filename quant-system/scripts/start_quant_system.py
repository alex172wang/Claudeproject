#!/usr/bin/env python3
"""
量化交易系统启动脚本

支持的功能:
- 检查并安装依赖
- 初始化数据库
- 启动 Django 服务器
- 启动 Dashboard 服务
- 自动打开浏览器

使用方法:
    python start_quant_system.py

可选参数:
    --no-browser    不自动打开浏览器
    --skip-checks   跳过环境检查
"""

import os
import sys
import time
import argparse
import subprocess
import webbrowser
import platform
from pathlib import Path


# 颜色定义
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_header():
    """打印标题"""
    print(f"""
{Colors.OKCYAN}{Colors.BOLD}
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║              量化交易系统 - 启动脚本                        ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
{Colors.ENDC}
""")


def check_python():
    """检查 Python 版本"""
    print(f"{Colors.OKBLUE}[1/6]{Colors.ENDC} 检查 Python...")
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print(f"{Colors.FAIL}✗ Python 版本过低，需要 3.8+，当前 {version.major}.{version.minor}{Colors.ENDC}")
        return False
    print(f"{Colors.OKGREEN}✓ Python {version.major}.{version.minor}.{version.micro}{Colors.ENDC}")
    return True


def check_venv():
    """检查虚拟环境"""
    print(f"{Colors.OKBLUE}[2/6]{Colors.ENDC} 检查虚拟环境...")
    venv_path = Path("venv")
    if not venv_path.exists():
        print(f"{Colors.WARNING}! 虚拟环境不存在，正在创建...{Colors.ENDC}")
        result = subprocess.run([sys.executable, "-m", "venv", "venv"], capture_output=True)
        if result.returncode != 0:
            print(f"{Colors.FAIL}✗ 创建虚拟环境失败{Colors.ENDC}")
            return False
        print(f"{Colors.OKGREEN}✓ 虚拟环境创建成功{Colors.ENDC}")
    else:
        print(f"{Colors.OKGREEN}✓ 虚拟环境已存在{Colors.ENDC}")
    return True


def check_dependencies():
    """检查依赖项"""
    print(f"{Colors.OKBLUE}[3/6]{Colors.ENDC} 检查依赖项...")

    # 检查是否在虚拟环境中
    in_venv = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)

    if not in_venv:
        # 激活虚拟环境
        if platform.system() == "Windows":
            python_path = os.path.join("venv", "Scripts", "python.exe")
        else:
            python_path = os.path.join("venv", "bin", "python")
    else:
        python_path = sys.executable

    # 尝试导入关键依赖
    try:
        result = subprocess.run(
            [python_path, "-c", "import django, dash, pandas, plotly"],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            raise ImportError("Missing dependencies")
        print(f"{Colors.OKGREEN}✓ 依赖项已安装{Colors.ENDC}")
        return True
    except Exception:
        print(f"{Colors.WARNING}! 依赖项未安装，正在安装...{Colors.ENDC}")
        # 安装依赖
        req_file = Path("requirements.txt")
        if req_file.exists():
            result = subprocess.run(
                [python_path, "-m", "pip", "install", "-r", "requirements.txt"],
                capture_output=True
            )
            if result.returncode == 0:
                print(f"{Colors.OKGREEN}✓ 依赖项安装成功{Colors.ENDC}")
                return True
        print(f"{Colors.FAIL}✗ 依赖项安装失败{Colors.ENDC}")
        return False


def check_database():
    """检查数据库"""
    print(f"{Colors.OKBLUE}[4/6]{Colors.ENDC} 检查数据库...")

    db_file = Path("quant-system") / "db.sqlite3"
    if db_file.exists():
        print(f"{Colors.OKGREEN}✓ 数据库已存在{Colors.ENDC}")
        return True

    print(f"{Colors.WARNING}! 数据库不存在，正在初始化...{Colors.ENDC}")

    # 获取Python解释器路径
    if platform.system() == "Windows":
        python_path = os.path.join("venv", "Scripts", "python.exe")
    else:
        python_path = os.path.join("venv", "bin", "python")

    # 进入项目目录
    os.chdir("quant-system")

    # 执行迁移
    result = subprocess.run([python_path, "manage.py", "migrate"], capture_output=True)
    if result.returncode != 0:
        print(f"{Colors.FAIL}✗ 数据库初始化失败{Colors.ENDC}")
        os.chdir("..")
        return False

    # 创建超级用户
    create_superuser_cmd = """
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', '', 'admin123')
    print('Superuser created')
"""
    subprocess.run([python_path, "manage.py", "shell", "-c", create_superuser_cmd],
                   capture_output=True)

    os.chdir("..")
    print(f"{Colors.OKGREEN}✓ 数据库初始化完成{Colors.ENDC}")
    print(f"{Colors.OKCYAN}  管理员账号: admin / admin123{Colors.ENDC}")
    return True


def start_services(no_browser=False):
    """启动服务"""
    print(f"\n{Colors.OKBLUE}[5/6]{Colors.ENDC} 启动服务...")

    # 获取Python解释器路径
    if platform.system() == "Windows":
        python_path = os.path.join("venv", "Scripts", "python.exe")
    else:
        python_path = os.path.join("venv", "bin", "python")

    print(f"{Colors.OKGREEN}✓ 准备启动 Django 服务器...{Colors.ENDC}")

    # 启动Django服务器
    if platform.system() == "Windows":
        subprocess.Popen(
            [python_path, "manage.py", "runserver", "0.0.0.0:8000"],
            cwd="quant-system",
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )
    else:
        subprocess.Popen(
            [python_path, "manage.py", "runserver", "0.0.0.0:8000"],
            cwd="quant-system",
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )

    print(f"{Colors.OKGREEN}✓ Django 服务器已启动 (http://localhost:8000){Colors.ENDC}")
    print(f"{Colors.OKGREEN}✓ 管理后台: http://localhost:8000/admin/{Colors.ENDC}")

    time.sleep(2)

    print(f"\n{Colors.OKBLUE}[6/6]{Colors.ENDC} 启动 Dashboard...")

    # 启动Dashboard
    if platform.system() == "Windows":
        subprocess.Popen(
            [python_path, "run_dashboard.py", "--port", "8050"],
            cwd="quant-system",
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )
    else:
        subprocess.Popen(
            [python_path, "run_dashboard.py", "--port", "8050"],
            cwd="quant-system",
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )

    print(f"{Colors.OKGREEN}✓ Dashboard 已启动 (http://localhost:8050){Colors.ENDC}")

    # 等待服务启动
    print(f"\n{Colors.OKCYAN}等待服务完全启动...{Colors.ENDC}")
    time.sleep(3)

    if not no_browser:
        print(f"{Colors.OKCYAN}正在打开浏览器...{Colors.ENDC}")
        webbrowser.open('http://localhost:8050')

    return True


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='量化交易系统启动脚本',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s                    # 默认启动
  %(prog)s --no-browser     # 不自动打开浏览器
  %(prog)s --skip-checks    # 跳过环境检查
        """
    )

    parser.add_argument(
        '--no-browser',
        action='store_true',
        help='不自动打开浏览器'
    )

    parser.add_argument(
        '--skip-checks',
        action='store_true',
        help='跳过环境检查（已验证环境时使用）'
    )

    args = parser.parse_args()

    try:
        print_header()

        if not args.skip_checks:
            # 检查步骤
            if not check_python():
                sys.exit(1)

            if not check_venv():
                sys.exit(1)

            if not check_dependencies():
                sys.exit(1)

            if not check_database():
                sys.exit(1)

        # 启动服务
        if start_services(args.no_browser):
            print(f"\n{Colors.OKGREEN}{Colors.BOLD}✓ 所有服务已启动！{Colors.ENDC}")
            print(f"\n{Colors.OKCYAN}访问地址:{Colors.ENDC}")
            print(f"  - Dashboard:    http://localhost:8050")
            print(f"  - Django Admin: http://localhost:8000/admin/")
            print(f"  - API:          http://localhost:8000/api/")
            print(f"\n{Colors.OKCYAN}默认管理员账号:{Colors.ENDC}")
            print(f"  用户名: admin")
            print(f"  密码:   admin123")
            print(f"\n{Colors.WARNING}提示: 关闭此窗口不会停止服务。{Colors.ENDC}")
            print(f"{Colors.WARNING}      请按 Ctrl+C 停止服务。{Colors.ENDC}")
            print()

            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print(f"\n{Colors.WARNING}正在停止服务...{Colors.ENDC}")
        else:
            print(f"\n{Colors.FAIL}✗ 服务启动失败{Colors.ENDC}")
            sys.exit(1)

    except Exception as e:
        print(f"\n{Colors.FAIL}错误: {e}{Colors.ENDC}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
