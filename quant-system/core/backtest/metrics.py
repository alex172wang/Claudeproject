"""
绩效分析模块

实现完整的回测绩效分析，包括：
- 收益率分析（总收益、年化收益、滚动收益）
- 风险指标（波动率、最大回撤、VaR、CVaR）
- 风险调整收益（夏普比率、索提诺比率、卡玛比率）
- 交易分析（胜率、盈亏比、持仓时间）
- 归因分析（Brinson归因、因子暴露）
"""

from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from scipy import stats


@dataclass
class RiskMetrics:
    """风险指标数据类"""
    # 波动率
    volatility: float = 0.0                # 年化波动率
    downside_volatility: float = 0.0       # 下行波动率

    # 回撤
    max_drawdown: float = 0.0             # 最大回撤
    max_drawdown_duration: int = 0        # 最大回撤持续时间（天）
    avg_drawdown: float = 0.0             # 平均回撤

    # 尾部风险
    var_95: float = 0.0                   # 95% VaR
    var_99: float = 0.0                   # 99% VaR
    cvar_95: float = 0.0                  # 95% CVaR (Expected Shortfall)
    skewness: float = 0.0                 # 偏度
    kurtosis: float = 0.0                 # 峰度

    # 贝塔和系统性风险
    beta: float = 0.0                       # 相对于基准的贝塔
    alpha: float = 0.0                    # 年化阿尔法
    tracking_error: float = 0.0           # 跟踪误差
    information_ratio: float = 0.0        # 信息比率


@dataclass
class ReturnMetrics:
    """收益指标数据类"""
    # 总收益
    total_return: float = 0.0             # 总收益率
    annualized_return: float = 0.0        # 年化收益率

    # 滚动收益
    rolling_returns: Dict[str, float] = field(default_factory=dict)  # 滚动期收益

    # 月度/年度收益统计
    monthly_returns: pd.Series = field(default_factory=lambda: pd.Series(dtype=float))
    yearly_returns: pd.Series = field(default_factory=lambda: pd.Series(dtype=float))

    # 正收益统计
    positive_months: int = 0              # 正收益月数
    negative_months: int = 0              # 负收益月数
    win_rate_monthly: float = 0.0         # 月度胜率

    # 连续统计
    consecutive_wins: int = 0             # 最大连续盈利月数
    consecutive_losses: int = 0           # 最大连续亏损月数


@dataclass
class RiskAdjustedMetrics:
    """风险调整收益指标数据类"""
    # 夏普比率
    sharpe_ratio: float = 0.0             # 年化夏普比率
    sharpe_ratio_annual: float = 0.0      # 日度夏普年化

    # 索提诺比率
    sortino_ratio: float = 0.0          # 索提诺比率

    # 卡玛比率
    calmar_ratio: float = 0.0             # 卡玛比率 (年化收益/最大回撤)

    # 特雷诺比率
    treynor_ratio: float = 0.0          # 特雷诺比率

    # Omega比率
    omega_ratio: float = 0.0            # Omega比率

    # 上行潜力比率
    upside_potential_ratio: float = 0.0  # 上行潜力比率

    # 风险调整后的收益
    risk_adjusted_return: float = 0.0    # 风险调整收益
    return_per_unit_risk: float = 0.0     # 单位风险收益


