"""
综合得分加权合成模块

将多个品种的四维评分合成为最终的品种排名/选择结果
"""

from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import numpy as np
import pandas as pd

from .scorer import FourDimensionalScore, LayerScore, ETFFourDimensionalScorer


class SortingMethod(Enum):
    """排序方法枚举"""
    OVERALL_SCORE = "overall_score"  # 按综合得分排序
    WEIGHTED_SCORE = "weighted_score"  # 按加权得分排序
    L1_PRIORITY = "l1_priority"  # L1优先（趋势跟踪）
    L4_PRIORITY = "l4_priority"  # L4优先（风险控制）
    RISK_ADJUSTED = "risk_adjusted"  # 风险调整后得分


@dataclass
class ComposedSignal:
    """合成后的信号结果"""
    etf_code: str = ""
    etf_name: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

    # 各维度得分
    overall_score: float = 50.0
    weighted_score: float = 50.0
    risk_adjusted_score: float = 50.0

    # 各层原始得分
    L1_score: float = 50.0
    L2_score: float = 50.0
    L3_score: float = 50.0
    L4_score: float = 50.0

    # 信号方向
    signal: int = 0  # -1=看空, 0=中性, 1=看多
    confidence: float = 0.0  # 置信度 0-1

    # 排名
    rank: int = 0
    percentile: float = 50.0  # 百分位排名

    # 风险指标
    volatility: float = 0.0
    max_drawdown: float = 0.0

    # 原始四维评分数据（用于详情展示）
    raw_scores: Optional[FourDimensionalScore] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'etf_code': self.etf_code,
            'etf_name': self.etf_name,
            'timestamp': self.timestamp.isoformat(),
            'overall_score': round(self.overall_score, 2),
            'weighted_score': round(self.weighted_score, 2),
            'risk_adjusted_score': round(self.risk_adjusted_score, 2),
            'L1_score': round(self.L1_score, 2),
            'L2_score': round(self.L2_score, 2),
            'L3_score': round(self.L3_score, 2),
            'L4_score': round(self.L4_score, 2),
            'signal': self.signal,
            'confidence': round(self.confidence, 2),
            'rank': self.rank,
            'percentile': round(self.percentile, 2),
            'volatility': round(self.volatility, 4),
            'max_drawdown': round(self.max_drawdown, 4),
        }


