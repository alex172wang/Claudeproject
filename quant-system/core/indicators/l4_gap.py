"""
L4 缺口层指标实现

包含：
- L4-01: 隐含-实现波动率价差
- L4-02: 期权偏度
- L4-03: 认沽认购比
- L4-04: 流动性缺口
- L4-05: 尾部风险度量
- L4-06: 跳空缺口频率
- L4-07: FRED压力合成
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
from scipy import stats

from .base import (
    BaseIndicator, IndicatorRegistry, IndicatorResult, IndicatorValue,
    normalize_score
)


@IndicatorRegistry.register
class L401IVRVSpread(BaseIndicator):
    """
    L4-01: 隐含-实现波动率价差 (IV-RV Spread)

    50ETF期权IV - 标的30d实现波动率
    用于评估期权市场对波动率的定价预期
    """

    INDICATOR_ID = 'L4-01'
    INDICATOR_NAME = '隐含-实现波动率价差'
    LAYER = 'L4'

    DEFAULT_PARAMS = {
        'iv_source': 'option_ATM',
        'rv_window': 30,
        'option_type': '50ETF',
    }

    def calculate(self, data: pd.DataFrame, iv_data: Optional[pd.Series] = None) -> IndicatorResult:
        """
        计算IV-RV价差

        Args:
            data: 标的资产价格数据
            iv_data: 隐含波动率数据（可选）
        """
        params = self.params
        close = data['close']

        # 计算实现波动率 (RV)
        returns = close.pct_change().dropna()
        if len(returns) >= params['rv_window']:
            rv = returns.iloc[-params['rv_window']:].std() * np.sqrt(252) * 100  # 转换为年化百分比
        else:
            rv = 20.0  # 默认值

        # 获取隐含波动率 (IV)
        if iv_data is not None and not iv_data.empty:
            iv = iv_data.iloc[-1]
        else:
            # 如果没有提供IV数据，使用历史RV的1.2倍作为代理
            iv = rv * 1.2

        # 计算价差
        spread = iv - rv

        # 归一化得分
        # 价差-10到20映射到0-100
        # 价差太高表示期权市场恐慌（风险），得低分；正常得高分
        normalized_score = normalize_score(spread, -10, 20, reverse=True)

        # 信号方向
        if spread > 15:
            signal = -1  # IV远高于RV，恐慌情绪
        elif spread < -5:
            signal = 1  # IV低于RV，乐观情绪
        else:
            signal = 0

        current_value = IndicatorValue(
            value=spread,
            raw_score=spread,
            normalized_score=normalized_score,
            signal=signal,
            metadata={
                'iv': iv,
                'rv': rv,
                'spread': spread,
                'note': 'IV>RV表示期权市场预期波动率高于历史波动率',
            }
        )

        result = IndicatorResult(
            indicator_id=self.INDICATOR_ID,
            indicator_name=self.INDICATOR_NAME,
            layer=self.LAYER,
            current=current_value,
            params=params,
        )

        return result


@IndicatorRegistry.register
class L402OptionSkew(BaseIndicator):
    """
    L4-02: 期权偏度 (Option Skew)

    25Δ看跌IV - 25Δ看涨IV（恐惧的不对称性）
    用于衡量市场对下跌风险的定价
    """

    INDICATOR_ID = 'L4-02'
    INDICATOR_NAME = '期权偏度'
    LAYER = 'L4'

    DEFAULT_PARAMS = {
        'delta_put': 25,
        'delta_call': 25,
        'maturity': 'monthly',
    }

    def calculate(self, data: pd.DataFrame, put_iv: Optional[float] = None,
                  call_iv: Optional[float] = None) -> IndicatorResult:
        """
        计算期权偏度

        Args:
            data: 标的资产价格数据
            put_iv: 看跌期权IV
            call_iv: 看涨期权IV
        """
        params = self.params

        # 计算偏度
        if put_iv is not None and call_iv is not None:
            skew = put_iv - call_iv
        else:
            # 如果没有提供数据，使用默认值
            skew = 2.0  # 默认正偏度（市场通常恐慌）

        # 归一化得分
        # 偏度-5到15映射到0-100
        # 偏度太高表示市场恐慌（风险），得低分；正常得高分
        normalized_score = normalize_score(skew, -5, 15, reverse=True)

        # 信号方向
        if skew > 10:
            signal = -1  # 高度偏斜，极度恐慌
        elif skew < 0:
            signal = 1  # 反向偏斜，贪婪
        else:
            signal = 0

        current_value = IndicatorValue(
            value=skew,
            raw_score=skew,
            normalized_score=normalized_score,
            signal=signal,
            metadata={
                'skew': skew,
                'put_iv': put_iv,
                'call_iv': call_iv,
                'note': 'Skew>0表示看跌期权IV高于看涨期权，市场恐慌',
            }
        )

        result = IndicatorResult(
            indicator_id=self.INDICATOR_ID,
            indicator_name=self.INDICATOR_NAME,
            layer=self.LAYER,
            current=current_value,
            params=params,
        )

        return result


@IndicatorRegistry.register
class L403PCRatio(BaseIndicator):
    """
    L4-03: 认沽认购比 (P/C Ratio)

    看跌期权成交量 / 看涨期权成交量
    用于衡量市场情绪（恐慌/贪婪）
    """

    INDICATOR_ID = 'L4-03'
    INDICATOR_NAME = '认沽认购比'
    LAYER = 'L4'

    DEFAULT_PARAMS = {
        'window': 5,
    }

    def calculate(self, data: pd.DataFrame, put_volume: Optional[pd.Series] = None,
                  call_volume: Optional[pd.Series] = None) -> IndicatorResult:
        """
        计算认沽认购比

        Args:
            data: 标的资产价格数据
            put_volume: 看跌期权成交量序列
            call_volume: 看涨期权成交量序列
        """
        params = self.params

        # 计算P/C比率
        if put_volume is not None and call_volume is not None:
            # 计算滚动平均
            put_ma = put_volume.rolling(window=params['window']).mean()
            call_ma = call_volume.rolling(window=params['window']).mean()

            # 避免除零
            pc_ratio = put_ma / call_ma.replace(0, np.nan)
            pc_ratio = pc_ratio.fillna(1.0)

            current_ratio = pc_ratio.iloc[-1] if not pc_ratio.empty else 1.0
        else:
            # 如果没有提供数据，使用默认值
            current_ratio = 1.0

        # 归一化得分
        # P/C比率0.5到2.0映射到0-100
        # 比率太高表示恐慌（风险），得低分；正常得高分
        normalized_score = normalize_score(current_ratio, 0.5, 2.0, reverse=True)

        # 信号方向
        if current_ratio > 1.5:
            signal = -1  # 高度恐慌
        elif current_ratio < 0.7:
            signal = 1  # 贪婪
        else:
            signal = 0

        current_value = IndicatorValue(
            value=current_ratio,
            raw_score=current_ratio,
            normalized_score=normalized_score,
            signal=signal,
            metadata={
                'pc_ratio': current_ratio,
                'interpretation': '恐慌' if current_ratio > 1.2 else ('贪婪' if current_ratio < 0.8 else '中性'),
            }
        )

        result = IndicatorResult(
            indicator_id=self.INDICATOR_ID,
            indicator_name=self.INDICATOR_NAME,
            layer=self.LAYER,
            current=current_value,
            params=params,
        )

        return result


@IndicatorRegistry.register
class L404LiquidityGap(BaseIndicator):
    """
    L4-04: 流动性缺口

    买一卖一价差/中间价的滚动均值
    用于衡量市场流动性状况
    """

    INDICATOR_ID = 'L4-04'
    INDICATOR_NAME = '流动性缺口'
    LAYER = 'L4'

    DEFAULT_PARAMS = {
        'window': 20,
    }

    def calculate(self, data: pd.DataFrame, bid: Optional[pd.Series] = None,
                  ask: Optional[pd.Series] = None) -> IndicatorResult:
        """
        计算流动性缺口

        Args:
            data: 价格数据
            bid: 买一价序列
            ask: 卖一价序列
        """
        params = self.params

        # 如果有提供买卖价数据
        if bid is not None and ask is not None:
            # 计算价差
            spread = ask - bid
            mid = (bid + ask) / 2
            spread_pct = spread / mid * 100  # 转换为百分比

            # 计算滚动平均
            spread_ma = spread_pct.rolling(window=params['window']).mean()
            current_spread = spread_ma.iloc[-1] if not spread_ma.empty else 0.1
        else:
            # 如果没有提供数据，使用收盘价估算
            # 使用日内振幅作为流动性的代理
            high = data['high']
            low = data['low']
            close = data['close']

            daily_range = (high - low) / close * 100
            range_ma = daily_range.rolling(window=params['window']).mean()
            current_spread = range_ma.iloc[-1] / 10 if not range_ma.empty else 0.1  # 估算

        # 归一化得分（价差0.05-0.5映射到0-100）
        # 价差越大流动性越差（风险），得低分
        normalized_score = normalize_score(current_spread, 0.05, 0.5, reverse=True)

        # 信号方向
        if current_spread > 0.3:
            signal = -1  # 流动性差
        elif current_spread < 0.1:
            signal = 1  # 流动性好
        else:
            signal = 0

        current_value = IndicatorValue(
            value=current_spread,
            raw_score=current_spread,
            normalized_score=normalized_score,
            signal=signal,
            metadata={
                'spread_pct': current_spread,
                'interpretation': '流动性差' if current_spread > 0.2 else ('流动性好' if current_spread < 0.1 else '正常'),
            }
        )

        result = IndicatorResult(
            indicator_id=self.INDICATOR_ID,
            indicator_name=self.INDICATOR_NAME,
            layer=self.LAYER,
            current=current_value,
            params=params,
        )

        return result


@IndicatorRegistry.register
class L405TailRisk(BaseIndicator):
    """
    L4-05: 尾部风险度量

    滚动N日收益率的峰度（Kurtosis）
    用于评估收益率分布的"肥尾"程度
    """

    INDICATOR_ID = 'L4-05'
    INDICATOR_NAME = '尾部风险度量'
    LAYER = 'L4'

    DEFAULT_PARAMS = {
        'window': 60,
    }

    def calculate(self, data: pd.DataFrame) -> IndicatorResult:
        """计算尾部风险度量"""
        params = self.params
        close = data['close']

        # 计算收益率
        returns = close.pct_change().dropna()

        # 计算滚动峰度
        if len(returns) >= params['window']:
            rolling_kurtosis = returns.rolling(window=params['window']).kurt()
            current_kurtosis = rolling_kurtosis.iloc[-1] if not rolling_kurtosis.empty else 3.0
        else:
            current_kurtosis = 3.0  # 正态分布的峰度

        # 处理NaN
        if pd.isna(current_kurtosis):
            current_kurtosis = 3.0

        # 归一化得分（峰度0到10映射到0-100）
        # 峰度越高表示尾部风险越大（风险），得低分
        # 正态分布峰度为3，高分表示接近正态
        normalized_score = normalize_score(current_kurtosis, 6, 0, reverse=False)

        # 信号方向
        if current_kurtosis > 6:
            signal = -1  # 肥尾风险高
        elif current_kurtosis < 4:
            signal = 1  # 接近正态，风险可控
        else:
            signal = 0

        current_value = IndicatorValue(
            value=current_kurtosis,
            raw_score=current_kurtosis,
            normalized_score=normalized_score,
            signal=signal,
            metadata={
                'kurtosis': current_kurtosis,
                'interpretation': '肥尾' if current_kurtosis > 4 else '接近正态',
                'reference': '正态分布峰度=3',
            }
        )

        result = IndicatorResult(
            indicator_id=self.INDICATOR_ID,
            indicator_name=self.INDICATOR_NAME,
            layer=self.LAYER,
            current=current_value,
            params=params,
        )

        return result


@IndicatorRegistry.register
class L406GapFrequency(BaseIndicator):
    """
    L4-06: 跳空缺口频率

    N日内跳空幅度>1%的天数占比
    用于识别市场不连续性风险
    """

    INDICATOR_ID = 'L4-06'
    INDICATOR_NAME = '跳空缺口频率'
    LAYER = 'L4'

    DEFAULT_PARAMS = {
        'window': 30,
        'gap_threshold': 0.01,
    }

    def calculate(self, data: pd.DataFrame) -> IndicatorResult:
        """计算跳空缺口频率"""
        params = self.params
        open_price = data['open']
        close = data['close']

        # 计算隔夜收益率（今开/昨收 - 1）
        overnight_returns = open_price / close.shift(1) - 1

        # 识别跳空缺口
        gaps = overnight_returns.abs() > params['gap_threshold']

        # 计算窗口内的缺口频率
        if len(gaps) >= params['window']:
            recent_gaps = gaps.iloc[-params['window']:]
            gap_frequency = recent_gaps.sum() / params['window']
        else:
            gap_frequency = 0.0

        # 归一化得分（频率0-0.3映射到0-100）
        # 缺口频率越高表示市场不连续性越大（风险），得低分
        normalized_score = normalize_score(gap_frequency, 0, 0.3, reverse=True)

        # 信号方向
        if gap_frequency > 0.2:
            signal = -1  # 频繁跳空，不稳定
        elif gap_frequency < 0.05:
            signal = 1  # 很少跳空，稳定
        else:
            signal = 0

        current_value = IndicatorValue(
            value=gap_frequency,
            raw_score=gap_frequency,
            normalized_score=normalized_score,
            signal=signal,
            metadata={
                'gap_frequency': gap_frequency,
                'gaps_in_window': int(gaps.iloc[-params['window']:].sum()) if len(gaps) >= params['window'] else 0,
                'threshold': params['gap_threshold'],
            }
        )

        result = IndicatorResult(
            indicator_id=self.INDICATOR_ID,
            indicator_name=self.INDICATOR_NAME,
            layer=self.LAYER,
            current=current_value,
            params=params,
        )

        return result


@IndicatorRegistry.register
class L407FREDPressureComposite(BaseIndicator):
    """
    L4-07: FRED压力合成

    美联储资产负债表变化率 + 信用利差(BAA-AAA)趋势
    用于评估宏观流动性压力
    """

    INDICATOR_ID = 'L4-07'
    INDICATOR_NAME = 'FRED压力合成'
    LAYER = 'L4'

    DEFAULT_PARAMS = {
        'fed_balance_sheet': 'WALCL',
        'credit_spread_baa': 'BAA',
        'credit_spread_aaa': 'AAA',
        'window': 90,
    }

    def calculate(self, data: pd.DataFrame,
                  fed_balance: Optional[pd.Series] = None,
                  credit_spread: Optional[pd.Series] = None) -> IndicatorResult:
        """
        计算FRED压力合成

        Args:
            data: 本地价格数据
            fed_balance: 美联储资产负债表数据
            credit_spread: 信用利差数据
        """
        params = self.params

        # 计算美联储资产负债表变化率
        if fed_balance is not None and not fed_balance.empty:
            if len(fed_balance) >= params['window']:
                # 计算变化率
                fed_change_rate = (fed_balance.iloc[-1] - fed_balance.iloc[-params['window']]) / fed_balance.iloc[-params['window']] * 100
            else:
                fed_change_rate = 0.0
        else:
            # 如果没有数据，使用代理（基于价格数据的趋势）
            fed_change_rate = 0.0

        # 计算信用利差
        if credit_spread is not None and not credit_spread.empty:
            current_spread = credit_spread.iloc[-1]
            # 计算趋势
            if len(credit_spread) >= 20:
                spread_trend = (current_spread - credit_spread.iloc[-20]) / credit_spread.iloc[-20] * 100
            else:
                spread_trend = 0.0
        else:
            current_spread = 1.0  # 默认1%利差
            spread_trend = 0.0

        # 合成压力指标
        # 美联储缩表（负变化）+ 利差扩大 = 压力大
        # 美联储扩表（正变化）+ 利差收窄 = 压力小
        pressure_score = (-fed_change_rate * 0.5) + (spread_trend * 0.5)

        # 归一化得分（压力-10到10映射到0-100）
        # 压力越大（高分）表示宏观环境紧张，得低分；压力小得高分
        normalized_score = normalize_score(pressure_score, -10, 10, reverse=True)

        # 信号方向
        if pressure_score > 5:
            signal = -1  # 高压力，宏观紧张
        elif pressure_score < -5:
            signal = 1  # 低压力，宏观宽松
        else:
            signal = 0

        current_value = IndicatorValue(
            value=pressure_score,
            raw_score=pressure_score,
            normalized_score=normalized_score,
            signal=signal,
            metadata={
                'pressure_score': pressure_score,
                'fed_change_rate': fed_change_rate,
                'spread_trend': spread_trend,
                'current_spread': current_spread,
                'note': '压力来自美联储缩表和信用利差扩大',
            }
        )

        result = IndicatorResult(
            indicator_id=self.INDICATOR_ID,
            indicator_name=self.INDICATOR_NAME,
            layer=self.LAYER,
            current=current_value,
            params=params,
        )

        return result
