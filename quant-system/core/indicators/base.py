"""
指标计算基类和注册表
定义所有指标的统一接口和工具方法
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import numpy as np
import pandas as pd


@dataclass
class IndicatorValue:
    """
    指标值数据类
    统一存储单个指标计算结果
    """
    # 数值结果
    value: float = 0.0

    # 原始得分（计算后未归一化的值）
    raw_score: float = 0.0

    # 归一化得分（0-100）
    normalized_score: float = 50.0

    # 百分位排名（0-100）
    percentile: float = 50.0

    # 信号方向（-1=负面, 0=中性, 1=正面）
    signal: int = 0

    # 是否触发阈值
    threshold_triggered: bool = False

    # 时间戳
    timestamp: datetime = field(default_factory=datetime.now)

    # 附加元数据
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'value': self.value,
            'raw_score': self.raw_score,
            'normalized_score': self.normalized_score,
            'percentile': self.percentile,
            'signal': self.signal,
            'threshold_triggered': self.threshold_triggered,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata,
        }


@dataclass
class IndicatorResult:
    """
    指标计算结果数据类
    存储单个指标的完整计算结果
    """
    # 指标ID
    indicator_id: str = ''

    # 指标名称
    indicator_name: str = ''

    # 指标层级（L1/L2/L3/L4）
    layer: str = ''

    # 当前值
    current: IndicatorValue = field(default_factory=IndicatorValue)

    # 历史序列（可选）
    history: List[IndicatorValue] = field(default_factory=list)

    # 附加指标值（子指标）
    sub_indicators: Dict[str, IndicatorValue] = field(default_factory=dict)

    # 计算参数
    params: Dict[str, Any] = field(default_factory=dict)

    # 计算时间
    computed_at: datetime = field(default_factory=datetime.now)

    # 计算状态
    status: str = 'success'  # success, error, partial

    # 错误信息
    error_message: str = ''

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'indicator_id': self.indicator_id,
            'indicator_name': self.indicator_name,
            'layer': self.layer,
            'current': self.current.to_dict(),
            'history': [h.to_dict() for h in self.history],
            'sub_indicators': {k: v.to_dict() for k, v in self.sub_indicators.items()},
            'params': self.params,
            'computed_at': self.computed_at.isoformat(),
            'status': self.status,
            'error_message': self.error_message,
        }

    def get_score(self) -> float:
        """获取标准化得分"""
        return self.current.normalized_score

    def get_signal(self) -> int:
        """获取信号方向"""
        return self.current.signal


class BaseIndicator(ABC):
    """
    指标计算基类

    所有指标必须继承此类，实现calculate方法
    """

    # 指标ID（子类必须覆盖）
    INDICATOR_ID: str = ''

    # 指标名称（子类必须覆盖）
    INDICATOR_NAME: str = ''

    # 指标层级（L1/L2/L3/L4，子类必须覆盖）
    LAYER: str = ''

    # 默认参数（子类可覆盖）
    DEFAULT_PARAMS: Dict[str, Any] = {}

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """
        初始化指标

        Args:
            params: 指标参数，将覆盖默认参数
        """
        self.params = {**self.DEFAULT_PARAMS, **(params or {})}
        self._validate_params()

    def _validate_params(self) -> None:
        """验证参数有效性"""
        pass  # 子类可覆盖

    @abstractmethod
    def calculate(self, data: pd.DataFrame) -> IndicatorResult:
        """
        计算指标

        Args:
            data: 包含OHLCV数据的DataFrame

        Returns:
            IndicatorResult: 指标计算结果
        """
        pass

    def calculate_series(self, data: pd.DataFrame) -> pd.Series:
        """
        计算指标序列

        Args:
            data: 包含OHLCV数据的DataFrame

        Returns:
            pd.Series: 指标值序列
        """
        result = self.calculate(data)
        return pd.Series([v.value for v in result.history], index=[v.timestamp for v in result.history])

    def get_info(self) -> Dict[str, Any]:
        """获取指标信息"""
        return {
            'indicator_id': self.INDICATOR_ID,
            'indicator_name': self.INDICATOR_NAME,
            'layer': self.LAYER,
            'params': self.params,
        }


class IndicatorRegistry:
    """
    指标注册表

    管理所有指标类的注册和实例化
    """

    _indicators: Dict[str, type] = {}

    @classmethod
    def register(cls, indicator_class: type) -> type:
        """
        注册指标类

        用法:
            @IndicatorRegistry.register
            class MyIndicator(BaseIndicator):
                ...
        """
        if not issubclass(indicator_class, BaseIndicator):
            raise ValueError(f"{indicator_class.__name__} 必须继承 BaseIndicator")

        indicator_id = indicator_class.INDICATOR_ID
        if not indicator_id:
            raise ValueError(f"{indicator_class.__name__} 必须定义 INDICATOR_ID")

        cls._indicators[indicator_id] = indicator_class
        return indicator_class

    @classmethod
    def create(cls, indicator_id: str, **kwargs) -> BaseIndicator:
        """
        创建指标实例

        Args:
            indicator_id: 指标ID
            **kwargs: 指标参数

        Returns:
            BaseIndicator: 指标实例
        """
        if indicator_id not in cls._indicators:
            raise ValueError(f"未知的指标ID: {indicator_id}，已注册: {list(cls._indicators.keys())}")

        indicator_class = cls._indicators[indicator_id]
        return indicator_class(params=kwargs)

    @classmethod
    def list_all(cls) -> List[str]:
        """列出所有已注册的指标ID"""
        return list(cls._indicators.keys())

    @classmethod
    def list_by_category(cls, layer: str) -> List[str]:
        """按层级列出指标ID"""
        return [
            indicator_id
            for indicator_id, indicator_class in cls._indicators.items()
            if indicator_class.LAYER == layer
        ]

    @classmethod
    def get_info(cls, indicator_id: str) -> Dict[str, Any]:
        """获取指标信息"""
        if indicator_id not in cls._indicators:
            raise ValueError(f"未知的指标ID: {indicator_id}")
        return cls._indicators[indicator_id].DEFAULT_PARAMS


# ==================== 工具函数 ====================

def normalize_score(value: float, min_val: float, max_val: float, reverse: bool = False) -> float:
    """
    归一化得分到0-100

    Args:
        value: 原始值
        min_val: 最小值
        max_val: 最大值
        reverse: 是否反向（值越大得分越低）

    Returns:
        float: 归一化得分（0-100）
    """
    if max_val == min_val:
        return 50.0

    score = (value - min_val) / (max_val - min_val) * 100
    score = max(0, min(100, score))  # 限制在0-100

    if reverse:
        score = 100 - score

    return score


def calculate_slope(series: pd.Series, window: int) -> float:
    """
    计算序列斜率

    Args:
        series: 数据序列
        window: 窗口大小

    Returns:
        float: 斜率值
    """
    if len(series) < window:
        return 0.0

    y = series.iloc[-window:].values
    x = np.arange(len(y))

    # 线性回归
    n = len(x)
    slope = (n * np.sum(x * y) - np.sum(x) * np.sum(y)) / (n * np.sum(x**2) - np.sum(x)**2)

    return slope


def calculate_r_squared(series: pd.Series, window: int) -> float:
    """
    计算R²（决定系数）

    Args:
        series: 数据序列
        window: 窗口大小

    Returns:
        float: R²值（0-1）
    """
    if len(series) < window:
        return 0.0

    y = series.iloc[-window:].values
    x = np.arange(len(y))

    # 计算相关系数
    correlation = np.corrcoef(x, y)[0, 1]
    r_squared = correlation ** 2

    return max(0, r_squared)


def hurst_exponent(series: pd.Series, window: int = 100) -> float:
    """
    计算Hurst指数

    Args:
        series: 数据序列
        window: 窗口大小

    Returns:
        float: Hurst指数（0.5-1.0表示趋势持续，0-0.5表示均值回归）
    """
    if len(series) < window:
        return 0.5

    # 使用R/S分析法
    lags = range(2, min(100, window // 4))
    tau = [np.std(np.subtract(series.iloc[-window:].values[lag:], series.iloc[-window:].values[:-lag])) for lag in lags]

    # 线性回归
    try:
        reg = np.polyfit(np.log(lags), np.log(tau), 1)
        h = reg[0]
    except:
        h = 0.5

    return h


def calculate_percentile(series: pd.Series, window: int = 252) -> float:
    """
    计算当前值在历史窗口中的百分位

    Args:
        series: 数据序列
        window: 历史窗口大小

    Returns:
        float: 百分位排名（0-100）
    """
    if len(series) < 2:
        return 50.0

    current = series.iloc[-1]
    history = series.iloc[-window:-1] if len(series) > window else series.iloc[:-1]

    percentile = (history < current).sum() / len(history) * 100

    return percentile
