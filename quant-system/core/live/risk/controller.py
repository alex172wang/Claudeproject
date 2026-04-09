"""
风险控制模块

提供全面的风险管理功能，包括：
- 仓位风险控制
- 单日损失限制
- 波动率控制
- 流动性风险检查
"""

import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
import pandas as pd


class RiskLevel(Enum):
    """风险等级"""
    LOW = "low"           # 低风险
    MEDIUM = "medium"     # 中等风险
    HIGH = "high"         # 高风险
    CRITICAL = "critical" # 严重风险


class RiskType(Enum):
    """风险类型"""
    POSITION_SIZE = "position_size"       # 仓位大小
    DAILY_LOSS = "daily_loss"             # 日损失
    DRAWDOWN = "drawdown"                 # 回撤
    VOLATILITY = "volatility"             # 波动率
    CONCENTRATION = "concentration"       # 集中度
    LIQUIDITY = "liquidity"               # 流动性
    LEVERAGE = "leverage"                 # 杠杆


@dataclass
class RiskCheck:
    """风险检查结果"""
    rule_name: str
    risk_type: RiskType
    level: RiskLevel
    passed: bool
    message: str
    current_value: float
    limit_value: float
    timestamp: datetime = field(default_factory=datetime.now)


class RiskRule:
    """
    风控规则基类

    所有风控规则必须继承此类
    """

    def __init__(
        self,
        name: str,
        risk_type: RiskType,
        level: RiskLevel = RiskLevel.MEDIUM,
        enabled: bool = True,
    ):
        self.name = name
        self.risk_type = risk_type
        self.level = level
        self.enabled = enabled

    def check(self, context: Dict[str, Any]) -> RiskCheck:
        """
        执行风控检查

        Args:
            context: 检查上下文数据

        Returns:
            RiskCheck: 检查结果
        """
        raise NotImplementedError

    def enable(self):
        """启用规则"""
        self.enabled = True

    def disable(self):
        """禁用规则"""
        self.enabled = False


class PositionSizeRule(RiskRule):
    """仓位大小风控规则"""

    def __init__(
        self,
        max_position_value: float,
        max_single_position_pct: float = 0.2,
    ):
        super().__init__(
            name="Position Size Limit",
            risk_type=RiskType.POSITION_SIZE,
            level=RiskLevel.HIGH,
        )
        self.max_position_value = max_position_value
        self.max_single_position_pct = max_single_position_pct

    def check(self, context: Dict[str, Any]) -> RiskCheck:
        """检查仓位大小"""
        positions = context.get('positions', [])
        total_value = sum(p.get('market_value', 0) for p in positions)

        # 检查总仓位
        if total_value > self.max_position_value:
            return RiskCheck(
                rule_name=self.name,
                risk_type=self.risk_type,
                level=self.level,
                passed=False,
                message=f"Total position value {total_value:.2f} exceeds limit {self.max_position_value:.2f}",
                current_value=total_value,
                limit_value=self.max_position_value,
            )

        # 检查单个仓位
        portfolio_value = context.get('portfolio_value', total_value)
        for pos in positions:
            pos_value = pos.get('market_value', 0)
            pos_pct = pos_value / portfolio_value if portfolio_value > 0 else 0
            if pos_pct > self.max_single_position_pct:
                return RiskCheck(
                    rule_name=self.name,
                    risk_type=self.risk_type,
                    level=self.level,
                    passed=False,
                    message=f"Position {pos.get('symbol')} {pos_pct:.2%} exceeds limit {self.max_single_position_pct:.2%}",
                    current_value=pos_pct,
                    limit_value=self.max_single_position_pct,
                )

        return RiskCheck(
            rule_name=self.name,
            risk_type=self.risk_type,
            level=RiskLevel.LOW,
            passed=True,
            message="Position size check passed",
            current_value=total_value,
            limit_value=self.max_position_value,
        )


