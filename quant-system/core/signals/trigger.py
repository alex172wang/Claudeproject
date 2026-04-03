"""
策略触发规则模块

根据策略类型（轮动/永久组合/主题）和合成信号，生成具体的交易触发规则
"""

from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from abc import ABC, abstractmethod
import numpy as np
import pandas as pd

from .composer import ComposedSignal, SignalComposer


class ActionType(Enum):
    """交易动作类型"""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    REBALANCE = "rebalance"
    RISK_ALERT = "risk_alert"


class TriggerReason(Enum):
    """触发原因"""
    SCORE_THRESHOLD = "score_threshold"  # 得分阈值
    RANK_CHANGE = "rank_change"  # 排名变化
    HOLDING_PERIOD = "holding_period"  # 持有期满
    REBALANCE_BAND = "rebalance_band"  # 再平衡带宽
    RISK_THRESHOLD = "risk_threshold"  # 风险阈值
    STOP_LOSS = "stop_loss"  # 止损


@dataclass
class TradeInstruction:
    """交易指令"""
    action: ActionType
    etf_code: str
    etf_name: str = ""
    target_weight: float = 0.0  # 目标权重
    current_weight: float = 0.0  # 当前权重
    quantity: int = 0  # 数量
    estimated_price: float = 0.0  # 预估价格
    estimated_amount: float = 0.0  # 预估金额

    # 触发信息
    trigger_reason: TriggerReason = TriggerReason.SCORE_THRESHOLD
    trigger_score: float = 0.0

    # 时间戳
    timestamp: datetime = field(default_factory=datetime.now)

    # 附加信息
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'action': self.action.value,
            'etf_code': self.etf_code,
            'etf_name': self.etf_name,
            'target_weight': round(self.target_weight, 4),
            'current_weight': round(self.current_weight, 4),
            'quantity': self.quantity,
            'estimated_price': round(self.estimated_price, 4),
            'estimated_amount': round(self.estimated_amount, 2),
            'trigger_reason': self.trigger_reason.value,
            'trigger_score': round(self.trigger_score, 2),
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata,
        }


@dataclass
class TriggerResult:
    """触发结果"""
    should_trigger: bool = False
    instructions: List[TradeInstruction] = field(default_factory=list)

    # 触发信息
    trigger_reasons: List[TriggerReason] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'should_trigger': self.should_trigger,
            'instructions': [i.to_dict() for i in self.instructions],
            'trigger_reasons': [r.value for r in self.trigger_reasons],
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata,
        }


class StrategyTrigger(ABC):
    """策略触发器基类"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化策略触发器

        Args:
            config: 配置字典
        """
        self.config = config or {}
        self._validate_config()

    def _validate_config(self) -> None:
        """验证配置，子类可覆盖"""
        pass

    @abstractmethod
    def should_trigger(self,
                      current_signals: List[ComposedSignal],
                      current_portfolio: Optional[Dict[str, float]] = None,
                      last_signals: Optional[List[ComposedSignal]] = None,
                      **kwargs) -> TriggerResult:
        """
        判断是否触发交易

        Args:
            current_signals: 当前信号列表
            current_portfolio: 当前持仓（ETF代码: 权重）
            last_signals: 上一次信号列表
            **kwargs: 其他参数

        Returns:
            TriggerResult: 触发结果
        """
        pass

    def _get_top_n_signals(self,
                          signals: List[ComposedSignal],
                          n: int,
                          min_score: float = 0.0) -> List[ComposedSignal]:
        """
        获取前N个信号

        Args:
            signals: 信号列表
            n: 数量
            min_score: 最低分数要求

        Returns:
            List[ComposedSignal]: 前N个信号
        """
        filtered = [s for s in signals if s.weighted_score >= min_score]
        sorted_signals = sorted(filtered, key=lambda x: x.weighted_score, reverse=True)
        return sorted_signals[:n]


