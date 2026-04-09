"""
Dashboard API 客户端

用于从 Django REST API 获取数据
替代直接连接 mootdx 的方式
"""

import requests
import json
from typing import Optional, Dict, List, Any
from datetime import datetime


class APIClient:
    """API 客户端"""

    def __init__(self, base_url: str = 'http://localhost:8000/api/'):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        })

    def _get(self, endpoint: str, params: Optional[Dict] = None) -> Any:
        """发送 GET 请求"""
        url = f"{self.base_url}{endpoint}"
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"[APIClient] GET {url} 失败: {e}")
            return None

    def _post(self, endpoint: str, data: Dict) -> Any:
        """发送 POST 请求"""
        url = f"{self.base_url}{endpoint}"
        try:
            response = self.session.post(url, json=data, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"[APIClient] POST {url} 失败: {e}")
            return None

    # =========================================================================
    # Portfolio API
    # =========================================================================

    def get_etf_list(self, category: Optional[str] = None) -> List[Dict]:
        """获取 ETF 列表"""
        params = {}
        if category:
            params['category'] = category

        result = self._get('portfolio/etfs/', params)
        return result.get('results', []) if isinstance(result, dict) else result or []

    def get_etf_detail(self, code: str) -> Optional[Dict]:
        """获取 ETF 详情"""
        return self._get(f'portfolio/etfs/{code}/')

    def get_etf_price(self, code: str) -> Optional[Dict]:
        """获取 ETF 实时价格"""
        return self._get(f'portfolio/etfs/{code}/price/')

    def get_etf_kline(self, code: str, days: int = 60, period: str = 'day') -> List[Dict]:
        """获取 ETF K 线数据"""
        result = self._get(
            f'portfolio/etfs/{code}/kline/',
            {'days': days, 'period': period}
        )
        return result or []

    def get_portfolio_summary(self) -> Optional[Dict]:
        """获取投资组合汇总"""
        return self._get('portfolio/summary/')

    def get_positions(self) -> List[Dict]:
        """获取当前持仓"""
        result = self._get('portfolio/positions/')
        return result or []

    def get_equity_curve(self, days: int = 365) -> List[Dict]:
        """获取权益曲线"""
        result = self._get('portfolio/equity_curve/', {'days': days})
        return result or []

    # =========================================================================
    # Backtest API
    # =========================================================================

    def get_backtest_tasks(self) -> List[Dict]:
        """获取回测任务列表"""
        result = self._get('backtest/tasks/')
        return result.get('results', []) if isinstance(result, dict) else result or []

    def get_backtest_task(self, task_id: int) -> Optional[Dict]:
        """获取回测任务详情"""
        return self._get(f'backtest/tasks/{task_id}/')

    def get_backtest_result(self, task_id: int) -> Optional[Dict]:
        """获取回测结果"""
        return self._get(f'backtest/tasks/{task_id}/result/')

    def run_backtest(self, config: Dict) -> Optional[Dict]:
        """启动回测任务"""
        return self._post('backtest/run/', config)

    # =========================================================================
    # Monitor API
    # =========================================================================

    def get_signals(self) -> List[Dict]:
        """获取当前信号"""
        result = self._get('monitor/signals/')
        return result or []

    def get_alerts(self) -> List[Dict]:
        """获取预警列表"""
        result = self._get('monitor/alerts/')
        return result or []

    def get_system_status(self) -> Optional[Dict]:
        """获取系统状态"""
        return self._get('monitor/system_status/')

    # =========================================================================
    # Journal API
    # =========================================================================

    def get_decisions(self) -> List[Dict]:
        """获取决策日志"""
        result = self._get('journal/decisions/')
        return result or []

    def get_deviations(self) -> List[Dict]:
        """获取偏差日志"""
        result = self._get('journal/deviations/')
        return result or []

    def log_decision(self, data: Dict) -> Optional[Dict]:
        """记录决策"""
        return self._post('journal/log_decision/', data)


# 创建全局 API 客户端实例
api_client = APIClient()
