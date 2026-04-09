#!/usr/bin/env python3
"""
量化交易系统启动脚本

支持的功能:
- 检查并安装依赖
- 初始化数据库
- 初始化ETF数据
- 启动数据同步服务
- 启动 Dashboard 服务
- 自动打开浏览器

使用方法:
    python scripts/start_quant_system.py

可选参数:
    --no-browser    不自动打开浏览器
    --skip-checks   跳过环境检查
    --init-only     仅初始化环境，不启动服务
"""

import os
import sys
import time
import argparse
import subprocess
import webbrowser
import platform
from pathlib import Path


# 获取项目路径
SCRIPT_DIR = Path(__file__).parent.absolute()  # scripts/
PROJECT_ROOT = SCRIPT_DIR.parent  # quant-system/

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
    print(f"{Colors.OKCYAN}项目路径: {PROJECT_ROOT}{Colors.ENDC}")
    print()


def check_python():
    """检查 Python 版本"""
    print(f"{Colors.OKBLUE}[1/8]{Colors.ENDC} 检查 Python...")
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print(f"{Colors.FAIL}✗ Python 版本过低，需要 3.8+，当前 {version.major}.{version.minor}{Colors.ENDC}")
        return False
    print(f"{Colors.OKGREEN}✓ Python {version.major}.{version.minor}.{version.micro}{Colors.ENDC}")
    return True


def get_python_path():
    """获取 Python 解释器路径"""
    return sys.executable


