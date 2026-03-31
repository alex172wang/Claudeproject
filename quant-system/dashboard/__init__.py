"""
仪表板与可视化系统

提供实时监控、回测结果展示、策略信号监控、风险监控等功能。

主要模块:
- main: 主应用与路由
- layout: 页面布局组件
- callbacks: 交互回调函数
- components: 可复用组件
- pages: 各功能页面
"""

__version__ = "1.0.0"

from .main import create_app

__all__ = ['create_app']
