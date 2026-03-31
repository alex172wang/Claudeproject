"""
FRED数据获取器实现
美联储经济数据，用于宏观指标和跨市场共振分析
"""

import pandas as pd
from datetime import datetime
from typing import Optional, List, Dict, Any
from .base import DataFetcher


class FREDFetcher(DataFetcher):
    """
    FRED数据获取器

    支持功能：
    - 美联储经济数据获取
    - 利率数据（10Y、2Y国债收益率）
    - 美元指数
    - 信用利差
    - 美联储资产负债表
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.connection_config = config.get('connection', {})
        self.series_config = config.get('series', {})
        self.api_key = self.connection_config.get('api_key', '')
        self._fred = None

    def connect(self) -> bool:
        """
        建立FRED连接

        Returns:
            bool: 连接是否成功
        """
        try:
            from fredapi import Fred

            # 如果没有提供API Key，尝试从环境变量读取
            if not self.api_key:
                import os
                self.api_key = os.environ.get('FRED_API_KEY', '')

            if not self.api_key:
                print(f"[FREDFetcher] 警告: 未设置FRED API Key")
                print(f"[FREDFetcher] 请设置环境变量 FRED_API_KEY 或在配置中提供")

            self._fred = Fred(api_key=self.api_key)
            self._connected = True
            print(f"[FREDFetcher] 连接成功")
            return True

        except ImportError:
            print(f"[FREDFetcher] 未安装fredapi，请运行: pip install fredapi")
            self._connected = False
            return False

        except Exception as e:
            print(f"[FREDFetcher] 连接失败: {e}")
            self._connected = False
            return False

    def disconnect(self) -> bool:
        """
        断开FRED连接

        Returns:
            bool: 断开是否成功
        """
        self._fred = None
        self._connected = False
        print(f"[FREDFetcher] 断开连接")
        return True

    def get_series(
        self,
        series_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Optional[pd.DataFrame]:
        """
        获取FRED数据系列

        Args:
            series_id: FRED系列ID（如 'GS10'、'DTWEXBGS'）
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            DataFrame: 时间序列数据
        """
        if not self._connected or not self._fred:
            print(f"[FREDFetcher] 未连接，无法获取数据")
            return None

        try:
            # 设置默认日期
            if not end_date:
                end_date = datetime.now().strftime('%Y-%m-%d')
            if not start_date:
                start_date = (datetime.now() - pd.Timedelta(days=252*2)).strftime('%Y-%m-%d')

            # 获取数据
            data = self._fred.get_series(series_id, start_date, end_date)

            if data is None or data.empty:
                return None

            # 转换为DataFrame
            df = pd.DataFrame({
                'date': data.index,
                'value': data.values
            })
            df['date'] = pd.to_datetime(df['date'])
            df['series_id'] = series_id

            return df

        except Exception as e:
            print(f"[FREDFetcher] 获取系列数据失败 {series_id}: {e}")
            return None

    def get_kline(
        self,
        code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        freq: str = 'day',
        **kwargs
    ) -> Optional[pd.DataFrame]:
        """
        获取K线数据（FRED数据源不支持标准K线）

        此方法主要用于获取FRED宏观经济指标的日度数据
        """
        # FRED数据以series_id为code
        return self.get_series(code, start_date, end_date)

    def get_realtime_quote(self, codes: List[str]) -> Optional[pd.DataFrame]:
        """
        获取实时行情（FRED不支持实时数据）
        """
        print(f"[FREDFetcher] FRED数据源不支持实时行情")
        return None

    def get_etf_list(self) -> Optional[pd.DataFrame]:
        """
        获取ETF列表（FRED不提供ETF列表）
        """
        print(f"[FREDFetcher] FRED数据源不提供ETF列表")
        return None

    def get_credit_spread(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Optional[pd.DataFrame]:
        """
        获取信用利差（BAA - AAA）

        Args:
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            DataFrame: 信用利差数据
        """
        baa = self.get_series('BAA', start_date, end_date)
        aaa = self.get_series('AAA', start_date, end_date)

        if baa is None or aaa is None:
            return None

        # 合并计算利差
        merged = pd.merge(
            baa[['date', 'value']].rename(columns={'value': 'baa'}),
            aaa[['date', 'value']].rename(columns={'value': 'aaa'}),
            on='date',
            how='inner'
        )
        merged['credit_spread'] = merged['baa'] - merged['aaa']

        return merged[['date', 'credit_spread']]

    def get_yield_curve_slope(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Optional[pd.DataFrame]:
        """
        获取收益率曲线斜率（10Y - 2Y）

        Args:
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            DataFrame: 收益率曲线斜率
        """
        gs10 = self.get_series('GS10', start_date, end_date)
        gs2 = self.get_series('GS2', start_date, end_date)

        if gs10 is None or gs2 is None:
            return None

        # 合并计算斜率
        merged = pd.merge(
            gs10[['date', 'value']].rename(columns={'value': 'gs10'}),
            gs2[['date', 'value']].rename(columns={'value': 'gs2'}),
            on='date',
            how='inner'
        )
        merged['yield_slope'] = merged['gs10'] - merged['gs2']

        return merged[['date', 'yield_slope']]
