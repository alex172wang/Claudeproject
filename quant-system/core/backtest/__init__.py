"""
回测引擎模块

实现基于事件驱动的回测框架，支持：
- 多策略回测（ETF轮动、永久组合、主题仓位）
- 完整的交易成本模型（佣金、滑点、冲击成本）
- 多维绩效分析（收益率、风险、回撤、夏普等）
- 信号合成与权重动态调整
"""

from .engine import BacktestEngine
from .broker import SimulatedBroker, Order, Trade
from .strategy import StrategyBase, ETFRotationStrategy, PermanentPortfolioStrategy, ThematicStrategy
from .metrics import PerformanceAnalyzer, TradeAnalyzer
from .results import BacktestResult

__all__ = [
    # 核心引擎
    'BacktestEngine',

    # 经纪商与订单
    'SimulatedBroker',
    'Order',
    'Trade',

    # 策略基类与实现
    'StrategyBase',
    'ETFRotationStrategy',
    'PermanentPortfolioStrategy',
    'ThematicStrategy',

    # 绩效分析
    'PerformanceAnalyzer',
    'TradeAnalyzer',

    # 结果存储
    'BacktestResult',
]
