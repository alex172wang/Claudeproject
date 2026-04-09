"""
Dashboard 数据适配器 - 直接使用 data_sync 模块

不依赖 API 服务器，直接从数据源获取数据
"""

import pandas as pd
import numpy as np
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from threading import Lock
import logging

logger = logging.getLogger(__name__)


class DashboardDataAdapterDirect:
    """仪表板数据适配器 - 直接使用 data_sync"""

    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._cache_lock = Lock()
        self._cache_expiry: Dict[str, datetime] = {}

        # 缓存 TTL 配置（秒）
        self.ttl_config = {
            'etf_list': 3600,      # ETF 列表：1 小时
            'etf_price': 5,         # 实时价格：5 秒
            'etf_kline': 3600,      # K 线：1 小时
        }

    def _get_cached(self, key: str) -> Optional[Any]:
        """获取缓存数据"""
        with self._cache_lock:
            if key in self._cache and key in self._cache_expiry:
                if datetime.now() < self._cache_expiry[key]:
                    return self._cache[key]
                else:
                    del self._cache[key]
                    del self._cache_expiry[key]
        return None

    def _set_cache(self, key: str, data: Any, ttl: Optional[int] = None):
        """设置缓存数据"""
        if ttl is None:
            for prefix, default_ttl in self.ttl_config.items():
                if key.startswith(prefix):
                    ttl = default_ttl
                    break
            if ttl is None:
                ttl = 60

        with self._cache_lock:
            self._cache[key] = data
            self._cache_expiry[key] = datetime.now() + timedelta(seconds=ttl)

    # =========================================================================
    # ETF 相关方法
    # =========================================================================

    def get_etf_list(self, category: Optional[str] = None) -> List[Dict]:
        """获取 ETF 列表"""
        cache_key = f'etf_list:{category}'
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        try:
            import django
            if not django.conf.settings.configured:
                import os
                import sys
                project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                sys.path.insert(0, project_root)
                os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'quant_system.settings')
                django.setup()

            from portfolio.models import ETF
            queryset = ETF.objects.filter(is_active=True)
            if category:
                queryset = queryset.filter(category=category)

            result = []
            for etf in queryset:
                result.append({
                    'code': etf.code,
                    'name': etf.name,
                    'category': etf.category,
                    'market': etf.market,
                    'is_active': etf.is_active,
                })

            self._set_cache(cache_key, result)
            return result
        except Exception as e:
            logger.error(f"获取 ETF 列表失败: {e}")
            return []

    def get_etf_price_real(self, code: str, days: int = 60) -> pd.DataFrame:
        """获取 ETF 实时价格数据"""
        cache_key = f'etf_price:{code}'
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        try:
            from data_sync.tasks import get_realtime_quote
            quote = get_realtime_quote(code)
            if quote:
                df = pd.DataFrame([{
                    'code': quote.get('code', code),
                    'name': quote.get('name', code),
                    'current_price': quote.get('price', 0),
                    'change': quote.get('change', 0),
                    'change_percent': (quote.get('change', 0) / quote.get('prev_close', 1)) * 100 if quote.get('prev_close', 0) != 0 else 0,
                    'volume': quote.get('volume', 0),
                    'turnover': quote.get('amount', 0),
                    'date': pd.to_datetime(quote.get('timestamp', datetime.now())),
                }])
                self._set_cache(cache_key, df)
                return df
        except Exception as e:
            logger.error(f"获取 {code} 价格失败: {e}")

        return pd.DataFrame(columns=['code', 'name', 'current_price', 'change', 'change_percent', 'volume', 'turnover', 'date'])

    def get_etf_kline(self, code: str, days: int = 60, period: str = 'day') -> pd.DataFrame:
        """获取 ETF K 线数据"""
        cache_key = f'etf_kline:{code}:{days}:{period}'
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        try:
            from data_sync.sync_service import data_sync_service
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days+10)

            df = data_sync_service.sync_historical_kline(
                code,
                start_date.strftime('%Y-%m-%d'),
                end_date.strftime('%Y-%m-%d'),
                period
            )

            if df is not None and not df.empty:
                self._set_cache(cache_key, df)
                return df
        except Exception as e:
            logger.error(f"获取 {code} K线失败: {e}")

        # 降级：返回空 DataFrame
        return pd.DataFrame(columns=['date', 'open', 'high', 'low', 'close', 'volume', 'amount'])

    # =========================================================================
    # 投资组合相关方法
    # =========================================================================

    def get_portfolio_summary(self) -> Dict[str, Any]:
        """获取投资组合汇总"""
        cache_key = 'portfolio:summary'
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        # 尝试从数据库加载真实数据
        try:
            import django
            if not django.conf.settings.configured:
                import os
                import sys
                project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                sys.path.insert(0, project_root)
                os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'quant_system.settings')
                django.setup()

            from journal.models import Position
            from django.contrib.auth import get_user_model

            User = get_user_model()
            # 获取默认用户的持仓
            try:
                user = User.objects.first()
            except Exception:
                user = None

            if user:
                positions = Position.objects.filter(user=user)
                if positions.exists():
                    total_value = 0.0
                    total_cost = 0.0
                    for pos in positions:
                        if pos.quantity > 0:
                            current_price = pos.get_current_price() or pos.avg_cost
                            total_value += pos.quantity * float(current_price)
                            total_cost += pos.quantity * float(pos.avg_cost)

                    total_return = ((total_value - total_cost) / total_cost * 100) if total_cost > 0 else 0

                    result = {
                        'total_assets': total_value,
                        'total_return': total_return,
                        'sharpe_ratio': 0.0,  # 需要计算
                        'max_drawdown': 0.0,  # 需要计算
                        'update_time': datetime.now().isoformat()
                    }
                    self._set_cache(cache_key, result, ttl=60)
                    return result
        except Exception as e:
            logger.error(f"获取投资组合汇总失败: {e}")

        # 无数据时返回空
        return {
            'total_assets': 0.0,
            'total_return': 0.0,
            'sharpe_ratio': 0.0,
            'max_drawdown': 0.0,
            'update_time': datetime.now().isoformat()
        }

    def get_positions(self) -> List[Dict]:
        """获取当前持仓"""
        cache_key = 'portfolio:positions'
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        # 尝试从数据库加载真实数据
        try:
            import django
            if not django.conf.settings.configured:
                import os
                import sys
                project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                sys.path.insert(0, project_root)
                os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'quant_system.settings')
                django.setup()

            from journal.models import Position
            from django.contrib.auth import get_user_model

            User = get_user_model()
            try:
                user = User.objects.first()
            except Exception:
                user = None

            if user:
                positions = Position.objects.filter(user=user, quantity__gt=0)
                result = []
                for pos in positions:
                    current_price = pos.get_current_price() or pos.avg_cost
                    market_value = pos.quantity * float(current_price)
                    pnl = (float(current_price) - float(pos.avg_cost)) * pos.quantity

                    result.append({
                        'code': pos.etf.code,
                        'name': pos.etf.name,
                        'quantity': pos.quantity,
                        'avg_price': float(pos.avg_cost),
                        'current_price': float(current_price),
                        'market_value': market_value,
                        'pnl': pnl,
                        'pnl_percent': (float(current_price) - float(pos.avg_cost)) / float(pos.avg_cost) * 100 if pos.avg_cost > 0 else 0
                    })

                self._set_cache(cache_key, result, ttl=30)
                return result
        except Exception as e:
            logger.error(f"获取持仓失败: {e}")

        # 无数据时返回空列表
        return []

    def get_equity_curve(self, days: int = 365) -> pd.DataFrame:
        """获取权益曲线"""
        cache_key = f'portfolio:equity_curve:{days}'
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        # 尝试从数据库加载真实数据
        try:
            import django
            if not django.conf.settings.configured:
                import os
                import sys
                project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                sys.path.insert(0, project_root)
                os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'quant_system.settings')
                django.setup()

            from journal.models import TradeRecord
            from django.contrib.auth import get_user_model

            User = get_user_model()
            try:
                user = User.objects.first()
            except Exception:
                user = None

            if user:
                # 获取用户的交易记录，计算权益曲线
                records = TradeRecord.objects.filter(
                    user=user
                ).order_by('trade_time')[:days]

                if records:
                    equity_data = []
                    running_cash = 1000000  # 初始资金

                    for record in records:
                        if record.action in ['buy', 'add']:
                            running_cash -= float(record.total_amount)
                        else:
                            running_cash += float(record.total_amount)

                        equity_data.append({
                            'date': record.trade_time,
                            'equity': running_cash,
                            'drawdown': 0.0
                        })

                    if equity_data:
                        df = pd.DataFrame(equity_data)
                        self._set_cache(cache_key, df, ttl=300)
                        return df
        except Exception as e:
            logger.error(f"获取权益曲线失败: {e}")

        # 无数据时返回空DataFrame
        return pd.DataFrame(columns=['date', 'equity', 'drawdown'])


# 创建全局适配器实例
_data_adapter_direct: Optional[DashboardDataAdapterDirect] = None


def get_direct_data_adapter() -> DashboardDataAdapterDirect:
    """获取全局直接数据适配器实例（单例模式）"""
    global _data_adapter_direct
    if _data_adapter_direct is None:
        _data_adapter_direct = DashboardDataAdapterDirect()
    return _data_adapter_direct
