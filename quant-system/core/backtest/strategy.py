"""
策略基类与实现

提供策略开发的框架和三个具体策略实现：
- ETF轮动策略：基于动量和多维度评分的ETF轮动
- 永久组合策略：资产配置与动态再平衡
- 主题仓位策略：事件驱动的主题择时
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
import pandas as pd
import numpy as np

from ..indicators import IndicatorRegistry, get_indicator, BaseIndicator
from .broker import SimulatedBroker, Order, OrderSide


@dataclass
class Signal:
    """交易信号数据类"""
    symbol: str
    action: str  # 'buy', 'sell', 'hold'
    weight: float = 0.0  # 目标权重（0-1）
    confidence: float = 0.5  # 信号置信度（0-1）

    # 元数据
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class StrategyBase(ABC):
    """
    策略基类

    所有策略必须继承此类，实现以下方法：
    - initialize: 策略初始化
    - generate_signals: 生成交易信号
    - on_data: 数据处理回调
    """

    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化策略

        Args:
            config: 策略配置参数
        """
        self.config = config or {}
        self.name = self.__class__.__name__

        # 状态
        self.is_initialized = False
        self.current_date: Optional[datetime] = None
        self.holdings: Dict[str, float] = {}  # 当前持仓权重

        # 历史记录
        self.signals_history: List[Signal] = []
        self.rebalance_history: List[Dict] = []

        # 指标实例缓存
        self._indicators: Dict[str, BaseIndicator] = {}

    def initialize(self, broker: SimulatedBroker, **kwargs):
        """
        策略初始化

        Args:
            broker: 经纪商实例
            **kwargs: 其他初始化参数
        """
        self.broker = broker
        self.is_initialized = True

        # 子类可以覆盖此方法进行额外初始化
        self._on_initialize(**kwargs)

    def _on_initialize(self, **kwargs):
        """子类覆盖此方法进行自定义初始化"""
        pass

    @abstractmethod
    def generate_signals(
        self,
        current_date: datetime,
        broker: SimulatedBroker,
        price_data: Dict[str, pd.Series]
    ) -> List[Dict]:
        """
        生成交易信号

        Args:
            current_date: 当前日期
            broker: 经纪商实例
            price_data: 价格数据字典

        Returns:
            List[Dict]: 交易信号列表
        """
        pass

    def on_data(self, timestamp: datetime, data: Dict[str, Any]):
        """
        新数据到达回调

        Args:
            timestamp: 时间戳
            data: 数据字典
        """
        self.current_date = timestamp

    def get_indicator(self, indicator_id: str, **params) -> BaseIndicator:
        """
        获取或创建指标实例

        Args:
            indicator_id: 指标ID
            **params: 指标参数

        Returns:
            BaseIndicator: 指标实例
        """
        cache_key = f"{indicator_id}_{hash(str(sorted(params.items())))}"

        if cache_key not in self._indicators:
            self._indicators[cache_key] = get_indicator(indicator_id, **params)

        return self._indicators[cache_key]

    def rebalance(
        self,
        target_weights: Dict[str, float],
        broker: SimulatedBroker,
        price_data: Dict[str, pd.Series]
    ) -> List[Order]:
        """
        执行再平衡

        Args:
            target_weights: 目标权重字典 {symbol: weight}
            broker: 经纪商实例
            price_data: 价格数据

        Returns:
            List[Order]: 生成的订单列表
        """
        orders = []
        total_value = broker.total_value

        # 当前持仓权重
        current_weights = {}
        for symbol, position in broker.positions.items():
            current_weights[symbol] = position.market_value / total_value

        # 所有涉及的品种
        all_symbols = set(target_weights.keys()) | set(current_weights.keys())

        for symbol in all_symbols:
            target = target_weights.get(symbol, 0)
            current = current_weights.get(symbol, 0)

            # 计算权重差异
            weight_diff = target - current

            # 如果差异小于阈值，不调仓
            if abs(weight_diff) < 0.01:  # 1%阈值
                continue

            # 计算交易数量
            if symbol in price_data:
                price = price_data[symbol]['close']
                trade_value = weight_diff * total_value
                quantity = int(abs(trade_value) / price)

                if quantity > 0:
                    side = OrderSide.BUY if weight_diff > 0 else OrderSide.SELL
                    order = Order(
                        id='',
                        symbol=symbol,
                        side=side,
                        quantity=quantity,
                        order_type=OrderType.MARKET
                    )
                    orders.append(order)

        # 记录再平衡
        self.rebalance_history.append({
            'date': self.current_date,
            'target_weights': target_weights.copy(),
            'current_weights': current_weights.copy(),
            'orders': orders
        })

        return orders

    def get_current_state(self) -> Dict[str, Any]:
        """获取当前策略状态"""
        return {
            'name': self.name,
            'initialized': self.is_initialized,
            'current_date': self.current_date,
            'holdings': self.holdings.copy(),
            'signal_count': len(self.signals_history),
            'rebalance_count': len(self.rebalance_history),
        }