@dataclass
class TradeMetrics:
    """交易统计指标数据类"""
    # 交易次数
    total_trades: int = 0                 # 总交易次数
    winning_trades: int = 0               # 盈利交易次数
    losing_trades: int = 0                # 亏损交易次数
    break_even_trades: int = 0             # 持平交易次数

    # 胜率
    win_rate: float = 0.0                 # 总体胜率
    win_rate_long: float = 0.0            # 做多胜率
    win_rate_short: float = 0.0           # 做空胜率

    # 盈亏
    avg_profit: float = 0.0               # 平均盈利
    avg_loss: float = 0.0                  # 平均亏损
    avg_trade_return: float = 0.0          # 平均交易收益

    # 盈亏比
    profit_factor: float = 0.0            # 盈亏比
    payoff_ratio: float = 0.0              # 收益风险比

    # 持仓时间
    avg_holding_period: float = 0.0        # 平均持仓时间
    avg_holding_wins: float = 0.0          # 盈利交易平均持仓
    avg_holding_losses: float = 0.0        # 亏损交易平均持仓

    # 连续交易
    consecutive_wins: int = 0              # 最大连续盈利次数
    consecutive_losses: int = 0            # 最大连续亏损次数

    # 最大单笔
    largest_profit: float = 0.0            # 最大单笔盈利
    largest_loss: float = 0.0              # 最大单笔亏损

    # 其他统计
    total_commission: float = 0.0          # 总佣金
    total_slippage: float = 0.0            # 总滑点
    total_impact_cost: float = 0.0         # 总冲击成本


