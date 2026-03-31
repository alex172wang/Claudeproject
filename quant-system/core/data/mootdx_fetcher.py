"""
mootdx数据获取器实现
支持通达信行情数据接口，用于A股/港股/期货实时和历史行情
"""

import pandas as pd
from datetime import datetime
from typing import Optional, List, Dict, Any
from .base import DataFetcher

# 市场代码映射（根据data_sources.yaml）
MARKET_MAP = {
    'SH': 1,    # 上海市场
    'SZ': 0,    # 深圳市场
}

# ETF代码前缀（根据data_sources.yaml）
ETF_PREFIXES = {
    'SH': ['51', '56', '58', '50'],  # 上海ETF前缀
    'SZ': ['15', '16'],              # 深圳ETF前缀
}


class MootdxFetcher(DataFetcher):
    """
    mootdx数据获取器

    支持功能：
    - 日K/周K/月K/分钟K线数据
    - 实时行情数据
    - ETF列表获取
    - 自动识别ETF代码前缀
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.connection_config = config.get('connection', {})
        self.markets = config.get('markets', MARKET_MAP)
        self.etf_prefixes = config.get('etf_prefixes', ETF_PREFIXES)
        self.client = None

    def connect(self) -> bool:
        """
        建立mootdx连接

        Returns:
            bool: 连接是否成功
        """
        try:
            from mootdx import get_config, set_config
            from mootdx.quotes import Quotes

            # 设置配置
            config = get_config()
            config['MULTITHREAD'] = self.connection_config.get('multithread', True)
            config['BESTIP'] = self.connection_config.get('bestip', True)
            config['TIMEOUT'] = self.connection_config.get('timeout', 30)
            set_config(config)

            # 初始化客户端
            self.client = Quotes.factory(market='std')
            self._connected = True
            print(f"[MootdxFetcher] 连接成功")
            return True

        except Exception as e:
            print(f"[MootdxFetcher] 连接失败: {e}")
            self._connected = False
            return False

    def disconnect(self) -> bool:
        """
        断开mootdx连接

        Returns:
            bool: 断开是否成功
        """
        try:
            if self.client:
                self.client.close()
                self.client = None
            self._connected = False
            print(f"[MootdxFetcher] 断开连接")
            return True
        except Exception as e:
            print(f"[MootdxFetcher] 断开连接失败: {e}")
            return False

    def _detect_market(self, code: str) -> int:
        """
        检测证券所属市场

        Args:
            code: 证券代码

        Returns:
            int: 市场代码（0=深圳，1=上海）
        """
        # 根据代码前缀判断
        if len(code) >= 2:
            prefix = code[:2]
            # 上海市场：51/56/58/50/60/68
            if prefix in ['51', '56', '58', '50', '60', '68']:
                return self.markets.get('SH', 1)
            # 深圳市场：00/30/15/16
            if prefix in ['00', '30', '15', '16']:
                return self.markets.get('SZ', 0)

        # 默认返回上海市场
        return self.markets.get('SH', 1)

    def _is_etf(self, code: str) -> bool:
        """
        判断是否为ETF代码

        Args:
            code: 证券代码

        Returns:
            bool: 是否为ETF
        """
        if len(code) < 2:
            return False

        prefix = code[:2]

        # 检查上海ETF前缀
        if prefix in self.etf_prefixes.get('SH', []):
            return True

        # 检查深圳ETF前缀
        if prefix in self.etf_prefixes.get('SZ', []):
            return True

        return False

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
            freq: 频率（day/week/month/minute）

        Returns:
            DataFrame: K线数据
        """
        if not self._connected or not self.client:
            print(f"[MootdxFetcher] 未连接，无法获取数据")
            return None

        try:
            # 设置默认日期
            if not end_date:
                end_date = datetime.now().strftime('%Y-%m-%d')
            if not start_date:
                # 默认获取252个交易日（约1年）
                start_date = (datetime.now() - pd.Timedelta(days=365)).strftime('%Y-%m-%d')

            # 频率映射
            freq_map = {
                'day': 9,
                'week': 5,
                'month': 6,
                'minute': 8,
            }
            mootdx_freq = freq_map.get(freq, 9)

            # 获取数据
            df = self.client.k(
                code=code,
                begin=start_date,
                end=end_date,
                frequency=mootdx_freq
            )

            if df is None or df.empty:
                return None

            # 标准化列名
            column_map = {
                'date': 'date',
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'volume': 'volume',
                'amount': 'amount',
            }

            df = df.rename(columns={k: v for k, v in column_map.items() if k in df.columns})

            # 确保日期格式正确
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])

            return df

        except Exception as e:
            print(f"[MootdxFetcher] 获取K线数据失败: {e}")
            return None

    def get_realtime_quote(self, codes: List[str]) -> Optional[pd.DataFrame]:
        """
        获取实时行情

        Args:
            codes: 标的代码列表

        Returns:
            DataFrame: 实时行情数据
        """
        if not self._connected or not self.client:
            print(f"[MootdxFetcher] 未连接，无法获取数据")
            return None

        try:
            # mootdx支持批量获取
            quotes = self.client.quotes(codes)

            if quotes is None or quotes.empty:
                return None

            return quotes

        except Exception as e:
            print(f"[MootdxFetcher] 获取实时行情失败: {e}")
            return None

    def get_etf_list(self) -> Optional[pd.DataFrame]:
        """
        获取ETF列表

        Returns:
            DataFrame: ETF基础信息
        """
        if not self._connected or not self.client:
            print(f"[MootdxFetcher] 未连接，无法获取数据")
            return None

        try:
            # 获取上海市场ETF
            sh_etf = self.client.stocks(market=1)  # 上海
            if sh_etf is not None:
                sh_etf['market'] = 'SH'

            # 获取深圳市场ETF
            sz_etf = self.client.stocks(market=0)  # 深圳
            if sz_etf is not None:
                sz_etf['market'] = 'SZ'

            # 合并
            etf_list = []
            if sh_etf is not None and not sh_etf.empty:
                # 筛选ETF
                sh_etf = sh_etf[sh_etf['code'].str.startswith(tuple(self.etf_prefixes.get('SH', [])))]
                etf_list.append(sh_etf)

            if sz_etf is not None and not sz_etf.empty:
                # 筛选ETF
                sz_etf = sz_etf[sz_etf['code'].str.startswith(tuple(self.etf_prefixes.get('SZ', [])))]
                etf_list.append(sz_etf)

            if etf_list:
                return pd.concat(etf_list, ignore_index=True)

            return None

        except Exception as e:
            print(f"[MootdxFetcher] 获取ETF列表失败: {e}")
            return None
