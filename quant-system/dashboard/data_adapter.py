"""
仪表板数据适配器

提供从真实数据源（mootdx通达信、Django数据库）获取数据的功能
替代原有的模拟数据
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import os
import sys

# 添加项目路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# 导入mootdx接口
try:
    from core.data.mootdx_fetcher import MootdxFetcher
    MOOTDX_AVAILABLE = True
except ImportError:
    MOOTDX_AVAILABLE = False
    print("[DataAdapter] mootdx接口不可用")


class DashboardDataAdapter:
    """仪表板数据适配器"""

    def __init__(self):
        self.mootdx_fetcher = None
        self._init_fetcher()

    def _init_fetcher(self):
        """初始化数据获取器"""
        if MOOTDX_AVAILABLE:
            config = {
                'connection': {
                    'multithread': True,
                    'bestip': True,
                    'timeout': 30,
                }
            }
            self.mootdx_fetcher = MootdxFetcher(config)
            if self.mootdx_fetcher.connect():
                print("[DataAdapter] mootdx连接成功")
            else:
                print("[DataAdapter] mootdx连接失败")
                self.mootdx_fetcher = None

    def get_etf_list(self) -> pd.DataFrame:
        """
        获取ETF列表

        Returns:
            DataFrame: ETF列表，包含code, name, market, category等信息
        """
        if self.mootdx_fetcher:
            try:
                etf_df = self.mootdx_fetcher.get_etf_list()
                if etf_df is not None and not etf_df.empty:
                    return etf_df
            except Exception as e:
                print(f"[DataAdapter] 获取ETF列表失败: {e}")

        # 备用：返回本地静态数据
        return self._get_local_etf_list()

    def get_etf_price(self, code: str, days: int = 252) -> pd.DataFrame:
        """
        获取ETF历史价格

        Args:
            code: ETF代码，如 '510300'
            days: 获取天数，默认252（一年交易日）

        Returns:
            DataFrame: 价格数据，包含open, high, low, close, volume等
        """
        if self.mootdx_fetcher:
            try:
                end_date = datetime.now().strftime('%Y-%m-%d')
                start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

                df = self.mootdx_fetcher.get_kline(
                    code=code,
                    start_date=start_date,
                    end_date=end_date,
                    freq='day'
                )

                if df is not None and not df.empty:
                    return df

            except Exception as e:
                print(f"[DataAdapter] 获取ETF价格失败: {e}")

        # 备用：生成模拟数据
        return self._generate_mock_price(code, days)

    def get_realtime_quotes(self, codes: List[str]) -> pd.DataFrame:
        """
        获取实时行情

        Args:
            codes: ETF代码列表

        Returns:
            DataFrame: 实时行情数据
        """
        if self.mootdx_fetcher:
            try:
                df = self.mootdx_fetcher.get_realtime_quote(codes)
                if df is not None and not df.empty:
                    return df
            except Exception as e:
                print(f"[DataAdapter] 获取实时行情失败: {e}")

        # 备用：返回模拟数据
        return self._generate_mock_quotes(codes)

    # ============ 私有方法：备用数据生成 ============

    def _get_local_etf_list(self) -> pd.DataFrame:
        """获取本地ETF列表（备用）"""
        # 从instruments.py导入静态数据
        from .pages.instruments import ETF_DATA
        return pd.DataFrame(ETF_DATA)

    def _generate_mock_price(self, code: str, days: int) -> pd.DataFrame:
        """生成模拟价格数据（备用）"""
        np.random.seed(42)
        dates = pd.date_range(end=datetime.now(), periods=days, freq='B')

        # 生成随机价格
        initial_price = np.random.uniform(1, 10)
        returns = np.random.normal(0.0005, 0.02, len(dates))
        prices = initial_price * (1 + returns).cumprod()

        df = pd.DataFrame({
            'date': dates,
            'open': prices * np.random.uniform(0.99, 1.01, len(dates)),
            'high': prices * np.random.uniform(1.00, 1.03, len(dates)),
            'low': prices * np.random.uniform(0.97, 1.00, len(dates)),
            'close': prices,
            'volume': np.random.randint(1000000, 10000000, len(dates)),
        })

        return df

    def _generate_mock_quotes(self, codes: List[str]) -> pd.DataFrame:
        """生成模拟实时行情（备用）"""
        data = []
        for code in codes:
            price = np.random.uniform(1, 10)
            data.append({
                'code': code,
                'name': f'ETF{code}',
                'price': price,
                'change': np.random.uniform(-0.05, 0.05),
                'volume': np.random.randint(1000000, 10000000),
            })
        return pd.DataFrame(data)


# 全局数据适配器实例
data_adapter = DashboardDataAdapter()
