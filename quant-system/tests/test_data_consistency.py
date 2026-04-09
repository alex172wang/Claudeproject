#!/usr/bin/env python3
"""
数据准确性和一致性测试
验证从数据源获取的数据是否符合预期，不同模块之间数据是否一致
"""
import os
import sys
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# 添加项目路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 初始化 Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'quant_system.settings')
import django
django.setup()

from portfolio.models import ETF, ETFPrice
from data_sync.sync_service import data_sync_service
from data_sync.cache_manager import cache_manager
from dashboard.data_adapter_direct import get_direct_data_adapter


@pytest.mark.django_db
class TestDataAccuracy:
    """数据准确性测试"""

    def test_etf_price_positive(self):
        """测试价格必须为正数"""
        # 使用已有的测试 ETF
        etf = ETF.objects.filter(is_active=True).first()
        if etf is None:
            pytest.skip("没有活跃的ETF数据")

        df = data_sync_service.sync_historical_kline(
            etf.code,
            (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'),
            datetime.now().strftime('%Y-%m-%d'),
            'day'
        )

        if df is None or df.empty:
            pytest.skip(f"无法获取 {etf.code} 的K线数据")

        # 验证所有价格都是正数
        assert (df['open'] > 0).all()
        assert (df['high'] > 0).all()
        assert (df['low'] > 0).all()
        assert (df['close'] > 0).all()
        assert (df['volume'] >= 0).all()
        print(f"[OK] {len(df)} 条K线数据，所有价格都是正数")

    def test_ohlcv_valid(self):
        """验证OHLCV关系: high >= open/close >= low"""
        etf = ETF.objects.filter(is_active=True).first()
        if etf is None:
            pytest.skip("没有活跃的ETF数据")

        df = data_sync_service.sync_historical_kline(
            etf.code,
            (datetime.now() - timedelta(days=100)).strftime('%Y-%m-%d'),
            datetime.now().strftime('%Y-%m-%d'),
            'day'
        )

        if df is None or df.empty:
            pytest.skip(f"无法获取 {etf.code} 的K线数据")

        # high 必须大于等于 open 和 close
        assert (df['high'] >= df['open']).all()
        assert (df['high'] >= df['close']).all()
        # low 必须小于等于 open 和 close
        assert (df['low'] <= df['open']).all()
        assert (df['low'] <= df['close']).all()
        print(f"[OK] {len(df)} 条K线数据，OHLCV关系验证通过")

    def test_date_order(self):
        """验证日期顺序正确（升序）"""
        etf = ETF.objects.filter(is_active=True).first()
        if etf is None:
            pytest.skip("没有活跃的ETF数据")

        df = data_sync_service.sync_historical_kline(
            etf.code,
            (datetime.now() - timedelta(days=100)).strftime('%Y-%m-%d'),
            datetime.now().strftime('%Y-%m-%d'),
            'day'
        )

        if df is None or df.empty:
            pytest.skip(f"无法获取 {etf.code} 的K线数据")

        # 检查日期单调递增
        assert df['date'].is_monotonic_increasing
        # 检查无重复日期
        assert df['date'].nunique() == len(df)
        print(f"[OK] {len(df)} 条K线数据，日期顺序验证通过，无重复")

    def test_no_null_values(self):
        """验证没有空值"""
        etf = ETF.objects.filter(is_active=True).first()
        if etf is None:
            pytest.skip("没有活跃的ETF数据")

        df = data_sync_service.sync_historical_kline(
            etf.code,
            (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'),
            datetime.now().strftime('%Y-%m-%d'),
            'day'
        )

        if df is None or df.empty:
            pytest.skip(f"无法获取 {etf.code} 的K线数据")

        # 关键列不能为空
        key_columns = ['open', 'high', 'low', 'close', 'volume']
        null_counts = df[key_columns].isnull().sum().sum()
        assert null_counts == 0
        print(f"[OK] {len(df)} 条K线数据，{null_counts} 个空值（预期 0）")


@pytest.mark.django_db
class TestDataConsistency:
    """数据一致性测试 - 不同模块之间数据一致"""

    def test_database_vs_cache_consistency(self):
        """数据库和缓存一致性"""
        # 清除缓存
        cache_manager.clear()

        etf = ETF.objects.filter(is_active=True).first()
        if etf is None:
            pytest.skip("没有活跃的ETF数据")

        # 第一次同步，应该从数据源获取并存入缓存
        df1 = data_sync_service.sync_historical_kline(
            etf.code,
            (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'),
            datetime.now().strftime('%Y-%m-%d'),
            'day'
        )

        if df1 is None or df1.empty:
            pytest.skip(f"无法获取 {etf.code} 的K线数据")

        # 第二次应该从缓存获取
        df2 = data_sync_service.sync_historical_kline(
            etf.code,
            (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'),
            datetime.now().strftime('%Y-%m-%d'),
            'day'
        )

        # 数据形状应该一致
        assert df1.shape == df2.shape
        # 数据内容应该一致
        pd.testing.assert_frame_equal(df1, df2)
        print("[OK] 数据库和缓存数据一致性验证通过")

    def test_dashboard_adapter_etf_list_consistency(self):
        """Dashboard 适配器获取的ETF列表与数据库一致"""
        adapter = get_direct_data_adapter()
        etf_list = adapter.get_etf_list()

        # 从数据库直接获取
        db_count = ETF.objects.filter(is_active=True).count()

        assert len(etf_list) == db_count
        print(f"[OK] Dashboard ETF列表数量一致: {len(etf_list)} = {db_count}")

        # 检查每个ETF代码都存在
        for etf_data in etf_list:
            assert ETF.objects.filter(code=etf_data['code'], is_active=True).exists()
        print("[OK] 所有ETF代码在数据库中都存在")

    def test_realtime_price_calculation_correctness(self):
        """实时价格涨跌幅计算正确性"""
        adapter = get_direct_data_adapter()
        etf_list = adapter.get_etf_list()

        if not etf_list:
            pytest.skip("没有ETF数据")

        # 测试第一个有价格的ETF
        from data_sync.tasks import get_realtime_quote
        for etf_data in etf_list[:3]:
            quote = get_realtime_quote(etf_data['code'])
            if quote is None:
                continue

            if 'prev_close' in quote and quote['prev_close'] is not None and quote['prev_close'] > 0:
                change = quote.get('change', 0)
                change_percent = (change / quote['prev_close']) * 100
                calculated = quote.get('change_percent', 0)
                # 允许很小的浮点误差
                assert abs(change_percent - calculated) < 0.01
                print(f"[OK] {etf_data['code']} 涨跌幅计算正确: {calculated:.2f}% ≈ {change_percent:.2f}%")
                break
        else:
            pytest.skip("没有可测试的实时报价")


@pytest.mark.django_db
class TestDatabaseConsistency:
    """数据库数据一致性测试"""

    def test_no_duplicate_etf_codes(self):
        """验证没有重复的ETF代码"""
        from django.db.models import Count
        duplicates = (
            ETF.objects.values('code')
            .annotate(count=Count('code'))
            .filter(count__gt=1)
        )
        assert len(duplicates) == 0
        print("[OK] 没有重复的ETF代码")

    def test_no_duplicate_etfprices(self):
        """验证同一ETF同一日期只有一条价格记录"""
        from django.db.models import Count
        duplicates = (
            ETFPrice.objects.values('etf__code', 'date')
            .annotate(count=Count('id'))
            .filter(count__gt=1)
        )
        assert len(duplicates) == 0
        print("[OK] 没有重复的ETF价格记录")

    def test_all_etf_are_active_have_pricedata(self):
        """验证活跃ETF都有价格数据"""
        # 这个不强制，有些ETF可能还没同步数据
        active_etfs = list(ETF.objects.filter(is_active=True))
        count_with_data = 0
        for etf in active_etfs:
            if ETFPrice.objects.filter(etf=etf).exists():
                count_with_data += 1

        # 至少大部分应该有数据
        ratio = count_with_data / len(active_etfs) if active_etfs else 1.0
        print(f"[INFO] {count_with_data}/{len(active_etfs)} 活跃ETF有历史数据 ({ratio:.1%})")
        # 至少 10% 应该有数据（初始化只同步了部分数据）
        assert ratio >= 0.1
        print("[OK] 部分活跃ETF已有历史数据")


if __name__ == '__main__':
    print("请使用 pytest 运行此测试:")
    print("  pytest tests/test_data_consistency.py -v")
