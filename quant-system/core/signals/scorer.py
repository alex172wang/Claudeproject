"""
单品种四维评分模块

计算单个ETF品种的四维评分（L1-L4），输出标准化得分（0-100）
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import numpy as np
import pandas as pd

# 导入指标层
from ..indicators.l1_trend import (
    L101CompositeSlopeMomentum as CompositeSlopeMomentum,
    L102EMATrendFilter as EMATrendFilter,
    L103TrendAcceleration as TrendAcceleration,
    L104PriceChannelPosition as PriceChannelPosition,
    L105FREDTrendResonance as FREDTrendResonance,
)
from ..indicators.l2_structure import (
    L201HurstExponent as HurstExponent,
    L202VolatilityStructureRatio as VolatilityStructureRatio,
    L203VolumeDivergence as VolumePatternDivergence,
    L204DrawdownFractal as DrawdownFractalDimension,
    L205BodyRatio as KLineEntityRatio,
    L206VolatilityAutocorrelation as VolatilityAutocorrelation,
)
from ..indicators.l3_resonance import (
    L301RollingCorrelationMatrix as RollingCorrelationMatrix,
    L302CorrelationVelocity as CorrelationChangeRate,
    L303PCAExplainedVariance as PCAExplainedVariance,
    L304CrossMarketConsistency as CrossMarketConsistency,
    L305MacroAssetResonance as MacroAssetResonance,
    L306RotationSpeed as SectorRotationSpeed,
)
from ..indicators.l4_gap import (
    L401IVRVSpread as IVRVSpread,
    L402OptionSkew as OptionSkew,
    L403PCRatio as PutCallRatio,
    L404LiquidityGap as LiquidityGap,
    L405TailRisk as TailRisk,
    L406GapFrequency as GapFrequency,
    L407FREDPressureComposite as FREDStressComposite,
)
from ..indicators.base import IndicatorResult, normalize_score


@dataclass
class LayerScore:
    """单层评分结果"""
    score: float = 50.0  # 标准化得分 0-100
    raw_value: float = 0.0  # 原始值
    weight: float = 0.25  # 权重
    details: Dict[str, Any] = field(default_factory=dict)  # 详细指标值
    signal: int = 0  # 信号方向 -1/0/1
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class FourDimensionalScore:
    """四维评分结果"""
    etf_code: str = ""
    etf_name: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

    # 综合得分
    overall_score: float = 50.0
    weighted_score: float = 50.0

    # 各层得分
    L1: LayerScore = field(default_factory=LayerScore)  # 趋势层
    L2: LayerScore = field(default_factory=LayerScore)  # 结构层
    L3: LayerScore = field(default_factory=LayerScore)  # 共振层
    L4: LayerScore = field(default_factory=LayerScore)  # 缺口层

    # 元数据
    data_quality: str = "good"  # good/poor/missing
    calculation_time_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'etf_code': self.etf_code,
            'etf_name': self.etf_name,
            'timestamp': self.timestamp.isoformat(),
            'overall_score': round(self.overall_score, 2),
            'weighted_score': round(self.weighted_score, 2),
            'L1': {
                'score': round(self.L1.score, 2),
                'signal': self.L1.signal,
                'details': self.L1.details,
            },
            'L2': {
                'score': round(self.L2.score, 2),
                'signal': self.L2.signal,
                'details': self.L2.details,
            },
            'L3': {
                'score': round(self.L3.score, 2),
                'signal': self.L3.signal,
                'details': self.L3.details,
            },
            'L4': {
                'score': round(self.L4.score, 2),
                'signal': self.L4.signal,
                'details': self.L4.details,
            },
            'data_quality': self.data_quality,
        }


class ETFFourDimensionalScorer:
    """ETF四维评分器"""

    def __init__(self,
                 l1_weight: float = 0.35,
                 l2_weight: float = 0.25,
                 l3_weight: float = 0.20,
                 l4_weight: float = 0.20):
        """
        初始化评分器

        Args:
            l1_weight: L1趋势层权重
            l2_weight: L2结构层权重
            l3_weight: L3共振层权重
            l4_weight: L4缺口层权重
        """
        self.weights = {
            'L1': l1_weight,
            'L2': l2_weight,
            'L3': l3_weight,
            'L4': l4_weight
        }

        # 验证权重和为1
        total_weight = sum(self.weights.values())
        if abs(total_weight - 1.0) > 0.001:
            # 归一化权重
            for key in self.weights:
                self.weights[key] /= total_weight

    def calculate_score(self,
                       etf_code: str,
                       data: pd.DataFrame,
                       timestamp: Optional[datetime] = None) -> FourDimensionalScore:
        """
        计算四维评分

        Args:
            etf_code: ETF代码
            data: 包含OHLCV数据的DataFrame
            timestamp: 时间戳（默认当前时间）

        Returns:
            FourDimensionalScore: 四维评分结果
        """
        import time
        start_time = time.time()

        if timestamp is None:
            timestamp = datetime.now()

        # 初始化结果
        result = FourDimensionalScore(
            etf_code=etf_code,
            timestamp=timestamp
        )

        # 检查数据质量
        if data is None or len(data) < 30:
            result.data_quality = "missing"
            result.calculation_time_ms = (time.time() - start_time) * 1000
            return result

        try:
            # 计算各层得分
            result.L1 = self._calculate_l1_score(etf_code, data)
            result.L2 = self._calculate_l2_score(etf_code, data)
            result.L3 = self._calculate_l3_score(etf_code, data)
            result.L4 = self._calculate_l4_score(etf_code, data)

            # 计算综合得分（简单平均）
            result.overall_score = np.mean([
                result.L1.score,
                result.L2.score,
                result.L3.score,
                result.L4.score
            ])

            # 计算加权得分
            result.weighted_score = (
                result.L1.score * self.weights['L1'] +
                result.L2.score * self.weights['L2'] +
                result.L3.score * self.weights['L3'] +
                result.L4.score * self.weights['L4']
            )

            result.data_quality = "good"

        except Exception as e:
            result.data_quality = "poor"
            # 记录错误但不中断
            print(f"计算{etf_code}四维评分时出错: {e}")

        result.calculation_time_ms = (time.time() - start_time) * 1000
        return result

    def _calculate_l1_score(self, etf_code: str, data: pd.DataFrame) -> LayerScore:
        """
        计算L1趋势层得分

        Args:
            etf_code: ETF代码
            data: OHLCV数据

        Returns:
            LayerScore: L1层评分结果
        """
        score = LayerScore(weight=self.weights['L1'])

        try:
            # 使用L1层指标计算得分
            indicators = [
                ('L1-01', CompositeSlopeMomentum()),
                ('L1-02', EMATrendFilter()),
                ('L1-03', TrendAcceleration()),
                ('L1-04', PriceChannelPosition()),
                ('L1-05', FREDTrendResonance()),
            ]

            scores = []
            for indicator_id, indicator in indicators:
                try:
                    result = indicator.calculate(data)
                    indicator_score = result.get_score()
                    scores.append(indicator_score)
                    score.details[indicator_id] = {
                        'score': round(indicator_score, 2),
                        'value': round(result.current.value, 4),
                        'signal': result.current.signal,
                    }
                except Exception as e:
                    # 单个指标失败不影响整体
                    score.details[indicator_id] = {'error': str(e)}

            # 计算平均分
            if scores:
                score.score = np.mean(scores)
                score.raw_value = score.score

            # 确定信号方向
            if score.score >= 60:
                score.signal = 1  # 看多
            elif score.score <= 40:
                score.signal = -1  # 看空
            else:
                score.signal = 0  # 中性

        except Exception as e:
            score.details['error'] = str(e)

        return score

    def _calculate_l2_score(self, etf_code: str, data: pd.DataFrame) -> LayerScore:
        """计算L2结构层得分"""
        score = LayerScore(weight=self.weights['L2'])

        try:
            indicators = [
                ('L2-01', HurstExponent()),
                ('L2-02', VolatilityStructureRatio()),
                ('L2-03', VolumePatternDivergence()),
                ('L2-04', DrawdownFractalDimension()),
                ('L2-05', KLineEntityRatio()),
                ('L2-06', VolatilityAutocorrelation()),
            ]

            scores = []
            for indicator_id, indicator in indicators:
                try:
                    result = indicator.calculate(data)
                    indicator_score = result.get_score()
                    scores.append(indicator_score)
                    score.details[indicator_id] = {
                        'score': round(indicator_score, 2),
                        'value': round(result.current.value, 4),
                    }
                except Exception as e:
                    score.details[indicator_id] = {'error': str(e)}

            if scores:
                score.score = np.mean(scores)
                score.raw_value = score.score

        except Exception as e:
            score.details['error'] = str(e)

        return score

    def _calculate_l3_score(self, etf_code: str, data: pd.DataFrame) -> LayerScore:
        """计算L3共振层得分"""
        score = LayerScore(weight=self.weights['L3'])

        try:
            # L3指标需要多品种数据，这里使用简化版本
            indicators = [
                ('L3-01', RollingCorrelationMatrix()),
                ('L3-03', PCAExplainedVariance()),
                ('L3-06', SectorRotationSpeed()),
            ]

            scores = []
            for indicator_id, indicator in indicators:
                try:
                    result = indicator.calculate(data)
                    indicator_score = result.get_score()
                    scores.append(indicator_score)
                    score.details[indicator_id] = {
                        'score': round(indicator_score, 2),
                    }
                except Exception as e:
                    score.details[indicator_id] = {'error': str(e)}

            if scores:
                score.score = np.mean(scores)
                score.raw_value = score.score
            else:
                # 如果没有L3数据，使用中性分数
                score.score = 50.0

        except Exception as e:
            score.score = 50.0  # 出错时使用中性分数
            score.details['error'] = str(e)

        return score

    def _calculate_l4_score(self, etf_code: str, data: pd.DataFrame) -> LayerScore:
        """计算L4缺口层得分（风险层）"""
        score = LayerScore(weight=self.weights['L4'])

        try:
            # L4指标用于风险预警，高分表示低风险
            indicators = [
                ('L4-01', IVRVSpread()),
                ('L4-02', OptionSkew()),
                ('L4-05', TailRisk()),
                ('L4-06', GapFrequency()),
            ]

            scores = []
            for indicator_id, indicator in indicators:
                try:
                    result = indicator.calculate(data)
                    # 对于风险指标，高分表示低风险
                    indicator_score = result.get_score()
                    scores.append(indicator_score)
                    score.details[indicator_id] = {
                        'score': round(indicator_score, 2),
                        'value': round(result.current.value, 4),
                    }
                except Exception as e:
                    score.details[indicator_id] = {'error': str(e)}

            if scores:
                # L4得分越高表示越安全
                score.score = np.mean(scores)
                score.raw_value = score.score
            else:
                score.score = 50.0

            # L4信号：高分（安全）= 1，低分（风险）= -1
            if score.score >= 60:
                score.signal = 1
            elif score.score <= 40:
                score.signal = -1
            else:
                score.signal = 0

        except Exception as e:
            score.score = 50.0
            score.details['error'] = str(e)

        return score


def calculate_four_dimensional_score(
    etf_code: str,
    data: pd.DataFrame,
    weights: Optional[Dict[str, float]] = None,
    timestamp: Optional[datetime] = None,
) -> FourDimensionalScore:
    """
    便捷函数：计算单个ETF的四维评分

    Args:
        etf_code: ETF代码
        data: OHLCV数据
        weights: 自定义权重，默认None使用默认权重
        timestamp: 时间戳

    Returns:
        FourDimensionalScore: 四维评分结果
    """
    if weights is None:
        weights = {'L1': 0.35, 'L2': 0.25, 'L3': 0.20, 'L4': 0.20}

    scorer = ETFFourDimensionalScorer(**weights)
    return scorer.calculate_score(etf_code, data, timestamp)


# 导出主要类和函数
__all__ = [
    'LayerScore',
    'FourDimensionalScore',
    'ETFFourDimensionalScorer',
    'calculate_four_dimensional_score',
]