class DailyLossRule(RiskRule):
    """日损失风控规则"""

    def __init__(self, max_daily_loss_pct: float = 0.05):
        super().__init__(
            name="Daily Loss Limit",
            risk_type=RiskType.DAILY_LOSS,
            level=RiskLevel.CRITICAL,
        )
        self.max_daily_loss_pct = max_daily_loss_pct

    def check(self, context: Dict[str, Any]) -> RiskCheck:
        """检查日损失"""
        daily_pnl = context.get('daily_pnl', 0)
        portfolio_value = context.get('portfolio_value', 1)

        daily_loss_pct = abs(daily_pnl) / portfolio_value if portfolio_value > 0 else 0

        if daily_loss_pct > self.max_daily_loss_pct:
            return RiskCheck(
                rule_name=self.name,
                risk_type=self.risk_type,
                level=self.level,
                passed=False,
                message=f"Daily loss {daily_loss_pct:.2%} exceeds limit {self.max_daily_loss_pct:.2%}",
                current_value=daily_loss_pct,
                limit_value=self.max_daily_loss_pct,
            )

        return RiskCheck(
            rule_name=self.name,
            risk_type=self.risk_type,
            level=RiskLevel.LOW,
            passed=True,
            message="Daily loss check passed",
            current_value=daily_loss_pct,
            limit_value=self.max_daily_loss_pct,
        )


class TrailingStopRule(RiskRule):
    """
    跟踪止损规则

    跟随持仓的最大盈利，当从高点回撤超过阈值时触发止损。
    专为趋势跟踪设计，避免固定止损被正常波动洗出。
    """

    def __init__(
        self,
        max_drawback_pct: float = 0.15,  # 从高点回撤15%止损
        lookback_days: int = 20,  # 计算高点的时间窗口
    ):
        super().__init__(
            name="Trailing Stop",
            risk_type=RiskType.DRAWDOWN,
            level=RiskLevel.HIGH,
        )
        self.max_drawback_pct = max_drawback_pct
        self.lookback_days = lookback_days
        # 记录每只持仓的最高价
        self._high_prices: Dict[str, float] = {}
        self._entry_prices: Dict[str, float] = {}

    def check(self, context: Dict[str, Any]) -> RiskCheck:
        """检查跟踪止损"""
        positions = context.get('positions', [])
        price_data = context.get('price_data', {})  # {symbol: {current, high, low, entry}}

        if not positions:
            return RiskCheck(
                rule_name=self.name,
                risk_type=self.risk_type,
                level=RiskLevel.LOW,
                passed=True,
                message="No positions to check trailing stop",
                current_value=0.0,
                limit_value=self.max_drawback_pct,
            )

        worst_drawback = 0.0
        triggered_symbol = None

        for pos in positions:
            symbol = pos.get('symbol', '')
            if not symbol:
                continue

            current_price = price_data.get(symbol, {}).get('current', pos.get('current_price', 0))
            if current_price <= 0:
                continue

            # 更新高点记录
            if symbol not in self._high_prices:
                self._high_prices[symbol] = current_price
                self._entry_prices[symbol] = pos.get('entry_price', current_price)

            if current_price > self._high_prices[symbol]:
                self._high_prices[symbol] = current_price

            # 计算从高点的回撤
            high_price = self._high_prices[symbol]
            drawback = (high_price - current_price) / high_price if high_price > 0 else 0

            # 计算总体盈亏（从入场价）
            entry_price = self._entry_prices[symbol]
            profit_pct = (current_price - entry_price) / entry_price if entry_price > 0 else 0

            # 只有盈利时检查回撤（亏损时按固定止损处理）
            if profit_pct > 0 and drawback > worst_drawback:
                worst_drawback = drawback
                if drawback > self.max_drawback_pct:
                    triggered_symbol = symbol

        if triggered_symbol:
            return RiskCheck(
                rule_name=self.name,
                risk_type=self.risk_type,
                level=self.level,
                passed=False,
                message=f"Trailing stop triggered for {triggered_symbol}: {worst_drawback:.2%} drawdown from high",
                current_value=worst_drawback,
                limit_value=self.max_drawback_pct,
            )

        return RiskCheck(
            rule_name=self.name,
            risk_type=self.risk_type,
            level=RiskLevel.LOW,
            passed=True,
            message=f"Trailing stop check passed, worst drawdown: {worst_drawback:.2%}",
            current_value=worst_drawback,
            limit_value=self.max_drawback_pct,
        )

    def reset(self, symbol: str = None):
        """重置高点记录"""
        if symbol:
            self._high_prices.pop(symbol, None)
            self._entry_prices.pop(symbol, None)
        else:
            self._high_prices.clear()
            self._entry_prices.clear()


