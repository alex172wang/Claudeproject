# -*- coding: utf-8 -*-
"""
AKShare 数据加载器模块

封装 AKShare 库，提供财经数据获取接口。

AKShare 特点：
- 纯 Python 实现，无需额外依赖
- 数据覆盖广泛：股票、期货、期权、基金、宏观、外汇等
- 实时更新，数据源来自各交易所/网站公开数据
- 无需账号，免费使用

支持数据（对应 docs/多维量化指标体系_v1.0.md 第七节数据源映射）：
- A股/港股行情 OHLCV：AKShare(日线)
- ETF净值/折溢价：AKShare fund_etf_hist_sina
- 50ETF/300ETF期权 IV/Greeks/成交量：AKShare option_sse_daily_sina
- 跨市场数据（A股/港股/美股/商品）：AKShare
- 宏观-资产共振度：FRED+AKShare
- PMI等宏观数据：AKShare

使用限制：
- 调用频率不宜过高，建议增加延时避免被封
- 数据仅供学习研究，商业使用请遵循数据源协议
"""

from typing import Dict, List, Optional, Union
from datetime import datetime, date
import time
import pandas as pd
import numpy as np

try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
except ImportError:
    AKSHARE_AVAILABLE = False

from .loaders import (
    BaseDataLoader, DataLoaderError, DataSourceNotAvailableError,
    DataValidationError, DataFrequency
)


