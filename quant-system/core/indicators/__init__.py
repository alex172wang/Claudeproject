"""
指标计算模块
实现L1-L4四层多维量化指标体系
"""

from .base import BaseIndicator, IndicatorRegistry
from .l1_trend import (
    L101CompositeSlopeMomentum,
    L102EMATrendFilter,
    L103TrendAcceleration,
    L104PriceChannelPosition,
    L105FREDTrendResonance,
)
from .l2_structure import (
    L201HurstExponent,
    L202VolatilityStructureRatio,
    L203VolumeDivergence,
    L204DrawdownFractal,
    L205BodyRatio,
    L206VolatilityAutocorrelation,
)
from .l3_resonance import (
    L301RollingCorrelationMatrix,
    L302CorrelationVelocity,
    L303PCAExplainedVariance,
    L304CrossMarketConsistency,
    L305MacroAssetResonance,
    L306RotationSpeed,
)
from .l4_gap import (
    L401IVRVSpread,
    L402OptionSkew,
    L403PCRatio,
    L404LiquidityGap,
    L405TailRisk,
    L406GapFrequency,
    L407FREDPressureComposite,
)

__all__ = [
    # 基础
    'BaseIndicator',
    'IndicatorRegistry',

    # L1 趋势层
    'L101CompositeSlopeMomentum',
    'L102EMATrendFilter',
    'L103TrendAcceleration',
    'L104PriceChannelPosition',
    'L105FREDTrendResonance',

    # L2 结构层
    'L201HurstExponent',
    'L202VolatilityStructureRatio',
    'L203VolumeDivergence',
    'L204DrawdownFractal',
    'L205BodyRatio',
    'L206VolatilityAutocorrelation',

    # L3 共振层
    'L301RollingCorrelationMatrix',
    'L302CorrelationVelocity',
    'L303PCAExplainedVariance',
    'L304CrossMarketConsistency',
    'L305MacroAssetResonance',
    'L306RotationSpeed',

    # L4 缺口层
    'L401IVRVSpread',
    'L402OptionSkew',
    'L403PCRatio',
    'L404LiquidityGap',
    'L405TailRisk',
    'L406GapFrequency',
    'L407FREDPressureComposite',
]


def get_indicator(indicator_id: str, **kwargs) -> BaseIndicator:
    """
    获取指标实例

    Args:
        indicator_id: 指标ID（如'L1-01', 'L2-03'等）
        **kwargs: 指标参数

    Returns:
        BaseIndicator: 指标实例
    """
    return IndicatorRegistry.create(indicator_id, **kwargs)


def list_indicators() -> dict:
    """
    列出所有可用指标

    Returns:
        dict: 按层级组织的指标字典
    """
    return {
        'L1': IndicatorRegistry.list_by_category('L1'),
        'L2': IndicatorRegistry.list_by_category('L2'),
        'L3': IndicatorRegistry.list_by_category('L3'),
        'L4': IndicatorRegistry.list_by_category('L4'),
    }
