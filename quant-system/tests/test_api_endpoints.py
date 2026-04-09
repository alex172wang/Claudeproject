"""
API 端点完整测试

测试所有 REST API 端点的功能，包括：
- Portfolio ETF 相关端点
- Backtest 回测端点
- Monitor 监控端点
- Journal 日志端点
"""

import os
import sys

# 添加项目路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 初始化 Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'quant_system.settings')
import django
django.setup()

import pytest
from django.test import Client
from rest_framework import status

from portfolio.models import ETF, Pool, ETFPrice


@pytest.fixture
def client():
    """Django 测试客户端"""
    return Client()


@pytest.fixture
def sample_pool(db):
    """创建测试池"""
    pool = Pool.objects.create(
        code='TEST_POOL',
        name='测试池',
        purpose='rotation',
        description='测试用池'
    )
    return pool


@pytest.fixture
def sample_etf(db):
    """创建测试 ETF"""
    etf = ETF.objects.create(
        code='TEST01',
        name='测试ETF',
        category='index',
        is_active=True
    )
    return etf


@pytest.fixture
def sample_etf_with_price(db, sample_etf):
    """创建带价格数据的测试 ETF"""
    ETFPrice.objects.create(
        etf=sample_etf,
        date='2026-04-01',
        open_price=5.0,
        high_price=5.1,
        low_price=4.9,
        close_price=5.05,
        volume=1000000,
        amount=5020000.0
    )
    ETFPrice.objects.create(
        etf=sample_etf,
        date='2026-04-02',
        open_price=5.05,
        high_price=5.15,
        low_price=5.0,
        close_price=5.1,
        volume=1100000,
        amount=5550000.0
    )
    return sample_etf


@pytest.fixture
def sample_backtest_task(db, sample_pool):
    """创建测试回测任务"""
    from backtest.models import BacktestTask
    from datetime import date
    task = BacktestTask.objects.create(
        name='测试回测',
        task_code='test_task_001',
        pool=sample_pool,
        strategy_type='rotation',
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
        status='completed'
    )
    return task


class TestApiRoot:
    """API 根路径测试"""

    def test_api_root_returns_endpoints(self, client):
        """API 根路径返回所有可用端点"""
        response = client.get('/api/')

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert 'name' in data
        assert 'version' in data
        assert 'endpoints' in data


class TestETFEndpoints:
    """ETF 相关 API 端点测试"""

    def test_list_etfs(self, client, sample_etf):
        """GET /api/portfolio/etfs/ - 列出所有 ETF"""
        response = client.get('/api/portfolio/etfs/')

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # 处理分页格式
        if isinstance(data, dict) and 'results' in data:
            etfs = data['results']
        else:
            etfs = data
        assert isinstance(etfs, list)
        # 验证 sample_etf 在列表中
        codes = [etf['code'] for etf in etfs]
        assert 'TEST01' in codes

    def test_get_etf_by_code(self, client, sample_etf):
        """GET /api/portfolio/etfs/{code}/ - 获取单个 ETF"""
        response = client.get('/api/portfolio/etfs/TEST01/')

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data['code'] == 'TEST01'
        assert data['name'] == '测试ETF'

    def test_get_etf_categories(self, client):
        """GET /api/portfolio/etfs/categories/ - 获取 ETF 分类"""
        response = client.get('/api/portfolio/etfs/categories/')

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # categories 应该是字典格式
        assert isinstance(data, dict)

    def test_get_etf_price_from_cache(self, client, sample_etf):
        """GET /api/portfolio/etfs/{code}/price/ - 获取实时价格(从缓存)"""
        # 先设置缓存
        from data_sync.cache_manager import cache_manager
        cache_key = f'quote:{sample_etf.code}'
        cache_manager.set(cache_key, {
            'code': 'TEST01',
            'name': '测试ETF',
            'price': 5.1,
            'change': 0.05,
            'prev_close': 5.0,
            'volume': 1000000,
            'amount': 5100000
        }, timeout=300)

        response = client.get('/api/portfolio/etfs/TEST01/price/')

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert 'current_price' in data
        assert 'change' in data

    def test_get_etf_kline(self, client, sample_etf_with_price):
        """GET /api/portfolio/etfs/{code}/kline/ - 获取 K 线数据"""
        # 先缓存 K 线数据
        from data_sync.cache_manager import cache_manager
        import pandas as pd

        kline_data = pd.DataFrame({
            'date': ['2026-04-01', '2026-04-02'],
            'open': [5.0, 5.05],
            'high': [5.1, 5.15],
            'low': [4.9, 5.0],
            'close': [5.05, 5.1],
            'volume': [1000000, 1100000],
            'amount': [5020000, 5550000]
        })
        cache_key = f'kline:TEST01:day:60'
        cache_manager.set(cache_key, kline_data, timeout=3600)

        response = client.get('/api/portfolio/etfs/TEST01/kline/?period=day&days=60')

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)

    def test_get_nonexistent_etf(self, client, db):
        """GET /api/portfolio/etfs/{code}/ - 不存在的 ETF 返回 404"""
        response = client.get('/api/portfolio/etfs/NONEXIST/')

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestPortfolioEndpoints:
    """Portfolio 相关 API 端点测试"""

    def test_get_portfolio_summary(self, client):
        """GET /api/portfolio/summary/ - 获取投资组合汇总"""
        response = client.get('/api/portfolio/summary/')

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert 'total_assets' in data
        assert 'total_return' in data

    def test_get_portfolio_positions(self, client):
        """GET /api/portfolio/positions/ - 获取当前持仓"""
        response = client.get('/api/portfolio/positions/')

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)

    def test_get_portfolio_equity_curve(self, client):
        """GET /api/portfolio/equity_curve/ - 获取权益曲线"""
        response = client.get('/api/portfolio/equity_curve/')

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)


