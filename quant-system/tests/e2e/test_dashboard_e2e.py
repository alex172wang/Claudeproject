"""
端到端测试 - Dashboard 页面显示验证

使用完整版 dashboard/main.py 进行测试
"""
import pytest
import time
from playwright.sync_api import Page, expect


# 注册 e2e marker
def pytest_configure(config):
    config.addinivalue_line(
        "markers", "e2e: mark test as end-to-end test"
    )


@pytest.mark.e2e
def test_dashboard_page_load(page: Page, dashboard_server):
    """测试 Dashboard 页面能否正常加载"""
    print(f"访问: {dashboard_server}")

    # 设置更长的超时
    page.set_default_timeout(90000)

    # 导航到页面，不等待特定事件，让页面自然加载
    page.goto(dashboard_server, timeout=90000)

    # 验证页面标题 - 完整版标题
    expect(page).to_have_title("量化交易系统 - 实时监控仪表板")
    print("✓ 页面标题正确")


@pytest.mark.e2e
def test_navbar_display(page: Page, dashboard_server):
    """测试导航栏显示"""
    page.set_default_timeout(90000)
    page.goto(dashboard_server, timeout=90000)

    # 等待一下让页面渲染
    time.sleep(5)

    # 验证导航栏存在
    navbar = page.locator("nav").first
    expect(navbar).to_be_visible()
    print("✓ 导航栏可见")

    # 验证标题文本包含关键内容
    expect(navbar).to_contain_text("量化交易系统")
    print("✓ 导航栏标题正确")

    # 验证运行状态
    expect(navbar).to_contain_text("运行中")
    print("✓ 运行状态显示正确")


@pytest.mark.e2e
def test_main_tabs_exist(page: Page, dashboard_server):
    """测试主标签页是否存在"""
    page.set_default_timeout(90000)
    page.goto(dashboard_server, timeout=90000)

    # 等待一下让页面渲染
    time.sleep(5)

    # 验证所有7个标签页存在
    tabs = ["总览", "实时监控", "回测分析", "策略信号", "风险控制", "品种维护", "参数配置"]
    for tab in tabs:
        tab_element = page.locator(f"text={tab}").first
        expect(tab_element).to_be_visible()
        print(f"✓ 标签页 '{tab}' 可见")


@pytest.mark.e2e
def test_overview_tab_metrics(page: Page, dashboard_server):
    """测试总览标签页的关键指标"""
    page.set_default_timeout(90000)
    page.goto(dashboard_server, timeout=90000)

    # 等待一下让页面渲染
    time.sleep(8)

    # 验证关键指标卡片标题
    metrics = ["总资产", "今日收益", "累计收益", "夏普比率"]
    for metric in metrics:
        metric_element = page.locator(f"text={metric}").first
        expect(metric_element).to_be_visible()
        print(f"✓ 指标 '{metric}' 可见")


@pytest.mark.e2e
def test_switch_tabs(page: Page, dashboard_server):
    """测试标签页切换功能"""
    page.set_default_timeout(90000)
    page.goto(dashboard_server, timeout=90000)

    # 等待一下让页面渲染
    time.sleep(5)

    # 切换到"实时监控"标签页
    page.click("text=实时监控")
    time.sleep(2)
    print("✓ 已切换到实时监控标签页")

    # 切换到"回测分析"标签页
    page.click("text=回测分析")
    time.sleep(2)
    print("✓ 已切换到回测分析标签页")

    # 切换回"总览"标签页
    page.click("text=总览")
    time.sleep(2)
    print("✓ 已切换回总览标签页")


@pytest.mark.e2e
def test_time_update(page: Page, dashboard_server):
    """测试时间自动更新"""
    page.set_default_timeout(90000)
    page.goto(dashboard_server, timeout=90000)

    # 等待一下让页面渲染
    time.sleep(5)

    # 获取初始时间
    time_element = page.locator("#current-time")
    expect(time_element).to_be_visible()

    initial_time = time_element.inner_text()
    print(f"初始时间: {initial_time}")

    # 等待几秒 - dashboard 每5秒更新一次
    time.sleep(10)

    # 验证时间更新了
    updated_time = time_element.inner_text()
    print(f"更新后时间: {updated_time}")

    assert initial_time != updated_time, "时间应该自动更新"
    print("✓ 时间自动更新正常")


@pytest.mark.e2e
def test_page_screenshot(page: Page, dashboard_server, tmp_path):
    """截图保存用于人工验证"""
    page.set_default_timeout(90000)
    page.goto(dashboard_server, timeout=90000)
    time.sleep(8)  # 等待完全加载和数据刷新

    screenshot_path = tmp_path / "dashboard_screenshot.png"
    page.screenshot(path=str(screenshot_path))

    print(f"✓ 截图已保存: {screenshot_path}")
    assert screenshot_path.exists()


if __name__ == "__main__":
    print("请使用 pytest 运行此测试:")
    print("  pytest tests/e2e/test_dashboard_e2e.py -v")
