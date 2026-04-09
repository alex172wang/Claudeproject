#!/usr/bin/env python3
"""
测试 Dashboard 能否正常启动
"""
import sys
import os

# 添加项目路径
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

print("=" * 60)
print("测试 Dashboard 依赖...")
print("=" * 60)

# 测试1: 检查 Django 导入
print("\n[1/5] 检查 Django 导入...")
try:
    import django
    print(f"✓ Django {django.get_version()}")
except ImportError as e:
    print(f"✗ Django 导入失败: {e}")
    sys.exit(1)

# 测试2: 检查 Dash 导入
print("\n[2/5] 检查 Dash 导入...")
try:
    import dash
    import dash_bootstrap_components as dbc
    import plotly
    print(f"✓ Dash {dash.__version__}, Plotly {plotly.__version__}")
except ImportError as e:
    print(f"✗ Dash 导入失败: {e}")
    sys.exit(1)

# 测试3: 检查数据处理库
print("\n[3/5] 检查数据处理库...")
try:
    import pandas as pd
    import numpy as np
    print(f"✓ pandas {pd.__version__}, numpy {np.__version__}")
except ImportError as e:
    print(f"✗ 数据处理库导入失败: {e}")
    sys.exit(1)

# 测试4: 初始化 Django
print("\n[4/5] 初始化 Django...")
try:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'quant_system.settings')
    django.setup()
    print("✓ Django 初始化成功")
except Exception as e:
    print(f"✗ Django 初始化失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 测试5: 检查数据库和 ETF 数据
print("\n[5/5] 检查数据库...")
try:
    from portfolio.models import ETF
    etf_count = ETF.objects.count()
    print(f"✓ 数据库连接成功，ETF 数量: {etf_count}")
except Exception as e:
    print(f"✗ 数据库检查失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("所有测试通过！现在可以启动 Dashboard 了。")
print("=" * 60)
print("\n启动命令:")
print("  python run_dashboard.py")
print()