class AKShareLoader(BaseDataLoader):
    """
    AKShare 数据加载器

    封装 AKShare 接口，提供股票、ETF、期权、宏观等数据获取。

    属性:
        rate_limit: 调用频率限制（秒）
        last_call_time: 上次调用时间

    示例:
        >>> loader = AKShareLoader()
        >>> df = loader.get_stock_history('000001', start='20230101', end='20231231')
        >>> etf_list = loader.get_etf_list()
    """

    default_params = {
        'rate_limit': 0.5,  # 调用间隔（秒）
        'timeout': 30,
    }

    # 周期映射（AKShare 使用字符串）
    FREQUENCY_MAP = {
        DataFrequency.DAILY: "daily",
        DataFrequency.WEEKLY: "weekly",
        DataFrequency.MONTHLY: "monthly",
        DataFrequency.QUARTERLY: "quarterly",
        DataFrequency.YEARLY: "yearly",
    }

    def __init__(self, config: Optional[Dict] = None):
        """
        初始化 AKShare 数据加载器

        参数:
            config: 配置参数字典，可覆盖默认参数

        抛出:
            DataSourceNotAvailableError: AKShare 库未安装
        """
        if not AKSHARE_AVAILABLE:
            raise DataSourceNotAvailableError(
                "AKShare 库未安装，请执行: pip install akshare"
            )

        super().__init__(name='akshare', config=config)
        self._last_call_time = 0

    def _rate_limit(self):
        """频率限制，避免调用过快"""
        min_interval = self.params.get('rate_limit', 0.5)
        elapsed = time.time() - self._last_call_time
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)
        self._last_call_time = time.time()

    def connect(self, **kwargs) -> bool:
        """
        AKShare 无需显式连接，此操作仅作状态标记

        返回:
            bool: 始终返回 True（AKShare 无需连接）
        """
        self._connected = True
        self.logger.info("AKShare 准备就绪（无需显式连接）")
        return True

    def disconnect(self) -> bool:
        """
        AKShare 无需显式断开，此操作仅作状态标记

        返回:
            bool: 始终返回 True
        """
        self._connected = False
        self.logger.info("AKShare 连接已标记为断开")
        return True

    def is_connected(self) -> bool:
        """
        检查 AKShare 是否已"连接"

        返回:
            bool: AKShare 是否准备就绪
        """
        return AKSHARE_AVAILABLE

    def get_stock_history(
        self,
        symbol: str,
        start: Optional[Union[str, datetime, date]] = None,
        end: Optional[Union[str, datetime, date]] = None,
        frequency: DataFrequency = DataFrequency.DAILY,
        **kwargs
    ) -> pd.DataFrame:
        """
        获取股票历史K线数据

        参数:
            symbol: 股票代码，如 '000001'、'600000'
            start: 开始日期，支持 '20230101' 或 datetime 对象
            end: 结束日期，默认为今天
            frequency: 数据频率，默认日线
            adjust: 复权类型，默认 "qfq"（前复权），可选 "hfq"（后复权）或 None

        返回:
            DataFrame，包含 OHLCV 列
        """
        self._rate_limit()

        # 标准化代码格式（AKShare需要带市场前缀）
        symbol = symbol.strip()
        if not (symbol.startswith('sh') or symbol.startswith('sz')):
            # 根据代码规则判断市场并添加前缀
            if symbol.startswith(('6', '5', '9')):
                symbol = f"sh{symbol}"
            else:
                symbol = f"sz{symbol}"

        # 处理日期
        if start is None:
            start = "19700101"
        else:
            start = self._parse_date(start)

        if end is None:
            end = datetime.now().strftime('%Y%m%d')
        else:
            end = self._parse_date(end)

        # 获取复权设置
        adjust = kwargs.get('adjust', 'qfq')

        try:
            # 调用 AKShare 获取历史数据
            df = ak.stock_zh_a_hist(
                symbol=symbol,
                start_date=str(start),
                end_date=str(end),
                adjust=adjust,
            )

            if df is None or df.empty:
                self.logger.warning(f"未获取到数据: {symbol}")
                return pd.DataFrame(columns=['date', 'open', 'high', 'low', 'close', 'volume', 'amount'])

            # 标准化列名
            column_mapping = {
                '日期': 'date',
                '开盘': 'open',
                '最高': 'high',
                '最低': 'low',
                '收盘': 'close',
                '成交量': 'volume',
                '成交额': 'amount',
            }

            # 重命名列
            for old, new in column_mapping.items():
                if old in df.columns and new not in df.columns:
                    df = df.rename(columns={old: new})

            # 转换日期格式
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])

            # 按日期排序
            df = df.sort_values('date').reset_index(drop=True)

            # 选择最终列
            final_cols = ['date', 'open', 'high', 'low', 'close', 'volume', 'amount']
            final_cols = [c for c in final_cols if c in df.columns]
            df = df[final_cols]

            self.logger.info(f"成功获取 {symbol} 数据: {len(df)} 条")

            return df

        except Exception as e:
            self.logger.error(f"获取 {symbol} 数据失败: {e}")
            raise DataLoaderError(f"获取 {symbol} 数据失败: {e}")

    def get_etf_list(self) -> pd.DataFrame:
        """
        获取ETF基金列表

        返回:
            DataFrame，包含ETF基本信息
        """
        self._rate_limit()

        try:
            df = ak.fund_etf_spot_em()
            return df
        except Exception as e:
            self.logger.error(f"获取ETF列表失败: {e}")
            raise DataLoaderError(f"获取ETF列表失败: {e}")

    def get_option_data(self, symbol: str = "510050") -> pd.DataFrame:
        """
        获取期权数据（50ETF或300ETF期权）

        参数:
            symbol: 标的代码，510050(50ETF) 或 510300(300ETF)

        返回:
            DataFrame，包含期权数据
        """
        self._rate_limit()

        try:
            if symbol == "510050":
                df = ak.option_sse_daily_sina(symbol="50ETF")
            elif symbol == "510300":
                df = ak.option_sse_daily_sina(symbol="300ETF")
            else:
                raise ValueError(f"不支持的期权标的: {symbol}")

            return df
        except Exception as e:
            self.logger.error(f"获取期权数据失败: {e}")
            raise DataLoaderError(f"获取期权数据失败: {e}")

    def get_index_data(self, symbol: str = "000001") -> pd.DataFrame:
        """
        获取指数数据

        参数:
            symbol: 指数代码，如 000001(上证指数), 399001(深证成指), 000300(沪深300)

        返回:
            DataFrame，包含指数历史数据
        """
        self._rate_limit()

        try:
            # 判断市场
            if symbol.startswith('0'):
                market = "sh"
            else:
                market = "sz"

            df = ak.index_zh_a_hist(symbol=symbol, period="daily", start_date="19700101", end_date="20991231")
            return df
        except Exception as e:
            self.logger.error(f"获取指数数据失败: {e}")
            raise DataLoaderError(f"获取指数数据失败: {e}")

    def _parse_date(self, date_val: Union[str, datetime, date, int]) -> str:
        """
        将日期转换为字符串格式（YYYYMMDD）

        参数:
            date_val: 日期值，支持多种类型

        返回:
            str: 格式为 YYYYMMDD 的字符串
        """
        if isinstance(date_val, int):
            return str(date_val)

        if isinstance(date_val, str):
            # 尝试解析多种格式
            for fmt in ['%Y%m%d', '%Y-%m-%d', '%Y/%m/%d']:
                try:
                    dt = datetime.strptime(date_val, fmt)
                    return dt.strftime('%Y%m%d')
                except ValueError:
                    continue
            # 如果无法解析，直接返回原字符串
            return date_val

        if isinstance(date_val, (datetime, date)):
            return date_val.strftime('%Y%m%d')

        raise ValueError(f"不支持的日期类型: {type(date_val)}")
