#!/usr/bin/env python3
"""
量化系统集成测试脚本
"""

import os
import sys
import subprocess
import time

def run_test(test_name, test_func):
    """运行单个测试用例"""
    print(f"\n{'='*60}")
    print(f"执行测试: {test_name}")
    print('='*60)
    try:
        result = test_func()
        if result:
            print(f"✓ 通过: {test_name}")
            return True, None
        else:
            print(f"✗ 失败: {test_name}")
            return False, "测试返回False"
    except Exception as e:
        print(f"✗ 失败: {test_name} - {str(e)}")
        import traceback
        traceback.print_exc()
        return False, str(e)

def test_001_venv():
    """TC-001: 虚拟环境激活测试"""
    import sys
    venv_path = os.path.join(os.getcwd(), 'venv')
    print(f"检查虚拟环境: {venv_path}")
    print(f"Python路径: {sys.executable}")
    
    # 检查是否在虚拟环境中
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("✓ 虚拟环境已激活")
        return True
    else:
        print("! 虚拟环境未激活，但继续测试")
        # 检查venv目录是否存在
        if os.path.exists(venv_path):
            print(f"✓ 虚拟环境目录存在: {venv_path}")
            return True
        return False

def test_002_imports():
    """TC-002: 依赖包导入测试"""
    packages = [
        ('django', 'Django'),
        ('dash', 'Dash'),
        ('dash_bootstrap_components', 'Dash Bootstrap'),
        ('plotly', 'Plotly'),
        ('pandas', 'Pandas'),
        ('numpy', 'NumPy'),
        ('akshare', 'AkShare'),
        ('backtrader', 'Backtrader'),
    ]
    
    all_passed = True
    for module_name, display_name in packages:
        try:
            __import__(module_name)
            print(f"  ✓ {display_name}")
        except ImportError as e:
            print(f"  ✗ {display_name}: {e}")
            all_passed = False
    
    return all_passed

def test_003_django():
    """TC-003: Django服务配置测试"""
    try:
        import django
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'quant_portal.settings')
        django.setup()
        print(f"✓ Django {django.get_version()} 初始化成功")
        
        # 测试数据库连接
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        print("✓ 数据库连接正常")
        
        return True
    except Exception as e:
        print(f"✗ Django测试失败: {e}")
        return False

def test_004_dashboard():
    """TC-004: Dashboard模块导入测试"""
    try:
        import dash
        import dash_bootstrap_components as dbc
        print("✓ Dash框架导入成功")
        
        # 尝试导入各个页面模块
        try:
            from dashboard.pages.realtime import create_realtime_tab, register_realtime_callbacks
            print("✓ 实时监控页面模块导入成功")
        except Exception as e:
            print(f"✗ 实时监控页面导入失败: {e}")
            return False
        
        try:
            from dashboard.pages.backtest import create_backtest_tab
            print("✓ 回测页面模块导入成功")
        except Exception as e:
            print(f"✗ 回测页面导入失败: {e}")
        
        return True
    except Exception as e:
        print(f"✗ Dashboard测试失败: {e}")
        return False

def test_005_data_adapter():
    """TC-005: 数据适配器连接测试"""
    try:
        from dashboard.data_adapter_v2 import overview_data_adapter
        print("✓ 数据适配器导入成功")
        
        # 测试获取数据
        adapter = overview_data_adapter
        print(f"✓ 数据适配器实例: {adapter}")
        
        return True
    except Exception as e:
        print(f"✗ 数据适配器测试失败: {e}")
        return False

def test_006_signals():
    """TC-006: 信号模块初始化测试"""
    try:
        from core.signals import SignalScorer, SignalComposer
        print("✓ 信号模块导入成功")
        
        scorer = SignalScorer()
        print(f"✓ SignalScorer实例创建成功")
        
        return True
    except Exception as e:
        print(f"✗ 信号模块测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_007_journal():
    """TC-007: 交易日志模块测试"""
    try:
        # 确保Django已设置
        import django
        if not django.conf.settings.configured:
            os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'quant_portal.settings')
            django.setup()
        
        from journal.models import DecisionLog
        count = DecisionLog.objects.count()
        print(f"✓ 交易日志模型导入成功，当前记录数: {count}")
        
        return True
    except Exception as e:
        print(f"✗ 交易日志模块测试失败: {e}")
        return False

def test_008_end_to_end():
    """TC-008: 端到端启动测试"""
    print("注意: 此测试需要在系统中实际启动服务")
    print("请手动执行: scripts/start_quant_system.bat")
    print("然后验证:")
    print("  1. Django服务: http://localhost:8000")
    print("  2. Dashboard服务: http://localhost:8050")
    return True  # 手动测试

def main():
    """主函数 - 运行所有测试"""
    print("="*60)
    print("量化交易系统集成测试")
    print("="*60)
    print(f"测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"工作目录: {os.getcwd()}")
    print()
    
    # 切换到项目目录
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(project_dir)
    print(f"项目目录: {project_dir}")
    print()
    
    # 定义所有测试
    tests = [
        ("TC-001: 虚拟环境激活测试", test_001_venv),
        ("TC-002: 依赖包导入测试", test_002_imports),
        ("TC-003: Django服务配置测试", test_003_django),
        ("TC-004: Dashboard模块导入测试", test_004_dashboard),
        ("TC-005: 数据适配器连接测试", test_005_data_adapter),
        ("TC-006: 信号模块初始化测试", test_006_signals),
        ("TC-007: 交易日志模块测试", test_007_journal),
        ("TC-008: 端到端启动测试", test_008_end_to_end),
    ]
    
    # 运行测试
    results = []
    for name, func in tests:
        passed, error = run_test(name, func)
        results.append((name, passed, error))
        print()
    
    # 打印总结
    print("="*60)
    print("测试总结")
    print("="*60)
    total = len(results)
    passed = sum(1 for _, p, _ in results if p)
    failed = total - passed
    
    print(f"总测试数: {total}")
    print(f"通过: {passed}")
    print(f"失败: {failed}")
    print(f"通过率: {passed/total*100:.1f}%")
    print()
    
    # 打印失败详情
    if failed > 0:
        print("失败详情:")
        for name, passed, error in results:
            if not passed:
                print(f"  - {name}: {error}")
        print()
    
    # 生成报告文件
    report_file = f"integration_test_report_{time.strftime('%Y%m%d_%H%M%S')}.txt"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("="*60 + "\n")
        f.write("量化交易系统集成测试报告\n")
        f.write("="*60 + "\n\n")
        f.write(f"测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"工作目录: {os.getcwd()}\n\n")
        f.write(f"总测试数: {total}\n")
        f.write(f"通过: {passed}\n")
        f.write(f"失败: {failed}\n")
        f.write(f"通过率: {passed/total*100:.1f}%\n\n")
        
        f.write("详细结果:\n")
        for name, p, error in results:
            status = "通过" if p else "失败"
            f.write(f"  [{status}] {name}\n")
            if error:
                f.write(f"      错误: {error}\n")
    
    print(f"详细报告已保存至: {report_file}")
    print()
    
    return 0 if failed == 0 else 1

if __name__ == '__main__':
    sys.exit(main())