class OvernightRiskRule(RiskRule):
    """
    隔夜/周末风险规则

    检查持仓是否适合隔夜持仓，尤其是周五和节假日前。
    主要针对QDII类ETF（恒生、标普等）可能受海外市场影响。
    """

    def __init__(
        self,
        friday_reduce_pct: float = 0.5,  # 周五降低50%仓位
        qdii_symbols: List[str] = None,  # QDII ETF列表
    ):
        super().__init__(
            name="Overnight/Weekend Risk",
            risk_type=RiskType.VOLATILITY,
            level=RiskLevel.MEDIUM,
        )
        self.friday_reduce_pct = friday_reduce_pct
        self.qdii_symbols = qdii_symbols or ['159920', '513500', '159941', '513100']  # 恒生、标普、纳指、德国

    def check(self, context: Dict[str, Any]) -> RiskCheck:
        """检查隔夜风险"""
        positions = context.get('positions', [])
        current_date = context.get('current_date')

        if not positions:
            return RiskCheck(
                rule_name=self.name,
                risk_type=self.risk_type,
                level=RiskLevel.LOW,
                passed=True,
                message="No positions to check overnight risk",
                current_value=0.0,
                limit_value=0.0,
            )

        # 检查是否是周五
        is_friday = False
        if current_date:
            is_friday = current_date.weekday() == 4  # Monday=0, Friday=4

        # 检查是否持有QDII
        has_qdii = any(
            pos.get('symbol', '') in self.qdii_symbols
            for pos in positions
        )

        # 检查是否有大量持仓
        total_value = sum(pos.get('market_value', 0) for pos in positions)
        portfolio_value = context.get('portfolio_value', total_value)
        position_ratio = total_value / portfolio_value if portfolio_value > 0 else 0

        # 风险评分
        risk_score = 0.0

        if is_friday:
            risk_score += 0.3
            if has_qdii:
                risk_score += 0.4  # 周五+QDII，风险较高

        if position_ratio > 0.8:  # 仓位过重
            risk_score += 0.3

        if risk_score >= 0.5:
            return RiskCheck(
                rule_name=self.name,
                risk_type=self.risk_type,
                level=RiskLevel.HIGH,
                passed=False,
                message=f"High weekend risk: friday={is_friday}, qdii={has_qdii}, position_ratio={position_ratio:.1%}",
                current_value=risk_score,
                limit_value=0.5,
            )

        return RiskCheck(
            rule_name=self.name,
            risk_type=self.risk_type,
            level=RiskLevel.LOW,
            passed=True,
            message="Weekend risk acceptable",
            current_value=risk_score,
            limit_value=0.5,
        )


