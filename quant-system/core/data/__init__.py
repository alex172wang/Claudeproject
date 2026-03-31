"""
数据获取模块
支持多数据源：mootdx、AKShare、FRED
"""

from .base import DataFetcher
from .cache import DataCache

try:
    from .mootdx_fetcher import MootdxFetcher
except ImportError:
    MootdxFetcher = None

try:
    from .akshare_fetcher import AKShareFetcher
except ImportError:
    AKShareFetcher = None

try:
    from .fred_fetcher import FREDFetcher
except ImportError:
    FREDFetcher = None

__all__ = [
    'DataFetcher',
    'DataCache',
    'MootdxFetcher',
    'AKShareFetcher',
    'FREDFetcher',
]
