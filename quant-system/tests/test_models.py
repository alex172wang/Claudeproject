#!/usr/bin/env python3
"""
数据模型测试套件
测试 Django ORM 模型的 CRUD 操作和数据验证
"""
import os
import sys
import pytest
import uuid
from datetime import datetime, date

# 添加项目路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 初始化 Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'quant_system.settings')
import django
django.setup()

from portfolio.models import ETF, Pool, PoolMember, ETFPrice


@pytest.mark.django_db
class TestETFModel:
    """ETF 模型测试"""

    def test_create_etf(self):
        """测试创建 ETF"""
        code = f'TEST{uuid.uuid4().hex[:4]}'
        etf = ETF.objects.create(
            code=code,
            name='测试ETF',
            market='SH',
            category='equity',
            tracking_index='测试指数',
            is_active=True
        )
        assert etf.code == code
        assert etf.name == '测试ETF'
        assert etf.market == 'SH'
        assert etf.category == 'equity'
        assert etf.is_active is True
        print("[OK] ETF 创建成功")

    def test_etf_market_display(self):
        """测试市场显示名称"""
        code = f'TEST{uuid.uuid4().hex[:4]}'
        etf = ETF.objects.create(
            code=code,
            name='测试ETF',
            market='SZ',
            category='equity'
        )
        assert etf.market_display == '深圳证券交易所'
        print("[OK] 市场显示名称正确")

    def test_etf_category_display(self):
        """测试类别显示名称"""
        code = f'TEST{uuid.uuid4().hex[:4]}'
        etf = ETF.objects.create(
            code=code,
            name='测试ETF',
            market='SH',
            category='commodity'
        )
        assert etf.category_display == '商品型'
        print("[OK] 类别显示名称正确")

    def test_etf_str_representation(self):
        """测试 ETF 字符串表示"""
        code = f'TEST{uuid.uuid4().hex[:4]}'
        etf = ETF.objects.create(
            code=code,
            name='测试ETF',
            market='SH',
            category='equity'
        )
        expected = f"{code} - 测试ETF"
        assert str(etf) == expected
        print("[OK] ETF 字符串表示正确")

    def test_etf_unique_code(self):
        """测试 ETF 代码唯一性约束"""
        code = f'TEST{uuid.uuid4().hex[:4]}'
        ETF.objects.create(
            code=code,
            name='沪深300ETF',
            market='SH',
            category='equity'
        )
        # 尝试创建相同代码的 ETF 应该失败
        with pytest.raises(Exception):
            ETF.objects.create(
                code=code,
                name='重复代码',
                market='SZ',
                category='bond'
            )
        print("[OK] ETF 代码唯一性约束正常")

    def test_query_active_etfs(self):
        """测试查询活跃 ETF"""
        # 创建测试数据
        code1 = f'TEST{uuid.uuid4().hex[:4]}'
        code2 = f'TEST{uuid.uuid4().hex[:4]}'
        ETF.objects.create(
            code=code1,
            name='测试ETF1',
            market='SH',
            category='equity',
            is_active=True
        )
        ETF.objects.create(
            code=code2,
            name='测试ETF2',
            market='SZ',
            category='equity',
            is_active=False
        )
        # 查询活跃 ETF
        active_etfs = ETF.objects.filter(is_active=True)
        assert active_etfs.count() >= 1
        print("[OK] 活跃 ETF 查询正常")


@pytest.mark.django_db
class TestPoolModel:
    """品种池模型测试"""

    def test_create_pool(self):
        """测试创建品种池"""
        code = f'TEST{uuid.uuid4().hex[:6]}'
        pool = Pool.objects.create(
            code=code,
            name='测试ETF轮动池',
            purpose='rotation',
            description='用于ETF轮动策略的品种池',
            is_active=True
        )
        assert pool.code == code
        assert pool.name == '测试ETF轮动池'
        assert pool.purpose == 'rotation'
        assert pool.is_active is True
        print("[OK] 品种池创建成功")

    def test_pool_purpose_display(self):
        """测试池用途显示"""
        code = f'TEST{uuid.uuid4().hex[:6]}'
        pool = Pool.objects.create(
            code=code,
            name='测试永久组合池',
            purpose='permanent'
        )
        assert pool.purpose_display == '永久组合'
        print("[OK] 池用途显示正确")

    def test_pool_str_representation(self):
        """测试池字符串表示"""
        code = f'TEST{uuid.uuid4().hex[:6]}'
        pool = Pool.objects.create(
            code=code,
            name='测试自定义池',
            purpose='custom'
        )
        expected = f"{code} - 测试自定义池"
        assert str(pool) == expected
        print("[OK] 池字符串表示正确")