class HolidayRiskRule(RiskRule):
    """
    长假风险暴露规则

    在A股长假（春节、国庆）前，检查QDII类ETF的仓位。
    长假期间海外市场正常交易，QDII可能大幅波动。
    """

    # A股长假日期（大致，每年需更新）
    LONG_HOLIDAYS = [
        # 春节（大约1月底-2月中）
        {'name': '春节', 'days_before': 2},
        # 国庆（10月1-7日）
        {'name': '国庆', 'days_before': 2},
    ]

    def __init__(
        self,
        days_before_holiday: int = 2,  # 假日前几天开始预警
        qdii_symbols: List[str] = None,
        max_qdii_position_pct: float = 0.15,  # 长假期间QDII最大仓位15%
    ):
        super().__init__(
            name="Holiday Risk Exposure",
            risk_type=RiskType.CONCENTRATION,
            level=RiskLevel.MEDIUM,
        )
        self.days_before_holiday = days_before_holiday
        self.qdii_symbols = qdii_symbols or ['159920', '513500', '159941', '513100']
        self.max_qdii_position_pct = max_qdii_position_pct

    def check(self, context: Dict[str, Any]) -> RiskCheck:
        """检查长假风险"""
        positions = context.get('positions', [])
        current_date = context.get('current_date')

        if not positions:
            return RiskCheck(
                rule_name=self.name,
                risk_type=self.risk_type,
                level=RiskLevel.LOW,
                passed=True,
                message="No positions to check",
                current_value=0.0,
                limit_value=self.max_qdii_position_pct,
            )

        # 检查是否接近长假
        is_near_holiday = self._is_near_holiday(current_date)

        if not is_near_holiday:
            return RiskCheck(
                rule_name=self.name,
                risk_type=self.risk_type,
                level=RiskLevel.LOW,
                passed=True,
                message="No holiday risk currently",
                current_value=0.0,
                limit_value=self.max_qdii_position_pct,
            )

        # 计算QDII仓位占比
        total_value = sum(pos.get('market_value', 0) for pos in positions)
        qdii_value = sum(
            pos.get('market_value', 0)
            for pos in positions
            if pos.get('symbol', '') in self.qdii_symbols
        )

        portfolio_value = context.get('portfolio_value', total_value)
        qdii_pct = qdii_value / portfolio_value if portfolio_value > 0 else 0

        if qdii_pct > self.max_qdii_position_pct:
            holiday_name = self._get_approaching_holiday(current_date)
            return RiskCheck(
                rule_name=self.name,
                risk_type=self.risk_type,
                level=self.level,
                passed=False,
                message=f"{holiday_name} approaching: QDII position {qdii_pct:.1%} exceeds limit {self.max_qdii_position_pct:.1%}",
                current_value=qdii_pct,
                limit_value=self.max_qdii_position_pct,
            )

        return RiskCheck(
            rule_name=self.name,
            risk_type=self.risk_type,
            level=RiskLevel.LOW,
            passed=True,
            message="Holiday risk acceptable",
            current_value=qdii_pct,
            limit_value=self.max_qdii_position_pct,
        )

    def _is_near_holiday(self, current_date) -> bool:
        """检查是否接近长假"""
        if current_date is None:
            return False

        for holiday in self.LONG_HOLIDAYS:
            days_before = holiday.get('days_before', 2)
            # 简化判断：检查是否在节假日附近
            # 实际应用中应该用更精确的日历
            month = current_date.month
            day = current_date.day

            # 国庆：9月最后一周到10月第一周
            if month == 9 and day >= 25:
                return True
            if month == 10 and day <= 7:
                return True

            # 春节：大致1月底到2月中
            if month == 1 and day >= 20:
                return True
            if month == 2 and day <= 15:
                return True

        return False

    def _get_approaching_holiday(self, current_date) -> str:
        """获取即将到来的假期名称"""
        if current_date is None:
            return "Holiday"

        month = current_date.month

        if month in [9, 10]:
            return "国庆节"
        if month in [1, 2]:
            return "春节"

        return "长假"


