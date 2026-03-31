"""
实时数据适配器

为不同数据源提供统一的实时数据接口
"""

import time
import threading
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional, Callable

import pandas as pd

from .stream import TickData, DataSource


class BaseRealtimeAdapter(ABC):
    """
    实时数据适配器基类

    所有数据源适配器必须继承此类
    """

    def __init__(self):
        self._running = False
        self._subscribed_symbols: set = set()
        self._callbacks: List[Callable[[TickData], None]] = []
        self._lock = threading.RLock()

    @abstractmethod
    def connect(self) -> bool:
        """连接数据源"""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """断开数据源"""
        pass

    @abstractmethod
    def subscribe(self, symbols: List[str]) -> None:
        """订阅品种"""
        pass

    @abstractmethod
    def unsubscribe(self, symbols: List[str]) -> None:
        """取消订阅"""
        pass

    def start(self) -> None:
        """启动数据接收"""
        self._running = True
        self.connect()

    def stop(self) -> None:
        """停止数据接收"""
        self._running = False
        self.disconnect()

    def add_callback(self, callback: Callable[[TickData], None]) -> None:
        """添加Tick回调"""
        with self._lock:
            self._callbacks.append(callback)

    def remove_callback(self, callback: Callable[[TickData], None]) -> None:
        """移除Tick回调"""
        with self._lock:
            if callback in self._callbacks:
                self._callbacks.remove(callback)

    def _notify_callbacks(self, tick: TickData) -> None:
        """通知所有回调"""
        with self._lock:
            for callback in self._callbacks:
                try:
                    callback(tick)
                except Exception as e:
                    print(f"Callback error: {e}")


class MootdxRealtimeAdapter(BaseRealtimeAdapter):
    """
    通达信实时数据适配器

    使用mootdx获取实时行情
    """

    def __init__(self, bestip: bool = True):
        super().__init__()
        self.bestip = bestip
        self._client = None
        self._poll_thread: Optional[threading.Thread] = None
        self._poll_interval = 3  # 3秒轮询

    def connect(self) -> bool:
        """连接通达信"""
        try:
            from mootdx import Quotes
            self._client = Quotes.factory(market='std', bestip=self.bestip)
            print(f"[MootdxAdapter] Connected")
            return True
        except Exception as e:
            print(f"[MootdxAdapter] Connect failed: {e}")
            return False

    def disconnect(self) -> None:
        """断开连接"""
        self._running = False
        if self._poll_thread:
            self._poll_thread.join(timeout=2)
        if self._client:
            try:
                self._client.close()
            except:
                pass
        print(f"[MootdxAdapter] Disconnected")

    def subscribe(self, symbols: List[str]) -> None:
        """订阅品种"""
        with self._lock:
            for s in symbols:
                self._subscribed_symbols.add(s)
        print(f"[MootdxAdapter] Subscribed: {symbols}")

    def unsubscribe(self, symbols: List[str]) -> None:
        """取消订阅"""
        with self._lock:
            for s in symbols:
                self._subscribed_symbols.discard(s)

    def start(self) -> None:
        """启动轮询"""
        super().start()
        self._poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._poll_thread.start()

    def _poll_loop(self) -> None:
        """轮询循环"""
        while self._running:
            try:
                symbols = list(self._subscribed_symbols)
                if symbols and self._client:
                    # 批量获取行情
                    quotes = self._client.quotes(symbols)
                    if quotes is not None:
                        for _, row in quotes.iterrows():
                            tick = self._quote_to_tick(row)
                            if tick:
                                self._notify_callbacks(tick)

                time.sleep(self._poll_interval)
            except Exception as e:
                print(f"[MootdxAdapter] Poll error: {e}")
                time.sleep(self._poll_interval)

    def _quote_to_tick(self, row: pd.Series) -> Optional[TickData]:
        """将quote转换为TickData"""
        try:
            return TickData(
                symbol=str(row.get('code', '')),
                timestamp=datetime.now(),
                price=float(row.get('price', 0)),
                open=float(row.get('open', 0)),
                high=float(row.get('high', 0)),
                low=float(row.get('low', 0)),
                prev_close=float(row.get('last_close', 0)),
                volume=int(row.get('volume', 0)),
                amount=float(row.get('amount', 0)),
                bid_1=float(row.get('bid1', 0)),
                bid_1_volume=int(row.get('bid1_volume', 0)),
                ask_1=float(row.get('ask1', 0)),
                ask_1_volume=int(row.get('ask1_volume', 0)),
            )
        except Exception as e:
            print(f"[MootdxAdapter] Convert error: {e}")
            return None


