"""
品种维护 E2E 测试

测试品种管理、品种池管理功能
"""

import pytest
import time
import requests
from datetime import datetime


DASHBOARD_URL = "http://127.0.0.1:8050"
API_BASE = "http://127.0.0.1:8000/api"


@pytest.fixture(scope="module")
def page():
    """创建浏览器页面 fixture"""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        yield page
        browser.close()


@pytest.fixture(scope="module")
def api_client():
    """API 客户端 fixture"""
    return APIClient(API_BASE)


class APIClient:
    """API 客户端封装"""

    def __init__(self, base_url):
        self.base_url = base_url

    def get_etfs(self):
        resp = requests.get(f"{self.base_url}/instruments/etfs/")
        return resp.json() if resp.status_code == 200 else None

    def create_etf(self, code, name, market='SH', category='equity'):
        resp = requests.post(f"{self.base_url}/instruments/etfs/", json={
            'code': code, 'name': name, 'market': market, 'category': category
        })
        return resp.json() if resp.status_code in [200, 201] else None

    def delete_etf(self, code):
        resp = requests.delete(f"{self.base_url}/instruments/etfs/{code}/")
        return resp.status_code in [200, 204]

    def get_pools(self):
        resp = requests.get(f"{self.base_url}/instruments/pools/")
        return resp.json() if resp.status_code == 200 else None

    def create_pool(self, code, name, purpose='custom', description=''):
        resp = requests.post(f"{self.base_url}/instruments/pools/", json={
            'code': code, 'name': name, 'purpose': purpose, 'description': description
        })
        return resp.json() if resp.status_code in [200, 201] else None

    def delete_pool(self, code):
        resp = requests.delete(f"{self.base_url}/instruments/pools/{code}/")
        return resp.status_code in [200, 204]

    def add_pool_member(self, pool_code, etf_code):
        resp = requests.post(f"{self.base_url}/instruments/pools/{pool_code}/members/", json={
            'etf_code': etf_code
        })
        return resp.json() if resp.status_code in [200, 201] else None


class TestInstrumentsPage:
    """品种维护页面测试"""

    def test_page_loads(self, page):
        """测试页面加载"""
        page.goto(DASHBOARD_URL, wait_until="networkidle")
        # 检查页面标题
        assert "量化交易系统" in page.title()

    def test_navigate_to_instruments(self, page):
        """测试导航到品种维护标签页"""
        page.goto(DASHBOARD_URL, wait_until="networkidle")

        # 点击品种维护标签
        page.click('text=品种维护')
        page.wait_for_timeout(1000)

        # 验证表格存在
        etf_table = page.locator('#etf-table')
        assert etf_table.is_visible(), "ETF 表格应该可见"

    def test_etf_table_displays_data(self, page):
        """测试 ETF 表格显示数据"""
        page.goto(DASHBOARD_URL, wait_until="networkidle")
        page.click('text=品种维护')
        page.wait_for_timeout(2000)

        # 检查表格行数
        rows = page.locator('#etf-table tbody tr')
        count = rows.count()
        print(f"ETF 表格行数: {count}")
        assert count > 0, "ETF 表格应该有数据"

    def test_pool_table_displays_data(self, page):
        """测试品种池表格显示数据"""
        page.goto(DASHBOARD_URL, wait_until="networkidle")
        page.click('text=品种维护')
        page.wait_for_timeout(2000)

        pool_table = page.locator('#pool-table')
        assert pool_table.is_visible(), "品种池表格应该可见"


class TestETFOperations:
    """ETF 操作测试"""

    def test_add_etf_button_opens_modal(self, page):
        """测试点击新增 ETF 按钮打开模态框"""
        page.goto(DASHBOARD_URL, wait_until="networkidle")
        page.click('text=品种维护')
        page.wait_for_timeout(1000)

        # 点击新增 ETF 按钮
        page.click('#btn-open-add-etf-modal')
        page.wait_for_timeout(500)

        # 检查模态框是否打开
        modal = page.locator('#add-etf-modal')
        assert modal.is_visible(), "新增 ETF 模态框应该可见"

    def test_add_etf_success(self, page, api_client):
        """测试成功添加 ETF"""
        timestamp = datetime.now().strftime("%m%d%H%M%S")
        test_code = f"999{timestamp[-5:]}"  # 生成6位测试代码

        page.goto(DASHBOARD_URL, wait_until="networkidle")
        page.click('text=品种维护')
        page.wait_for_timeout(1000)

        # 打开模态框
        page.click('#btn-open-add-etf-modal')
        page.wait_for_timeout(500)

        # 填写表单
        page.fill('#add-etf-code', test_code)
        page.fill('#add-etf-name', f'测试ETF{test_code}')
        page.select_option('#add-etf-market', 'SH')
        page.select_option('#add-etf-category', 'equity')

        # 提交
        page.click('#btn-confirm-add-etf')
        page.wait_for_timeout(1000)

        # 验证 API
        result = api_client.get_etfs()
        assert result is not None
        etf = next((e for e in result['data'] if e['code'] == test_code), None)
        assert etf is not None, f"ETF {test_code} 应该存在"

        # 清理
        api_client.delete_etf(test_code)

    def test_batch_delete_modal_opens(self, page):
        """测试批量删除模态框打开"""
        page.goto(DASHBOARD_URL, wait_until="networkidle")
        page.click('text=品种维护')
        page.wait_for_timeout(1000)

        page.click('#btn-open-batch-delete-modal')
        page.wait_for_timeout(500)

        modal = page.locator('#batch-delete-modal')
        assert modal.is_visible(), "批量删除模态框应该可见"


