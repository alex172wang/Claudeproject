#!/usr/bin/env python3
"""
完整集成测试脚本
从环境检查 -> 数据初始化 -> 功能验证 -> 页面测试
"""
import os
import sys
import time
import subprocess
import webbrowser
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


def print_header(title):
    """打印标题"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}  {title}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")


def print_step(step, total, description):
    """打印步骤"""
    print(f"\n{Colors.OKBLUE}[{step}/{total}]{Colors.ENDC} {description}")


def print_success(message):
    """打印成功"""
    print(f"{Colors.OKGREEN}✓ {message}{Colors.ENDC}")


def print_error(message):
    """打印错误"""
    print(f"{Colors.FAIL}✗ {message}{Colors.ENDC}")


def print_warning(message):
    """打印警告"""
    print(f"{Colors.WARNING}! {message}{Colors.ENDC}")


def check_python():
    """检查 Python"""
    print_step(1, 8, "检查 Python 环境...")
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print_error(f"Python 版本过低，需要 3.8+，当前 {version.major}.{version.minor}")
        return False
    print_success(f"Python {version.major}.{version.minor}.{version.micro}")
    return True


def check_dependencies():
    """检查依赖"""
    print_step(2, 8, "检查依赖包...")

    required_packages = [
        ('django', 'Django'),
        ('dash', 'Dash'),
        ('dash_bootstrap_components', 'Dash Bootstrap Components'),
        ('plotly', 'Plotly'),
        ('pandas', 'pandas'),
        ('numpy', 'numpy'),
    ]

    all_ok = True
    for module_name, display_name in required_packages:
        try:
            __import__(module_name)
            print_success(f"{display_name} 已安装")
        except ImportError:
            print_error(f"{display_name} 未安装")
            all_ok = False

    # 可选依赖
    optional_packages = [
        ('mootdx', 'mootdx'),
        ('akshare', 'akshare'),
    ]
    for module_name, display_name in optional_packages:
        try:
            __import__(module_name)
            print_success(f"{display_name} 已安装")
        except ImportError:
            print_warning(f"{display_name} 未安装（可选）")

    return all_ok


def init_django():
    """初始化 Django"""
    print_step(3, 8, "初始化 Django...")
    try:
        project_root = Path(__file__).parent
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'quant_system.settings')
        sys.path.insert(0, str(project_root))

        import django
        django.setup()
        print_success("Django 初始化成功")
        return True
    except Exception as e:
        print_error(f"Django 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def init_etf_data():
    """初始化 ETF 数据"""
    print_step(4, 8, "初始化 ETF 数据...")
    try:
        from portfolio.models import ETF
        from django.conf import settings

        etf_configs = settings.QUANT_SYSTEM.get('etf_pool', [])

        created_count = 0
        updated_count = 0

        for etf_config in etf_configs:
            code = etf_config.get('code')
            defaults = {
                'name': etf_config.get('name', code),
                'category': etf_config.get('category', 'equity'),
                'market': etf_config.get('market', 'SH'),
                'is_active': etf_config.get('is_active', True),
            }

            etf, created = ETF.objects.update_or_create(
                code=code,
                defaults=defaults
            )

            if created:
                created_count += 1
            else:
                updated_count += 1

        total_count = ETF.objects.count()
        print_success(f"ETF 数据: 新建 {created_count}, 更新 {updated_count}, 总计 {total_count}")
        return total_count > 0
    except Exception as e:
        print_error(f"ETF 数据初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_data_fetch():
    """测试数据获取"""
    print_step(5, 8, "测试数据获取功能...")
    try:
        from portfolio.models import ETF

        # 测试 ETF 数据访问
        etf_count = ETF.objects.count()
        print_success(f"数据库中共有 {etf_count} 个 ETF")

        # 列出所有 ETF
        etfs = list(ETF.objects.values('code', 'name'))
        for etf in etfs[:5]:
            print(f"  - {etf['code']}: {etf['name']}")

        # 尝试测试实时行情（不强制要求成功）
        try:
            from data_sync.tasks import get_realtime_quote
            if etfs:
                code = etfs[0]['code']
                quote = get_realtime_quote(code)
                if quote and quote.get('price'):
                    print_success(f"实时行情获取成功: {code} = {quote['price']}")
                else:
                    print_warning("实时行情获取失败（可能是网络问题）")
        except Exception as e:
            print_warning(f"实时行情测试跳过: {e}")

        return True
    except Exception as e:
        print_error(f"数据获取测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_dashboard_import():
    """测试 Dashboard 导入"""
    print_step(6, 8, "测试 Dashboard 模块导入...")
    try:
        from dashboard.simple_dashboard import app
        print_success("Dashboard 模块导入成功")
        return True
    except Exception as e:
        print_error(f"Dashboard 导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def start_dashboard():
    """启动 Dashboard"""
    print_step(7, 8, "启动 Dashboard...")

    project_root = Path(__file__).parent
    python_path = sys.executable

    proc = subprocess.Popen(
        [python_path, str(project_root / "run_dashboard.py"), "--port", "8050"],
        cwd=str(project_root)
    )

    print_success("Dashboard 正在启动...")
    print(f"{Colors.OKCYAN}等待 5 秒让服务完全启动...{Colors.ENDC}")
    time.sleep(5)

    if proc.poll() is not None:
        print_error("Dashboard 启动失败")
        return None, None

    print_success("Dashboard 已启动")
    return proc, "http://localhost:8050"


def manual_verification(url):
    """手动验证指引"""
    print_step(8, 8, "手动验证页面...")

    print(f"\n{Colors.OKCYAN}请在浏览器中打开: {url}{Colors.ENDC}")
    print(f"\n{Colors.BOLD}验证清单:{Colors.ENDC}")

    checklist = [
        "页面标题显示为 '量化交易系统 - 实时监控'",
        "顶部导航栏显示 '量化交易系统 - ETF监控'",
        "右上角显示 '运行中' 状态和当前时间",
        "左侧显示 'ETF 列表' 标题",
        "左侧显示至少 3 个 ETF 卡片",
        "右侧显示 'K线图' 标题",
        "右侧有 ETF 选择下拉框",
        "右侧有时间周期选择下拉框（7天/30天/60天/180天）",
        "右侧显示 K线图区域",
        "等待 10 秒，确认时间自动更新",
    ]

    for i, item in enumerate(checklist, 1):
        print(f"  {i}. {item}")

    print(f"\n{Colors.WARNING}提示: 按 Ctrl+C 停止 Dashboard{Colors.ENDC}")

    # 尝试自动打开浏览器
    try:
        webbrowser.open(url)
        print_success("已自动打开浏览器")
    except:
        print_warning("无法自动打开浏览器，请手动访问")


def main():
    """主函数"""
    print_header("量化交易系统 - 完整集成测试")

    dashboard_proc = None
    try:
        # 步骤 1-6: 环境和功能测试
        if not check_python():
            return 1
        if not check_dependencies():
            print_warning("部分依赖缺失，继续测试...")
        if not init_django():
            return 1
        if not init_etf_data():
            return 1
        if not test_data_fetch():
            return 1
        if not test_dashboard_import():
            return 1

        # 步骤 7: 启动 Dashboard
        dashboard_proc, url = start_dashboard()
        if not dashboard_proc:
            return 1

        # 步骤 8: 手动验证
        manual_verification(url)

        # 保持运行
        print(f"\n{Colors.OKGREEN}{Colors.BOLD}✓ 集成测试完成！{Colors.ENDC}")
        print(f"\n{Colors.OKCYAN}Dashboard 正在运行中...{Colors.ENDC}")

        try:
            while dashboard_proc.poll() is None:
                time.sleep(1)
        except KeyboardInterrupt:
            print(f"\n{Colors.WARNING}正在停止 Dashboard...{Colors.ENDC}")

    except Exception as e:
        print_error(f"测试过程出错: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        if dashboard_proc and dashboard_proc.poll() is None:
            dashboard_proc.terminate()
            try:
                dashboard_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                dashboard_proc.kill()

    return 0


if __name__ == '__main__':
    sys.exit(main())