class AKShareRealtimeAdapter(BaseRealtimeAdapter):
    """
    AKShare实时数据适配器

    使用AKShare获取实时行情
    适用于ETF、股票列表等数据
    """

    def __init__(self):
        super().__init__()
        self._poll_interval = 5  # 5秒轮询
        self._poll_thread: Optional[threading.Thread] = None

    def connect(self) -> bool:
        """连接AKShare"""
        try:
            import akshare as ak
            print(f"[AKShareAdapter] Connected")
            return True
        except Exception as e:
            print(f"[AKShareAdapter] Connect failed: {e}")
            return False

    def disconnect(self) -> None:
        """断开连接"""
        self._running = False
        if self._poll_thread:
            self._poll_thread.join(timeout=2)
        print(f"[AKShareAdapter] Disconnected")

    def subscribe(self, symbols: List[str]) -> None:
        """订阅品种"""
        with self._lock:
            for s in symbols:
                self._subscribed_symbols.add(s)
        print(f"[AKShareAdapter] Subscribed: {symbols}")

    def unsubscribe(self, symbols: List[str]) -> None:
        """取消订阅"""
        with self._lock:
            for s in symbols:
                self._subscribed_symbols.discard(s)

    def start(self) -> None:
        """启动轮询"""
        super().start()
        self._poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._poll_thread.start()

    def _poll_loop(self) -> None:
        """轮询循环"""
        import akshare as ak

        while self._running:
            try:
                symbols = list(self._subscribed_symbols)
                if symbols:
                    # AKShare适合获取ETF列表等信息
                    # 实时行情使用spot接口
                    for symbol in symbols:
                        try:
                            # 获取实时行情
                            df = ak.stock_zh_a_spot_em()
                            if df is not None and not df.empty:
                                row = df[df['代码'] == symbol]
                                if not row.empty:
                                    tick = self._row_to_tick(row.iloc[0])
                                    if tick:
                                        self._notify_callbacks(tick)
                        except Exception as e:
                            print(f"[AKShareAdapter] Get {symbol} error: {e}")

                time.sleep(self._poll_interval)
            except Exception as e:
                print(f"[AKShareAdapter] Poll error: {e}")
                time.sleep(self._poll_interval)

    def _row_to_tick(self, row: pd.Series) -> Optional[TickData]:
        """将DataFrame行转换为TickData"""
        try:
            return TickData(
                symbol=str(row.get('代码', '')),
                timestamp=datetime.now(),
                price=float(row.get('最新价', 0)),
                open=float(row.get('今开', 0)),
                high=float(row.get('最高', 0)),
                low=float(row.get('最低', 0)),
                prev_close=float(row.get('昨收', 0)),
                volume=int(row.get('成交量', 0)),
                amount=float(row.get('成交额', 0)),
                bid_1=float(row.get('买一二', 0)),
                bid_1_volume=int(row.get('买一量', 0)),
                ask_1=float(row.get('卖一', 0)),
                ask_1_volume=int(row.get('卖一量', 0)),
            )
        except Exception as e:
            print(f"[AKShareAdapter] Convert error: {e}")
            return None


def create_stream(
    data_source: DataSource = DataSource.MOOTDX,
    **kwargs
) -> RealtimeDataStream:
    """
    创建实时数据流的工厂函数

    Args:
        data_source: 数据源类型
        **kwargs: 传递给RealtimeDataStream的参数

    Returns:
        RealtimeDataStream: 配置好的数据流实例

    示例:
        stream = create_stream(DataSource.MOOTDX, cache_size=500)
        stream.subscribe(['510300', '510500'])
        stream.start()
    """
    return RealtimeDataStream(data_source=data_source, **kwargs)
