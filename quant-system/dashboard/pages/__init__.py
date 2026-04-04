"""
仪表板页面模块

提供各个功能页面的布局定义。
"""

"""Dashboard页面模块"""

# 基础页面组件（无循环依赖）
from .backtest import create_backtest_tab
from .signals import create_signals_tab
from .risk import create_risk_tab
from .instruments import create_instruments_tab
from .config import create_config_tab, register_config_callbacks

# realtime_tab 有循环依赖，延迟导入
_create_realtime_tab = None

def create_realtime_tab():
    """延迟导入realtime_tab"""
    global _create_realtime_tab
    if _create_realtime_tab is None:
        from .realtime import create_realtime_tab as _crt
        _create_realtime_tab = _crt
    return _create_realtime_tab()

# register_realtime_callbacks 延迟导入
_reg_rtc = None

def register_realtime_callbacks(app):
    """延迟导入并注册实时监控回调"""
    global _reg_rtc
    if _reg_rtc is None:
        from .realtime import register_realtime_callbacks as _rrc
        _reg_rtc = _rrc
    return _reg_rtc(app)

__all__ = [
    'create_realtime_tab',
    'register_realtime_callbacks',
    'create_backtest_tab',
    'create_signals_tab',
    'create_risk_tab',
    'create_instruments_tab',
    'create_config_tab',
    'register_config_callbacks',
]
