# -*- coding: utf-8 -*-
"""
mootdx 数据加载器模块

封装 pytdx / mootdx 库，提供通达信行情数据获取接口。

支持数据：
- A股/港股/期货历史K线（日/周/月/分钟）
- 实时行情
- 板块/成分股列表
- 财务数据

注意事项：
- 单次请求最多 800 条数据，超出需分页
- 首次连接建议使用 bestip=True 自动选择最优服务器
- 程序结束务必调用 close_client() 关闭连接
- 日K线返回数据已做前复权处理

数据源映射（来自 docs/多维量化指标体系_v1.0.md 第七节）：
- A股/港股行情 OHLCV：mootdx(实时) / AKShare(日线)
- 流动性缺口：mootdx
"""

from typing import Dict, List, Optional, Union
from datetime import datetime, date
import pandas as pd
import numpy as np

try:
    from mootdx.quotes import Quotes
    from mootdx.consts import MARKET_SH, MARKET_SZ
    MOOTDX_AVAILABLE = True
except ImportError:
    MOOTDX_AVAILABLE = False
    # 定义占位符以避免导入错误
    MARKET_SH = 1
    MARKET_SZ = 0

from .loaders import BaseDataLoader, DataLoaderError, DataSourceNotAvailableError, DataValidationError, DataFrequency