class TestBacktestEndpoints:
    """Backtest 回测 API 端点测试"""

    def test_list_backtest_tasks(self, client, sample_backtest_task):
        """GET /api/backtest/tasks/ - 列出回测任务"""
        response = client.get('/api/backtest/tasks/')

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # 处理分页格式
        if isinstance(data, dict) and 'results' in data:
            tasks = data['results']
        else:
            tasks = data
        assert isinstance(tasks, list)
        assert len(tasks) >= 1

    def test_get_backtest_task_detail(self, client, sample_backtest_task):
        """GET /api/backtest/tasks/{id}/ - 获取回测任务详情"""
        response = client.get(f'/api/backtest/tasks/{sample_backtest_task.id}/')

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data['name'] == '测试回测'

    def test_get_backtest_task_result_not_exist(self, client, sample_backtest_task):
        """GET /api/backtest/tasks/{id}/result/ - 回测结果不存在"""
        response = client.get(f'/api/backtest/tasks/{sample_backtest_task.id}/result/')

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_run_backtest(self, client):
        """POST /api/backtest/run/ - 启动回测任务"""
        response = client.post('/api/backtest/run/', {
            'strategy': 'test',
            'start_date': '2025-01-01',
            'end_date': '2025-12-31'
        })

        assert response.status_code == status.HTTP_202_ACCEPTED
        data = response.json()
        assert 'detail' in data


class TestMonitorEndpoints:
    """Monitor 监控 API 端点测试"""

    def test_get_signals(self, client):
        """GET /api/monitor/signals/ - 获取当前信号"""
        response = client.get('/api/monitor/signals/')

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)

    def test_get_alerts(self, client):
        """GET /api/monitor/alerts/ - 获取预警列表"""
        response = client.get('/api/monitor/alerts/')

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)

    def test_get_system_status(self, client):
        """GET /api/monitor/system_status/ - 获取系统状态"""
        response = client.get('/api/monitor/system_status/')

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data['status'] == 'running'
        assert 'database' in data
        assert 'timestamp' in data


@pytest.mark.django_db
class TestJournalEndpoints:
    """Journal 日志 API 端点测试"""

    def test_get_decisions_empty(self, client):
        """GET /api/journal/decisions/ - 获取决策日志(空)"""
        response = client.get('/api/journal/decisions/')

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)

    def test_get_deviations_empty(self, client):
        """GET /api/journal/deviations/ - 获取偏差日志(空)"""
        response = client.get('/api/journal/deviations/')

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)

    def test_log_decision(self, client):
        """POST /api/journal/log_decision/ - 记录决策"""
        response = client.post('/api/journal/log_decision/', {
            'decision': 'buy',
            'symbol': '510300',
            'reason': 'test'
        })

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert 'detail' in data


@pytest.mark.django_db
class TestAPIResponseFormat:
    """API 响应格式测试"""

    def test_json_content_type(self, client):
        """所有端点返回 JSON 格式"""
        response = client.get('/api/')

        assert response.status_code == status.HTTP_200_OK
        assert 'application/json' in response['Content-Type']

    def test_error_response_format(self, client):
        """错误响应格式正确"""
        response = client.get('/api/portfolio/etfs/NONEXIST/')

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert 'detail' in data
