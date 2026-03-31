#!/usr/bin/env python3
"""
Phase 5 仪表板系统验证脚本
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

print("="*70)
print("量化交易系统 - Phase 5 仪表板系统验证")
print("="*70)

results = {}
all_passed = True

# 测试1: 仪表板模块导入
print("\n[测试1] 仪表板模块导入")
print("-"*70)

try:
    from dashboard import create_app
    print("  [OK] dashboard.create_app 导入成功")
    results['dashboard_import'] = True
except Exception as e:
    print(f"  [FAIL] 导入失败: {e}")
    results['dashboard_import'] = False
    all_passed = False

# 测试2: 页面模块导入
print("\n[测试2] 页面模块导入")
print("-"*70)

try:
    from dashboard.pages import (
        create_realtime_tab,
        create_backtest_tab,
        create_signals_tab,
        create_risk_tab,
    )
    print("  [OK] 所有页面模块导入成功")
    results['pages_import'] = True
except Exception as e:
    print(f"  [FAIL] 导入失败: {e}")
    results['pages_import'] = False
    all_passed = False

# 测试3: 依赖检查
print("\n[测试3] 仪表板依赖检查")
print("-"*70)

dependencies = [
    ('dash', 'Dash'),
    ('dash_bootstrap_components', 'Dash Bootstrap'),
    ('plotly', 'Plotly'),
]

for module_name, display_name in dependencies:
    try:
        __import__(module_name)
        print(f"  [OK] {display_name} 已安装")
    except ImportError:
        print(f"  [FAIL] {display_name} 未安装")
        all_passed = False

# 测试4: 主题配置
print("\n[测试4] 主题配置检查")
print("-"*70)

try:
    from dashboard.main import THEME
    required_keys = ['bg_dark', 'bg_card', 'bg_light', 'accent', 'text', 'border']
    missing = [k for k in required_keys if k not in THEME]
    if missing:
        print(f"  [FAIL] 缺少主题键: {missing}")
        all_passed = False
    else:
        print(f"  [OK] 主题配置完整")
        results['theme_config'] = True
except Exception as e:
    print(f"  [FAIL] 主题配置检查失败: {e}")
    all_passed = False

# 测试5: 文件结构检查
print("\n[测试5] 文件结构检查")
print("-"*70)

required_files = [
    'dashboard/__init__.py',
    'dashboard/main.py',
    'dashboard/pages/__init__.py',
    'dashboard/pages/realtime.py',
    'dashboard/pages/backtest.py',
    'dashboard/pages/signals.py',
    'dashboard/pages/risk.py',
    'run_dashboard.py',
]

for file_path in required_files:
    full_path = os.path.join(os.path.dirname(__file__), file_path)
    if os.path.exists(full_path):
        print(f"  [OK] {file_path}")
    else:
        print(f"  [FAIL] 缺少文件: {file_path}")
        all_passed = False

# 汇总
print("\n" + "="*70)
print("验证结果汇总")
print("="*70)

passed = sum(1 for v in results.values() if v)
total = len(results)
print(f"\n核心测试: {passed}/{total} 通过")

if all_passed:
    print("\n[✓] Phase 5 仪表板系统验证通过！")
    print("\n启动仪表板:")
    print("  python run_dashboard.py")
    print("\n访问地址: http://127.0.0.1:8050")
    sys.exit(0)
else:
    print("\n[✗] Phase 5 验证未完全通过，请检查错误信息。")
    sys.exit(1)
