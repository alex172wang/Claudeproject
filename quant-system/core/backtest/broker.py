"""
经纪商模拟模块

实现模拟交易环境，包含：
- 订单管理系统（OMS）
- 成交撮合引擎
- 资金与持仓管理
- 完整交易成本模型
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
import pandas as pd
import numpy as np


class OrderType(Enum):
    """订单类型"""
    MARKET = "market"          # 市价单
    LIMIT = "limit"            # 限价单
    STOP = "stop"              # 止损单
    STOP_LIMIT = "stop_limit"  # 止损限价单


class OrderSide(Enum):
    """订单方向"""
    BUY = "buy"
    SELL = "sell"


class OrderStatus(Enum):
    """订单状态"""
    PENDING = "pending"        # 待提交
    SUBMITTED = "submitted"    # 已提交
    PARTIAL = "partial"        # 部分成交
    FILLED = "filled"          # 完全成交
    CANCELLED = "cancelled"    # 已取消
    REJECTED = "rejected"      # 已拒绝


@dataclass
class Order:
    """订单数据类"""
    # 基本信息
    id: str
    symbol: str
    side: OrderSide
    quantity: float

    # 订单类型
    order_type: OrderType = OrderType.MARKET
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None

    # 状态
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: float = 0.0
    avg_fill_price: float = 0.0

    # 时间戳
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def remaining_quantity(self) -> float:
        """剩余未成交数量"""
        return self.quantity - self.filled_quantity

    @property
    def is_filled(self) -> bool:
        """是否完全成交"""
        return abs(self.filled_quantity - self.quantity) < 1e-10

    @property
    def fill_ratio(self) -> float:
        """成交比例"""
        if self.quantity == 0:
            return 0.0
        return self.filled_quantity / self.quantity


@dataclass
class Trade:
    """成交记录数据类"""
    id: str
    order_id: str
    symbol: str
    side: OrderSide
    quantity: float
    price: float
    timestamp: datetime

    # 成本明细
    commission: float = 0.0
    slippage: float = 0.0
    impact_cost: float = 0.0

    # 总成本
    total_cost: float = 0.0

    @property
    def amount(self) -> float:
        """成交金额"""
        return self.quantity * self.price

    @property
    def net_amount(self) -> float:
        """净成交金额（扣除成本）"""
        if self.side == OrderSide.BUY:
            return self.amount + self.total_cost
        else:
            return self.amount - self.total_cost


@dataclass
class Position:
    """持仓数据类"""
    symbol: str
    quantity: float = 0.0
    avg_cost: float = 0.0

    # 市值（实时更新）
    market_value: float = 0.0
    last_price: float = 0.0

    # 盈亏
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0

    # 交易统计
    trade_count: int = 0

    @property
    def cost_basis(self) -> float:
        """持仓成本"""
        return self.quantity * self.avg_cost

    @property
    def pnl_ratio(self) -> float:
        """盈亏比例"""
        if self.cost_basis == 0:
            return 0.0
        return self.unrealized_pnl / self.cost_basis

    def update_price(self, price: float):
        """更新最新价格"""
        self.last_price = price
        self.market_value = self.quantity * price
        self.unrealized_pnl = self.market_value - self.cost_basis

    def add_trade(self, trade: Trade):
        """添加成交记录更新持仓"""
        self.trade_count += 1

        if trade.side == OrderSide.BUY:
            # 买入 - 更新平均成本
            total_cost = self.cost_basis + trade.net_amount
            self.quantity += trade.quantity
            if self.quantity > 0:
                self.avg_cost = total_cost / self.quantity
        else:
            # 卖出 - 实现盈亏
            self.realized_pnl += (trade.price - self.avg_cost) * trade.quantity - trade.total_cost
            self.quantity -= trade.quantity

            if self.quantity <= 0:
                self.quantity = 0
                self.avg_cost = 0


class SimulatedBroker:
    """
    模拟经纪商

    提供完整的交易模拟环境，包括：
    - 订单提交、修改、取消
    - 基于价格数据的撮合成交
    - 资金管理和持仓跟踪
    - 完整的交易成本模型
    """

    def __init__(
        self,
        initial_cash: float = 1000000.0,
        commission_rate: float = 0.001,      # 佣金 0.1%
        min_commission: float = 5.0,         # 最低佣金
        slippage_rate: float = 0.001,       # 滑点 0.1%
        impact_cost_model: str = 'linear',   # 冲击成本模型
        enable_margin: bool = False,          # 是否启用杠杆
        margin_ratio: float = 1.0,           # 保证金比例
    ):
        """
        初始化模拟经纪商

        Args:
            initial_cash: 初始资金
            commission_rate: 佣金费率（默认 0.001 = 0.1%）
            min_commission: 最低佣金
            slippage_rate: 滑点率
            impact_cost_model: 冲击成本模型 ('linear', 'square_root')
            enable_margin: 是否启用保证金交易
            margin_ratio: 保证金比例（1.0 = 无杠杆）
        """
        # 资金设置
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.margin_used = 0.0

        # 费用设置
        self.commission_rate = commission_rate
        self.min_commission = min_commission
        self.slippage_rate = slippage_rate
        self.impact_cost_model = impact_cost_model

        # 杠杆设置
        self.enable_margin = enable_margin
        self.margin_ratio = margin_ratio

        # 状态跟踪
        self.positions: Dict[str, Position] = {}
        self.orders: Dict[str, Order] = {}
        self.trades: List[Trade] = []
        self.order_history: List[Order] = []

        # 时间戳
        self.current_time: Optional[datetime] = None

        # 计数器
        self._order_counter = 0
        self._trade_counter = 0

    def _generate_order_id(self) -> str:
        """生成唯一订单ID"""
        self._order_counter += 1
        return f"ORD_{self.current_time.strftime('%Y%m%d')}_{self._order_counter:06d}"

    def _generate_trade_id(self) -> str:
        """生成唯一成交ID"""
        self._trade_counter += 1
        return f"TRD_{self.current_time.strftime('%Y%m%d')}_{self._trade_counter:06d}"

    @property
    def total_value(self) -> float:
        """总资产价值"""
        position_value = sum(p.market_value for p in self.positions.values())
        return self.cash + position_value

    @property
    def unrealized_pnl(self) -> float:
        """未实现盈亏"""
        return sum(p.unrealized_pnl for p in self.positions.values())

    @property
    def realized_pnl(self) -> float:
        """已实现盈亏"""
        return sum(p.realized_pnl for p in self.positions.values())

    @property
    def total_pnl(self) -> float:
        """总盈亏"""
        return self.total_value - self.initial_cash

    def get_position(self, symbol: str) -> Optional[Position]:
        """获取指定品种的持仓"""
        return self.positions.get(symbol)

    def submit_order(self, order: Order) -> bool:
        """
        提交订单

        Args:
            order: 订单对象

        Returns:
            bool: 是否提交成功
        """
        # 验证订单
        if order.quantity <= 0:
            order.status = OrderStatus.REJECTED
            order.metadata['reject_reason'] = '数量必须大于0'
            return False

        # 检查资金/持仓
        if order.side == OrderSide.BUY:
            required_cash = order.quantity * (order.limit_price or 0)
            if required_cash > self.cash * 0.95:  # 预留5%缓冲
                order.status = OrderStatus.REJECTED
                order.metadata['reject_reason'] = '资金不足'
                return False
        else:
            position = self.positions.get(order.symbol)
            if not position or position.quantity < order.quantity:
                order.status = OrderStatus.REJECTED
                order.metadata['reject_reason'] = '持仓不足'
                return False

        # 设置订单ID和时间
        order.id = self._generate_order_id()
        order.created_at = self.current_time
        order.updated_at = self.current_time
        order.status = OrderStatus.SUBMITTED

        # 保存订单
        self.orders[order.id] = order
        self.order_history.append(order)

        return True

    def cancel_order(self, order_id: str) -> bool:
        """取消订单"""
        order = self.orders.get(order_id)
        if not order:
            return False

        if order.status in [OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED]:
            return False

        order.status = OrderStatus.CANCELLED
        order.updated_at = self.current_time
        return True

    def process_market_data(self, timestamp: datetime, market_data: Dict[str, pd.Series]):
        """
        处理市场数据，撮合订单

        Args:
            timestamp: 当前时间戳
            market_data: 市场数据字典 {symbol: price_data}
        """
        self.current_time = timestamp

        # 更新持仓市值
        for symbol, position in self.positions.items():
            if symbol in market_data:
                current_price = market_data[symbol]['close']
                position.update_price(current_price)

        # 撮合订单
        for order in list(self.orders.values()):
            if order.status not in [OrderStatus.SUBMITTED, OrderStatus.PARTIAL]:
                continue

            if order.symbol not in market_data:
                continue

            price_data = market_data[order.symbol]
            self._match_order(order, price_data)

    def _match_order(self, order: Order, price_data: pd.Series):
        """撮合单个订单"""
        # 获取价格
        if order.order_type == OrderType.MARKET:
            fill_price = price_data['open']  # 市价单以开盘价成交
        elif order.order_type == OrderType.LIMIT:
            fill_price = order.limit_price
            # 检查限价条件
            if order.side == OrderSide.BUY and fill_price < price_data['low']:
                return  # 未达到买入限价
            if order.side == OrderSide.SELL and fill_price > price_data['high']:
                return  # 未达到卖出限价
        else:
            return  # 不支持的其他类型

        # 计算成交量（这里简化处理，实际应考虑流动性）
        fill_quantity = order.remaining_quantity

        # 计算成本
        trade = self._create_trade(order, fill_price, fill_quantity, price_data)

        # 更新订单状态
        order.filled_quantity += fill_quantity
        order.avg_fill_price = (order.avg_fill_price * (order.filled_quantity - fill_quantity) +
                               fill_price * fill_quantity) / order.filled_quantity

        if order.is_filled:
            order.status = OrderStatus.FILLED
        else:
            order.status = OrderStatus.PARTIAL

        order.updated_at = self.current_time

        # 更新持仓和资金
        self._update_position_and_cash(trade)

    def _create_trade(self, order: Order, price: float, quantity: float, price_data: pd.Series) -> Trade:
        """创建成交记录"""
        # 计算佣金
        amount = price * quantity
        commission = max(amount * self.commission_rate, self.min_commission)

        # 计算滑点（简化模型：波动率越大滑点越大）
        volatility = (price_data['high'] - price_data['low']) / price_data['close']
        slippage = amount * self.slippage_rate * (1 + volatility * 10)

        # 计算冲击成本（大额订单）
        impact_cost = 0.0
        if self.impact_cost_model == 'linear':
            # 线性冲击成本模型
            volume_ratio = quantity / price_data.get('volume', quantity * 10)
            impact_cost = amount * volume_ratio * 0.1  # 10%的冲击系数

        total_cost = commission + slippage + impact_cost

        trade = Trade(
            id=self._generate_trade_id(),
            order_id=order.id,
            symbol=order.symbol,
            side=order.side,
            quantity=quantity,
            price=price,
            timestamp=self.current_time,
            commission=commission,
            slippage=slippage,
            impact_cost=impact_cost,
            total_cost=total_cost
        )

        self.trades.append(trade)
        return trade

    def _update_position_and_cash(self, trade: Trade):
        """更新持仓和资金"""
        symbol = trade.symbol

        # 更新或创建持仓
        if symbol not in self.positions:
            self.positions[symbol] = Position(symbol=symbol)

        position = self.positions[symbol]
        position.add_trade(trade)

        # 更新资金
        if trade.side == OrderSide.BUY:
            self.cash -= trade.net_amount
        else:
            self.cash += trade.net_amount

        # 清理空仓
        if position.quantity <= 0:
            del self.positions[symbol]

    def get_account_summary(self) -> Dict[str, Any]:
        """获取账户摘要"""
        position_value = sum(p.market_value for p in self.positions.values())

        return {
            'cash': self.cash,
            'position_value': position_value,
            'total_value': self.cash + position_value,
            'unrealized_pnl': self.unrealized_pnl,
            'realized_pnl': self.realized_pnl,
            'total_pnl': self.total_pnl,
            'position_count': len(self.positions),
            'open_order_count': len([o for o in self.orders.values() if o.status in [OrderStatus.SUBMITTED, OrderStatus.PARTIAL]]),
        }
