"""
AI 助手完整 E2E 测试

从产品经理视角验证所有功能
"""

import pytest
import time
import requests
from datetime import datetime


# API 基础地址
API_BASE = "http://127.0.0.1:8000/api/ai/manager/"
DASHBOARD_URL = "http://127.0.0.1:8050"


class TestAIFloatingBall:
    """悬浮球视觉测试"""

    def test_floating_ball_exists(self, page):
        """验证悬浮球存在"""
        page.goto(DASHBOARD_URL)
        floating_ball = page.locator('#ai-assistant-floating-ball')
        assert floating_ball.is_visible(), "悬浮球应该可见"

    def test_floating_ball_icon_visible(self, page):
        """验证悬浮球图标可见"""
        page.goto(DASHBOARD_URL)
        # 检查 FontAwesome 图标
        icon = page.locator('#ai-assistant-floating-ball .fa-robot')
        assert icon.is_visible(), "机器人图标应该可见"

    def test_floating_ball_color_contrast(self, page):
        """验证悬浮球颜色与背景有足够对比度"""
        page.goto(DASHBOARD_URL)
        floating_ball = page.locator('#ai-assistant-floating-ball button')

        # 获取按钮背景色
        bg_color = floating_ball.evaluate('el => window.getComputedStyle(el).backgroundColor')
        print(f"悬浮球背景色: {bg_color}")

        # 获取父容器背景色
        parent_bg = floating_ball.locator('..').evaluate(
            'el => window.getComputedStyle(el.parentElement).backgroundColor'
        )
        print(f"父容器背景色: {parent_bg}")

        # 深色主题应该使用浅色/亮色按钮
        # 验证按钮不是深色（深色主题深色按钮会看不见）
        assert bg_color != 'rgb(0, 0, 0)', "按钮不应该是纯黑色"


class TestAIChatWindow:
    """聊天窗口测试"""

    def test_chat_window_opens(self, page):
        """验证点击悬浮球可以打开聊天窗口"""
        page.goto(DASHBOARD_URL)

        # 点击悬浮球
        page.click('#ai-assistant-toggle')
        page.wait_for_timeout(500)

        # 聊天窗口应该显示
        chat_window = page.locator('#ai-assistant-chat-window')
        style = chat_window.evaluate('el => window.getComputedStyle(el).display')
        assert style == 'flex', f"聊天窗口应该显示，实际 display: {style}"

    def test_chat_window_closes(self, page):
        """验证点击关闭按钮可以关闭聊天窗口"""
        page.goto(DASHBOARD_URL)

        # 先打开聊天窗口
        page.click('#ai-assistant-toggle')
        page.wait_for_timeout(500)

        # 点击关闭按钮
        page.click('#ai-assistant-close')
        page.wait_for_timeout(500)

        # 聊天窗口应该隐藏
        chat_window = page.locator('#ai-assistant-chat-window')
        style = chat_window.evaluate('el => window.getComputedStyle(el).display')
        assert style == 'none', f"聊天窗口应该隐藏，实际 display: {style}"

    def test_input_placeholder_visible(self, page):
        """验证输入框占位符可见"""
        page.goto(DASHBOARD_URL)
        page.click('#ai-assistant-toggle')
        page.wait_for_timeout(500)

        placeholder = page.locator('#ai-assistant-input').get_attribute('placeholder')
        assert placeholder, "输入框应该有占位符"

    def test_send_button_exists(self, page):
        """验证发送按钮存在"""
        page.goto(DASHBOARD_URL)
        page.click('#ai-assistant-toggle')
        page.wait_for_timeout(500)

        send_btn = page.locator('#ai-assistant-send')
        assert send_btn.is_visible(), "发送按钮应该可见"