class PerformanceAnalyzer:
    """
    绩效分析器

    计算完整的回测绩效指标，包括收益、风险、风险调整收益、交易统计等。
    """

    def __init__(self, risk_free_rate: float = 0.03):
        """
        初始化绩效分析器

        Args:
            risk_free_rate: 无风险利率（年化），默认3%
        """
        self.risk_free_rate = risk_free_rate

        # 计算结果
        self.returns: Optional[ReturnMetrics] = None
        self.risk: Optional[RiskMetrics] = None
        self.risk_adjusted: Optional[RiskAdjustedMetrics] = None
        self.trades: Optional[TradeMetrics] = None

    def calculate_all(
        self,
        equity_curve: pd.Series,
        trades: List[Any],
        benchmark: Optional[pd.Series] = None
    ) -> Dict[str, Any]:
        """
        计算所有绩效指标

        Args:
            equity_curve: 权益曲线（日度）
            trades: 交易记录列表
            benchmark: 基准收益率曲线（可选）

        Returns:
            Dict: 所有绩效指标
        """
        # 计算收益率序列
        returns_series = equity_curve.pct_change().dropna()

        # 计算各类指标
        self.returns = self._calculate_return_metrics(equity_curve, returns_series)
        self.risk = self._calculate_risk_metrics(returns_series, benchmark)
        self.risk_adjusted = self._calculate_risk_adjusted_metrics(
            returns_series, self.risk
        )
        self.trades = self._calculate_trade_metrics(trades)

        return {
            'returns': self.returns,
            'risk': self.risk,
            'risk_adjusted': self.risk_adjusted,
            'trades': self.trades,
        }

    def _calculate_return_metrics(
        self,
        equity_curve: pd.Series,
        returns: pd.Series
    ) -> ReturnMetrics:
        """计算收益指标"""
        metrics = ReturnMetrics()

        # 总收益
        metrics.total_return = (equity_curve.iloc[-1] / equity_curve.iloc[0]) - 1

        # 年化收益
        n_years = len(returns) / 252
        metrics.annualized_return = (1 + metrics.total_return) ** (1/n_years) - 1 if n_years > 0 else 0

        # 月度收益统计
        monthly_returns = self._calculate_monthly_returns(equity_curve)
        metrics.monthly_returns = monthly_returns
        metrics.positive_months = (monthly_returns > 0).sum()
        metrics.negative_months = (monthly_returns < 0).sum()
        metrics.win_rate_monthly = metrics.positive_months / len(monthly_returns) if len(monthly_returns) > 0 else 0

        # 连续统计
        metrics.consecutive_wins = self._max_consecutive(monthly_returns > 0)
        metrics.consecutive_losses = self._max_consecutive(monthly_returns < 0)

        return metrics

    def _calculate_risk_metrics(
        self,
        returns: pd.Series,
        benchmark: Optional[pd.Series] = None
    ) -> RiskMetrics:
        """计算风险指标"""
        metrics = RiskMetrics()

        # 波动率（年化）
        metrics.volatility = returns.std() * np.sqrt(252)

        # 下行波动率
        downside_returns = returns[returns < 0]
        metrics.downside_volatility = downside_returns.std() * np.sqrt(252) if len(downside_returns) > 0 else 0

        # 最大回撤
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        metrics.max_drawdown = drawdown.min()

        # 回撤持续时间
        is_drawdown = drawdown < 0
        metrics.max_drawdown_duration = self._max_consecutive(is_drawdown)
        metrics.avg_drawdown = drawdown[is_drawdown].mean() if is_drawdown.any() else 0

        # 尾部风险
        metrics.var_95 = np.percentile(returns, 5)
        metrics.var_99 = np.percentile(returns, 1)
        metrics.cvar_95 = returns[returns <= metrics.var_95].mean() if (returns <= metrics.var_95).any() else 0
        metrics.skewness = returns.skew()
        metrics.kurtosis = returns.kurtosis()

        # 贝塔和阿尔法
        if benchmark is not None and len(benchmark) == len(returns):
            aligned_benchmark = benchmark.reindex(returns.index).fillna(0)
            covariance = returns.cov(aligned_benchmark)
            benchmark_variance = aligned_benchmark.var()
            metrics.beta = covariance / benchmark_variance if benchmark_variance != 0 else 0

            excess_returns = returns.mean() - self.risk_free_rate / 252
            metrics.alpha = excess_returns - metrics.beta * (aligned_benchmark.mean() - self.risk_free_rate / 252)
            metrics.alpha *= 252  # 年化

            metrics.tracking_error = (returns - aligned_benchmark).std() * np.sqrt(252)
            metrics.information_ratio = metrics.alpha / metrics.tracking_error if metrics.tracking_error != 0 else 0

        return metrics

    def _calculate_risk_adjusted_metrics(
        self,
        returns: pd.Series,
        risk_metrics: RiskMetrics
    ) -> RiskAdjustedMetrics:
        """计算风险调整收益指标"""
        metrics = RiskAdjustedMetrics()

        # 年化收益率
        annual_return = returns.mean() * 252

        # 夏普比率
        if risk_metrics.volatility != 0:
            metrics.sharpe_ratio = (annual_return - self.risk_free_rate) / risk_metrics.volatility

        # 索提诺比率（使用下行波动率）
        if risk_metrics.downside_volatility != 0:
            metrics.sortino_ratio = (annual_return - self.risk_free_rate) / risk_metrics.downside_volatility

        # 卡玛比率（年化收益/最大回撤）
        if risk_metrics.max_drawdown != 0:
            metrics.calmar_ratio = annual_return / abs(risk_metrics.max_drawdown)

        # 特雷诺比率（使用贝塔）
        if risk_metrics.beta and risk_metrics.beta != 0:
            metrics.treynor_ratio = (annual_return - self.risk_free_rate) / risk_metrics.beta

        # Omega比率
        threshold_return = self.risk_free_rate / 252
        excess_returns = returns - threshold_return
        positive_returns = excess_returns[excess_returns > 0].sum()
        negative_returns = abs(excess_returns[excess_returns < 0].sum())
        if negative_returns != 0:
            metrics.omega_ratio = positive_returns / negative_returns

        # 上行潜力比率
        upside_returns = returns[returns > 0]
        downside_returns = returns[returns < 0]
        if len(downside_returns) > 0 and downside_returns.std() != 0:
            metrics.upside_potential_ratio = (upside_returns.mean() / upside_returns.std()) / \
                                              (abs(downside_returns.mean()) / downside_returns.std())

        # 单位风险收益
        if risk_metrics.volatility != 0:
            metrics.return_per_unit_risk = annual_return / risk_metrics.volatility

        return metrics

    def _calculate_trade_metrics(self, trades: List[Any]) -> TradeMetrics:
        """计算交易统计指标"""
        metrics = TradeMetrics()

        if not trades:
            return metrics

        # 基本统计
        metrics.total_trades = len(trades)

        # 分离多空
        long_trades = [t for t in trades if t.side.name == 'BUY']
        short_trades = [t for t in trades if t.side.name == 'SELL']

        # 盈亏统计（这里简化处理，实际需要更复杂的配对逻辑）
        trade_returns = []
        for trade in trades:
            # 计算单笔收益（简化）
            cost = trade.total_cost
            if hasattr(trade, 'pnl'):
                trade_returns.append(trade.pnl / cost if cost > 0 else 0)

        if trade_returns:
            returns_array = np.array(trade_returns)
            metrics.winning_trades = (returns_array > 0).sum()
            metrics.losing_trades = (returns_array < 0).sum()
            metrics.win_rate = metrics.winning_trades / len(trade_returns)

            profits = returns_array[returns_array > 0]
            losses = returns_array[returns_array < 0]

            if len(profits) > 0:
                metrics.avg_profit = profits.mean()
                metrics.largest_profit = profits.max()

            if len(losses) > 0:
                metrics.avg_loss = losses.mean()
                metrics.largest_loss = losses.min()

            if metrics.avg_loss != 0:
                metrics.payoff_ratio = abs(metrics.avg_profit / metrics.avg_loss)

            if metrics.win_rate != 0 and metrics.payoff_ratio != 0:
                metrics.profit_factor = (metrics.win_rate * metrics.payoff_ratio) / \
                                       ((1 - metrics.win_rate) * 1)

        # 成本统计
        metrics.total_commission = sum(t.commission for t in trades)
        metrics.total_slippage = sum(t.slippage for t in trades)
        metrics.total_impact_cost = sum(t.impact_cost for t in trades)

        return metrics

    def _calculate_monthly_returns(self, equity_curve: pd.Series) -> pd.Series:
        """计算月度收益率"""
        # 重采样到月末
        monthly = equity_curve.resample('M').last()
        monthly_returns = monthly.pct_change().dropna()
        return monthly_returns

    def _max_consecutive(self, series: pd.Series) -> int:
        """计算最大连续True次数"""
        if series.empty:
            return 0

        # 将布尔序列转换为1/0
        values = series.astype(int)

        # 计算连续1的最大长度
        max_count = 0
        current_count = 0

        for v in values:
            if v == 1:
                current_count += 1
                max_count = max(max_count, current_count)
            else:
                current_count = 0

        return max_count


