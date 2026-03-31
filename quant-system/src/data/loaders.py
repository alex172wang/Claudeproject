# -*- coding: utf-8 -*-
"""
数据加载器基类模块

定义统一的数据加载接口，所有具体数据加载器都应继承 BaseDataLoader。
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Union, Tuple
from datetime import datetime, date
from enum import Enum
import pandas as pd


class DataFrequency(Enum):
    """数据频率枚举"""
    TICK = "tick"           # Tick数据
    MINUTE_1 = "1min"       # 1分钟
    MINUTE_5 = "5min"       # 5分钟
    MINUTE_15 = "15min"     # 15分钟
    MINUTE_30 = "30min"     # 30分钟
    MINUTE_60 = "60min"     # 60分钟
    DAILY = "day"           # 日线
    WEEKLY = "week"         # 周线
    MONTHLY = "month"       # 月线
    QUARTERLY = "quarter"   # 季线
    YEARLY = "year"         # 年线


class DataLoaderError(Exception):
    """数据加载器异常基类"""
    pass


class DataSourceNotAvailableError(DataLoaderError):
    """数据源不可用异常"""
    pass


class DataValidationError(DataLoaderError):
    """数据验证失败异常"""
    pass


class BaseDataLoader(ABC):
    """
    数据加载器基类

    所有具体数据加载器都应继承此类，实现以下抽象方法：
    - connect(): 建立数据连接
    - disconnect(): 断开数据连接
    - is_connected(): 检查连接状态
    - get_stock_history(): 获取股票历史数据
    - get_realtime_quotes(): 获取实时行情

    属性:
        name: 加载器名称
        config: 配置字典
        _connected: 连接状态
    """

    def __init__(self, name: str, config: Optional[Dict] = None):
        """
        初始化数据加载器

        参数:
            name: 加载器名称标识
            config: 配置参数字典，如超时时间、重试次数等
        """
        self.name = name
        self.config = config or {}
        self._connected = False
        self._client = None

    @abstractmethod
    def connect(self, **kwargs) -> bool:
        """
        建立数据连接

        参数:
            **kwargs: 连接参数（如用户名、密码、服务器地址等）

        返回:
            bool: 连接是否成功

        抛出:
            DataSourceNotAvailableError: 数据源不可用
        """
        pass

    @abstractmethod
    def disconnect(self) -> bool:
        """
        断开数据连接

        返回:
            bool: 断开是否成功
        """
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """
        检查连接状态

        返回:
            bool: 是否已连接
        """
        pass

    def ensure_connected(self):
        """
        确保连接已建立，未连接时自动连接

        抛出:
            DataSourceNotAvailableError: 无法建立连接
        """
        if not self.is_connected():
            if not self.connect():
                raise DataSourceNotAvailableError(
                    f"无法连接到数据源: {self.name}"
                )

    @abstractmethod
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
            symbol: 股票代码（如 '000001'、'600000'）
            start: 开始日期，支持字符串 '20230101' 或 datetime 对象
            end: 结束日期，默认为今天
            frequency: 数据频率，默认日线
            **kwargs: 额外参数（如是否复权、字段筛选等）

        返回:
            DataFrame，包含 OHLCV 列：
            - open: 开盘价
            - high: 最高价
            - low: 最低价
            - close: 收盘价
            - volume: 成交量
            可选列：
            - amount: 成交额
            - turnover: 换手率
            - vwap: 成交量加权平均价

        抛出:
            DataValidationError: 数据验证失败
            DataSourceNotAvailableError: 数据源不可用
        """
        pass

    @abstractmethod
    def get_realtime_quotes(
        self,
        symbols: Union[str, List[str]],
        **kwargs
    ) -> pd.DataFrame:
        """
        获取实时行情数据

        参数:
            symbols: 股票代码或代码列表
            **kwargs: 额外参数

        返回:
            DataFrame，包含实时行情字段：
            - symbol: 代码
            - name: 名称
            - last_price: 最新价
            - bid_price: 买一价
            - ask_price: 卖一价
            - bid_volume: 买一量
            - ask_volume: 卖一量
            - volume: 成交量
            - amount: 成交额
            - high: 最高价
            - low: 最低价
            - open: 开盘价
            - pre_close: 昨收
            - change_pct: 涨跌幅
            - timestamp: 时间戳
        """
        pass

    def get_stock_list(
        self,
        market: Optional[str] = None,
        **kwargs
    ) -> pd.DataFrame:
        """
        获取股票列表（可选实现）

        参数:
            market: 市场代码，如 'sh'（上海）、'sz'（深圳）、'hk'（香港）
            **kwargs: 额外参数

        返回:
            DataFrame，包含股票基本信息：
            - symbol: 代码
            - name: 名称
            - market: 市场
            - industry: 行业
            - list_date: 上市日期
            - total_shares: 总股本
            - float_shares: 流通股本
        """
        # 默认抛出未实现异常，子类可选择性实现
        raise NotImplementedError(
            f"{self.name} 未实现 get_stock_list 方法"
        )

    def validate_data(self, df: pd.DataFrame, required_cols: List[str]) -> bool:
        """
        验证数据是否包含必要列

        参数:
            df: 待验证的DataFrame
            required_cols: 必要列名列表

        返回:
            bool: 验证是否通过

        抛出:
            DataValidationError: 验证失败
        """
        if df is None or df.empty:
            raise DataValidationError("数据为空")

        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            raise DataValidationError(f"缺少必要列: {missing}")

        return True

    def __enter__(self):
        """上下文管理器入口"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.disconnect()
        return False

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name='{self.name}', connected={self.is_connected()})>"

    def __del__(self):
        """析构时确保断开连接"""
        if hasattr(self, '_connected') and self._connected:
            try:
                self.disconnect()
            except:
                pass  # 忽略清理时的错误
