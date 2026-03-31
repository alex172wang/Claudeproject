"""
实时数据流模块

提供实时行情数据订阅、推送和缓存功能。
支持多数据源、多品种同时订阅。
"""

import time
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Dict, List, Optional, Set
from enum import Enum

import pandas as pd
import numpy as np


class DataSource(Enum):
    """数据源类型"""
    MOOTDX = "mootdx"           # 通达信
    AKSHARE = "akshare"         # AKShare
    SINA = "sina"               # 新浪财经
    TUSHARE = "tushare"         # Tushare
    MOCK = "mock"               # 模拟数据（测试用）


@dataclass
class TickData:
    """
    实时Tick数据

    保存单个时间点的行情快照
    """
    symbol: str                          # 股票/ETF代码
    timestamp: datetime                  # 时间戳
    price: float                         # 最新价格
    open: float = 0.0                    # 开盘价
    high: float = 0.0                    # 最高价
    low: float = 0.0                     # 最低价
    prev_close: float = 0.0              # 昨收价
    volume: int = 0                      # 成交量（股）
    amount: float = 0.0                  # 成交额
    bid_1: float = 0.0                   # 买1价
    bid_1_volume: int = 0                # 买1量
    ask_1: float = 0.0                   # 卖1价
    ask_1_volume: int = 0                # 卖1量

    @property
    def change_pct(self) -> float:
        """涨跌幅百分比"""
        if self.prev_close > 0:
            return (self.price - self.prev_close) / self.prev_close * 100
        return 0.0

    @property
    def mid_price(self) -> float:
        """中间价"""
        if self.bid_1 > 0 and self.ask_1 > 0:
            return (self.bid_1 + self.ask_1) / 2
        return self.price


@dataclass
class BarData:
    """
    K线数据

    保存一段时间内的OHLCV数据
    """
    symbol: str
    timestamp: datetime
    interval: str           # 周期: 1m, 5m, 15m, 1h, 1d
    open: float
    high: float
    low: float
    close: float
    volume: int
    amount: float = 0.0


