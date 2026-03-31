"""
实盘交易执行模块

提供订单管理、执行跟踪、成交回报等功能。
"""

import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class OrderStatus(Enum):
    """订单状态"""
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIAL_FILLED = "partial_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class OrderType(Enum):
    """订单类型"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"


class OrderSide(Enum):
    """买卖方向"""
    BUY = "buy"
    SELL = "sell"


@dataclass
class Order:
    """订单对象"""
    order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: int
    price: Optional[float] = None
    filled_quantity: int = 0
    avg_fill_price: float = 0.0
    status: OrderStatus = OrderStatus.PENDING
    create_time: datetime = field(default_factory=datetime.now)
    update_time: datetime = field(default_factory=datetime.now)

    @property
    def remaining_quantity(self) -> int:
        return self.quantity - self.filled_quantity


@dataclass
class FillEvent:
    """成交事件"""
    fill_id: str
    order_id: str
    symbol: str
    side: OrderSide
    fill_price: float
    fill_quantity: int
    fill_time: datetime
    commission: float = 0.0


class OrderManager:
    """订单管理器"""

    def __init__(self):
        self._active_orders: Dict[str, Order] = {}
        self._history_orders: Dict[str, Order] = {}
        self._fill_events: List[FillEvent] = []
        self._lock = threading.RLock()
        self._counter = 0

    def create_order(
        self,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        quantity: int,
        price: Optional[float] = None,
    ) -> Order:
        """创建新订单"""
        with self._lock:
            self._counter += 1
            order_id = f"ORD{datetime.now().strftime('%Y%m%d%H%M%S')}_{self._counter:04d}"

            order = Order(
                order_id=order_id,
                symbol=symbol,
                side=side,
                order_type=order_type,
                quantity=quantity,
                price=price,
            )

            self._active_orders[order_id] = order
            return order

    def cancel_order(self, order_id: str) -> bool:
        """撤单"""
        with self._lock:
            order = self._active_orders.get(order_id)
            if not order:
                return False

            order.status = OrderStatus.CANCELLED
            order.update_time = datetime.now()

            self._history_orders[order_id] = order
            del self._active_orders[order_id]

        return True

    def get_order(self, order_id: str) -> Optional[Order]:
        """获取订单"""
        with self._lock:
            order = self._active_orders.get(order_id)
            if not order:
                order = self._history_orders.get(order_id)
            return order

    def get_active_orders(self) -> List[Order]:
        """获取活跃订单"""
        with self._lock:
            return list(self._active_orders.values())


class LiveTrader:
    """
    实盘交易器

    整合订单管理、风险控制和执行策略，
    提供完整的实盘交易功能。
    """

    def __init__(self, order_manager: Optional[OrderManager] = None):
        self.order_manager = order_manager or OrderManager()
        self._running = False
        self._lock = threading.RLock()

    def start(self):
        """启动交易器"""
        with self._lock:
            self._running = True
        print("[LiveTrader] Started")

    def stop(self):
        """停止交易器"""
        with self._lock:
            self._running = False
        print("[LiveTrader] Stopped")

    def buy_market(self, symbol: str, quantity: int) -> Optional[Order]:
        """市价买入"""
        order = self.order_manager.create_order(
            symbol=symbol,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=quantity,
        )
        self.order_manager.submit_order(order.order_id)
        return order

    def sell_market(self, symbol: str, quantity: int) -> Optional[Order]:
        """市价卖出"""
        order = self.order_manager.create_order(
            symbol=symbol,
            side=OrderSide.SELL,
            order_type=OrderType.MARKET,
            quantity=quantity,
        )
        self.order_manager.submit_order(order.order_id)
        return order

    def buy_limit(self, symbol: str, quantity: int, price: float) -> Optional[Order]:
        """限价买入"""
        order = self.order_manager.create_order(
            symbol=symbol,
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=quantity,
            price=price,
        )
        self.order_manager.submit_order(order.order_id)
        return order

    def sell_limit(self, symbol: str, quantity: int, price: float) -> Optional[Order]:
        """限价卖出"""
        order = self.order_manager.create_order(
            symbol=symbol,
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            quantity=quantity,
            price=price,
        )
        self.order_manager.submit_order(order.order_id)
        return order

    def cancel(self, order_id: str) -> bool:
        """撤单"""
        return self.order_manager.cancel_order(order_id)

    def get_order(self, order_id: str) -> Optional[Order]:
        """获取订单"""
        return self.order_manager.get_order(order_id)

    def get_active_orders(self) -> List[Order]:
        """获取活跃订单"""
        return self.order_manager.get_active_orders()
