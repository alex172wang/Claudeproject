"""
Dashboard 数据适配器 v3 - 使用 Django REST API

替代直接连接 mootdx 的方式，通过 API 获取数据
实现离线缓存和降级方案
"""

import pandas as pd
import numpy as np
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from threading import Lock
import json

from .api_client import APIClient


class CachedAPIResponse:
    """缓存的 API 响应"""

    def __init__(self, data: Any, ttl: int = 60):
        self.data = data
        self.expires_at = datetime.now() + timedelta(seconds=ttl)

    def is_expired(self) -> bool:
        """检查是否过期"""
        return datetime.now() > self.expires_at


class DashboardDataAdapterAPI:
    """仪表板数据适配器 v3 - 使用 Django REST API"""

    def __init__(self, base_url: str = 'http://localhost:8000/api/'):
        self.api = APIClient(base_url=base_url)
        self._cache: Dict[str, CachedAPIResponse] = {}
        self._cache_lock = Lock()

        # 缓存 TTL 配置（秒）
        self.ttl_config = {
            'etf_list': 3600,      # ETF 列表：1 小时
            'etf_price': 5,         # 实时价格：5 秒
            'etf_kline': 3600,      # K 线：1 小时
            'portfolio': 30,         # 投资组合：30 秒
            'signals': 10,           # 信号：10 秒
            'alerts': 30,            # 预警：30 秒
        }

    def _get_cached(self, key: str) -> Optional[Any]:
        """获取缓存数据"""
        with self._cache_lock:
            if key in self._cache:
                cached = self._cache[key]
                if not cached.is_expired():
                    return cached.data
                else:
                    del self._cache[key]
        return None

    def _set_cache(self, key: str, data: Any, ttl: Optional[int] = None):
        """设置缓存数据"""
        if ttl is None:
            # 根据 key 前缀确定 ttl
            for prefix, default_ttl in self.ttl_config.items():
                if key.startswith(prefix):
                    ttl = default_ttl
                    break
            if ttl is None:
                ttl = 60  # 默认 60 秒

        with self._cache_lock:
            self._cache[key] = CachedAPIResponse(data, ttl=ttl)

    def clear_cache(self, prefix: Optional[str] = None):
        """清理缓存"""
        with self._cache_lock:
            if prefix:
                keys_to_remove = [k for k in self._cache if k.startswith(prefix)]
                for k in keys_to_remove:
                    del self._cache[k]
            else:
                self._cache.clear()

    # =========================================================================
    # ETF 相关方法
    # =========================================================================

    def get_etf_list(self, category: Optional[str] = None) -> List[Dict]:
        """
        获取 ETF 列表

        Args:
            category: 可选分类过滤

        Returns:
            ETF 列表
        """
        cache_key = f'etf_list:{category}'
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        try:
            result = self.api.get_etf_list(category)
            self._set_cache(cache_key, result)
            return result
        except Exception as e:
            print(f"[DataAdapterAPI] 获取 ETF 列表失败: {e}")
            # 返回空列表或降级数据
            return []

    def get_etf_price_real(self, code: str, days: int = 60) -> pd.DataFrame:
        """
        获取 ETF 实时价格数据

        Args:
            code: ETF 代码，如 '510300'
            days: 保留参数，兼容性

        Returns:
            DataFrame: 包含真实价格数据的 DataFrame
        """
        cache_key = f'etf_price:{code}'
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        try:
            price_data = self.api.get_etf_price(code)
            if price_data:
                # 转换为 DataFrame
                df = pd.DataFrame([price_data])
                if 'update_time' in df.columns:
                    df['date'] = pd.to_datetime(df['update_time'])
                self._set_cache(cache_key, df)
                return df
        except Exception as e:
            print(f"[DataAdapterAPI] 获取 {code} 价格失败: {e}")

        # 降级：返回空 DataFrame
        return pd.DataFrame(columns=['code', 'name', 'current_price', 'change', 'change_percent', 'volume', 'turnover', 'date'])

    def get_etf_kline(self, code: str, days: int = 60, period: str = 'day') -> pd.DataFrame:
        """
        获取 ETF K 线数据

        Args:
            code: ETF 代码
            days: 获取天数
            period: 时间周期

        Returns:
            K 线 DataFrame
        """
        cache_key = f'etf_kline:{code}:{days}:{period}'
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        try:
            kline_data = self.api.get_etf_kline(code, days, period)
            if kline_data:
                df = pd.DataFrame(kline_data)
                if 'date' in df.columns:
                    df['date'] = pd.to_datetime(df['date'])
                self._set_cache(cache_key, df)
                return df
        except Exception as e:
            print(f"[DataAdapterAPI] 获取 {code} K线失败: {e}")

        # 降级：返回模拟数据
        dates = pd.date_range(end=datetime.now(), periods=days, freq='D')
        base_price = 4.5

        data = []
        for i, date in enumerate(dates):
            price = base_price + (i * 0.01) + (i % 5 - 2) * 0.02
            data.append({
                'date': date,
                'open': round(price - 0.01, 3),
                'high': round(price + 0.03, 3),
                'low': round(price - 0.02, 3),
                'close': round(price, 3),
                'volume': 1000000 + i * 1000,
                'amount': round((1000000 + i * 1000) * price, 2)
            })

        df = pd.DataFrame(data)
        self._set_cache(cache_key, df, ttl=300)  # 降级数据缓存 5 分钟
        return df

    # =========================================================================
    # 投资组合相关方法
    # =========================================================================

    def get_portfolio_summary(self) -> Dict[str, Any]:
        """获取投资组合汇总"""
        cache_key = 'portfolio:summary'
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        try:
            summary = self.api.get_portfolio_summary()
            if summary:
                self._set_cache(cache_key, summary)
                return summary
        except Exception as e:
            print(f"[DataAdapterAPI] 获取投资组合汇总失败: {e}")

        # 降级数据：无真实数据时返回空
        fallback = {
            'total_assets': 0.0,
            'total_return': 0.0,
            'sharpe_ratio': 0.0,
            'max_drawdown': 0.0,
            'update_time': datetime.now().isoformat()
        }
        self._set_cache(cache_key, fallback, ttl=300)
        return fallback

    def get_positions(self) -> List[Dict]:
        """获取当前持仓"""
        cache_key = 'portfolio:positions'
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        try:
            positions = self.api.get_positions()
            if positions:
                self._set_cache(cache_key, positions)
                return positions
        except Exception as e:
            print(f"[DataAdapterAPI] 获取持仓失败: {e}")

        # 降级数据：无真实数据时返回空列表
        fallback = []
        self._set_cache(cache_key, fallback, ttl=300)
        return fallback

    def get_equity_curve(self, days: int = 365) -> pd.DataFrame:
        """获取权益曲线"""
        cache_key = f'portfolio:equity_curve:{days}'
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        try:
            curve_data = self.api.get_equity_curve(days)
            if curve_data:
                df = pd.DataFrame(curve_data)
                if 'date' in df.columns:
                    df['date'] = pd.to_datetime(df['date'])
                self._set_cache(cache_key, df)
                return df
        except Exception as e:
            print(f"[DataAdapterAPI] 获取权益曲线失败: {e}")

        # 降级：无真实数据时返回空DataFrame
        df = pd.DataFrame(columns=['date', 'equity', 'drawdown'])
        self._set_cache(cache_key, df, ttl=300)
        return df

    # =========================================================================
    # 监控相关方法
    # =========================================================================

    def get_signals(self) -> List[Dict]:
        """获取当前信号"""
        cache_key = 'monitor:signals'
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        try:
            signals = self.api.get_signals()
            if signals:
                self._set_cache(cache_key, signals)
                return signals
        except Exception as e:
            print(f"[DataAdapterAPI] 获取信号失败: {e}")

        return []

    def get_alerts(self) -> List[Dict]:
        """获取预警列表"""
        cache_key = 'monitor:alerts'
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        try:
            alerts = self.api.get_alerts()
            if alerts:
                self._set_cache(cache_key, alerts)
                return alerts
        except Exception as e:
            print(f"[DataAdapterAPI] 获取预警失败: {e}")

        return []

    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        cache_key = 'monitor:system_status'
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        try:
            status = self.api.get_system_status()
            if status:
                self._set_cache(cache_key, status)
                return status
        except Exception as e:
            print(f"[DataAdapterAPI] 获取系统状态失败: {e}")

        fallback = {
            'status': 'disconnected',
            'database': 'disconnected',
            'timestamp': datetime.now().isoformat(),
            'version': '1.0.0'
        }
        self._set_cache(cache_key, fallback, ttl=60)
        return fallback


# 创建全局适配器实例
_data_adapter_api: Optional[DashboardDataAdapterAPI] = None


def get_api_data_adapter(base_url: str = 'http://localhost:8000/api/') -> DashboardDataAdapterAPI:
    """获取全局 API 数据适配器实例（单例模式）"""
    global _data_adapter_api
    if _data_adapter_api is None:
        _data_adapter_api = DashboardDataAdapterAPI(base_url=base_url)
    return _data_adapter_api