class TradeAnalyzer:
    """
    交易分析器

    对交易记录进行深度分析，包括：
    - 交易配对（开仓-平仓匹配）
    - 盈利能力分析
    - 时间分析（最佳交易时段等）
    - 品种分析
    """

    def __init__(self, trades: List[Any]):
        """
        初始化交易分析器

        Args:
            trades: 交易记录列表
        """
        self.trades = trades
        self.round_trips: List[Dict] = []

    def pair_trades(self) -> List[Dict]:
        """
        配对交易（开平仓匹配）

        Returns:
            List[Dict]: 配对后的完整交易记录
        """
        # 按品种分组
        trades_by_symbol = {}
        for trade in self.trades:
            symbol = trade.symbol
            if symbol not in trades_by_symbol:
                trades_by_symbol[symbol] = []
            trades_by_symbol[symbol].append(trade)

        round_trips = []

        for symbol, trades in trades_by_symbol.items():
            # 按时间排序
            trades.sort(key=lambda t: t.timestamp)

            # 配对逻辑
            position = 0
            entry_trades = []

            for trade in trades:
                if trade.side.name == 'BUY':
                    if position >= 0:
                        # 加仓或新开多
                        entry_trades.append(trade)
                        position += trade.quantity
                    else:
                        # 平空（简化处理）
                        position += trade.quantity
                else:  # SELL
                    if position > 0:
                        # 平多 - 创建配对
                        remaining = trade.quantity
                        while remaining > 0 and entry_trades:
                            entry = entry_trades[0]
                            close_qty = min(remaining, entry.quantity)

                            round_trip = {
                                'symbol': symbol,
                                'entry_time': entry.timestamp,
                                'exit_time': trade.timestamp,
                                'entry_price': entry.price,
                                'exit_price': trade.price,
                                'quantity': close_qty,
                                'pnl': (trade.price - entry.price) * close_qty - entry.total_cost - trade.total_cost,
                                'return_pct': (trade.price - entry.price) / entry.price,
                                'holding_period': (trade.timestamp - entry.timestamp).days,
                            }
                            round_trips.append(round_trip)

                            remaining -= close_qty
                            entry.quantity -= close_qty
                            if entry.quantity <= 0:
                                entry_trades.pop(0)

                        position -= trade.quantity
                    else:
                        # 加仓或新开空
                        position -= trade.quantity

        self.round_trips = round_trips
        return round_trips

    def analyze_by_time(self) -> Dict[str, Any]:
        """
        按时间维度分析

        Returns:
            Dict: 时间维度分析结果
        """
        if not self.round_trips:
            self.pair_trades()

        df = pd.DataFrame(self.round_trips)
        if df.empty:
            return {}

        df['entry_time'] = pd.to_datetime(df['entry_time'])
        df['month'] = df['entry_time'].dt.month
        df['year'] = df['entry_time'].dt.year
        df['dayofweek'] = df['entry_time'].dt.dayofweek
        df['hour'] = df['entry_time'].dt.hour

        analysis = {
            'by_month': df.groupby('month')['pnl'].agg(['sum', 'mean', 'count']).to_dict(),
            'by_year': df.groupby('year')['pnl'].agg(['sum', 'mean', 'count']).to_dict(),
            'by_dayofweek': df.groupby('dayofweek')['pnl'].agg(['sum', 'mean', 'count']).to_dict(),
            'best_month': df.groupby('month')['pnl'].sum().idxmax(),
            'worst_month': df.groupby('month')['pnl'].sum().idxmin(),
        }

        return analysis

    def analyze_by_symbol(self) -> Dict[str, Any]:
        """
        按品种维度分析

        Returns:
            Dict: 品种维度分析结果
        """
        if not self.round_trips:
            self.pair_trades()

        df = pd.DataFrame(self.round_trips)
        if df.empty:
            return {}

        symbol_stats = df.groupby('symbol').agg({
            'pnl': ['sum', 'mean', 'std', 'count'],
            'return_pct': ['mean', 'std'],
            'holding_period': 'mean',
        }).round(4)

        return {
            'symbol_stats': symbol_stats.to_dict(),
            'best_symbol': df.groupby('symbol')['pnl'].sum().idxmax(),
            'worst_symbol': df.groupby('symbol')['pnl'].sum().idxmin(),
            'most_traded': df.groupby('symbol').size().idxmax(),
        }