def check_dependencies():
    """检查依赖项"""
    print(f"{Colors.OKBLUE}[2/8]{Colors.ENDC} 检查依赖项...")

    python_path = get_python_path()

    # 尝试导入关键依赖
    try:
        result = subprocess.run(
            [python_path, "-c", "import django, dash, pandas, plotly, rest_framework"],
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
        req_file = PROJECT_ROOT / "requirements.txt"
        if not req_file.exists():
            req_file = PROJECT_ROOT.parent / "requirements.txt"
        if req_file.exists():
            result = subprocess.run(
                [python_path, "-m", "pip", "install", "-r", str(req_file)],
                cwd=str(PROJECT_ROOT)
            )
            if result.returncode == 0:
                print(f"{Colors.OKGREEN}✓ 依赖项安装成功{Colors.ENDC}")
                return True
        print(f"{Colors.FAIL}✗ 依赖项安装失败{Colors.ENDC}")
        return False


def check_database():
    """检查数据库"""
    print(f"{Colors.OKBLUE}[3/8]{Colors.ENDC} 检查数据库...")

    db_file = PROJECT_ROOT / "db.sqlite3"
    # 也检查旧路径
    old_db_file = PROJECT_ROOT / "data" / "db" / "quant_system.sqlite3"
    if db_file.exists() or old_db_file.exists():
        print(f"{Colors.OKGREEN}✓ 数据库已存在{Colors.ENDC}")
        return True

    print(f"{Colors.WARNING}! 数据库不存在，正在初始化...{Colors.ENDC}")

    python_path = get_python_path()

    # 执行迁移
    result = subprocess.run([python_path, "manage.py", "migrate"], cwd=str(PROJECT_ROOT))
    if result.returncode != 0:
        print(f"{Colors.FAIL}✗ 数据库初始化失败{Colors.ENDC}")
        return False

    # 创建超级用户
    create_superuser_cmd = """
from django.contrib.auth import get_user_model
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'quant_system.settings')
import django
django.setup()
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', '', 'admin123')
    print('Superuser created')
"""
    subprocess.run([python_path, "manage.py", "shell", "-c", create_superuser_cmd],
                   cwd=str(PROJECT_ROOT), capture_output=True)

    print(f"{Colors.OKGREEN}✓ 数据库初始化完成{Colors.ENDC}")
    print(f"{Colors.OKCYAN}  管理员账号: admin / admin123{Colors.ENDC}")
    return True


def init_etf_data():
    """初始化ETF数据"""
    print(f"{Colors.OKBLUE}[4/8]{Colors.ENDC} 初始化ETF数据...")

    python_path = get_python_path()

    init_cmd = """
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath('.')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'quant_system.settings')
import django
django.setup()
from portfolio.models import ETF

# 从 settings 读取配置
from django.conf import settings
etf_configs = settings.QUANT_SYSTEM.get('etf_pool', [])

created_count = 0
updated_count = 0

for etf_config in etf_configs:
    code = etf_config.get('code')
    defaults = {
        'name': etf_config.get('name', code),
        'category': etf_config.get('category', 'broad'),
        'market': etf_config.get('market', 'sh'),
        'is_active': True,
    }

    etf, created = ETF.objects.update_or_create(
        code=code,
        defaults=defaults
    )

    if created:
        created_count += 1
        print(f'  创建: {code} - {defaults["name"]}')
    else:
        updated_count += 1

print(f'完成: 新建 {created_count} 个, 更新 {updated_count} 个')
"""

    result = subprocess.run(
        [python_path, "manage.py", "shell", "-c", init_cmd],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        print(f"{Colors.OKGREEN}✓ ETF数据初始化完成{Colors.ENDC}")
        if result.stdout:
            for line in result.stdout.strip().split('\n'):
                if line:
                    print(f"  {line}")
        return True
    else:
        print(f"{Colors.WARNING}! ETF数据初始化可能有问题，但继续...{Colors.ENDC}")
        return True


def test_data_sync():
    """测试数据同步"""
    print(f"{Colors.OKBLUE}[5/8]{Colors.ENDC} 测试数据同步...")

    python_path = get_python_path()

    test_cmd = """
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath('.')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'quant_system.settings')
import django
django.setup()

print('测试实时行情获取...')
from data_sync.tasks import get_realtime_quote
from django.conf import settings

etf_pool = settings.QUANT_SYSTEM.get('etf_pool', [])
success_count = 0

for etf_config in etf_pool[:3]:  # 只测试前3个
    code = etf_config.get('code')
    quote = get_realtime_quote(code)
    if quote and quote.get('price'):
        print(f'  ✓ {code}: {quote.get("name")} - {quote.get("price")}')
        success_count += 1
    else:
        print(f'  ✗ {code}: 获取失败')

print(f'测试完成: {success_count}/{len(etf_pool[:3])} 成功')
"""

    try:
        result = subprocess.run(
            [python_path, "manage.py", "shell", "-c", test_cmd],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.stdout:
            for line in result.stdout.strip().split('\n'):
                if line:
                    print(f"  {line}")

        print(f"{Colors.OKGREEN}✓ 数据同步测试完成{Colors.ENDC}")
        return True
    except subprocess.TimeoutExpired:
        print(f"{Colors.WARNING}! 数据同步测试超时，跳过...{Colors.ENDC}")
        return True


def start_api_server():
    """启动 Django API 服务器"""
    print(f"\n{Colors.OKBLUE}[6/8]{Colors.ENDC} 启动 Django API 服务器...")

    python_path = get_python_path()

    # 启动 Django API 服务器
    if platform.system() == "Windows":
        proc = subprocess.Popen(
            [python_path, "manage.py", "runserver", "8000", "--noreload"],
            cwd=str(PROJECT_ROOT),
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )
    else:
        proc = subprocess.Popen(
            [python_path, "manage.py", "runserver", "8000", "--noreload"],
            cwd=str(PROJECT_ROOT),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )

    print(f"{Colors.OKGREEN}✓ API 服务器已启动 (http://localhost:8000){Colors.ENDC}")
    return proc


def start_dashboard(no_browser=False):
    """启动 Dashboard"""
    print(f"\n{Colors.OKBLUE}[7/8]{Colors.ENDC} 启动 Dashboard...")

    python_path = get_python_path()

    # 启动Dashboard
    if platform.system() == "Windows":
        proc = subprocess.Popen(
            [python_path, "run_dashboard.py", "--host", "0.0.0.0", "--port", "8050"],
            cwd=str(PROJECT_ROOT),
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )
    else:
        proc = subprocess.Popen(
            [python_path, "run_dashboard.py", "--host", "0.0.0.0", "--port", "8050"],
            cwd=str(PROJECT_ROOT),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )

    print(f"{Colors.OKGREEN}✓ Dashboard 已启动 (http://localhost:8050){Colors.ENDC}")

    # 等待服务启动
    print(f"\n{Colors.OKCYAN}等待 Dashboard 完全启动...{Colors.ENDC}")
    time.sleep(3)

    if not no_browser:
        print(f"{Colors.OKCYAN}正在打开浏览器...{Colors.ENDC}")
        webbrowser.open('http://localhost:8050')

    return proc


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
  %(prog)s --init-only      # 仅初始化，不启动服务
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

    parser.add_argument(
        '--init-only',
        action='store_true',
        help='仅初始化环境，不启动服务'
    )

    args = parser.parse_args()

    try:
        print_header()

        if not args.skip_checks:
            # 检查步骤
            if not check_python():
                sys.exit(1)

            if not check_dependencies():
                sys.exit(1)

            if not check_database():
                sys.exit(1)

            if not init_etf_data():
                sys.exit(1)

            if not test_data_sync():
                sys.exit(1)

        if args.init_only:
            print(f"\n{Colors.OKGREEN}{Colors.BOLD}✓ 环境初始化完成！{Colors.ENDC}")
            print(f"\n{Colors.OKCYAN}下一步:{Colors.ENDC}")
            print(f"  运行 'python scripts/start_quant_system.py' 启动服务")
            print()
            return

        # 启动服务
        api_proc = start_api_server()
        time.sleep(2)  # 等待API服务器启动
        dashboard_proc = start_dashboard(args.no_browser)

        print(f"\n{Colors.OKGREEN}{Colors.BOLD}✓ 系统已启动！{Colors.ENDC}")
        print(f"\n{Colors.OKCYAN}访问地址:{Colors.ENDC}")
        print(f"  - Dashboard:    http://localhost:8050")
        print(f"  - API 接口:     http://localhost:8000")
        print(f"\n{Colors.OKCYAN}数据同步:{Colors.ENDC}")
        print(f"  - 实时行情: 每 5 秒自动同步")
        print(f"  - K线数据: 按需获取并缓存 1 小时")
        print(f"\n{Colors.OKCYAN}默认管理员账号 (Django Admin):{Colors.ENDC}")
        print(f"  用户名: admin")
        print(f"  密码:   admin123")
        print(f"\n{Colors.WARNING}提示: 关闭此窗口不会停止服务。{Colors.ENDC}")
        print(f"{Colors.WARNING}      请按 Ctrl+C 停止所有服务。{Colors.ENDC}")
        print()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print(f"\n{Colors.WARNING}正在停止...{Colors.ENDC}")
            if dashboard_proc and dashboard_proc.poll() is None:
                dashboard_proc.terminate()
            if api_proc and api_proc.poll() is None:
                api_proc.terminate()
            try:
                if dashboard_proc:
                    dashboard_proc.wait(timeout=5)
                if api_proc:
                    api_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                if dashboard_proc:
                    dashboard_proc.kill()
                if api_proc:
                    api_proc.kill()

    except Exception as e:
        print(f"\n{Colors.FAIL}错误: {e}{Colors.ENDC}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
