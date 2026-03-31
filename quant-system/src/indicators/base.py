# -*- coding: utf-8 -*-
"""
指标计算基类模块

提供所有指标计算的基类，定义通用接口和工具方法。
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple, Union
import pandas as pd
import numpy as np


class BaseIndicator(ABC):
    """
    指标计算基类

    所有具体指标类都应继承此类，实现 calculate 方法。

    属性:
        data (pd.DataFrame): 输入数据，必须包含 OHLCV 列
        params (dict): 指标参数字典
    """

    # 默认参数
    default_params = {}

    def __init__(self, data: pd.DataFrame, **kwargs):
        """
        初始化指标计算器

        参数:
            data: 输入数据，DataFrame格式，必须包含以下列之一:
                  - OHLCV标准列: open, high, low, close, volume
                  - 或中文列: 开盘, 最高, 最低, 收盘, 成交量
            **kwargs: 指标参数，会覆盖默认参数
        """
        # 标准化列名
        self.data = self._standardize_columns(data)

        # 合并参数
        self.params = {**self.default_params, **kwargs}

        # 验证数据
        self._validate_data()

    def _standardize_columns(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        标准化列名为英文小写格式

        映射关系:
            开盘/open -> open
            最高/high -> high
            最低/low -> low
            收盘/close -> close
            成交量/volume -> volume
        """
        df = data.copy()

        # 列名映射
        column_mapping = {
            # 中文映射
            '开盘': 'open',
            '最高': 'high',
            '最低': 'low',
            '收盘': 'close',
            '成交量': 'volume',
            # 英文大小写映射
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume',
        }

        # 重命名列
        df = df.rename(columns=column_mapping)

        # 确保列名小写
        df.columns = [col.lower() for col in df.columns]

        return df

    def _validate_data(self):
        """验证输入数据是否满足最低要求"""
        required_cols = ['close']
        missing = [col for col in required_cols if col not in self.data.columns]
        if missing:
            raise ValueError(f"数据缺少必要列: {missing}")

    @abstractmethod
    def calculate(self) -> pd.Series:
        """
        计算指标值

        子类必须实现此方法，返回指标的 Series。

        返回:
            pd.Series: 指标值序列，索引与输入数据一致
        """
        pass

    def get_result(self) -> pd.Series:
        """获取计算结果（calculate 的包装）"""
        return self.calculate()

    def __call__(self) -> pd.Series:
        """使实例可调用"""
        return self.calculate()


class IndicatorUtils:
    """
    指标计算工具类

    提供常用的数学计算工具方法。
    """

    @staticmethod
    def linear_regression_slope(series: pd.Series, window: int) -> pd.Series:
        """
        计算线性回归斜率

        参数:
            series: 输入序列
            window: 回归窗口

        返回:
            斜率序列
        """
        x = np.arange(window)
        slopes = []

        for i in range(len(series)):
            if i < window - 1:
                slopes.append(np.nan)
            else:
                y = series.iloc[i - window + 1:i + 1].values
                # 线性回归: y = a + bx
                A = np.vstack([x, np.ones(window)]).T
                b, a = np.linalg.lstsq(A, y, rcond=None)[0]
                slopes.append(b)

        return pd.Series(slopes, index=series.index)

    @staticmethod
    def r_squared(series: pd.Series, window: int) -> pd.Series:
        """
        计算 R²（决定系数）

        参数:
            series: 输入序列
            window: 计算窗口

        返回:
            R²序列
        """
        x = np.arange(window)
        r2_values = []

        for i in range(len(series)):
            if i < window - 1:
                r2_values.append(np.nan)
            else:
                y = series.iloc[i - window + 1:i + 1].values

                # 计算R²
                ss_res = np.sum((y - np.mean(y)) ** 2)
                ss_tot = np.sum((y - np.mean(y)) ** 2)

                if ss_tot == 0:
                    r2 = 0
                else:
                    # 使用线性回归计算R²
                    A = np.vstack([x, np.ones(window)]).T
                    y_pred = A @ np.linalg.lstsq(A, y, rcond=None)[0]
                    ss_res = np.sum((y - y_pred) ** 2)
                    r2 = 1 - (ss_res / ss_tot)

                r2_values.append(max(0, r2))

        return pd.Series(r2_values, index=series.index)

    @staticmethod
    def z_score_normalize(series: pd.Series, window: int = 252) -> pd.Series:
        """
        Z-Score标准化

        参数:
            series: 输入序列
            window: 滚动窗口（默认252个交易日）

        返回:
            标准化后的序列
        """
        rolling_mean = series.rolling(window=window, min_periods=1).mean()
        rolling_std = series.rolling(window=window, min_periods=1).std()

        return (series - rolling_mean) / (rolling_std + 1e-10)

    @staticmethod
    def min_max_normalize(series: pd.Series) -> pd.Series:
        """
        Min-Max标准化到 [0, 1] 区间

        参数:
            series: 输入序列

        返回:
            标准化后的序列
        """
        min_val = series.min()
        max_val = series.max()

        if max_val == min_val:
            return pd.Series(0.5, index=series.index)

        return (series - min_val) / (max_val - min_val)