class ETFRotationStrategy(StrategyBase):
    """
    ETF轮动策略

    基于L1-L4多维度评分的ETF轮动策略：
    - 每周计算候选ETF的综合评分
    - 选取评分最高的N只ETF
    - 等权重或按评分加权配置
    """

    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化ETF轮动策略

        Args:
            config: 策略配置
                - etf_universe: ETF候选池
                - top_n: 选取前N只
                - min_score: 最低入选分数
                - rebalance_freq: 调仓频率（weekly/monthly）
        """
        default_config = {
            'etf_universe': ['159920', '513500', '518880', '159949'],  # 恒生、标普、黄金、创业板
            'top_n': 2,
            'min_score': 50,
            'rebalance_freq': 'weekly',
            'weight_method': 'equal',  # equal, score_weighted
        }

        if config:
            default_config.update(config)

        super().__init__(default_config)
        self.name = "ETFRotationStrategy"

        # 状态
        self.last_rebalance_date: Optional[datetime] = None
        self.current_holdings: Dict[str, float] = {}
        self.scores_history: List[Dict] = []

    def generate_signals(
        self,
        current_date: datetime,
        broker: SimulatedBroker,
        price_data: Dict[str, pd.Series]
    ) -> List[Dict]:
        """
        生成ETF轮动信号

        每周检查一次，计算评分并调仓
        """
        signals = []

        # 检查是否需要调仓
        if not self._should_rebalance(current_date):
            return signals

        # 计算各ETF的综合评分
        scores = {}
        for symbol in self.config['etf_universe']:
            if symbol in price_data:
                score = self._calculate_score(symbol, price_data, current_date)
                scores[symbol] = score

        # 记录评分
        self.scores_history.append({
            'date': current_date,
            'scores': scores.copy()
        })

        # 筛选符合条件的ETF
        valid_scores = {s: score for s, score in scores.items() if score >= self.config['min_score']}

        if not valid_scores:
            # 没有符合条件的，清空持仓
            self.current_holdings = {}
            return self._generate_clear_signals(broker, price_data)

        # 选取前N名
        sorted_scores = sorted(valid_scores.items(), key=lambda x: x[1], reverse=True)
        selected = sorted_scores[:self.config['top_n']]

        # 计算目标权重
        if self.config['weight_method'] == 'equal':
            target_weights = {s: 1.0 / len(selected) for s, _ in selected}
        else:  # score_weighted
            total_score = sum(score for _, score in selected)
            target_weights = {s: score / total_score for s, score in selected}

        # 生成调仓信号
        signals = self._generate_rebalance_signals(
            target_weights, broker, price_data
        )

        self.current_holdings = target_weights
        self.last_rebalance_date = current_date

        return signals

    def _should_rebalance(self, current_date: datetime) -> bool:
        """检查是否需要调仓"""
        if self.last_rebalance_date is None:
            return True

        freq = self.config['rebalance_freq']
        days_since_last = (current_date - self.last_rebalance_date).days

        if freq == 'daily':
            return days_since_last >= 1
        elif freq == 'weekly':
            return days_since_last >= 7
        elif freq == 'monthly':
            return days_since_last >= 30
        else:
            return False

    def _calculate_score(
        self,
        symbol: str,
        price_data: Dict[str, pd.Series],
        current_date: datetime
    ) -> float:
        """
        计算ETF综合评分

        简化版本：基于动量和价格位置
        实际应使用完整的多维度指标系统
        """
        data = price_data[symbol]
        close = data['close']

        # 这里简化处理，实际应该调用L1-L4指标系统
        # 模拟一个基于近期涨跌幅的评分
        if 'close_20_days_ago' in data:
            momentum_20d = (close - data['close_20_days_ago']) / data['close_20_days_ago']
        else:
            momentum_20d = 0

        # 将动量转换为0-100评分
        score = 50 + momentum_20d * 1000  # 放大系数
        score = max(0, min(100, score))  # 限制在0-100

        return score

    def _generate_clear_signals(
        self,
        broker: SimulatedBroker,
        price_data: Dict[str, pd.Series]
    ) -> List[Dict]:
        """生成清仓信号"""
        signals = []

        for symbol, position in broker.positions.items():
            if position.quantity > 0:
                signals.append({
                    'action': 'sell',
                    'symbol': symbol,
                    'quantity': position.quantity,
                    'reason': 'clear_position'
                })

        return signals

    def _generate_rebalance_signals(
        self,
        target_weights: Dict[str, float],
        broker: SimulatedBroker,
        price_data: Dict[str, pd.Series]
    ) -> List[Dict]:
        """生成再平衡信号"""
        signals = []
        total_value = broker.total_value

        # 计算当前权重
        current_weights = {}
        for symbol, position in broker.positions.items():
            current_weights[symbol] = position.market_value / total_value

        # 所有涉及的品种
        all_symbols = set(target_weights.keys()) | set(current_weights.keys())

        for symbol in all_symbols:
            target = target_weights.get(symbol, 0)
            current = current_weights.get(symbol, 0)

            # 计算需要调整的值
            weight_diff = target - current

            if abs(weight_diff) < 0.01:  # 差异小于1%不调仓
                continue

            # 计算交易数量
            if symbol in price_data:
                price = price_data[symbol]['close']
                trade_value = weight_diff * total_value
                quantity = int(abs(trade_value) / price)

                if quantity > 0:
                    action = 'buy' if weight_diff > 0 else 'sell'
                    signals.append({
                        'action': action,
                        'symbol': symbol,
                        'quantity': quantity,
                        'target_weight': target,
                        'current_weight': current,
                        'reason': 'rebalance'
                    })

        return signals


class PermanentPortfolioStrategy(StrategyBase):
    """
    永久组合策略

    基于资产配置的被动策略，定期再平衡：
    - 股票 40%
    - 债券 25%
    - 黄金 20%
    - 现金 15%
    """

    def __init__(self, config: Dict[str, Any] = None):
        default_config = {
            'assets': {
                '510300': 0.40,  # 沪深300ETF
                '511010': 0.25,  # 国债ETF
                '518880': 0.20,  # 黄金ETF
                '511880': 0.15,  # 货币基金
            },
            'rebalance_freq': 'monthly',  # monthly, quarterly
            'rebalance_threshold': 0.05,  # 偏离超过5%再平衡
        }

        if config:
            default_config.update(config)

        super().__init__(default_config)
        self.name = "PermanentPortfolioStrategy"
        self.last_rebalance_date: Optional[datetime] = None

    def generate_signals(
        self,
        current_date: datetime,
        broker: SimulatedBroker,
        price_data: Dict[str, pd.Series]
    ) -> List[Dict]:
        """生成再平衡信号"""
        signals = []

        # 检查是否需要再平衡
        if not self._should_rebalance(current_date, broker):
            return signals

        # 计算目标权重
        target_weights = self.config['assets']

        # 生成调仓信号
        signals = self._generate_rebalance_signals(
            target_weights, broker, price_data
        )

        self.last_rebalance_date = current_date
        return signals

    def _should_rebalance(
        self,
        current_date: datetime,
        broker: SimulatedBroker
    ) -> bool:
        """检查是否需要再平衡"""
        if self.last_rebalance_date is None:
            return True

        freq = self.config['rebalance_freq']
        days_since = (current_date - self.last_rebalance_date).days

        # 时间条件
        time_trigger = False
        if freq == 'monthly':
            time_trigger = days_since >= 30
        elif freq == 'quarterly':
            time_trigger = days_since >= 90

        if not time_trigger:
            return False

        # 阈值条件 - 检查各资产偏离
        threshold = self.config['rebalance_threshold']
        total_value = broker.total_value

        for symbol, target_weight in self.config['assets'].items():
            position = broker.positions.get(symbol)
            current_weight = (position.market_value / total_value) if position else 0

            if abs(current_weight - target_weight) > threshold:
                return True

        return False


class ThematicStrategy(StrategyBase):
    """
    主题仓位策略

    基于事件驱动的主题择时策略：
    - 识别市场主题（如能源、绿电、农产品）
    - 根据多维度评分确定仓位
    - 严格止损止盈
    """

    def __init__(self, config: Dict[str, Any] = None):
        default_config = {
            'themes': {
                'energy': {
                    'symbols': ['513350', '515220', '159930'],  # 油气、煤炭、能源
                    'entry_score': 65,
                    'exit_score': 45,
                },
                'green_power': {
                    'symbols': ['159669'],  # 绿电ETF
                    'entry_score': 60,
                    'exit_score': 40,
                },
            },
            'max_themes': 2,  # 最多同时持有几个主题
            'position_per_theme': 0.30,  # 每个主题仓位上限
            'stop_loss': 0.08,  # 8%止损
            'take_profit': 0.20,  # 20%止盈
        }

        if config:
            default_config.update(config)

        super().__init__(default_config)
        self.name = "ThematicStrategy"

        # 状态
        self.active_themes: Dict[str, Dict] = {}  # 当前活跃的主题
        self.entry_prices: Dict[str, float] = {}  # 入场价格记录

    def generate_signals(
        self,
        current_date: datetime,
        broker: SimulatedBroker,
        price_data: Dict[str, pd.Series]
    ) -> List[Dict]:
        """生成主题交易信号"""
        signals = []

        # 1. 检查止盈止损
        stop_signals = self._check_stop_loss_take_profit(broker, price_data)
        signals.extend(stop_signals)

        # 2. 计算各主题评分
        theme_scores = {}
        for theme_name, theme_config in self.config['themes'].items():
            score = self._calculate_theme_score(theme_name, theme_config, price_data)
            theme_scores[theme_name] = score

        # 3. 检查需要退出的主题
        for theme_name in list(self.active_themes.keys()):
            score = theme_scores.get(theme_name, 0)
            theme_config = self.config['themes'][theme_name]

            if score < theme_config['exit_score']:
                # 退出信号
                for symbol in theme_config['symbols']:
                    position = broker.positions.get(symbol)
                    if position and position.quantity > 0:
                        signals.append({
                            'action': 'sell',
                            'symbol': symbol,
                            'quantity': position.quantity,
                            'reason': 'theme_exit',
                            'theme': theme_name,
                            'score': score
                        })

                del self.active_themes[theme_name]

        # 4. 检查可以新进入的主题
        active_count = len(self.active_themes)
        available_slots = self.config['max_themes'] - active_count

        if available_slots > 0:
            # 按评分排序
            sorted_themes = sorted(theme_scores.items(), key=lambda x: x[1], reverse=True)

            for theme_name, score in sorted_themes:
                if theme_name in self.active_themes:
                    continue

                theme_config = self.config['themes'][theme_name]

                if score >= theme_config['entry_score'] and available_slots > 0:
                    # 入场信号
                    position_value = broker.total_value * self.config['position_per_theme']

                    for symbol in theme_config['symbols']:
                        if symbol in price_data:
                            price = price_data[symbol]['close']
                            quantity = int(position_value / len(theme_config['symbols']) / price)

                            if quantity > 0:
                                signals.append({
                                    'action': 'buy',
                                    'symbol': symbol,
                                    'quantity': quantity,
                                    'reason': 'theme_entry',
                                    'theme': theme_name,
                                    'score': score
                                })

                                # 记录入场价格
                                self.entry_prices[symbol] = price

                    self.active_themes[theme_name] = {
                        'entry_date': current_date,
                        'score': score,
                        'config': theme_config
                    }

                    available_slots -= 1

        return signals

    def _check_stop_loss_take_profit(
        self,
        broker: SimulatedBroker,
        price_data: Dict[str, pd.Series]
    ) -> List[Dict]:
        """检查止盈止损"""
        signals = []

        for symbol, position in broker.positions.items():
            if position.quantity <= 0:
                continue

            if symbol not in price_data:
                continue

            current_price = price_data[symbol]['close']
            entry_price = self.entry_prices.get(symbol)

            if entry_price is None:
                continue

            pnl_ratio = (current_price - entry_price) / entry_price

            # 止损
            if pnl_ratio <= -self.config['stop_loss']:
                signals.append({
                    'action': 'sell',
                    'symbol': symbol,
                    'quantity': position.quantity,
                    'reason': 'stop_loss',
                    'pnl_ratio': pnl_ratio
                })
                if symbol in self.entry_prices:
                    del self.entry_prices[symbol]

            # 止盈
            elif pnl_ratio >= self.config['take_profit']:
                signals.append({
                    'action': 'sell',
                    'symbol': symbol,
                    'quantity': position.quantity,
                    'reason': 'take_profit',
                    'pnl_ratio': pnl_ratio
                })
                if symbol in self.entry_prices:
                    del self.entry_prices[symbol]

        return signals

    def _calculate_theme_score(
        self,
        theme_name: str,
        theme_config: Dict,
        price_data: Dict[str, pd.Series]
    ) -> float:
        """计算主题评分"""
        # 简化版本：基于主题内ETF的平均动量
        momentums = []

        for symbol in theme_config['symbols']:
            if symbol in price_data:
                data = price_data[symbol]
                if 'close_20_days_ago' in data:
                    momentum = (data['close'] - data['close_20_days_ago']) / data['close_20_days_ago']
                    momentums.append(momentum)

        if not momentums:
            return 50  # 默认中值

        avg_momentum = np.mean(momentums)
        # 转换到0-100评分
        score = 50 + avg_momentum * 500  # 放大
        return max(0, min(100, score))

    def _calculate_monthly_returns(self, equity_curve: pd.Series) -> pd.Series:
        """计算月度收益率"""
        monthly = equity_curve.resample('M').last()
        monthly_returns = monthly.pct_change().dropna()
        return monthly_returns

    def _max_consecutive(self, series: pd.Series) -> int:
        """计算最大连续True次数"""
        if series.empty:
            return 0

        values = series.astype(int)
        max_count = 0
        current_count = 0

        for v in values:
            if v == 1:
                current_count += 1
                max_count = max(max_count, current_count)
            else:
                current_count = 0

        return max_count
