#!/usr/bin/env python3
"""
初始化 ETF 数据到数据库
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
print("初始化 ETF 数据")
print("=" * 60)

# 从 settings 读取 ETF 配置
etf_configs = settings.QUANT_SYSTEM.get('etf_pool', [])

print(f"\n找到 {len(etf_configs)} 个 ETF 配置\n")

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
        print(f"  [创建] {code} - {defaults['name']}")
    else:
        updated_count += 1
        print(f"  [更新] {code} - {defaults['name']}")

print("\n" + "=" * 60)
print(f"完成: 新建 {created_count} 个, 更新 {updated_count} 个")
print(f"当前数据库中共有 {ETF.objects.count()} 个 ETF")
print("=" * 60)
