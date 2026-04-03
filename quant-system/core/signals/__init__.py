"""
信号合成引擎模块

整合四维评分、信号合成和策略触发规则
"""

from .scorer import (
    LayerScore,
    FourDimensionalScore,
    ETFFourDimensionalScorer,
    calculate_four_dimensional_score,
)

from .composer import (
    SortingMethod,
    ComposedSignal,
    SignalComposer,
    compose_signals,
)

from .trigger import (
    ActionType,
    TriggerReason,
    TradeInstruction,
    TriggerResult,
    StrategyTrigger,
    RotationTrigger,
    PermanentPortfolioTrigger,
    ThematicTrigger,
    create_trigger,
)

__all__ = [
    # 评分模块
    'LayerScore',
    'FourDimensionalScore',
    'ETFFourDimensionalScorer',
    'calculate_four_dimensional_score',
    # 合成模块
    'SortingMethod',
    'ComposedSignal',
    'SignalComposer',
    'compose_signals',
    # 触发模块
    'ActionType',
    'TriggerReason',
    'TradeInstruction',
    'TriggerResult',
    'StrategyTrigger',
    'RotationTrigger',
    'PermanentPortfolioTrigger',
    'ThematicTrigger',
    'create_trigger',
]