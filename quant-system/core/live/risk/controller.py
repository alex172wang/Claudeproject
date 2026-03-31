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
