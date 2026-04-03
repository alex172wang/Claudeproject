"""
仪表板页面模块

提供各个功能页面的布局定义。
"""

from .realtime import create_realtime_tab
from .backtest import create_backtest_tab
from .signals import create_signals_tab
from .risk import create_risk_tab
from .instruments import create_instruments_tab
from .config import create_config_tab, register_config_callbacks

__all__ = [
    'create_realtime_tab',
    'create_backtest_tab',
    'create_signals_tab',
    'create_risk_tab',
    'create_instruments_tab',
    'create_config_tab',
    'register_config_callbacks',
]
