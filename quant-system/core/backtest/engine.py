"""
回测引擎核心模块

实现基于事件驱动的回测框架，支持：
- 时间序列数据驱动的事件循环
- 多策略并发回测
- 完整的交易成本模拟
- 实时绩效计算
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
import pandas as pd
import numpy as np
from tqdm import tqdm

from .broker import SimulatedBroker, Order, OrderSide, OrderType
from .metrics import PerformanceAnalyzer
from .results import BacktestResult


@dataclass
class BacktestConfig:
    """回测配置"""
    # 时间范围
    start_date: str
    end_date: str

    # 初始资金
    initial_capital: float = 1000000.0

    # 交易成本
    commission_rate: float = 0.001      # 佣金 0.1%
    min_commission: float = 5.0          # 最低佣金
    slippage_rate: float = 0.001        # 滑点 0.1%

    # 回测参数
    rebalance_frequency: str = 'daily'   # 调仓频率: daily, weekly, monthly
    max_positions: int = 5              # 最大持仓数量
    position_size_type: str = 'equal'    # 仓位分配: equal, risk_parity, target_vol

    # 风险管理
    max_drawdown_limit: float = 0.20    # 最大回撤限制
    position_limit: float = 0.30        # 单个品种仓位上限

    # 其他
    benchmark: str = '000001'           # 基准指数
    save_intermediate: bool = True      # 保存中间结果


class BacktestEngine:
    """
    回测引擎

    负责协调数据加载、策略执行、订单撮合、绩效计算等模块，
    完成完整的回测流程。
    """

    def __init__(self, config: BacktestConfig):
        """
        初始化回测引擎

        Args:
            config: 回测配置
        """
        self.config = config

        # 创建模拟经纪商
        self.broker = SimulatedBroker(
            initial_cash=config.initial_capital,
            commission_rate=config.commission_rate,
            min_commission=config.min_commission,
            slippage_rate=config.slippage_rate
        )

        # 绩效分析器
        self.performance = PerformanceAnalyzer()

        # 回测状态
        self.is_running = False
        self.current_date: Optional[datetime] = None
        self.trading_days: List[datetime] = []
        self.current_index = 0

        # 历史记录
        self.daily_stats: List[Dict[str, Any]] = []
        self.signals_history: List[Dict[str, Any]] = []

        # 数据缓存
        self.price_data: Dict[str, pd.DataFrame] = {}
        self.current_prices: Dict[str, pd.Series] = {}

        # 策略（在run时设置）
        self.strategy = None

        # 结果
        self.result: Optional[BacktestResult] = None

    def load_data(self, symbols: List[str], data_loader: Callable) -> bool:
        """
        加载回测所需数据

        Args:
            symbols: 品种代码列表
            data_loader: 数据加载函数，接收symbol返回DataFrame

        Returns:
            bool: 是否加载成功
        """
        print(f"正在加载数据，品种数量: {len(symbols)}")

        for symbol in tqdm(symbols, desc="加载数据"):
            try:
                df = data_loader(symbol, self.config.start_date, self.config.end_date)
                if df is not None and not df.empty:
                    self.price_data[symbol] = df
            except Exception as e:
                print(f"加载 {symbol} 数据失败: {e}")

        if not self.price_data:
            print("错误：没有加载到任何数据")
            return False

        # 构建交易日历
        all_dates = set()
        for df in self.price_data.values():
            all_dates.update(df.index)
        self.trading_days = sorted(list(all_dates))

        print(f"数据加载完成，交易日数量: {len(self.trading_days)}")
        return True

    def run(self, strategy) -> BacktestResult:
        """
        运行回测

        Args:
            strategy: 策略实例

        Returns:
            BacktestResult: 回测结果
        """
        if not self.trading_days:
            raise ValueError("请先调用load_data加载数据")

        self.strategy = strategy
        self.is_running = True

        print(f"开始回测: {self.config.start_date} 至 {self.config.end_date}")
        print(f"初始资金: {self.config.initial_capital:,.2f}")

        # 主回测循环
        for i, date in enumerate(tqdm(self.trading_days, desc="回测进度")):
            self.current_date = date
            self.current_index = i

            # 更新当前价格
            self._update_prices()

            # 处理待成交订单
            self.broker.process_market_data(date, self.current_prices)

            # 策略生成信号
            signals = self.strategy.generate_signals(
                current_date=date,
                broker=self.broker,
                price_data=self.current_prices
            )

            # 执行交易
            self._execute_signals(signals)

            # 记录每日统计
            self._record_daily_stats(signals)

        # 回测结束，计算最终绩效
        self.is_running = False
        self.result = self._generate_result()

        print("\n回测完成!")
        self._print_summary()

        return self.result

    def _update_prices(self):
        """更新当前价格"""
        self.current_prices = {}
        for symbol, df in self.price_data.items():
            if self.current_date in df.index:
                self.current_prices[symbol] = df.loc[self.current_date]

    def _execute_signals(self, signals: List[Dict]):
        """执行交易信号"""
        for signal in signals:
            action = signal.get('action')
            symbol = signal.get('symbol')
            quantity = signal.get('quantity', 0)

            if not all([action, symbol, quantity > 0]):
                continue

            # 创建订单
            side = OrderSide.BUY if action == 'buy' else OrderSide.SELL
            order = Order(
                id='',  # 由broker生成
                symbol=symbol,
                side=side,
                quantity=quantity,
                order_type=OrderType.MARKET,
                metadata={'signal': signal}
            )

            # 提交订单
            self.broker.submit_order(order)

    def _record_daily_stats(self, signals: List[Dict]):
        """记录每日统计"""
        stats = {
            'date': self.current_date,
            'cash': self.broker.cash,
            'position_value': sum(p.market_value for p in self.broker.positions.values()),
            'total_value': self.broker.total_value,
            'unrealized_pnl': self.broker.unrealized_pnl,
            'realized_pnl': self.broker.realized_pnl,
            'signal_count': len(signals),
            'open_orders': len([o for o in self.broker.orders.values() if o.status in [OrderStatus.SUBMITTED, OrderStatus.PARTIAL]]),
        }
        self.daily_stats.append(stats)

    def _generate_result(self) -> 'BacktestResult':
        """生成回测结果"""
        from .results import BacktestResult

        return BacktestResult(
            config=self.config,
            daily_stats=pd.DataFrame(self.daily_stats),
            trades=self.broker.trades,
            orders=self.broker.order_history,
            broker=self.broker
        )

    def _print_summary(self):
        """打印回测摘要"""
        result = self.result
        if not result:
            return

        print("\n" + "="*60)
        print("回测结果摘要")
        print("="*60)
        print(f"回测区间: {self.config.start_date} 至 {self.config.end_date}")
        print(f"初始资金: {self.config.initial_capital:,.2f}")
        print(f"最终资产: {result.final_value:,.2f}")
        print(f"总收益率: {result.total_return*100:.2f}%")
        print(f"年化收益: {result.annual_return*100:.2f}%")
        print(f"最大回撤: {result.max_drawdown*100:.2f}%")
        print(f"夏普比率: {result.sharpe_ratio:.2f}")
        print(f"交易次数: {len(self.broker.trades)}")
        print("="*60)