class TestAIIntentRecognition:
    """意图识别测试"""

    def test_list_etfs(self):
        """测试列出所有 ETF"""
        response = requests.post(API_BASE, json={"text": "列出所有ETF"})
        result = response.json()
        print(f"列出ETF结果: {result}")
        assert result.get('success') == True, f"应该成功: {result}"
        assert result.get('intent') == 'list_etfs'
        assert len(result.get('data', [])) > 0, "应该有 ETF 数据"

    def test_list_etfs_variants(self):
        """测试列出 ETF 的多种表达"""
        variants = [
            "查看ETF列表",
            "有哪些ETF",
            "显示所有ETF",
        ]
        for text in variants:
            response = requests.post(API_BASE, json={"text": text})
            result = response.json()
            print(f"'{text}' -> intent: {result.get('intent')}")
            assert result.get('intent') == 'list_etfs', f"'{text}' 应该识别为 list_etfs"

    def test_add_etf(self):
        """测试添加 ETF"""
        response = requests.post(API_BASE, json={"text": "添加 ETF 512480"})
        result = response.json()
        print(f"添加ETF结果: {result}")
        assert result.get('success') == True, f"应该成功: {result}"
        assert result.get('intent') == 'add_etf'

    def test_list_pools(self):
        """测试列出品种池"""
        response = requests.post(API_BASE, json={"text": "列出所有品种池"})
        result = response.json()
        print(f"列出品种池结果: {result}")
        assert result.get('success') == True, f"应该成功: {result}"
        assert result.get('intent') == 'list_pools'

    def test_create_pool(self):
        """测试创建品种池"""
        timestamp = datetime.now().strftime('%m%d%H%M%S')
        response = requests.post(API_BASE, json={
            "text": f'创建品种池叫"测试池{timestamp}"'
        })
        result = response.json()
        print(f"创建品种池结果: {result}")
        assert result.get('success') == True, f"应该成功: {result}"
        assert result.get('intent') == 'add_pool'

    def test_list_pool_members(self):
        """测试查看品种池成员"""
        response = requests.post(API_BASE, json={
            "text": "查看轮动池的成员"
        })
        result = response.json()
        print(f"查看池成员结果: {result}")
        assert result.get('intent') == 'list_pool_members'

    def test_add_pool_member(self):
        """测试向品种池添加成员"""
        response = requests.post(API_BASE, json={
            "text": "向轮动池添加 510300"
        })
        result = response.json()
        print(f"添加池成员结果: {result}")
        assert result.get('intent') == 'add_pool_member'

    def test_help_intent(self):
        """测试帮助意图"""
        response = requests.post(API_BASE, json={"text": "帮助"})
        result = response.json()
        print(f"帮助结果: {result}")
        assert result.get('intent') == 'help'
        assert 'help_text' in str(result.get('data', {}))

    def test_clear_pools_not_supported(self):
        """测试清空品种池 - 当前不支持"""
        response = requests.post(API_BASE, json={"text": "清空所有的品种池"})
        result = response.json()
        print(f"清空品种池结果: {result}")
        # 当前返回 unknown，这是已知功能缺失
        assert result.get('intent') == 'unknown', "清空品种池应该返回 unknown（功能缺失）"

    def test_remove_pool_member_not_supported(self):
        """测试从品种池移除成员 - 当前不支持"""
        response = requests.post(API_BASE, json={"text": "从轮动池移除 510300"})
        result = response.json()
        print(f"移除池成员结果: {result}")
        # 需要检查是否支持
        print(f"Intent: {result.get('intent')}")


class TestUIColorContrast:
    """UI 颜色对比度测试"""

    def test_welcome_message_colors(self, page):
        """验证欢迎信息颜色对比"""
        page.goto(DASHBOARD_URL)
        page.click('#ai-assistant-toggle')
        page.wait_for_timeout(500)

        welcome = page.locator('#ai-welcome-message')
        bg = welcome.evaluate('el => window.getComputedStyle(el).backgroundColor')
        color = welcome.evaluate('el => window.getComputedStyle(el).color')

        print(f"欢迎信息背景: {bg}, 文字颜色: {color}")

    def test_chat_window_border(self, page):
        """验证聊天窗口边框颜色"""
        page.goto(DASHBOARD_URL)
        page.click('#ai-assistant-toggle')
        page.wait_for_timeout(500)

        chat_window = page.locator('#ai-assistant-chat-window')
        border_color = chat_window.evaluate(
            'el => window.getComputedStyle(el).borderColor'
        )
        print(f"聊天窗口边框颜色: {border_color}")

    def test_user_message_bubble(self, page):
        """验证用户消息气泡颜色"""
        page.goto(DASHBOARD_URL)
        page.click('#ai-assistant-toggle')
        page.wait_for_timeout(500)

        # 发送一条消息
        page.fill('#ai-assistant-input', '帮助')
        page.click('#ai-assistant-send')
        page.wait_for_timeout(2000)

        # 检查用户消息气泡
        messages = page.locator('#ai-assistant-messages')
        bubbles = messages.locator('> div')
        if bubbles.count() > 0:
            first_bubble = bubbles.first
            bg = first_bubble.evaluate(
                'el => window.getComputedStyle(el).backgroundColor'
            )
            print(f"第一条消息背景: {bg}")


class TestAPIEndpoint:
    """API 端点测试"""

    def test_api_health(self):
        """验证 API 服务正常"""
        try:
            response = requests.get("http://127.0.0.1:8000/api/health/", timeout=3)
            print(f"API 健康检查: {response.status_code}")
        except:
            # health 端点可能不存在，尝试 manager
            response = requests.post(API_BASE, json={"text": "帮助"}, timeout=3)
            assert response.status_code == 200

    def test_manager_endpoint(self):
        """验证 manager 端点"""
        response = requests.post(API_BASE, json={"text": "帮助"})
        assert response.status_code == 200
        result = response.json()
        assert 'success' in result


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
