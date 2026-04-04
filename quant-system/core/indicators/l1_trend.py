"""
L1 趋势层指标实现

包含：
- L1-01: 复合斜率动量
- L1-02: EMA趋势过滤
- L1-03: 趋势加速度
- L1-04: 价格通道位置
- L1-05: FRED趋势共振
"""

# 向后兼容别名（供scorer.py导入使用）
CompositeSlopeMomentum = None
EMATrendFilter = None
TrendAcceleration = None
PriceChannelPosition = None
FREDTrendResonance = None

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional

from .base import (
    BaseIndicator, IndicatorRegistry, IndicatorResult, IndicatorValue,
    normalize_score, calculate_slope, calculate_r_squared
)


@IndicatorRegistry.register
# 定义实际类，并设置向后兼容别名
class L101CompositeSlopeMomentum(BaseIndicator):
    """
    L1-01: 复合斜率动量

    计算公式：30日斜率×R²(0.6) + 15日斜率×R²(0.4)
    信号意义：正向动量越强得分越高（0-100）
    """

    INDICATOR_ID = 'L1-01'
    INDICATOR_NAME = '复合斜率动量'
    LAYER = 'L1'

    DEFAULT_PARAMS = {
        'long_window': 30,
        'short_window': 15,
        'long_weight': 0.6,
        'short_weight': 0.4,
    }

    def calculate(self, data: pd.DataFrame) -> IndicatorResult:
        """计算复合斜率动量"""
        params = self.params
        close = data['close']

        # 计算长周期斜率和R²
        long_slope = calculate_slope(close, params['long_window'])
        long_r2 = calculate_r_squared(close, params['long_window'])

        # 计算短周期斜率和R²
        short_slope = calculate_slope(close, params['short_window'])
        short_r2 = calculate_r_squared(close, params['short_window'])

        # 复合斜率
        composite_slope = (
            long_slope * long_r2 * params['long_weight'] +
            short_slope * short_r2 * params['short_weight']
        )

        # 归一化得分（斜率通常在-0.1到0.1之间）
        normalized_score = normalize_score(composite_slope, -0.05, 0.05)

        # 确定信号方向
        if normalized_score > 60:
            signal = 1
        elif normalized_score < 40:
            signal = -1
        else:
            signal = 0

        # 构建结果
        current_value = IndicatorValue(
            value=composite_slope,
            raw_score=composite_slope,
            normalized_score=normalized_score,
            signal=signal,
            metadata={
                'long_slope': long_slope,
                'long_r2': long_r2,
                'short_slope': short_slope,
                'short_r2': short_r2,
            }
        )

        return IndicatorResult(
            indicator_id=self.INDICATOR_ID,
            indicator_name=self.INDICATOR_NAME,
            layer=self.LAYER,
            current=current_value,
            params=params,
        )


# 设置向后兼容别名
CompositeSlopeMomentum = L101CompositeSlopeMomentum

@IndicatorRegistry.register
class L102EMATrendFilter(BaseIndicator):
    """
    L1-02: EMA趋势过滤

    计算公式：收盘价 > EMA(N) 为多头环境
    信号意义：价格在均线上方为多头，下方为空头
    """

    INDICATOR_ID = 'L1-02'
    INDICATOR_NAME = 'EMA趋势过滤'
    LAYER = 'L1'

    DEFAULT_PARAMS = {
        'period': 120,
    }

    def calculate(self, data: pd.DataFrame) -> IndicatorResult:
        """计算EMA趋势过滤"""
        params = self.params
        close = data['close']

        # 计算EMA
        ema = close.ewm(span=params['period'], adjust=False).mean()

        # 当前值
        current_close = close.iloc[-1]
        current_ema = ema.iloc[-1]

        # 价格在均线上方比例（偏离程度）
        deviation = (current_close - current_ema) / current_ema * 100

        # 归一化得分（偏离-10%到10%映射到0-100）
        normalized_score = normalize_score(deviation, -10, 10)

        # 信号方向
        if normalized_score > 55:
            signal = 1
        elif normalized_score < 45:
            signal = -1
        else:
            signal = 0

        current_value = IndicatorValue(
            value=deviation,
            raw_score=deviation,
            normalized_score=normalized_score,
            signal=signal,
            metadata={
                'close': current_close,
                'ema': current_ema,
                'deviation_pct': deviation,
            }
        )

        return IndicatorResult(
            indicator_id=self.INDICATOR_ID,
            indicator_name=self.INDICATOR_NAME,
            layer=self.LAYER,
            current=current_value,
            params=params,
        )


@IndicatorRegistry.register
class L103TrendAcceleration(BaseIndicator):
    """
    L1-03: 趋势加速度

    计算公式：复合斜率动量的一阶差分（动量的动量）
    信号意义：加速上涨得高分，减速上涨得分下降
    """

    INDICATOR_ID = 'L1-03'
    INDICATOR_NAME = '趋势加速度'
    LAYER = 'L1'

    DEFAULT_PARAMS = {
        'diff_window': 5,
        'momentum_long_window': 30,
        'momentum_short_window': 15,
    }

    def calculate(self, data: pd.DataFrame) -> IndicatorResult:
        """计算趋势加速度"""
        params = self.params
        close = data['close']

        # 首先计算复合斜率动量
        long_slope = calculate_slope(close, params['momentum_long_window'])
        long_r2 = calculate_r_squared(close, params['momentum_long_window'])
        short_slope = calculate_slope(close, params['momentum_short_window'])
        short_r2 = calculate_r_squared(close, params['momentum_short_window'])

        composite_momentum = (
            long_slope * long_r2 * 0.6 +
            short_slope * short_r2 * 0.4
        )

        # 计算动量的差分（加速度）
        if len(close) >= params['diff_window'] + 5:
            momentum_series = close.rolling(window=20).apply(
                lambda x: calculate_slope(x, len(x)), raw=True
            )
            acceleration = momentum_series.diff(params['diff_window']).iloc[-1]
        else:
            acceleration = 0.0

        # 归一化（加速度通常在-0.001到0.001之间）
        normalized_score = normalize_score(acceleration, -0.001, 0.001)

        # 信号方向
        if normalized_score > 60:
            signal = 1  # 加速上涨
        elif normalized_score < 40:
            signal = -1  # 加速下跌
        else:
            signal = 0

        current_value = IndicatorValue(
            value=acceleration,
            raw_score=acceleration,
            normalized_score=normalized_score,
            signal=signal,
            metadata={
                'composite_momentum': composite_momentum,
                'acceleration': acceleration,
            }
        )

        return IndicatorResult(
            indicator_id=self.INDICATOR_ID,
            indicator_name=self.INDICATOR_NAME,
            layer=self.LAYER,
            current=current_value,
            params=params,
        )