class RotationTrigger(StrategyTrigger):
    """ETF轮动策略触发器

    适用于ETF轮动策略，定期选择得分最高的N个品种
    """

    DEFAULT_CONFIG = {
        'top_n': 1,  # 选择前N个
        'min_hold_days': 5,  # 最小持有天数
        'score_threshold': 45.0,  # 最低得分阈值
        'rank_change_threshold': 2,  # 排名变化阈值
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化轮动策略触发器

        Args:
            config: 配置字典，可包含top_n, min_hold_days, score_threshold等
        """
        merged_config = {**self.DEFAULT_CONFIG, **(config or {})}
        super().__init__(merged_config)

        self.top_n = self.config['top_n']
        self.min_hold_days = self.config['min_hold_days']
        self.score_threshold = self.config['score_threshold']
        self.rank_change_threshold = self.config['rank_change_threshold']

    def should_trigger(self,
                      current_signals: List[ComposedSignal],
                      current_portfolio: Optional[Dict[str, float]] = None,
                      last_signals: Optional[List[ComposedSignal]] = None,
                      **kwargs) -> TriggerResult:
        """
        判断是否触发轮动交易

        逻辑：
        1. 选出当前得分最高的top_n个品种
        2. 与当前持仓对比
        3. 如果不同且满足最小持有期，则触发调仓
        """
        result = TriggerResult()
        result.timestamp = datetime.now()

        current_portfolio = current_portfolio or {}

        # 获取当前Top N
        top_signals = self._get_top_n_signals(
            current_signals,
            self.top_n,
            self.score_threshold
        )

        if not top_signals:
            result.should_trigger = False
            result.metadata['reason'] = '没有符合条件的品种'
            return result

        # 获取当前持仓的ETF代码
        current_holdings = set(current_portfolio.keys())
        target_holdings = set(s.etf_code for s in top_signals)

        # 检查是否需要调仓
        if current_holdings == target_holdings:
            result.should_trigger = False
            result.metadata['reason'] = '持仓与目标一致，无需调仓'
            return result

        # 检查排名变化（避免过于频繁的调仓）
        if last_signals and self._check_rank_stability(
            current_signals, last_signals):
            result.should_trigger = False
            result.metadata['reason'] = '排名变化在阈值范围内，保持稳定'
            return result

        # 生成交易指令
        instructions = self._generate_rotation_instructions(
            top_signals, current_portfolio, current_signals
        )

        result.should_trigger = True
        result.instructions = instructions
        result.trigger_reasons = [TriggerReason.RANK_CHANGE]
        result.metadata['target_holdings'] = list(target_holdings)
        result.metadata['current_holdings'] = list(current_holdings)

        return result

    def _check_rank_stability(self,
                             current_signals: List[ComposedSignal],
                             last_signals: List[ComposedSignal]) -> bool:
        """
        检查排名是否稳定

        Returns:
            bool: 如果排名变化在阈值内返回True
        """
        # 获取当前的Top N
        current_top = set(s.etf_code for s in current_signals[:self.top_n])

        # 获取上一次的Top N
        last_top = set(s.etf_code for s in last_signals[:self.top_n])

        # 计算差异
        diff = current_top.symmetric_difference(last_top)

        # 如果差异小于阈值，认为是稳定的
        return len(diff) <= self.rank_change_threshold

    def _generate_rotation_instructions(
        self,
        target_signals: List[ComposedSignal],
        current_portfolio: Dict[str, float],
        all_signals: List[ComposedSignal]
    ) -> List[TradeInstruction]:
        """生成轮动交易指令"""
        instructions = []

        target_codes = set(s.etf_code for s in target_signals)
        current_codes = set(current_portfolio.keys())

        # 需要卖出的
        for code in current_codes - target_codes:
            instruction = TradeInstruction(
                action=ActionType.SELL,
                etf_code=code,
                current_weight=current_portfolio.get(code, 0),
                target_weight=0,
                trigger_reason=TriggerReason.RANK_CHANGE,
            )
            instructions.append(instruction)

        # 需要买入的
        for signal in target_signals:
            code = signal.etf_code
            if code not in current_codes:
                instruction = TradeInstruction(
                    action=ActionType.BUY,
                    etf_code=code,
                    etf_name=signal.etf_name,
                    target_weight=1.0 / len(target_signals),  # 等权
                    trigger_reason=TriggerReason.RANK_CHANGE,
                    trigger_score=signal.weighted_score,
                )
                instructions.append(instruction)

        return instructions


class PermanentPortfolioTrigger(StrategyTrigger):
    """永久组合策略触发器

    适用于永久组合等资产配置策略，基于目标权重进行再平衡
    """

    DEFAULT_CONFIG = {
        'rebalance_band': 0.05,  # 再平衡带宽（偏离超过此值触发）
        'min_hold_days': 20,  # 最小持有天数
        'target_weights': {},  # 目标权重
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化永久组合策略触发器

        Args:
            config: 配置字典
        """
        merged_config = {**self.DEFAULT_CONFIG, **(config or {})}
        super().__init__(merged_config)

        self.rebalance_band = self.config['rebalance_band']
        self.min_hold_days = self.config['min_hold_days']
        self.target_weights = self.config.get('target_weights', {})

    def should_trigger(self,
                      current_signals: List[ComposedSignal],
                      current_portfolio: Optional[Dict[str, float]] = None,
                      last_signals: Optional[List[ComposedSignal]] = None,
                      **kwargs) -> TriggerResult:
        """
        判断是否触发再平衡

        逻辑：
        1. 检查各品种的当前权重与目标权重的偏离
        2. 如果偏离超过rebalance_band，则触发再平衡
        """
        result = TriggerResult()
        result.timestamp = datetime.now()

        current_portfolio = current_portfolio or {}

        # 如果没有目标权重，无法触发
        if not self.target_weights:
            result.should_trigger = False
            result.metadata['reason'] = '没有设置目标权重'
            return result

        # 检查权重偏离
        deviations = []
        for etf_code, target_weight in self.target_weights.items():
            current_weight = current_portfolio.get(etf_code, 0)
            deviation = abs(current_weight - target_weight)
            deviations.append({
                'etf_code': etf_code,
                'target': target_weight,
                'current': current_weight,
                'deviation': deviation,
            })

        # 找出偏离超过阈值的品种
        rebalance_needed = [d for d in deviations if d['deviation'] > self.rebalance_band]

        if not rebalance_needed:
            result.should_trigger = False
            result.metadata['reason'] = '权重偏离在阈值范围内，无需再平衡'
            result.metadata['max_deviation'] = max([d['deviation'] for d in deviations]) if deviations else 0
            return result

        # 生成再平衡指令
        instructions = self._generate_rebalance_instructions(
            deviations, current_portfolio, current_signals
        )

        result.should_trigger = True
        result.instructions = instructions
        result.trigger_reasons = [TriggerReason.REBALANCE_BAND]
        result.metadata['rebalance_count'] = len(rebalance_needed)
        result.metadata['deviations'] = deviations

        return result

    def _generate_rebalance_instructions(
        self,
        deviations: List[Dict],
        current_portfolio: Dict[str, float],
        current_signals: List[ComposedSignal]
    ) -> List[TradeInstruction]:
        """生成再平衡指令"""
        instructions = []

        # 创建信号查找字典
        signal_map = {s.etf_code: s for s in current_signals}

        for dev in deviations:
            etf_code = dev['etf_code']
            target = dev['target']
            current = dev['current']

            signal = signal_map.get(etf_code)

            if target > current:
                # 需要买入
                instruction = TradeInstruction(
                    action=ActionType.REBALANCE,
                    etf_code=etf_code,
                    etf_name=signal.etf_name if signal else "",
                    current_weight=current,
                    target_weight=target,
                    trigger_reason=TriggerReason.REBALANCE_BAND,
                    trigger_score=signal.weighted_score if signal else 0,
                )
                instructions.append(instruction)
            elif target < current:
                # 需要卖出
                instruction = TradeInstruction(
                    action=ActionType.REBALANCE,
                    etf_code=etf_code,
                    etf_name=signal.etf_name if signal else "",
                    current_weight=current,
                    target_weight=target,
                    trigger_reason=TriggerReason.REBALANCE_BAND,
                    trigger_score=signal.weighted_score if signal else 0,
                )
                instructions.append(instruction)

        return instructions


class ThematicTrigger(StrategyTrigger):
    """主题仓位策略触发器

    适用于主题投资策略，基于主题得分和动量进行调仓
    """

    DEFAULT_CONFIG = {
        'max_positions': 5,  # 最大持仓数
        'min_score': 50.0,  # 最低得分
        'momentum_threshold': 0.05,  # 动量阈值
        'rebalance_frequency': 'weekly',  # 调仓频率
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化主题策略触发器

        Args:
            config: 配置字典
        """
        merged_config = {**self.DEFAULT_CONFIG, **(config or {})}
        super().__init__(merged_config)

        self.max_positions = self.config['max_positions']
        self.min_score = self.config['min_score']
        self.momentum_threshold = self.config['momentum_threshold']
        self.rebalance_frequency = self.config['rebalance_frequency']

    def should_trigger(self,
                      current_signals: List[ComposedSignal],
                      current_portfolio: Optional[Dict[str, float]] = None,
                      last_signals: Optional[List[ComposedSignal]] = None,
                      **kwargs) -> TriggerResult:
        """
        判断是否触发主题调仓

        逻辑：
        1. 选择得分最高且超过阈值的主题
        2. 检查动量变化
        3. 动态调整仓位
        """
        result = TriggerResult()
        result.timestamp = datetime.now()

        current_portfolio = current_portfolio or {}

        # 过滤低分品种
        eligible_signals = [
            s for s in current_signals
            if s.weighted_score >= self.min_score
        ]

        if not eligible_signals:
            result.should_trigger = False
            result.metadata['reason'] = '没有符合条件的主题品种'
            return result

        # 按得分排序
        sorted_signals = sorted(
            eligible_signals,
            key=lambda x: x.weighted_score,
            reverse=True
        )

        # 选择Top N
        selected_signals = sorted_signals[:self.max_positions]
        selected_codes = set(s.etf_code for s in selected_signals)
        current_codes = set(current_portfolio.keys())

        # 检查是否需要调仓
        if selected_codes == current_codes:
            # 持仓未变，检查权重是否需要调整
            need_rebalance = self._check_weight_adjustment(
                selected_signals, current_portfolio
            )

            if not need_rebalance:
                result.should_trigger = False
                result.metadata['reason'] = '持仓和权重均在合理范围内'
                return result

        # 生成交易指令
        instructions = self._generate_thematic_instructions(
            selected_signals, current_portfolio, current_signals
        )

        result.should_trigger = True
        result.instructions = instructions
        result.trigger_reasons = [TriggerReason.SCORE_THRESHOLD]
        result.metadata['selected_count'] = len(selected_signals)
        result.metadata['selected_codes'] = list(selected_codes)

        return result

    def _check_weight_adjustment(
        self,
        selected_signals: List[ComposedSignal],
        current_portfolio: Dict[str, float]
    ) -> bool:
        """检查是否需要调整权重"""
        # 基于得分的动态权重
        total_score = sum(s.weighted_score for s in selected_signals)

        for signal in selected_signals:
            target_weight = signal.weighted_score / total_score if total_score > 0 else 0
            current_weight = current_portfolio.get(signal.etf_code, 0)

            # 如果偏离超过5%，需要调整
            if abs(target_weight - current_weight) > 0.05:
                return True

        return False

    def _generate_thematic_instructions(
        self,
        selected_signals: List[ComposedSignal],
        current_portfolio: Dict[str, float],
        all_signals: List[ComposedSignal]
    ) -> List[TradeInstruction]:
        """生成主题调仓指令"""
        instructions = []

        selected_codes = set(s.etf_code for s in selected_signals)
        current_codes = set(current_portfolio.keys())

        # 基于得分的动态权重计算
        total_score = sum(s.weighted_score for s in selected_signals)

        # 需要卖出的
        for code in current_codes - selected_codes:
            signal = next((s for s in all_signals if s.etf_code == code), None)

            instruction = TradeInstruction(
                action=ActionType.SELL,
                etf_code=code,
                etf_name=signal.etf_name if signal else "",
                current_weight=current_portfolio.get(code, 0),
                target_weight=0,
                trigger_reason=TriggerReason.SCORE_THRESHOLD,
                trigger_score=signal.weighted_score if signal else 0,
            )
            instructions.append(instruction)

        # 需要买入或调整权重的
        for signal in selected_signals:
            code = signal.etf_code
            target_weight = signal.weighted_score / total_score if total_score > 0 else 0
            current_weight = current_portfolio.get(code, 0)

            if code in current_codes:
                # 调整权重
                action = ActionType.REBALANCE
            else:
                # 新建仓
                action = ActionType.BUY

            instruction = TradeInstruction(
                action=action,
                etf_code=code,
                etf_name=signal.etf_name,
                current_weight=current_weight,
                target_weight=target_weight,
                trigger_reason=TriggerReason.SCORE_THRESHOLD,
                trigger_score=signal.weighted_score,
            )
            instructions.append(instruction)

        return instructions


# 便捷函数
def create_trigger(
    strategy_type: str,
    config: Optional[Dict[str, Any]] = None
) -> StrategyTrigger:
    """
    工厂函数：创建策略触发器

    Args:
        strategy_type: 策略类型（'rotation', 'permanent', 'thematic'）
        config: 配置字典

    Returns:
        StrategyTrigger: 策略触发器实例
    """
    if strategy_type == 'rotation':
        return RotationTrigger(config)
    elif strategy_type == 'permanent':
        return PermanentPortfolioTrigger(config)
    elif strategy_type == 'thematic':
        return ThematicTrigger(config)
    else:
        raise ValueError(f"未知的策略类型: {strategy_type}")


# 导出主要类和函数
__all__ = [
    'ActionType',
    'TriggerReason',
    'TradeInstruction',
    'TriggerResult',
    'StrategyTrigger',
    'RotationTrigger',
    'PermanentPortfolioTrigger',
    'ThematicTrigger',
    'create_trigger',
]