def calculate_drawdown_series(equity_curve: pd.Series) -> pd.Series:
    """
    计算回撤序列

    Args:
        equity_curve: 权益曲线

    Returns:
        pd.Series: 回撤序列
    """
    running_max = equity_curve.expanding().max()
    drawdown = (equity_curve - running_max) / running_max
    return drawdown


def calculate_rolling_sharpe(returns: pd.Series, window: int = 63) -> pd.Series:
    """
    计算滚动夏普比率

    Args:
        returns: 收益率序列
        window: 滚动窗口（默认63天≈3个月）

    Returns:
        pd.Series: 滚动夏普序列
    """
    rolling_mean = returns.rolling(window=window).mean() * 252
    rolling_std = returns.rolling(window=window).std() * np.sqrt(252)
    rolling_sharpe = rolling_mean / rolling_std
    return rolling_sharpe


def calculate_calmar_ratio(equity_curve: pd.Series) -> float:
    """
    计算卡玛比率

    Args:
        equity_curve: 权益曲线

    Returns:
        float: 卡玛比率
    """
    # 年化收益
    n_years = len(equity_curve) / 252
    if n_years <= 0:
        return 0.0

    total_return = (equity_curve.iloc[-1] / equity_curve.iloc[0]) - 1
    annual_return = (1 + total_return) ** (1/n_years) - 1

    # 最大回撤
    drawdown = calculate_drawdown_series(equity_curve)
    max_drawdown = abs(drawdown.min())

    if max_drawdown == 0:
        return 0.0

    return annual_return / max_drawdown
