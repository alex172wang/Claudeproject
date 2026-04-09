#!/usr/bin/env python3
"""
初始化 E2E 测试数据到数据库
"""
import os
import sys

# 添加项目路径
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 初始化 Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'quant_system.settings')
import django
django.setup()

from portfolio.models import ETF
from django.conf import settings

print("=" * 60)
print("初始化 E2E 测试数据")
print("=" * 60)

# 测试用 ETF 配置
test_etfs = [
    {
        'code': '510300',
        'name': '沪深300ETF',
        'category': 'equity',
        'market': 'SH',
        'is_active': True,
        'tracking_index': '沪深300',
    },
    {
        'code': '159915',
        'name': '创业板ETF',
        'category': 'equity',
        'market': 'SZ',
        'is_active': True,
        'tracking_index': '创业板指',
    },
    {
        'code': '510500',
        'name': '中证500ETF',
        'category': 'equity',
        'market': 'SH',
        'is_active': True,
        'tracking_index': '中证500',
    },
    {
        'code': '518880',
        'name': '黄金ETF',
        'category': 'commodity',
        'market': 'SH',
        'is_active': True,
        'tracking_index': '黄金9999',
    },
]

print(f"\n准备初始化 {len(test_etfs)} 个 ETF\n")

created_count = 0
updated_count = 0

for etf_config in test_etfs:
    code = etf_config['code']
    defaults = {
        'name': etf_config.get('name', code),
        'category': etf_config.get('category', 'equity'),
        'market': etf_config.get('market', 'SH'),
        'is_active': etf_config.get('is_active', True),
        'tracking_index': etf_config.get('tracking_index', ''),
    }

    etf, created = ETF.objects.update_or_create(
        code=code,
        defaults=defaults
    )

    if created:
        created_count += 1
        print(f"  [创建] {code} - {defaults['name']}")
    else:
        updated_count += 1
        print(f"  [更新] {code} - {defaults['name']}")

print("\n" + "=" * 60)
print(f"完成: 新建 {created_count} 个, 更新 {updated_count} 个")
print(f"当前数据库中共有 {ETF.objects.count()} 个 ETF")
print("=" * 60)

# 显示活跃的ETF
print("\n活跃 ETF 列表:")
active_etfs = ETF.objects.filter(is_active=True)
for etf in active_etfs:
    print(f"  {etf.code} - {etf.name} ({etf.market_display})")
