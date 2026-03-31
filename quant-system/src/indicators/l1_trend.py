# -*- coding: utf-8 -*-
"""
L1 趋势层指标模块

实现趋势层的核心指标：
- L1-01: 复合斜率动量
- L1-02: EMA趋势过滤
- L1-03: 趋势加速度
- L1-04: 价格通道位置
- L1-05: FRED趋势共振

哲学隐喻："概率最高的路径"
"""

from typing import Optional, Tuple
import pandas as pd
import numpy as np
from .base import BaseIndicator, IndicatorUtils


class CompositeSlopeMomentum(BaseIndicator):
    """
    L1-01: 复合斜率动量

    计算加权斜率动量，综合考虑趋势强度和拟合优度。

    公式：
        Momentum = 30日斜率 × R²(0.6) + 15日斜率 × R²(0.4)

    参数:
        slope_long: 长期斜率窗口，默认30
        slope_short: 短期斜率窗口，默认15
        weight_long: 长期权重，默认0.6
        weight_short: 短期权重，默认0.4
    """

    default_params = {
        'slope_long': 30,
        'slope_short': 15,
        'weight_long': 0.6,
        'weight_short': 0.4,
    }

    def calculate(self) -> pd.Series:
        """计算复合斜率动量"""
        close = self.data['close']
        p = self.params

        # 计算长期斜率和R²
        slope_long = IndicatorUtils.linear_regression_slope(
            close, p['slope_long']
        )
        r2_long = IndicatorUtils.r_squared(close, p['slope_long'])

        # 计算短期斜率和R²
        slope_short = IndicatorUtils.linear_regression_slope(
            close, p['slope_short']
        )
        r2_short = IndicatorUtils.r_squared(close, p['slope_short'])

        # 加权合成
        momentum = (
            slope_long * r2_long * p['weight_long'] +
            slope_short * r2_short * p['weight_short']
        )

        return momentum


class EMATrendFilter(BaseIndicator):
    """
    L1-02: EMA趋势过滤

    基于价格与EMA的关系判断趋势方向。

    公式：
        多头环境：收盘价 > EMA(N)
        空头环境：收盘价 < EMA(N)

    参数:
        period: EMA周期，默认120
        confirmation_days: 确认天数，默认3
    """

    default_params = {
        'period': 120,
        'confirmation_days': 3,
    }

    def calculate(self) -> pd.Series:
        """计算EMA趋势过滤信号"""
        close = self.data['close']
        p = self.params

        # 计算EMA
        ema = close.ewm(span=p['period'], adjust=False).mean()

        # 价格与EMA的关系
        above_ema = (close > ema).astype(int)
        below_ema = (close < ema).astype(int)

        # N日确认
        confirmed_bull = above_ema.rolling(
            window=p['confirmation_days']
        ).sum() >= p['confirmation_days']

        confirmed_bear = below_ema.rolling(
            window=p['confirmation_days']
        ).sum() >= p['confirmation_days']

        # 生成信号：1=多头，-1=空头，0=中性
        signal = pd.Series(0, index=close.index)
        signal[confirmed_bull] = 1
        signal[confirmed_bear] = -1

        return signal


class TrendAcceleration(BaseIndicator):
    """
    L1-03: 趋势加速度

    衡量动量的变化率，识别趋势的加速或减速。

    公式：
        加速度 = 动量(t) - 动量(t-窗口)

    参数:
        momentum_window: 动量计算窗口，默认使用L1-01参数
        diff_window: 差分窗口，默认5
    """

    default_params = {
        'momentum_params': {
            'slope_long': 30,
            'slope_short': 15,
            'weight_long': 0.6,
            'weight_short': 0.4,
        },
        'diff_window': 5,
    }

    def calculate(self) -> pd.Series:
        """计算趋势加速度"""
        # 先计算动量
        momentum = CompositeSlopeMomentum(
            self.data, **self.params['momentum_params']
        ).calculate()

        # 计算动量的差分（加速度）
        acceleration = momentum.diff(self.params['diff_window'])

        return acceleration


class PriceChannelPosition(BaseIndicator):
    """
    L1-04: 价格通道位置

    衡量价格在其近期波动区间中的相对位置。

    公式：
        位置 = (Close - N日最低) / (N日最高 - N日最低)

    参数:
        period: 通道周期，默认60
    """

    default_params = {
        'period': 60,
    }

    def calculate(self) -> pd.Series:
        """计算价格通道位置"""
        close = self.data['close']
        high = self.data['high']
        low = self.data['low']
        p = self.params

        # 计算N日高低点
        highest_high = high.rolling(window=p['period']).max()
        lowest_low = low.rolling(window=p['period']).min()

        # 计算位置
        channel_range = highest_high - lowest_low
        position = (close - lowest_low) / (channel_range + 1e-10)

        # 限制在 [0, 1] 范围内
        position = position.clip(0, 1)

        return position


class FREDTrendResonance(BaseIndicator):
    """
    L1-05: FRED趋势共振

    基于 FRED 宏观数据的趋势共振指标。

    计算：
        美10Y国债收益率斜率 + 美元指数DXY斜率

    参数:
        yield_period: 收益率计算周期，默认30
        dxy_period: DXY计算周期，默认30
        data_source: 数据源，默认'fred'
    """

    default_params = {
        'yield_symbol': 'GS10',      # 10年期国债收益率
        'dxy_symbol': 'DTWEXBGS',    # 美元指数
        'slope_window': 30,
    }

    def __init__(self, data: pd.DataFrame, **kwargs):
        """
        初始化 FRED 趋势共振指标

        注意：此指标需要外部传入 FRED 数据
        """
        super().__init__(data, **kwargs)

        # 检查必要的列
        required_cols = ['yield_rate', 'dxy']
        missing = [col for col in required_cols if col not in self.data.columns]

        if missing:
            # 如果缺少FRED数据，生成空序列（后续从外部加载）
            for col in missing:
                self.data[col] = np.nan

    def calculate(self) -> pd.Series:
        """计算 FRED 趋势共振"""
        p = self.params

        # 获取收益率和DXY数据
        if 'yield_rate' in self.data.columns:
            yield_rate = self.data['yield_rate']
        else:
            return pd.Series(np.nan, index=self.data.index)

        if 'dxy' in self.data.columns:
            dxy = self.data['dxy']
        else:
            dxy = pd.Series(0, index=self.data.index)  # 如果没有DXY数据，设为0

        # 计算斜率
        yield_slope = IndicatorUtils.linear_regression_slope(
            yield_rate, p['slope_window']
        )
        dxy_slope = IndicatorUtils.linear_regression_slope(
            dxy, p['slope_window']
        )

        # 合成共振指标（标准化后相加）
        yield_slope_norm = IndicatorUtils.z_score_normalize(yield_slope, 252)
        dxy_slope_norm = IndicatorUtils.z_score_normalize(dxy_slope, 252)

        resonance = yield_slope_norm + dxy_slope_norm

        return resonance
