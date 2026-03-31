# -*- coding: utf-8 -*-
"""
指标计算模块

实现L1-L4四维指标体系的计算。

层级结构：
- L1 趋势层：方向判断
- L2 结构层：品质验证
- L3 共振层：关联分析
- L4 缺口层：风险预警
"""

from .base import BaseIndicator, IndicatorUtils
from .l1_trend import (
    CompositeSlopeMomentum,
    EMATrendFilter,
    TrendAcceleration,
    PriceChannelPosition,
    FREDTrendResonance,
)

__all__ = [
    # 基础类
    'BaseIndicator',
    'IndicatorUtils',
    # L1 趋势层
    'CompositeSlopeMomentum',
    'EMATrendFilter',
    'TrendAcceleration',
    'PriceChannelPosition',
    'FREDTrendResonance',
]