class SignalComposer:
    """信号合成器

    将多个品种的四维评分合成为最终的品种排名/选择结果
    """

    def __init__(self,
                 l1_weight: float = 0.35,
                 l2_weight: float = 0.25,
                 l3_weight: float = 0.20,
                 l4_weight: float = 0.20):
        """
        初始化信号合成器

        Args:
            l1_weight: L1趋势层权重
            l2_weight: L2结构层权重
            l3_weight: L3共振层权重
            l4_weight: L4缺口层权重
        """
        self.weights = {
            'L1': l1_weight,
            'L2': l2_weight,
            'L3': l3_weight,
            'L4': l4_weight
        }

        # 验证权重
        total = sum(self.weights.values())
        if abs(total - 1.0) > 0.001:
            for key in self.weights:
                self.weights[key] /= total

    def compose(self,
                four_d_scores: List[FourDimensionalScore],
                sorting_method: SortingMethod = SortingMethod.WEIGHTED_SCORE,
                risk_adjust: bool = True) -> List[ComposedSignal]:
        """
        合成信号，返回排序后的品种列表

        Args:
            four_d_scores: 四维评分列表
            sorting_method: 排序方法
            risk_adjust: 是否进行风险调整

        Returns:
            List[ComposedSignal]: 排序后的合成信号列表
        """
        if not four_d_scores:
            return []

        # 转换为ComposedSignal
        composed_list = []
        for fd_score in four_d_scores:
            composed = self._convert_to_composed_signal(fd_score)
            composed_list.append(composed)

        # 计算排名和百分位
        composed_list = self._calculate_ranks(composed_list, sorting_method)

        # 风险调整
        if risk_adjust:
            composed_list = self._apply_risk_adjustment(composed_list)

        # 最终排序
        composed_list = self._final_sort(composed_list, sorting_method)

        return composed_list

    def _convert_to_composed_signal(self, fd_score: FourDimensionalScore) -> ComposedSignal:
        """将FourDimensionalScore转换为ComposedSignal"""
        composed = ComposedSignal(
            etf_code=fd_score.etf_code,
            etf_name=fd_score.etf_name,
            timestamp=fd_score.timestamp,
            overall_score=fd_score.overall_score,
            weighted_score=fd_score.weighted_score,
            L1_score=fd_score.L1.score,
            L2_score=fd_score.L2.score,
            L3_score=fd_score.L3.score,
            L4_score=fd_score.L4.score,
            raw_scores=fd_score,
        )

        # 计算信号方向（基于加权得分）
        if composed.weighted_score >= 60:
            composed.signal = 1
        elif composed.weighted_score <= 40:
            composed.signal = -1
        else:
            composed.signal = 0

        # 计算置信度（基于各层得分的一致性）
        scores = [composed.L1_score, composed.L2_score, composed.L3_score, composed.L4_score]
        score_std = np.std(scores)
        composed.confidence = max(0, 1 - score_std / 50)  # 标准差越小，置信度越高

        return composed

    def _calculate_ranks(self,
                        composed_list: List[ComposedSignal],
                        sorting_method: SortingMethod) -> List[ComposedSignal]:
        """计算排名和百分位"""
        if not composed_list:
            return composed_list

        # 根据排序方法选择排序键
        def get_sort_key(c: ComposedSignal) -> float:
            if sorting_method == SortingMethod.OVERALL_SCORE:
                return c.overall_score
            elif sorting_method == SortingMethod.WEIGHTED_SCORE:
                return c.weighted_score
            elif sorting_method == SortingMethod.L1_PRIORITY:
                return c.L1_score * 0.5 + c.weighted_score * 0.5
            elif sorting_method == SortingMethod.L4_PRIORITY:
                return c.L4_score * 0.5 + c.weighted_score * 0.5
            else:
                return c.weighted_score

        # 排序（降序）
        sorted_list = sorted(composed_list, key=get_sort_key, reverse=True)

        # 计算排名和百分位
        n = len(sorted_list)
        for i, composed in enumerate(sorted_list):
            composed.rank = i + 1
            composed.percentile = (n - i) / n * 100

        return sorted_list

    def _apply_risk_adjustment(self, composed_list: List[ComposedSignal]) -> List[ComposedSignal]:
        """应用风险调整"""
        if len(composed_list) < 2:
            return composed_list

        # 计算波动率调整因子
        scores = [c.weighted_score for c in composed_list]
        mean_score = np.mean(scores)

        for composed in composed_list:
            # 简单的风险调整：基于与均值的偏离
            deviation = abs(composed.weighted_score - mean_score)
            adjustment_factor = max(0.8, 1 - deviation / 200)  # 偏离越大，调整越大

            composed.risk_adjusted_score = composed.weighted_score * adjustment_factor

        return composed_list

    def _final_sort(self,
                   composed_list: List[ComposedSignal],
                   sorting_method: SortingMethod) -> List[ComposedSignal]:
        """最终排序"""

        def get_sort_key(c: ComposedSignal) -> float:
            if sorting_method == SortingMethod.RISK_ADJUSTED:
                return getattr(c, 'risk_adjusted_score', c.weighted_score)
            elif sorting_method == SortingMethod.OVERALL_SCORE:
                return c.overall_score
            else:
                return c.weighted_score

        return sorted(composed_list, key=get_sort_key, reverse=True)

    def select_top_n(self,
                    composed_signals: List[ComposedSignal],
                    n: int = 3,
                    min_score: float = 40.0) -> List[ComposedSignal]:
        """
        选择前N个品种

        Args:
            composed_signals: 合成信号列表
            n: 选择数量
            min_score: 最低分数要求

        Returns:
            List[ComposedSignal]: 选中的品种列表
        """
        # 过滤低分品种
        filtered = [c for c in composed_signals if c.weighted_score >= min_score]

        # 返回前N个
        return filtered[:n]

    def generate_portfolio_suggestion(
        self,
        composed_signals: List[ComposedSignal],
        total_capital: float = 1000000.0,
        max_positions: int = 5,
        risk_per_position: float = 0.02,
    ) -> Dict[str, Any]:
        """
        生成组合建议

        Args:
            composed_signals: 合成信号列表
            total_capital: 总资金
            max_positions: 最大持仓数量
            risk_per_position: 每个头寸的风险比例

        Returns:
            Dict: 组合建议
        """
        # 选择品种
        selected = self.select_top_n(composed_signals, n=max_positions, min_score=45.0)

        if not selected:
            return {
                'status': 'no_signal',
                'message': '当前没有符合条件的品种',
                'positions': [],
            }

        # 计算权重（基于得分加权）
        total_score = sum(c.weighted_score for c in selected)
        positions = []

        for composed in selected:
            weight = composed.weighted_score / total_score if total_score > 0 else 1 / len(selected)
            capital_allocation = total_capital * weight

            positions.append({
                'etf_code': composed.etf_code,
                'etf_name': composed.etf_name,
                'weight': round(weight, 4),
                'capital': round(capital_allocation, 2),
                'score': round(composed.weighted_score, 2),
                'signal': composed.signal,
                'confidence': round(composed.confidence, 2),
            })

        return {
            'status': 'success',
            'timestamp': datetime.now().isoformat(),
            'total_capital': total_capital,
            'position_count': len(positions),
            'average_score': round(np.mean([p['score'] for p in positions]), 2),
            'positions': positions,
        }


# 便捷函数
def compose_signals(
    four_d_scores: List[FourDimensionalScore],
    l1_weight: float = 0.35,
    l2_weight: float = 0.25,
    l3_weight: float = 0.20,
    l4_weight: float = 0.20,
    sorting_method: SortingMethod = SortingMethod.WEIGHTED_SCORE,
) -> List[ComposedSignal]:
    """
    便捷函数：合成信号

    Args:
        four_d_scores: 四维评分列表
        l1_weight: L1权重
        l2_weight: L2权重
        l3_weight: L3权重
        l4_weight: L4权重
        sorting_method: 排序方法

    Returns:
        List[ComposedSignal]: 合成信号列表
    """
    composer = SignalComposer(l1_weight, l2_weight, l3_weight, l4_weight)
    return composer.compose(four_d_scores, sorting_method)


# 导出主要类和函数
__all__ = [
    'SortingMethod',
    'ComposedSignal',
    'SignalComposer',
    'compose_signals',
]