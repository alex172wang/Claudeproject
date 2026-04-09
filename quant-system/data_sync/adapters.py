"""
外部数据源适配器

提供统一的接口来连接不同的数据源（mootdx、akshare 等）
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
import logging

logger = logging.getLogger(__name__)


class DataSourceError(Exception):
    """数据源错误"""
    pass


class BaseDataAdapter:
    """数据源适配器基类"""

    def __init__(self, name: str, config: Optional[Dict] = None):
        self.name = name
        self.config = config or {}
        self._connected = False
        self._client = None

    def connect(self) -> bool:
        """连接数据源"""
        raise NotImplementedError

    def disconnect(self) -> None:
        """断开连接"""
        self._connected = False
        self._client = None

    def is_connected(self) -> bool:
        """检查连接状态"""
        return self._connected

    def get_kline(self, symbol: str, period: str = 'day',
                  start_date: Optional[datetime] = None,
                  end_date: Optional[datetime] = None) -> pd.DataFrame:
        """获取 K 线数据"""
        raise NotImplementedError

    def get_realtime_quote(self, symbol: str) -> Dict[str, Any]:
        """获取实时行情"""
        raise NotImplementedError


class MootdxAdapter(BaseDataAdapter):
    """mootdx 数据源适配器"""

    def __init__(self, config: Optional[Dict] = None):
        super().__init__('mootdx', config)
        self.market = self.config.get('market', 'std')

    def connect(self) -> bool:
        """连接 mootdx"""
        try:
            from mootdx.quotes import Quotes

            self._client = Quotes.factory(market=self.market)
            self._connected = True
            logger.info(f"[MootdxAdapter] 连接成功")
            return True

        except Exception as e:
            logger.error(f"[MootdxAdapter] 连接失败: {e}")
            self._connected = False
            return False

    def get_kline(self, symbol: str, period: str = 'day',
                  start_date: Optional[datetime] = None,
                  end_date: Optional[datetime] = None) -> pd.DataFrame:
        """
        获取 K 线数据

        Args:
            symbol: 股票代码，如 '510300'
            period: 周期，可选 'day', 'week', 'month', 'minute'
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            DataFrame 包含 K 线数据
        """
        if not self._connected and not self.connect():
            logger.error("[MootdxAdapter] 未连接，无法获取 K 线数据")
            return pd.DataFrame()

        try:
            # 转换周期代码
            frequency_map = {
                'day': 9,      # 日线
                'week': 5,     # 周线
                'month': 6,    # 月线
                'minute': 8,   # 分钟线
            }
            frequency = frequency_map.get(period, 9)

            # 标准化代码
            clean_symbol = symbol[-6:] if symbol.startswith(('SH', 'SZ', 'sh', 'sz')) else symbol

            # 计算 limit
            limit = 240  # 默认获取 240 条
            if start_date and end_date:
                days = (end_date - start_date).days
                limit = max(days, 240)

            # 调用 mootdx API
            df = self._client.bars(
                symbol=clean_symbol,
                frequency=frequency,
                limit=limit
            )

            if df is None or df.empty:
                logger.warning(f"[MootdxAdapter] 获取 {symbol} K 线数据为空")
                return pd.DataFrame()

            # 标准化列名
            column_mapping = {
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'volume': 'volume',
                'amount': 'amount',
                'vol': 'volume',
                '成交额': 'amount',
                '成交量': 'volume',
                '开盘': 'open',
                '最高': 'high',
                '最低': 'low',
                '收盘': 'close',
            }

            # 转换为小写并映射标准列名
            df.columns = [str(c).lower().strip() for c in df.columns]
            for old_col, new_col in list(column_mapping.items()):
                if old_col.lower() in df.columns and new_col not in df.columns:
                    df.rename(columns={old_col.lower(): new_col}, inplace=True)

            # 处理 date 列 - mootdx 返回的 datetime 通常在索引中
            # 创建副本以避免修改原数据
            df = df.copy()

            if 'date' not in df.columns:
                # 先检查索引
                if df.index.name == 'datetime':
                    # 从索引创建 date 列，先重命名索引避免冲突
                    df.index.name = 'datetime_index'
                    df = df.reset_index(drop=False)
                    df['date'] = pd.to_datetime(df['datetime_index'])
                elif 'datetime' in df.columns:
                    df['date'] = pd.to_datetime(df['datetime'])
                elif all(c in df.columns for c in ['year', 'month', 'day']):
                    df['date'] = pd.to_datetime(df[['year', 'month', 'day']])

            # 按日期过滤
            if 'date' in df.columns:
                if start_date:
                    df = df[df['date'] >= pd.to_datetime(start_date)]
                if end_date:
                    df = df[df['date'] <= pd.to_datetime(end_date)]

            logger.info(f"[MootdxAdapter] 获取 {symbol} K 线数据成功，共 {len(df)} 条")
            return df

        except Exception as e:
            logger.error(f"[MootdxAdapter] 获取 {symbol} K 线数据失败: {e}")
            return pd.DataFrame()

    def get_realtime_quote(self, symbol: str) -> Dict[str, Any]:
        """
        获取实时行情

        Args:
            symbol: 股票代码，如 '510300'

        Returns:
            包含实时行情数据的字典
        """
        if not self._connected and not self.connect():
            logger.error("[MootdxAdapter] 未连接，无法获取实时行情")
            return {}

        try:
            # 标准化代码
            clean_symbol = symbol[-6:] if symbol.startswith(('SH', 'SZ', 'sh', 'sz')) else symbol

            # 获取报价（注意：mootdx 用的是 quotes 不是 quote）
            quote_df = self._client.quotes(symbol=clean_symbol)

            if quote_df is None or quote_df.empty:
                logger.warning(f"[MootdxAdapter] 获取 {symbol} 实时行情为空")
                return {}

            # 转换为字典
            data = quote_df.iloc[0].to_dict()

            # 计算涨跌幅
            last_close = float(data.get('last_close', 0))
            current_price = float(data.get('price', 0))
            change = current_price - last_close if last_close > 0 else 0
            change_percent = (change / last_close * 100) if last_close > 0 else 0

            # 标准化字段名
            result = {
                'code': symbol,
                'name': data.get('code', symbol),  # mootdx 不返回名称，用代码代替
                'current_price': current_price,
                'open': float(data.get('open', 0)),
                'high': float(data.get('high', 0)),
                'low': float(data.get('low', 0)),
                'close': current_price,  # 当前价格作为收盘
                'prev_close': last_close,
                'volume': int(data.get('volume', data.get('vol', 0))),
                'amount': float(data.get('amount', 0)),
                'change': change,
                'change_percent': change_percent,
                'timestamp': datetime.now().isoformat()
            }

            logger.info(f"[MootdxAdapter] 获取 {symbol} 实时行情成功: 价格={current_price}, 涨跌={change:.3f} ({change_percent:.2f}%)")
            return result

        except Exception as e:
            logger.error(f"[MootdxAdapter] 获取 {symbol} 实时行情失败: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return {}


class DataSourceManager:
    """数据源管理器"""

    def __init__(self):
        self._adapters: Dict[str, BaseDataAdapter] = {}
        self._primary: Optional[str] = None

    def register(self, name: str, adapter: BaseDataAdapter, primary: bool = False):
        """注册数据源"""
        self._adapters[name] = adapter
        if primary or self._primary is None:
            self._primary = name
        logger.info(f"[DataSourceManager] 注册数据源: {name}")

    def get_adapter(self, name: Optional[str] = None) -> Optional[BaseDataAdapter]:
        """获取数据源适配器"""
        if name:
            return self._adapters.get(name)
        return self._adapters.get(self._primary)

    def connect_all(self) -> Dict[str, bool]:
        """连接所有数据源"""
        results = {}
        for name, adapter in self._adapters.items():
            results[name] = adapter.connect()
        return results

    def disconnect_all(self):
        """断开所有数据源"""
        for adapter in self._adapters.values():
            adapter.disconnect()


# 创建全局数据源管理器实例
data_source_manager = DataSourceManager()