@IndicatorRegistry.register
class L104PriceChannelPosition(BaseIndicator):
    """
    L1-04: 价格通道位置

    计算公式：(Close - N日最低) / (N日最高 - N日最低)
    信号意义：价格越接近N日高点，得分越高
    """

    INDICATOR_ID = 'L1-04'
    INDICATOR_NAME = '价格通道位置'
    LAYER = 'L1'

    DEFAULT_PARAMS = {
        'period': 60,
    }

    def calculate(self, data: pd.DataFrame) -> IndicatorResult:
        """计算价格通道位置"""
        params = self.params
        close = data['close']

        # 计算N日最高和最低
        high_n = close.rolling(window=params['period']).max()
        low_n = close.rolling(window=params['period']).min()

        # 当前值
        current_close = close.iloc[-1]
        current_high = high_n.iloc[-1]
        current_low = low_n.iloc[-1]

        # 计算位置比例
        if current_high > current_low:
            position = (current_close - current_low) / (current_high - current_low)
        else:
            position = 0.5

        # 归一化到0-100
        normalized_score = position * 100

        # 信号方向
        if normalized_score > 70:
            signal = 1
        elif normalized_score < 30:
            signal = -1
        else:
            signal = 0

        current_value = IndicatorValue(
            value=position,
            raw_score=position,
            normalized_score=normalized_score,
            signal=signal,
            metadata={
                'close': current_close,
                'high_n': current_high,
                'low_n': current_low,
                'position_pct': position * 100,
            }
        )

        return IndicatorResult(
            indicator_id=self.INDICATOR_ID,
            indicator_name=self.INDICATOR_NAME,
            layer=self.LAYER,
            current=current_value,
            params=params,
        )


@IndicatorRegistry.register
class L105FREDTrendResonance(BaseIndicator):
    """
    L1-05: FRED趋势共振

    计算公式：美10Y国债收益率斜率 + 美元指数DXY斜率
    信号意义：美国基本面越强，A股资金面压力越大（负相关）
    注：本指标需要FRED数据源
    """

    INDICATOR_ID = 'L1-05'
    INDICATOR_NAME = 'FRED趋势共振'
    LAYER = 'L1'

    DEFAULT_PARAMS = {
        'yield_slope_window': 30,
        'dxy_slope_window': 30,
        'weight_yield': 0.5,
        'weight_dxy': 0.5,
    }

    def calculate(self, data: pd.DataFrame, yield_data: Optional[pd.Series] = None,
                  dxy_data: Optional[pd.Series] = None) -> IndicatorResult:
        """
        计算FRED趋势共振

        Args:
            data: 本地价格数据（备用）
            yield_data: 10Y美债收益率序列
            dxy_data: 美元指数序列
        """
        params = self.params

        # 如果没有提供外部数据，使用默认值或尝试获取
        if yield_data is None or dxy_data is None:
            # 使用数据中的收益率代理（如ETF的收益率）
            yield_slope = 0.0
            dxy_slope = 0.0
            status = 'partial'
            error_msg = 'FRED数据未提供，使用默认值'
        else:
            # 计算斜率
            yield_slope = calculate_slope(yield_data, params['yield_slope_window'])
            dxy_slope = calculate_slope(dxy_data, params['dxy_slope_window'])
            status = 'success'
            error_msg = ''

        # 加权合成（注意：FRED共振与A股通常负相关）
        # 美国基本面越强（收益率和美元上升），A股压力越大
        composite = (
            yield_slope * params['weight_yield'] +
            dxy_slope * params['weight_dxy']
        )

        # 归一化（斜率通常在-0.01到0.01之间）
        # 注意：这里反向归一化，因为美国基本面越强，A股压力越大
        normalized_score = normalize_score(composite, -0.01, 0.01, reverse=True)

        # 信号方向
        if normalized_score > 60:
            signal = 1  # 美国基本面弱，利好A股
        elif normalized_score < 40:
            signal = -1  # 美国基本面强，利空A股
        else:
            signal = 0

        current_value = IndicatorValue(
            value=composite,
            raw_score=composite,
            normalized_score=normalized_score,
            signal=signal,
            metadata={
                'yield_slope': yield_slope,
                'dxy_slope': dxy_slope,
                'composite': composite,
                'note': '负相关：美国基本面越强，A股压力越大' if not error_msg else error_msg,
            }
        )

        result = IndicatorResult(
            indicator_id=self.INDICATOR_ID,
            indicator_name=self.INDICATOR_NAME,
            layer=self.LAYER,
            current=current_value,
            params=params,
        )
        result.status = status
        result.error_message = error_msg

        return result