class MootdxLoader(BaseDataLoader):
    """
    mootdx 数据加载器

    封装通达信行情接口，提供A股、港股、期货等市场数据获取。

    属性:
        client: mootdx Quotes 实例
        market_map: 市场代码映射字典

    示例:
        >>> loader = MootdxLoader()
        >>> with loader:
        ...     df = loader.get_stock_history('000001', start='20230101', end='20231231')
        >>> print(df.head())
    """

    # 市场代码映射
    MARKET_MAP = {
        'sh': MARKET_SH,  # 上海
        'sz': MARKET_SZ,  # 深圳
        1: MARKET_SH,
        0: MARKET_SZ,
    }

    # 周期映射（mootdx 内部使用）
    FREQUENCY_MAP = {
        DataFrequency.DAILY: 9,      # 日线
        DataFrequency.WEEKLY: 5,     # 周线
        DataFrequency.MONTHLY: 6,    # 月线
        DataFrequency.MINUTE_1: 8,   # 1分钟
        DataFrequency.MINUTE_5: 0,   # 5分钟
        DataFrequency.MINUTE_15: 1,  # 15分钟
        DataFrequency.MINUTE_30: 2,  # 30分钟
        DataFrequency.MINUTE_60: 3,  # 60分钟
    }

    default_params = {
        'multithread': True,   # 是否使用多线程
        'bestip': True,        # 自动选择最优服务器
        'timeout': 30,         # 超时时间（秒）
    }

    def __init__(self, config: Optional[Dict] = None):
        """
        初始化 mootdx 数据加载器

        参数:
            config: 配置参数字典，可覆盖默认参数

        抛出:
            DataSourceNotAvailableError: mootdx 库未安装
        """
        if not MOOTDX_AVAILABLE:
            raise DataSourceNotAvailableError(
                "mootdx 库未安装，请执行: pip install mootdx"
            )

        super().__init__(name='mootdx', config=config)
        self._client = None
        self._ip_pool = None

    def connect(self, **kwargs) -> bool:
        """
        建立 mootdx 数据连接

        参数:
            **kwargs: 连接参数，可覆盖配置中的参数
                - multithread: 是否使用多线程
                - bestip: 是否自动选择最优服务器
                - timeout: 超时时间

        返回:
            bool: 连接是否成功
        """
        try:
            # 合并参数
            params = {**self.params, **kwargs}

            # 创建客户端
            self._client = Quotes.factory(
                multithread=params.get('multithread', True),
                bestip=params.get('bestip', True),
            )

            self._connected = True
            self.logger.info(f"mootdx 连接成功")
            return True

        except Exception as e:
            self.logger.error(f"mootdx 连接失败: {e}")
            self._connected = False
            return False

    def disconnect(self) -> bool:
        """
        断开 mootdx 数据连接

        返回:
            bool: 断开是否成功
        """
        try:
            if self._client is not None:
                # mootdx 的 Quotes 类没有显式的 close 方法
                # 但需要确保连接被释放
                self._client = None

            self._connected = False
            self.logger.info("mootdx 连接已断开")
            return True

        except Exception as e:
            self.logger.error(f"mootdx 断开连接时出错: {e}")
            return False

    def is_connected(self) -> bool:
        """
        检查连接状态

        返回:
            bool: 是否已连接
        """
        return self._connected and self._client is not None

    def _symbol_to_market(self, symbol: str) -> tuple:
        """
        将股票代码转换为市场代码

        参数:
            symbol: 股票代码，如 '000001'、'600000'

        返回:
            tuple: (symbol, market_code)

        说明:
            - 上海市场：600xxx, 601xxx, 603xxx, 688xxx（科创板）, 510xxx（ETF）
            - 深圳市场：000xxx（主板）, 002xxx（中小板）, 300xxx（创业板）, 159xxx（ETF）
        """
        # 去除可能的前缀
        symbol = symbol.strip().upper()
        if symbol.startswith('SH'):
            symbol = symbol[2:]
        elif symbol.startswith('SZ'):
            symbol = symbol[2:]

        # 判断市场
        # ETF: 上海51/58开头，深圳15/16开头
        if symbol.startswith(('6', '5', '9', '51', '58', '56', '50')):
            # 上海市场
            return symbol, MARKET_SH
        else:
            # 深圳市场（0, 1, 2, 3, 15, 16）
            return symbol, MARKET_SZ

    def _parse_date(self, date_str: Union[str, datetime, date]) -> int:
        """
        将日期转换为整数格式（YYYYMMDD）

        参数:
            date_str: 日期字符串、datetime 对象或 date 对象

        返回:
            int: 格式为 YYYYMMDD 的整数
        """
        if isinstance(date_str, str):
            # 尝试解析多种格式
            for fmt in ['%Y%m%d', '%Y-%m-%d', '%Y/%m/%d', '%d/%m/%Y']:
                try:
                    dt = datetime.strptime(date_str, fmt)
                    return int(dt.strftime('%Y%m%d'))
                except ValueError:
                    continue
            raise ValueError(f"无法解析日期格式: {date_str}")
        elif isinstance(date_str, datetime):
            return int(date_str.strftime('%Y%m%d'))
        elif isinstance(date_str, date):
            return int(date_str.strftime('%Y%m%d'))
        else:
            raise ValueError(f"不支持的日期类型: {type(date_str)}")

    def get_stock_history(
        self,
        symbol: str,
        start: Optional[Union[str, datetime, date]] = None,
        end: Optional[Union[str, datetime, date]] = None,
        frequency: DataFrequency = DataFrequency.DAILY,
        **kwargs
    ) -> pd.DataFrame:
        """
        获取股票历史K线数据（覆盖基类方法）

        参数:
            symbol: 股票代码，如 '000001'、'600000'
            start: 开始日期，支持 '20230101' 或 datetime 对象
            end: 结束日期，默认为今天
            frequency: 数据频率，默认日线
            **kwargs: 额外参数
                - adjust: 是否复权，默认 True（前复权）
                - fields: 指定返回字段列表

        返回:
            DataFrame，包含 OHLCV 列：
            - date: 日期
            - open: 开盘价
            - high: 最高价
            - low: 最低价
            - close: 收盘价
            - volume: 成交量
            - amount: 成交额（如可用）

        示例:
            >>> loader = MootdxLoader()
            >>> with loader:
            ...     df = loader.get_stock_history('000001', start='20230101', end='20231231')
            >>> print(df.head())
        """
        self.ensure_connected()

        # 处理默认参数
        if end is None:
            end = datetime.now()
        if start is None:
            # 默认获取最近一年数据
            start = datetime.now().replace(year=datetime.now().year - 1)

        # 解析代码和市场
        code, market = self._symbol_to_market(symbol)

        # 解析日期
        start_int = self._parse_date(start)
        end_int = self._parse_date(end)

        # 获取周期代码
        freq = self.FREQUENCY_MAP.get(frequency, 9)  # 默认日线

        try:
            # 调用 mootdx 获取数据
            df = self._client.bars(
                symbol=code,
                market=market,
                frequency=freq,
                start=start_int,
                end=end_int,
            )

            if df is None or df.empty:
                self.logger.warning(f"未获取到数据: {symbol} [{start} ~ {end}]")
                return pd.DataFrame(columns=['date', 'open', 'high', 'low', 'close', 'volume', 'amount'])

            # 标准化列名
            column_mapping = {
                'datetime': 'date',
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'vol': 'volume',
                'amount': 'amount',
            }

            # 重命名列（如果存在）
            for old, new in column_mapping.items():
                if old in df.columns and new not in df.columns:
                    df = df.rename(columns={old: new})

            # 确保必要的列存在
            required_cols = ['date', 'open', 'high', 'low', 'close', 'volume']
            for col in required_cols:
                if col not in df.columns:
                    df[col] = np.nan

            # 转换日期格式
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])

            # 按日期排序
            df = df.sort_values('date').reset_index(drop=True)

            # 选择并排序最终列
            final_cols = ['date', 'open', 'high', 'low', 'close', 'volume', 'amount']
            final_cols = [c for c in final_cols if c in df.columns]
            df = df[final_cols]

            self.logger.info(f"成功获取 {symbol} 数据: {len(df)} 条 [{df['date'].min()} ~ {df['date'].max()}]")

            return df

        except Exception as e:
            self.logger.error(f"获取 {symbol} 数据失败: {e}")
            raise DataLoaderError(f"获取 {symbol} 数据失败: {e}")

    def get_realtime_quotes(
        self,
        symbols: Union[str, List[str]],
        **kwargs
    ) -> pd.DataFrame:
        """
        获取实时行情数据（覆盖基类方法）

        参数:
            symbols: 股票代码或代码列表，如 '000001' 或 ['000001', '600000']
            **kwargs: 额外参数

        返回:
            DataFrame，包含实时行情字段
        """
        self.ensure_connected()

        # 统一处理为列表
        if isinstance(symbols, str):
            symbols = [symbols]

        results = []

        for symbol in symbols:
            try:
                code, market = self._symbol_to_market(symbol)

                # 获取实时行情
                quote = self._client.quote(symbol=code, market=market)

                if quote is not None and not quote.empty:
                    quote['symbol'] = symbol
                    results.append(quote)

            except Exception as e:
                self.logger.warning(f"获取 {symbol} 实时行情失败: {e}")
                continue

        if not results:
            return pd.DataFrame()

        # 合并结果
        df = pd.concat(results, ignore_index=True)

        return df

    def get_etf_list(
        self,
        market: Optional[str] = None,
        **kwargs
    ) -> pd.DataFrame:
        """
        获取ETF基金列表

        参数:
            market: 市场代码，如 'sh'（上海）、'sz'（深圳）、None（全部）
            **kwargs: 额外参数

        返回:
            DataFrame，包含ETF基本信息：
            - symbol: 代码
            - name: 名称
            - market: 市场(sh/sz)
        """
        self.ensure_connected()

        results = []

        try:
            if market is None or market.lower() == 'sh':
                # 上海ETF：51、58开头
                sh_etf = self._client.stocks(market=MARKET_SH)
                if sh_etf is not None and not sh_etf.empty:
                    # 筛选ETF（51、56、58、50开头）
                    sh_etf = sh_etf[sh_etf['code'].str.startswith(('51', '56', '58', '50'))]
                    if not sh_etf.empty:
                        sh_etf = sh_etf.copy()
                        sh_etf['market'] = 'sh'
                        results.append(sh_etf)

            if market is None or market.lower() == 'sz':
                # 深圳ETF：15、16开头
                sz_etf = self._client.stocks(market=MARKET_SZ)
                if sz_etf is not None and not sz_etf.empty:
                    # 筛选ETF（15、16开头）
                    sz_etf = sz_etf[sz_etf['code'].str.startswith(('15', '16'))]
                    if not sz_etf.empty:
                        sz_etf = sz_etf.copy()
                        sz_etf['market'] = 'sz'
                        results.append(sz_etf)

        except Exception as e:
            self.logger.error(f"获取ETF列表失败: {e}")
            raise DataLoaderError(f"获取ETF列表失败: {e}")

        if not results:
            return pd.DataFrame(columns=['symbol', 'name', 'market'])

        # 合并结果
        df = pd.concat(results, ignore_index=True)

        # 标准化列名
        column_mapping = {}
        if 'code' in df.columns:
            column_mapping['code'] = 'symbol'
        if 'name' in df.columns and 'name' not in df.columns:
            pass  # name 列名相同
        if '简称' in df.columns:
            column_mapping['简称'] = 'name'

        if column_mapping:
            df = df.rename(columns=column_mapping)

        # 选择必要列
        result_cols = ['symbol', 'name', 'market']
        available_cols = [c for c in result_cols if c in df.columns]
        df = df[available_cols].copy()

        return df

    def get_stock_list(
        self,
        market: Optional[str] = None,
        **kwargs
    ) -> pd.DataFrame:
        """
        获取股票列表（覆盖基类方法）

        参数:
            market: 市场代码，如 'sh'（上海）、'sz'（深圳）、None（全部）
            **kwargs: 额外参数

        返回:
            DataFrame，包含股票基本信息
        """
        self.ensure_connected()

        results = []

        try:
            if market is None or market.lower() == 'sh':
                # 上海市场
                sh_list = self._client.stocks(market=MARKET_SH)
                if sh_list is not None and not sh_list.empty:
                    sh_list = sh_list.copy()
                    sh_list['market'] = 'sh'
                    results.append(sh_list)

            if market is None or market.lower() == 'sz':
                # 深圳市场
                sz_list = self._client.stocks(market=MARKET_SZ)
                if sz_list is not None and not sz_list.empty:
                    sz_list = sz_list.copy()
                    sz_list['market'] = 'sz'
                    results.append(sz_list)

        except Exception as e:
            self.logger.error(f"获取股票列表失败: {e}")
            raise DataLoaderError(f"获取股票列表失败: {e}")

        if not results:
            return pd.DataFrame()

        # 合并结果
        df = pd.concat(results, ignore_index=True)

        # 标准化列名
        if 'code' in df.columns and 'symbol' not in df.columns:
            df = df.rename(columns={'code': 'symbol'})

        return df