class TrendConsistencyRule(RiskRule):
    """
    趋势一致性预警规则

    当多个持仓ETF的L1评分同时恶化时，可能预示系统性风险。
    适用于大趋势策略，因为趋势反转通常是群体性的。
    """

    def __init__(
        self,
        min_holding_count: int = 3,  # 最少持仓数量才检查
        score_threshold: float = 40.0,  # 评分低于此值视为恶化
        simultaneous_threshold: float = 0.6,  # 60%以上持仓恶化则预警
    ):
        super().__init__(
            name="Trend Consistency",
            risk_type=RiskType.VOLATILITY,
            level=RiskLevel.HIGH,
        )
        self.min_holding_count = min_holding_count
        self.score_threshold = score_threshold
        self.simultaneous_threshold = simultaneous_threshold

    def check(self, context: Dict[str, Any]) -> RiskCheck:
        """检查趋势一致性"""
        positions = context.get('positions', [])
        scores = context.get('l1_scores', {})  # {symbol: score}

        if len(positions) < self.min_holding_count:
            return RiskCheck(
                rule_name=self.name,
                risk_type=self.risk_type,
                level=RiskLevel.LOW,
                passed=True,
                message=f"Only {len(positions)} positions, not enough for trend check",
                current_value=len(positions),
                limit_value=self.min_holding_count,
            )

        if not scores:
            return RiskCheck(
                rule_name=self.name,
                risk_type=self.risk_type,
                level=RiskLevel.LOW,
                passed=True,
                message="No L1 scores available",
                current_value=0.0,
                limit_value=self.simultaneous_threshold,
            )

        # 计算有多少持仓的L1评分低于阈值
        deteriorating = 0
        deteriorating_symbols = []

        for pos in positions:
            symbol = pos.get('symbol', '')
            score = scores.get(symbol, 50.0)

            if score < self.score_threshold:
                deteriorating += 1
                deteriorating_symbols.append(f"{symbol}({score:.0f})")

        ratio = deteriorating / len(positions) if positions else 0

        if ratio >= self.simultaneous_threshold:
            return RiskCheck(
                rule_name=self.name,
                risk_type=self.risk_type,
                level=self.level,
                passed=False,
                message=f"Systemic risk: {deteriorating}/{len(positions)} holdings L1<{self.score_threshold}: {', '.join(deteriorating_symbols[:3])}",
                current_value=ratio,
                limit_value=self.simultaneous_threshold,
            )

        return RiskCheck(
            rule_name=self.name,
            risk_type=self.risk_type,
            level=RiskLevel.LOW,
            passed=True,
            message=f"Trend consistency OK: {deteriorating}/{len(positions)} deteriorating",
            current_value=ratio,
            limit_value=self.simultaneous_threshold,
        )


class VolatilityAnomalyRule(RiskRule):
    """
    波动率异常预警规则

    当市场波动率异常放大时预警，建议降低仓位。
    使用持仓ETF的20日波动率与历史平均波动率对比。
    """

    def __init__(
        self,
        volatility_lookback: int = 20,  # 计算波动率的窗口
        anomaly_multiplier: float = 2.0,  # 波动率超过历史均值2倍则预警
        historical_months: int = 3,  # 历史波动率参考期（月）
    ):
        super().__init__(
            name="Volatility Anomaly",
            risk_type=RiskType.VOLATILITY,
            level=RiskLevel.MEDIUM,
        )
        self.volatility_lookback = volatility_lookback
        self.anomaly_multiplier = anomaly_multiplier
        self.historical_months = historical_months
        self._historical_volatility: float = 0.0

    def check(self, context: Dict[str, Any]) -> RiskCheck:
        """检查波动率异常"""
        positions = context.get('positions', [])
        price_data = context.get('price_data', {})  # {symbol: DataFrame with prices}

        if not positions:
            return RiskCheck(
                rule_name=self.name,
                risk_type=self.risk_type,
                level=RiskLevel.LOW,
                passed=True,
                message="No positions to check",
                current_value=0.0,
                limit_value=self.anomaly_multiplier,
            )

        # 计算当前持仓的加权波动率
        total_value = sum(pos.get('market_value', 0) for pos in positions)
        weighted_volatility = 0.0

        for pos in positions:
            symbol = pos.get('symbol', '')
            pos_value = pos.get('market_value', 0)
            weight = pos_value / total_value if total_value > 0 else 0

            # 计算该品种的20日波动率
            volatility = self._calculate_volatility(symbol, price_data)
            weighted_volatility += volatility * weight

        # 如果没有历史波动率数据，用当前值初始化
        if self._historical_volatility <= 0:
            self._historical_volatility = weighted_volatility
            return RiskCheck(
                rule_name=self.name,
                risk_type=self.risk_type,
                level=RiskLevel.LOW,
                passed=True,
                message="Volatility baseline initialized",
                current_value=1.0,
                limit_value=self.anomaly_multiplier,
            )

        # 计算波动率比率
        vol_ratio = weighted_volatility / self._historical_volatility if self._historical_volatility > 0 else 1.0

        # 更新历史波动率（使用指数移动平均）
        self._historical_volatility = 0.9 * self._historical_volatility + 0.1 * weighted_volatility

        if vol_ratio > self.anomaly_multiplier:
            return RiskCheck(
                rule_name=self.name,
                risk_type=self.risk_type,
                level=self.level,
                passed=False,
                message=f"Volatility anomaly: current {weighted_volatility:.2%} vs baseline {self._historical_volatility:.2%} ({vol_ratio:.1f}x)",
                current_value=vol_ratio,
                limit_value=self.anomaly_multiplier,
            )

        return RiskCheck(
            rule_name=self.name,
            risk_type=self.risk_type,
            level=RiskLevel.LOW,
            passed=True,
            message=f"Volatility normal: {vol_ratio:.2f}x baseline",
            current_value=vol_ratio,
            limit_value=self.anomaly_multiplier,
        )

    def _calculate_volatility(self, symbol: str, price_data: Dict) -> float:
        """计算某品种的波动率"""
        if symbol not in price_data:
            return 0.15  # 默认15%年化波动率

        df_or_series = price_data[symbol]
        if hasattr(df_or_series, 'get') and hasattr(df_or_series.get('close', pd.Series()), 'pct_change'):
            data = df_or_series.get('close', pd.Series())
        elif hasattr(df_or_series, 'close'):
            data = df_or_series.close
        elif hasattr(df_or_series, 'get'):
            data = df_or_series.get('close')
        else:
            return 0.15

        if len(data) < self.volatility_lookback:
            return 0.15

        returns = data.pct_change().dropna()
        recent_returns = returns[-self.volatility_lookback:]

        # 年化波动率
        volatility = recent_returns.std() * (252 ** 0.5)
        return volatility if volatility > 0 else 0.15

    def reset_baseline(self):
        """重置波动率基准"""
        self._historical_volatility = 0.0


