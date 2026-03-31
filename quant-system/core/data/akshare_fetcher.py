"""
AKShare数据获取器实现
支持ETF列表、期权数据、宏观数据等
"""

import time
import pandas as pd
from datetime import datetime
from typing import Optional, List, Dict, Any
from .base import DataFetcher


class AKShareFetcher(DataFetcher):
    """
    AKShare数据获取器

    支持功能：
    - ETF列表和实时行情
    - 期权数据（50ETF、300ETF期权）
    - 宏观数据（PMI、CPI、GDP等）
    - 交易日历
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.connection_config = config.get('connection', {})
        self.rate_limit = self.connection_config.get('rate_limit', 0.5)  # 调用间隔（秒）
        self._last_call_time = 0
        self._ak = None

    def _rate_limited_call(self, func, *args, **kwargs):
        """带限速的API调用"""
        elapsed = time.time() - self._last_call_time
        if elapsed < self.rate_limit:
            time.sleep(self.rate_limit - elapsed)

        result = func(*args, **kwargs)
        self._last_call_time = time.time()
        return result

    def connect(self) -> bool:
        """
        建立AKShare连接

        Returns:
            bool: 连接是否成功
        """
        try:
            import akshare as ak
            self._ak = ak
            self._connected = True
            print(f"[AKShareFetcher] 连接成功")
            return True

        except ImportError:
            print(f"[AKShareFetcher] 未安装akshare，请运行: pip install akshare")
            self._connected = False
            return False

        except Exception as e:
            print(f"[AKShareFetcher] 连接失败: {e}")
            self._connected = False
            return False

    def disconnect(self) -> bool:
        """
        断开AKShare连接

        Returns:
            bool: 断开是否成功
        """
        self._ak = None
        self._connected = False
        print(f"[AKShareFetcher] 断开连接")
        return True

    def get_kline(
        self,
        code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        freq: str = 'day',
        **kwargs
    ) -> Optional[pd.DataFrame]:
        """
        获取K线数据

        Args:
            code: 标的代码
            start_date: 开始日期
            end_date: 结束日期
            freq: 频率

        Returns:
            DataFrame: K线数据
        """
        if not self._connected or not self._ak:
            print(f"[AKShareFetcher] 未连接，无法获取数据")
            return None

        try:
            # 设置默认日期
            if not end_date:
                end_date = datetime.now().strftime('%Y%m%d')
            if not start_date:
                start_date = (datetime.now() - pd.Timedelta(days=365)).strftime('%Y%m%d')

            # 获取ETF历史数据
            df = self._rate_limited_call(
                self._ak.fund_etf_hist_em,
                symbol=code,
                period="daily" if freq == 'day' else freq,
                start_date=start_date,
                end_date=end_date,
                adjust="qfq"  # 前复权
            )

            if df is None or df.empty:
                return None

            # 标准化列名
            df = df.rename(columns={
                '日期': 'date',
                '开盘': 'open',
                '最高': 'high',
                '最低': 'low',
                '收盘': 'close',
                '成交量': 'volume',
                '成交额': 'amount',
            })

            # 确保日期格式正确
            df['date'] = pd.to_datetime(df['date'])

            return df

        except Exception as e:
            print(f"[AKShareFetcher] 获取K线数据失败: {e}")
            return None

    def get_realtime_quote(self, codes: List[str]) -> Optional[pd.DataFrame]:
        """
        获取实时行情

        Args:
            codes: 标的代码列表

        Returns:
            DataFrame: 实时行情数据
        """
        if not self._connected or not self._ak:
            print(f"[AKShareFetcher] 未连接，无法获取数据")
            return None

        try:
            # 获取所有ETF实时行情
            df = self._rate_limited_call(self._ak.fund_etf_spot_em)

            if df is None or df.empty:
                return None

            # 筛选指定代码
            df = df[df['代码'].isin(codes)]

            return df

        except Exception as e:
            print(f"[AKShareFetcher] 获取实时行情失败: {e}")
            return None

    def get_etf_list(self) -> Optional[pd.DataFrame]:
        """
        获取ETF列表

        Returns:
            DataFrame: ETF基础信息
        """
        if not self._connected or not self._ak:
            print(f"[AKShareFetcher] 未连接，无法获取数据")
            return None

        try:
            # 获取ETF列表
            df = self._rate_limited_call(self._ak.fund_etf_category_em)

            if df is None or df.empty:
                return None

            return df

        except Exception as e:
            print(f"[AKShareFetcher] 获取ETF列表失败: {e}")
            return None

    def get_option_data(self, option_type: str = "50ETF") -> Optional[pd.DataFrame]:
        """
        获取期权数据

        Args:
            option_type: 期权类型（50ETF/300ETF）

        Returns:
            DataFrame: 期权数据
        """
        if not self._connected or not self._ak:
            print(f"[AKShareFetcher] 未连接，无法获取数据")
            return None

        try:
            if option_type == "50ETF":
                df = self._rate_limited_call(self._ak.option_current_em)
            elif option_type == "300ETF":
                df = self._rate_limited_call(self._ak.option_300etf_current_em)
            else:
                print(f"[AKShareFetcher] 不支持的期权类型: {option_type}")
                return None

            return df

        except Exception as e:
            print(f"[AKShareFetcher] 获取期权数据失败: {e}")
            return None

    def get_trade_calendar(self, start_year: int, end_year: int) -> Optional[pd.DataFrame]:
        """
        获取交易日历

        Args:
            start_year: 开始年份
            end_year: 结束年份

        Returns:
            DataFrame: 交易日历
        """
        if not self._connected or not self._ak:
            print(f"[AKShareFetcher] 未连接，无法获取数据")
            return None

        try:
            dfs = []
            for year in range(start_year, end_year + 1):
                df = self._rate_limited_call(
                    self._ak.tool_trade_date_hist_sina,
                    year=year
                )
                if df is not None and not df.empty:
                    dfs.append(df)

            if dfs:
                return pd.concat(dfs, ignore_index=True)
            return None

        except Exception as e:
            print(f"[AKShareFetcher] 获取交易日历失败: {e}")
            return None
