"""
L2 结构层指标实现

包含：
- L2-01: Hurst指数
- L2-02: 波动率结构比
- L2-03: 成交量形态分歧
- L2-04: 回撤分形维度
- L2-05: K线实体比
- L2-06: 波动率自相关
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional

from .base import (
    BaseIndicator, IndicatorRegistry, IndicatorResult, IndicatorValue,
    normalize_score, hurst_exponent
)


@IndicatorRegistry.register
class L201HurstExponent(BaseIndicator):
    """
    L2-01: Hurst指数

    使用R/S分析法，衡量趋势持续性品质
    H > 0.5 表示趋势持续，H < 0.5 表示均值回归
    """

    INDICATOR_ID = 'L2-01'
    INDICATOR_NAME = 'Hurst指数'
    LAYER = 'L2'

    DEFAULT_PARAMS = {
        'window': 60,
    }

    def calculate(self, data: pd.DataFrame) -> IndicatorResult:
        """计算Hurst指数"""
        params = self.params
        close = data['close']

        # 计算Hurst指数
        h = hurst_exponent(close, params['window'])

        # 归一化得分（Hurst通常在0.3-0.7之间）
        # H > 0.5 趋势强（高分），H < 0.5 趋势弱（低分）
        normalized_score = normalize_score(h, 0.3, 0.7)

        # 信号方向
        if h > 0.55:
            signal = 1  # 强趋势
        elif h < 0.45:
            signal = -1  # 均值回归
        else:
            signal = 0

        current_value = IndicatorValue(
            value=h,
            raw_score=h,
            normalized_score=normalized_score,
            signal=signal,
            metadata={
                'hurst': h,
                'interpretation': 'trending' if h > 0.5 else 'mean_reverting',
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
class L202VolatilityStructureRatio(BaseIndicator):
    """
    L2-02: 波动率结构比

    短期实现波动率 / 长期实现波动率
    用于识别波动率结构异常（如黑天鹅前短期波动率快速上升）
    """

    INDICATOR_ID = 'L2-02'
    INDICATOR_NAME = '波动率结构比'
    LAYER = 'L2'

    DEFAULT_PARAMS = {
        'short_window': 5,
        'long_window': 30,
    }

    def calculate(self, data: pd.DataFrame) -> IndicatorResult:
        """计算波动率结构比"""
        params = self.params
        close = data['close']

        # 计算收益率
        returns = close.pct_change().dropna()

        # 计算短期和长期波动率
        short_vol = returns.rolling(window=params['short_window']).std() * np.sqrt(252)
        long_vol = returns.rolling(window=params['long_window']).std() * np.sqrt(252)

        # 计算波动率结构比
        vol_ratio = short_vol / long_vol

        current_ratio = vol_ratio.iloc[-1] if not vol_ratio.empty else 1.0

        # 归一化得分（比率通常在0.5-2.0之间）
        # 比率接近1表示正常，偏离1表示异常
        # 这里我们反转：正常结构得高分，异常得低分
        deviation = abs(current_ratio - 1.0)
        normalized_score = normalize_score(deviation, 0, 1.5, reverse=True)

        # 信号方向
        if current_ratio > 1.3:
            signal = -1  # 短期波动率飙升，风险警示
        elif current_ratio < 0.7:
            signal = 1  # 短期波动率低，可能有机会
        else:
            signal = 0

        current_value = IndicatorValue(
            value=current_ratio,
            raw_score=current_ratio,
            normalized_score=normalized_score,
            signal=signal,
            metadata={
                'volatility_ratio': current_ratio,
                'short_volatility': short_vol.iloc[-1] if not short_vol.empty else None,
                'long_volatility': long_vol.iloc[-1] if not long_vol.empty else None,
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
class L203VolumeDivergence(BaseIndicator):
    """
    L2-03: 成交量形态分歧

    价格新高时成交量相对MA(20)的偏离度
    用于识别量价背离（顶部放量、底部缩量等形态）
    """

    INDICATOR_ID = 'L2-03'
    INDICATOR_NAME = '成交量形态分歧'
    LAYER = 'L2'

    DEFAULT_PARAMS = {
        'volume_ma_period': 20,
    }

    def calculate(self, data: pd.DataFrame) -> IndicatorResult:
        """计算成交量形态分歧"""
        params = self.params
        close = data['close']
        volume = data['volume']

        # 计算成交量MA
        volume_ma = volume.rolling(window=params['volume_ma_period']).mean()

        # 计算偏离度
        volume_deviation = (volume - volume_ma) / volume_ma * 100

        # 判断价格是否创新高/新低
        price_ma20 = close.rolling(window=20).mean()

        current_close = close.iloc[-1]
        current_vol_dev = volume_deviation.iloc[-1]

        # 量价配合分析
        # 价格上涨 + 成交量放大 = 健康上涨（高分）
        # 价格上涨 + 成交量萎缩 = 量价背离（低分）

        # 计算最近N天的趋势
        if len(close) >= 5:
            price_trend = (close.iloc[-1] - close.iloc[-5]) / close.iloc[-5] * 100
        else:
            price_trend = 0

        # 得分逻辑：
        # 上涨趋势中，成交量放大 = 确认趋势（高分）
        # 上涨趋势中，成交量萎缩 = 背离（低分）
        if price_trend > 0:  # 上涨趋势
            if current_vol_dev > 0:  # 放量
                normalized_score = 50 + min(abs(current_vol_dev), 50)  # 50-100
            else:  # 缩量（背离）
                normalized_score = 50 - min(abs(current_vol_dev), 50)  # 0-50
        else:  # 下跌趋势或横盘
            if current_vol_dev < 0:  # 缩量
                normalized_score = 50 + min(abs(current_vol_dev), 50)
            else:  # 放量
                normalized_score = 50 - min(abs(current_vol_dev), 50)

        # 信号方向
        if normalized_score > 65:
            signal = 1  # 量价配合良好
        elif normalized_score < 35:
            signal = -1  # 量价背离
        else:
            signal = 0

        current_value = IndicatorValue(
            value=current_vol_dev,
            raw_score=current_vol_dev,
            normalized_score=normalized_score,
            signal=signal,
            metadata={
                'volume_deviation_pct': current_vol_dev,
                'volume_ma': volume_ma.iloc[-1] if not volume_ma.empty else None,
                'price_trend_5d': price_trend,
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
class L204DrawdownFractal(BaseIndicator):
    """
    L2-04: 回撤分形维度

    最大回撤序列的Hurst指数（回撤是否有自相似性）
    用于评估回撤模式，判断是黑天鹅还是正常调整
    """

    INDICATOR_ID = 'L2-04'
    INDICATOR_NAME = '回撤分形维度'
    LAYER = 'L2'

    DEFAULT_PARAMS = {
        'rolling_window': 120,
    }

    def calculate(self, data: pd.DataFrame) -> IndicatorResult:
        """计算回撤分形维度"""
        params = self.params
        close = data['close']

        # 计算回撤序列
        rolling_max = close.expanding().max()
        drawdown = (close - rolling_max) / rolling_max

        # 提取回撤期（回撤 < 0 的段）
        drawdown_periods = []
        in_drawdown = False
        start_idx = 0

        for i, dd in enumerate(drawdown):
            if dd < -0.001 and not in_drawdown:  # 进入回撤
                in_drawdown = True
                start_idx = i
            elif dd >= -0.001 and in_drawdown:  # 退出回撤
                in_drawdown = False
                if i - start_idx >= 3:  # 至少3天
                    drawdown_periods.append(i - start_idx)

        # 计算回撤期的Hurst指数
        if len(drawdown_periods) >= 10:
            hurst = hurst_exponent(pd.Series(drawdown_periods))
        else:
            hurst = 0.5  # 默认随机游走

        # 归一化得分
        # H > 0.5 表示回撤有自相似性（可预测），得低分（风险警示）
        # H < 0.5 表示回撤是随机的（正常），得高分
        normalized_score = normalize_score(hurst, 0.3, 0.7, reverse=True)

        # 信号方向
        if hurst > 0.6:
            signal = -1  # 回撤模式化，警惕
        elif hurst < 0.4:
            signal = 1  # 回撤随机，正常
        else:
            signal = 0

        current_value = IndicatorValue(
            value=hurst,
            raw_score=hurst,
            normalized_score=normalized_score,
            signal=signal,
            metadata={
                'hurst': hurst,
                'drawdown_periods_count': len(drawdown_periods),
                'max_drawdown': drawdown.min() if not drawdown.empty else 0,
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
class L205BodyRatio(BaseIndicator):
    """
    L2-05: K线实体比

    N日内实体占比均值（实体/振幅），衡量趋势纯净度
    实体比高表示趋势强，影线多表示博弈激烈
    """

    INDICATOR_ID = 'L2-05'
    INDICATOR_NAME = 'K线实体比'
    LAYER = 'L2'

    DEFAULT_PARAMS = {
        'period': 20,
    }

    def calculate(self, data: pd.DataFrame) -> IndicatorResult:
        """计算K线实体比"""
        params = self.params
        open_price = data['open']
        high = data['high']
        low = data['low']
        close = data['close']

        # 计算实体和振幅
        body = abs(close - open_price)
        range_total = high - low

        # 实体比（避免除零）
        body_ratio = body / range_total.replace(0, np.nan)
        body_ratio = body_ratio.fillna(0)

        # 计算N日均值
        body_ratio_ma = body_ratio.rolling(window=params['period']).mean()

        current_ratio = body_ratio_ma.iloc[-1] if not body_ratio_ma.empty else 0.5

        # 归一化得分（实体比0.3-0.8映射到0-100）
        normalized_score = normalize_score(current_ratio, 0.3, 0.8)

        # 信号方向
        if current_ratio > 0.7:
            signal = 1  # 趋势强
        elif current_ratio < 0.4:
            signal = -1  # 博弈激烈
        else:
            signal = 0

        current_value = IndicatorValue(
            value=current_ratio,
            raw_score=current_ratio,
            normalized_score=normalized_score,
            signal=signal,
            metadata={
                'body_ratio': current_ratio,
                'body_ratio_std': body_ratio.iloc[-params['period']:].std() if len(body_ratio) >= params['period'] else 0,
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
class L206VolatilityAutocorrelation(BaseIndicator):
    """
    L2-06: 波动率自相关

    日收益率绝对值的ACF(1)，衡量波动率聚集程度
    用于评估波动率持续性
    """

    INDICATOR_ID = 'L2-06'
    INDICATOR_NAME = '波动率自相关'
    LAYER = 'L2'

    DEFAULT_PARAMS = {
        'lag': 1,
        'window': 30,
    }

    def calculate(self, data: pd.DataFrame) -> IndicatorResult:
        """计算波动率自相关"""
        params = self.params
        close = data['close']

        # 计算收益率
        returns = close.pct_change().dropna()

        # 计算绝对收益率（波动率代理）
        abs_returns = returns.abs()

        # 计算自相关
        if len(abs_returns) >= params['window'] + params['lag']:
            autocorr = abs_returns.rolling(window=params['window']).apply(
                lambda x: x.autocorr(lag=params['lag']) if len(x) > params['lag'] else 0,
                raw=False
            )
            current_autocorr = autocorr.iloc[-1] if not autocorr.empty else 0
        else:
            current_autocorr = 0

        # 归一化得分（自相关-0.2到0.8映射到0-100）
        # 自相关高表示波动率聚集（风险），得低分
        normalized_score = normalize_score(current_autocorr, -0.2, 0.8, reverse=True)

        # 信号方向
        if current_autocorr > 0.5:
            signal = -1  # 波动率聚集，风险高
        elif current_autocorr < 0.1:
            signal = 1  # 波动率独立，相对稳定
        else:
            signal = 0

        current_value = IndicatorValue(
            value=current_autocorr,
            raw_score=current_autocorr,
            normalized_score=normalized_score,
            signal=signal,
            metadata={
                'autocorr': current_autocorr,
                'lag': params['lag'],
            }
        )

        return IndicatorResult(
            indicator_id=self.INDICATOR_ID,
            indicator_name=self.INDICATOR_NAME,
            layer=self.LAYER,
            current=current_value,
            params=params,
        )
