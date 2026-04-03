"""
Dashboard组件模块

提供可复用的图表组件和UI组件
"""

from .charts import (
    create_price_chart,
    create_radar_chart,
    create_risk_gauge,
    create_signal_timeline,
    create_backtest_equity_chart,
    create_backtest_drawdown_chart,
    create_monthly_heatmap,
    create_layer_score_chart,
)

from .widgets import (
    create_metric_card,
    create_kpi_card,
    create_status_badge,
    create_signal_badge,
)

__all__ = [
    # 图表组件
    'create_price_chart',
    'create_radar_chart',
    'create_risk_gauge',
    'create_signal_timeline',
    'create_backtest_equity_chart',
    'create_backtest_drawdown_chart',
    'create_monthly_heatmap',
    'create_layer_score_chart',
    # UI组件
    'create_metric_card',
    'create_kpi_card',
    'create_status_badge',
    'create_signal_badge',
]