class RiskController:
    """
    风险控制主控制器

    管理所有风控规则，执行统一的风险检查。
    """

    def __init__(self):
        self._rules: Dict[str, RiskRule] = {}
        self._check_history: List[RiskCheck] = []
        self._lock = threading.RLock()
        self._emergency_callbacks: List[Callable[[RiskCheck], None]] = []

    def add_rule(self, rule: RiskRule) -> None:
        """添加风控规则"""
        self._rules[rule.name] = rule

    def remove_rule(self, name: str) -> bool:
        """移除风控规则"""
        if name in self._rules:
            del self._rules[name]
            return True
        return False

    def get_rule(self, name: str) -> Optional[RiskRule]:
        """获取风控规则"""
        return self._rules.get(name)

    def check_all(self, context: Dict[str, Any]) -> List[RiskCheck]:
        """
        执行所有风控检查

        Args:
            context: 检查上下文

        Returns:
            List[RiskCheck]: 所有检查结果
        """
        results = []

        for rule in self._rules.values():
            if not rule.enabled:
                continue

            try:
                result = rule.check(context)
                results.append(result)

                # 保存到历史
                with self._lock:
                    self._check_history.append(result)

                # 触发紧急回调
                if not result.passed and result.level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
                    self._trigger_emergency(result)

            except Exception as e:
                print(f"[RiskController] Rule {rule.name} check error: {e}")

        return results

    def can_trade(self, context: Dict[str, Any]) -> bool:
        """
        检查是否可以交易

        如果有高风险或严重风险未通过，则禁止交易
        """
        results = self.check_all(context)

        for result in results:
            if not result.passed and result.level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
                return False

        return True

    def _trigger_emergency(self, check: RiskCheck) -> None:
        """触发紧急处理"""
        for callback in self._emergency_callbacks:
            try:
                callback(check)
            except Exception as e:
                print(f"[RiskController] Emergency callback error: {e}")

    def add_emergency_callback(self, callback: Callable[[RiskCheck], None]) -> None:
        """添加紧急处理回调"""
        self._emergency_callbacks.append(callback)

    def get_check_history(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[RiskCheck]:
        """获取检查历史"""
        with self._lock:
            history = self._check_history.copy()

        if start_time:
            history = [h for h in history if h.timestamp >= start_time]
        if end_time:
            history = [h for h in history if h.timestamp <= end_time]

        # 按时间倒序
        history = sorted(history, key=lambda h: h.timestamp, reverse=True)
        return history[:limit]

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            history = self._check_history.copy()

        if not history:
            return {
                'total_checks': 0,
                'passed': 0,
                'failed': 0,
                'by_level': {},
            }

        passed = sum(1 for h in history if h.passed)
        failed = len(history) - passed

        by_level = {}
        for h in history:
            level = h.level.value
            if level not in by_level:
                by_level[level] = {'total': 0, 'passed': 0, 'failed': 0}
            by_level[level]['total'] += 1
            if h.passed:
                by_level[level]['passed'] += 1
            else:
                by_level[level]['failed'] += 1

        return {
            'total_checks': len(history),
            'passed': passed,
            'failed': failed,
            'by_level': by_level,
        }

    def clear_history(self, before: Optional[datetime] = None) -> int:
        """清除历史记录"""
        with self._lock:
            if before is None:
                count = len(self._check_history)
                self._check_history.clear()
            else:
                to_remove = [h for h in self._check_history if h.timestamp < before]
                for h in to_remove:
                    self._check_history.remove(h)
                count = len(to_remove)

            return count

    # ========== 便捷方法 ==========

    def add_trend_following_rules(
        self,
        max_drawback_pct: float = 0.15,
        friday_reduce_pct: float = 0.5,
        qdii_symbols: List[str] = None,
    ) -> None:
        """
        添加趋势跟踪专用风控规则集

        Args:
            max_drawback_pct: 跟踪止损回撤阈值
            friday_reduce_pct: 周五仓位降低比例
            qdii_symbols: QDII ETF代码列表
        """
        self.add_rule(TrailingStopRule(max_drawback_pct=max_drawback_pct))
        self.add_rule(OvernightRiskRule(
            friday_reduce_pct=friday_reduce_pct,
            qdii_symbols=qdii_symbols,
        ))
        self.add_rule(HolidayRiskRule(qdii_symbols=qdii_symbols))
        self.add_rule(TrendConsistencyRule())
        self.add_rule(VolatilityAnomalyRule())

    def get_active_alerts(self) -> List[RiskCheck]:
        """
        获取当前未通过的风控检查（用于告警）

        Returns:
            List[RiskCheck]: 未通过的检查列表
        """
        with self._lock:
            return [
                h for h in self._check_history
                if not h.passed
            ]

    def get_risk_report(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成完整风险报告

        Args:
            context: 检查上下文

        Returns:
            Dict: 风险报告
        """
        results = self.check_all(context)

        # 分类结果
        passed = [r for r in results if r.passed]
        failed = [r for r in results if not r.passed]

        # 按等级分类
        by_level = {}
        for r in results:
            level_name = r.level.value
            if level_name not in by_level:
                by_level[level_name] = []
            by_level[level_name].append({
                'rule': r.rule_name,
                'message': r.message,
                'risk_type': r.risk_type.value,
            })

        # 严重风险
        critical = [r for r in failed if r.level == RiskLevel.CRITICAL]
        high_risk = [r for r in failed if r.level == RiskLevel.HIGH]

        return {
            'timestamp': datetime.now().isoformat(),
            'can_trade': len(critical) == 0 and len(high_risk) == 0,
            'total_rules': len(results),
            'passed': len(passed),
            'failed': len(failed),
            'critical_count': len(critical),
            'high_risk_count': len(high_risk),
            'critical_alerts': [
                {'rule': r.rule_name, 'message': r.message}
                for r in critical
            ],
            'high_risk_alerts': [
                {'rule': r.rule_name, 'message': r.message}
                for r in high_risk
            ],
            'all_alerts_by_level': by_level,
            'statistics': self.get_statistics(),
        }