class RealtimeDataStream:
    """
    实时数据流管理器

    管理多个数据源的实时行情订阅和推送

    功能：
    1. 多品种订阅/取消订阅
    2. 实时数据推送（回调机制）
    3. 数据缓存（最近N条）
    4. 自动重连
    5. 多线程处理

    示例：
        stream = RealtimeDataStream(data_source=DataSource.MOOTDX)

        # 注册回调
        stream.on_tick = lambda tick: print(f"收到 {tick.symbol}: {tick.price}")

        # 订阅品种
        stream.subscribe(['510300', '510500'])

        # 启动数据流
        stream.start()
    """

    def __init__(
        self,
        data_source: DataSource = DataSource.MOOTDX,
        cache_size: int = 1000,
        auto_reconnect: bool = True,
        reconnect_interval: int = 5,
    ):
        """
        初始化实时数据流

        Args:
            data_source: 数据源类型
            cache_size: 每个品种的缓存大小
            auto_reconnect: 是否自动重连
            reconnect_interval: 重连间隔（秒）
        """
        self.data_source = data_source
        self.cache_size = cache_size
        self.auto_reconnect = auto_reconnect
        self.reconnect_interval = reconnect_interval

        # 订阅管理
        self._subscribed_symbols: Set[str] = set()
        self._tick_callbacks: List[Callable[[TickData], None]] = []
        self._bar_callbacks: List[Callable[[BarData], None]] = []

        # 数据缓存
        self._tick_cache: Dict[str, List[TickData]] = {}
        self._bar_cache: Dict[str, Dict[str, List[BarData]]] = {}  # symbol -> interval -> bars

        # 运行状态
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()

        # 数据源适配器
        self._adapter = self._create_adapter()

        # 公开回调（方便单个回调设置）
        self.on_tick: Optional[Callable[[TickData], None]] = None
        self.on_bar: Optional[Callable[[BarData], None]] = None

    def _create_adapter(self):
        """创建数据源适配器"""
        if self.data_source == DataSource.MOOTDX:
            from .adapters import MootdxRealtimeAdapter
            return MootdxRealtimeAdapter()
        elif self.data_source == DataSource.AKSHARE:
            from .adapters import AKShareRealtimeAdapter
            return AKShareRealtimeAdapter()
        elif self.data_source == DataSource.MOCK:
            return MockAdapter()
        else:
            raise ValueError(f"不支持的数据源: {self.data_source}")

    def subscribe(self, symbols: List[str]) -> None:
        """
        订阅品种

        Args:
            symbols: 品种代码列表
        """
        with self._lock:
            for symbol in symbols:
                self._subscribed_symbols.add(symbol)
                if symbol not in self._tick_cache:
                    self._tick_cache[symbol] = []
                if symbol not in self._bar_cache:
                    self._bar_cache[symbol] = {}

        # 通知适配器
        if self._adapter and hasattr(self._adapter, 'subscribe'):
            self._adapter.subscribe(symbols)

    def unsubscribe(self, symbols: List[str]) -> None:
        """取消订阅"""
        with self._lock:
            for symbol in symbols:
                self._subscribed_symbols.discard(symbol)

        if self._adapter and hasattr(self._adapter, 'unsubscribe'):
            self._adapter.unsubscribe(symbols)

    def start(self) -> None:
        """启动数据流"""
        if self._running:
            return

        self._running = True

        # 启动适配器
        if self._adapter and hasattr(self._adapter, 'start'):
            self._adapter.start()

        # 启动处理线程
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """停止数据流"""
        self._running = False

        if self._adapter and hasattr(self._adapter, 'stop'):
            self._adapter.stop()

        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None

    def _run_loop(self) -> None:
        """主循环"""
        while self._running:
            try:
                # 从适配器获取数据
                if self._adapter and hasattr(self._adapter, 'get_ticks'):
                    ticks = self._adapter.get_ticks()
                    for tick in ticks:
                        self._process_tick(tick)

                time.sleep(0.1)  # 100ms轮询

            except Exception as e:
                print(f"数据流错误: {e}")
                if self.auto_reconnect:
                    time.sleep(self.reconnect_interval)
                else:
                    break

    def _process_tick(self, tick: TickData) -> None:
        """处理Tick数据"""
        # 缓存
        with self._lock:
            if tick.symbol in self._tick_cache:
                self._tick_cache[tick.symbol].append(tick)
                # 限制缓存大小
                if len(self._tick_cache[tick.symbol]) > self.cache_size:
                    self._tick_cache[tick.symbol].pop(0)

        # 回调
        if self.on_tick:
            try:
                self.on_tick(tick)
            except Exception as e:
                print(f"Tick回调错误: {e}")

        for callback in self._tick_callbacks:
            try:
                callback(tick)
            except Exception as e:
                print(f"Tick回调错误: {e}")

    def get_latest_tick(self, symbol: str) -> Optional[TickData]:
        """获取最新Tick"""
        with self._lock:
            if symbol in self._tick_cache and self._tick_cache[symbol]:
                return self._tick_cache[symbol][-1]
        return None

    def get_tick_history(self, symbol: str, n: int = 100) -> List[TickData]:
        """获取Tick历史"""
        with self._lock:
            if symbol in self._tick_cache:
                return self._tick_cache[symbol][-n:]
        return []

    def add_tick_callback(self, callback: Callable[[TickData], None]) -> None:
        """添加Tick回调"""
        self._tick_callbacks.append(callback)

    def remove_tick_callback(self, callback: Callable[[TickData], None]) -> None:
        """移除Tick回调"""
        if callback in self._tick_callbacks:
            self._tick_callbacks.remove(callback)

    @property
    def is_running(self) -> bool:
        """是否运行中"""
        return self._running

    @property
    def subscribed_symbols(self) -> List[str]:
        """已订阅品种"""
        with self._lock:
            return list(self._subscribed_symbols)


class MockAdapter:
    """模拟数据适配器（用于测试）"""

    def __init__(self):
        self._running = False
        self._symbols = set()
        self._tick_queue = []
        self._counter = 0

    def subscribe(self, symbols):
        for s in symbols:
            self._symbols.add(s)

    def unsubscribe(self, symbols):
        for s in symbols:
            self._symbols.discard(s)

    def start(self):
        self._running = True

    def stop(self):
        self._running = False

    def get_ticks(self):
        """生成模拟Tick数据"""
        if not self._running:
            return []

        ticks = []
        import random
        for symbol in self._symbols:
            base_price = {'510300': 4.0, '510500': 6.5, '510050': 2.5, '159915': 2.0}.get(symbol, 5.0)
            price = base_price + random.gauss(0, 0.01)

            tick = TickData(
                symbol=symbol,
                timestamp=datetime.now(),
                price=round(price, 3),
                open=base_price,
                high=price + 0.02,
                low=price - 0.02,
                prev_close=base_price,
                volume=random.randint(1000, 10000),
                amount=random.randint(10000, 100000),
                bid_1=price - 0.01,
                bid_1_volume=random.randint(100, 1000),
                ask_1=price + 0.01,
                ask_1_volume=random.randint(100, 1000),
            )
            ticks.append(tick)

        return ticks
