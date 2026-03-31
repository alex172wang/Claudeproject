# -*- coding: utf-8 -*-
"""
配置模块

提供全局配置、策略参数、权重设置等配置管理。
"""

from .settings import PROJECT_CONFIG, LOGGING_CONFIG, DATA_CONFIG

__all__ = [
    'PROJECT_CONFIG',
    'LOGGING_CONFIG',
    'DATA_CONFIG',
]
