# -*- coding: utf-8 -*-
"""
数据获取层模块

提供统一的数据加载接口，封装 mootdx、AKShare、FRED 等数据源。
"""

from .loaders import BaseDataLoader, DataLoaderError
from .mootdx_loader import MootdxLoader
from .akshare_loader import AKShareLoader
from .fred_loader import FREDLoader

__all__ = [
    'BaseDataLoader',
    'DataLoaderError',
    'MootdxLoader',
    'AKShareLoader',
    'FREDLoader',
]