@pytest.mark.django_db
class TestPoolMemberModel:
    """池成员模型测试"""

    def test_create_pool_member(self):
        """测试创建池成员"""
        # 创建 ETF 和池
        etf_code = f'TEST{uuid.uuid4().hex[:4]}'
        pool_code = f'TEST{uuid.uuid4().hex[:6]}'
        etf = ETF.objects.create(
            code=etf_code,
            name='池成员测试',
            market='SH',
            category='equity'
        )
        pool = Pool.objects.create(
            code=pool_code,
            name='测试池',
            purpose='custom'
        )
        # 创建池成员
        member = PoolMember.objects.create(
            pool=pool,
            etf=etf,
            weight=0.4,
            order=1
        )
        assert member.pool == pool
        assert member.etf == etf
        assert float(member.weight) == 0.4
        print("[OK] 池成员创建成功")

    def test_pool_member_count(self):
        """测试池成员数量属性"""
        etf_code1 = f'TEST{uuid.uuid4().hex[:4]}'
        etf_code2 = f'TEST{uuid.uuid4().hex[:4]}'
        pool_code = f'TEST{uuid.uuid4().hex[:6]}'
        etf1 = ETF.objects.create(
            code=etf_code1,
            name='计数测试1',
            market='SH',
            category='equity'
        )
        etf2 = ETF.objects.create(
            code=etf_code2,
            name='计数测试2',
            market='SZ',
            category='equity'
        )
        pool = Pool.objects.create(
            code=pool_code,
            name='测试计数池',
            purpose='custom'
        )
        PoolMember.objects.create(pool=pool, etf=etf1, weight=0.5)
        PoolMember.objects.create(pool=pool, etf=etf2, weight=0.5)

        assert pool.member_count == 2
        print("[OK] 池成员数量属性正确")

    def test_pool_member_unique_constraint(self):
        """测试池成员唯一性约束"""
        etf_code = f'TEST{uuid.uuid4().hex[:4]}'
        pool_code = f'TEST{uuid.uuid4().hex[:6]}'
        etf = ETF.objects.create(
            code=etf_code,
            name='唯一测试1',
            market='SH',
            category='equity'
        )
        pool = Pool.objects.create(
            code=pool_code,
            name='测试唯一约束池',
            purpose='custom'
        )
        # 创建第一个成员
        PoolMember.objects.create(pool=pool, etf=etf, weight=0.5)
        # 尝试创建重复成员应该失败
        with pytest.raises(Exception):
            PoolMember.objects.create(pool=pool, etf=etf, weight=0.3)
        print("[OK] 池成员唯一性约束正常")


@pytest.mark.django_db
class TestETFPriceModel:
    """ETF价格模型测试"""

    def test_create_etf_price(self):
        """测试创建ETF价格记录"""
        etf_code = f'TEST{uuid.uuid4().hex[:4]}'
        etf = ETF.objects.create(
            code=etf_code,
            name='价格测试',
            market='SH',
            category='equity'
        )
        price = ETFPrice.objects.create(
            etf=etf,
            date=date(2024, 1, 2),
            open_price=4.100,
            high_price=4.150,
            low_price=4.080,
            close_price=4.120,
            volume=1000000,
            amount=4120000.00
        )
        assert price.etf == etf
        assert float(price.open_price) == 4.100
        assert float(price.high_price) == 4.150
        assert float(price.low_price) == 4.080
        assert float(price.close_price) == 4.120
        print("[OK] ETF价格记录创建成功")

    def test_etf_price_str_representation(self):
        """测试ETF价格字符串表示"""
        etf_code = f'TEST{uuid.uuid4().hex[:4]}'
        etf = ETF.objects.create(
            code=etf_code,
            name='价格测试',
            market='SH',
            category='equity'
        )
        price = ETFPrice.objects.create(
            etf=etf,
            date=date(2024, 1, 2),
            open_price=4.100,
            high_price=4.150,
            low_price=4.080,
            close_price=4.120,
            volume=1000000
        )
        assert etf_code in str(price)
        assert '4.12' in str(price)
        print("[OK] ETF价格字符串表示正确")

    def test_etf_price_unique_constraint(self):
        """测试ETF价格唯一性约束（同一ETF同一日期只能有一条记录）"""
        etf_code = f'TEST{uuid.uuid4().hex[:4]}'
        etf = ETF.objects.create(
            code=etf_code,
            name='价格测试',
            market='SH',
            category='equity'
        )
        test_date = date(2024, 1, 2)
        # 创建第一条记录
        ETFPrice.objects.create(
            etf=etf,
            date=test_date,
            open_price=4.100,
            high_price=4.150,
            low_price=4.080,
            close_price=4.120,
            volume=1000000
        )
        # 尝试创建重复记录应该失败
        with pytest.raises(Exception):
            ETFPrice.objects.create(
                etf=etf,
                date=test_date,
                open_price=4.200,
                high_price=4.250,
                low_price=4.180,
                close_price=4.220,
                volume=2000000
            )
        print("[OK] ETF价格唯一性约束正常")


if __name__ == '__main__':
    print("请使用 pytest 运行此测试:")
    print("  pytest tests/test_models.py -v")
