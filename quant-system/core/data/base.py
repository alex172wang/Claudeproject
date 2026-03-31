"""
数据获取器抽象基类
定义统一的数据获取接口
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from datetime import datetime
import pandas as pd


class DataFetcher(ABC):
    """
    数据获取器抽象基类

    所有具体数据获取器（mootdx、AKShare、FRED）都必须继承此类
    并实现以下抽象方法
    """

    def __init__(self, config: Dict[str, Any]):
        """
        初始化数据获取器

        Args:
            config: 配置字典，包含连接参数等
        """
        self.config = config
        self.name = config.get('name', 'unknown')
        self.description = config.get('description', '')
        self._connected = False

    @abstractmethod
    def connect(self) -> bool:
        """
        建立数据源连接

        Returns:
            bool: 连接是否成功
        """
        pass

    @abstractmethod
    def disconnect(self) -> bool:
        """
        断开数据源连接

        Returns:
            bool: 断开是否成功
        """
        pass

    @abstractmethod
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
            code: 标的代码（如 '510300'、'000001'）
            start_date: 开始日期，格式 'YYYY-MM-DD'
            end_date: 结束日期，格式 'YYYY-MM-DD'
            freq: 频率，支持 'day'、'week'、'month'、'minute'
            **kwargs: 其他参数

        Returns:
            DataFrame: 包含以下列的数据表
                - date: 日期
                - open: 开盘价
                - high: 最高价
                - low: 最低价
                - close: 收盘价
                - volume: 成交量
                - amount: 成交额（可选）
        """
        pass

    @abstractmethod
    def get_realtime_quote(self, codes: List[str]) -> Optional[pd.DataFrame]:
        """
        获取实时行情

        Args:
            codes: 标的代码列表

        Returns:
            DataFrame: 实时行情数据
        """
        pass

    @abstractmethod
    def get_etf_list(self) -> Optional[pd.DataFrame]:
        """
        获取ETF列表

        Returns:
            DataFrame: ETF基础信息
        """
        pass

    @property
    def is_connected(self) -> bool:
        """检查连接状态"""
        return self._connected

    def health_check(self) -> Dict[str, Any]:
        """
        健康检查

        Returns:
            dict: 包含状态信息的字典
        """
        return {
            'name': self.name,
            'connected': self._connected,
            'config_loaded': bool(self.config),
        }