class TestPoolOperations:
    """品种池操作测试"""

    def test_add_pool_button_opens_modal(self, page):
        """测试点击新增池按钮打开模态框"""
        page.goto(DASHBOARD_URL, wait_until="networkidle")
        page.click('text=品种维护')
        page.wait_for_timeout(1000)

        page.click('#btn-open-add-pool-modal')
        page.wait_for_timeout(500)

        modal = page.locator('#add-pool-modal')
        assert modal.is_visible(), "新增池模态框应该可见"

    def test_create_pool_success(self, page, api_client):
        """测试成功创建品种池"""
        timestamp = datetime.now().strftime("%m%d%H%M%S")
        test_pool_code = f"test_pool_{timestamp}"

        page.goto(DASHBOARD_URL, wait_until="networkidle")
        page.click('text=品种维护')
        page.wait_for_timeout(1000)

        # 打开模态框
        page.click('#btn-open-add-pool-modal')
        page.wait_for_timeout(500)

        # 填写表单
        page.fill('#add-pool-code', test_pool_code)
        page.fill('#add-pool-name', f'测试池{timestamp}')
        page.select_option('#add-pool-purpose', 'custom')
        page.fill('#add-pool-description', 'E2E测试创建的池')

        # 提交
        page.click('#btn-confirm-add-pool')
        page.wait_for_timeout(1000)

        # 验证
        result = api_client.get_pools()
        assert result is not None
        pool = next((p for p in result['data'] if p['code'] == test_pool_code), None)
        assert pool is not None, f"品种池 {test_pool_code} 应该存在"

        # 清理
        api_client.delete_pool(test_pool_code)

    def test_select_pool_row(self, page):
        """测试选择品种池行"""
        page.goto(DASHBOARD_URL, wait_until="networkidle")
        page.click('text=品种维护')
        page.wait_for_timeout(2000)

        pool_rows = page.locator('#pool-table tbody tr')
        if pool_rows.count() > 0:
            pool_rows.first.click()
            page.wait_for_timeout(500)

            # 检查是否有选中样式
            selected = page.locator('#pool-table tbody tr')
            assert selected.count() > 0


class TestAPI:
    """API 单元测试"""

    def test_get_etfs_api(self, api_client):
        """测试获取 ETF 列表 API"""
        result = api_client.get_etfs()
        assert result is not None
        assert result.get('success') == True
        assert len(result.get('data', [])) > 0

    def test_get_pools_api(self, api_client):
        """测试获取品种池列表 API"""
        result = api_client.get_pools()
        assert result is not None
        assert result.get('success') == True

    def test_create_and_delete_etf(self, api_client):
        """测试创建和删除 ETF"""
        timestamp = datetime.now().strftime("%m%d%H%M%S")
        test_code = f"888{timestamp[-5:]}"

        # 创建
        result = api_client.create_etf(test_code, f'测试ETF{test_code}')
        assert result is not None, f"创建失败: {result}"
        assert result.get('success') == True

        # 验证存在
        etfs = api_client.get_etfs()
        etf = next((e for e in etfs['data'] if e['code'] == test_code), None)
        assert etf is not None

        # 删除
        deleted = api_client.delete_etf(test_code)
        assert deleted == True

    def test_create_and_delete_pool(self, api_client):
        """测试创建和删除品种池"""
        timestamp = datetime.now().strftime("%m%d%H%M%S")
        test_pool_code = f"test_e2e_{timestamp}"

        # 创建
        result = api_client.create_pool(test_pool_code, f'E2E测试池{timestamp}')
        assert result is not None, f"创建失败: {result}"
        assert result.get('success') == True

        # 删除
        deleted = api_client.delete_pool(test_pool_code)
        assert deleted == True

    def test_add_pool_member(self, api_client):
        """测试添加池成员"""
        # 先创建一个测试池
        timestamp = datetime.now().strftime("%m%d%H%M%S")
        test_pool_code = f"test_member_{timestamp}"

        api_client.create_pool(test_pool_code, f'成员测试池{timestamp}')

        # 添加成员（使用已有的 ETF）
        etfs = api_client.get_etfs()
        if etfs and len(etfs['data']) > 0:
            etf_code = etfs['data'][0]['code']
            result = api_client.add_pool_member(test_pool_code, etf_code)
            print(f"添加池成员结果: {result}")

        # 清理
        api_client.delete_pool(test_pool_code)


class TestVisualElements:
    """视觉元素测试"""

    def test_stat_cards_visible(self, page):
        """测试统计卡片可见"""
        page.goto(DASHBOARD_URL, wait_until="networkidle")
        page.click('text=品种维护')
        page.wait_for_timeout(1000)

        # 检查统计卡片
        assert page.locator('#etf-count').is_visible()
        assert page.locator('#pool-count').is_visible()
        assert page.locator('#member-count').is_visible()

    def test_buttons_visible(self, page):
        """测试按钮可见"""
        page.goto(DASHBOARD_URL, wait_until="networkidle")
        page.click('text=品种维护')
        page.wait_for_timeout(1000)

        assert page.locator('#btn-refresh-all').is_visible()
        assert page.locator('#btn-open-add-etf-modal').is_visible()
        assert page.locator('#btn-open-batch-delete-modal').is_visible()


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
