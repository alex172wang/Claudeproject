"""
L5偏差日志分析模块

提供偏差日志的统计分析、逆向验证、直觉胜率追踪等功能
"""

from django.db import models
from django.db.models import (
    Count, Sum, Avg, Max, Min, F, Q,
    Case, When, Value, IntegerField
)
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Any

from .models import DeviationLog, TradeRecord
from monitor.models import Signal


class DeviationAnalytics:
    """
    偏差日志分析器
    提供多维度的偏差分析功能
    """

    def __init__(self, user=None, start_date=None, end_date=None):
        """
        初始化分析器

        Args:
            user: 指定用户（None表示所有用户）
            start_date: 开始日期
            end_date: 结束日期
        """
        self.user = user
        self.start_date = start_date or (timezone.now() - timedelta(days=90))
        self.end_date = end_date or timezone.now()

        # 基础查询集
        self.base_queryset = self._get_base_queryset()

    def _get_base_queryset(self):
        """获取基础查询集"""
        queryset = DeviationLog.objects.filter(
            timestamp__date__gte=self.start_date,
            timestamp__date__lte=self.end_date
        )

        if self.user:
            queryset = queryset.filter(created_by=self.user)

        return queryset

    def get_overview_stats(self) -> Dict[str, Any]:
        """
        获取偏差日志概览统计

        Returns:
            {
                'total_deviations': 总偏差数,
                'by_type': 按类型统计,
                'by_verification': 按验证结果统计,
                'intuition_accuracy': 直觉准确率,
            }
        """
        # 基础统计
        total = self.base_queryset.count()

        # 按偏差类型统计
        by_type = self.base_queryset.values('deviation_type').annotate(
            count=Count('id')
        ).order_by('-count')

        # 按验证结果统计
        by_verification = self.base_queryset.values('verification_result').annotate(
            count=Count('id')
        )

        # 直觉准确率（已验证的偏差中判断正确的比例）
        verified = self.base_queryset.filter(
            verification_result__in=['correct', 'wrong']
        )
        correct_count = verified.filter(verification_result='correct').count()
        total_verified = verified.count()

        intuition_accuracy = (
            (correct_count / total_verified * 100)
            if total_verified > 0 else 0
        )

        # 盈亏统计
        pnl_stats = self.base_queryset.aggregate(
            total_pnl_diff=Sum('pnl_difference'),
            avg_pnl_diff=Avg('pnl_difference'),
            max_pnl_diff=Max('pnl_difference'),
            min_pnl_diff=Min('pnl_difference'),
        )

        return {
            'total_deviations': total,
            'date_range': {
                'start': self.start_date.strftime('%Y-%m-%d'),
                'end': self.end_date.strftime('%Y-%m-%d'),
            },
            'by_type': list(by_type),
            'by_verification': list(by_verification),
            'intuition_accuracy': {
                'correct_count': correct_count,
                'total_verified': total_verified,
                'accuracy_rate': round(intuition_accuracy, 2),
            },
            'pnl_stats': {
                'total_pnl_diff': float(pnl_stats['total_pnl_diff'] or 0),
                'avg_pnl_diff': float(pnl_stats['avg_pnl_diff'] or 0),
                'max_pnl_diff': float(pnl_stats['max_pnl_diff'] or 0),
                'min_pnl_diff': float(pnl_stats['min_pnl_diff'] or 0),
            },
        }

    def get_time_series_analysis(self) -> List[Dict]:
        """
        获取时间序列分析数据

        Returns:
            按时间段统计的偏差数据列表
        """
        # 按周统计
        from django.db.models.functions import TruncWeek

        weekly_stats = self.base_queryset.annotate(
            week=TruncWeek('timestamp')
        ).values('week').annotate(
            count=Count('id'),
            correct_count=Count(
                Case(
                    When(verification_result='correct', then=1),
                    output_field=IntegerField()
                )
            ),
            wrong_count=Count(
                Case(
                    When(verification_result='wrong', then=1),
                    output_field=IntegerField()
                )
            ),
            total_pnl_diff=Sum('pnl_difference'),
        ).order_by('week')

        return list(weekly_stats)

    def get_intuition_score_by_type(self) -> List[Dict]:
        """
        按偏差类型统计直觉准确率

        Returns:
            各偏差类型的准确率统计
        """
        type_stats = self.base_queryset.values('deviation_type').annotate(
            total=Count('id'),
            verified=Count(
                Case(
                    When(verification_result__in=['correct', 'wrong'], then=1),
                    output_field=IntegerField()
                )
            ),
            correct=Count(
                Case(
                    When(verification_result='correct', then=1),
                    output_field=IntegerField()
                )
            ),
        ).order_by('-total')

        # 计算准确率
        result = []
        for stat in type_stats:
            verified = stat['verified']
            correct = stat['correct']
            accuracy = (correct / verified * 100) if verified > 0 else 0

            result.append({
                'deviation_type': stat['deviation_type'],
                'deviation_type_display': self._get_deviation_type_display(stat['deviation_type']),
                'total': stat['total'],
                'verified': verified,
                'correct': correct,
                'accuracy_rate': round(accuracy, 2),
            })

        return result

    def _get_deviation_type_display(self, deviation_type):
        """获取偏差类型的显示名称"""
        type_map = {
            'override': '人工覆盖',
            'delayed': '延迟执行',
            'skipped': '跳过交易',
            'modified': '修改参数',
            'additional': '额外交易',
            'no_deviation': '无偏差',
        }
        return type_map.get(deviation_type, deviation_type)


class IntuitionTracker:
    """
    直觉追踪器
    用于追踪和分析用户的直觉决策质量
    """

    def __init__(self, user):
        self.user = user

    def get_intuition_profile(self) -> Dict:
        """
        获取直觉决策画像

        Returns:
            直觉决策的各项指标
        """
        # 获取所有已验证的偏差
        deviations = DeviationLog.objects.filter(
            created_by=self.user,
            verification_result__in=['correct', 'wrong']
        )

        total = deviations.count()
        if total == 0:
            return {
                'total_decisions': 0,
                'accuracy_rate': None,
                'confidence_level': None,
                'patterns': [],
            }

        correct = deviations.filter(verification_result='correct').count()
        accuracy_rate = (correct / total) * 100

        # 计算置信区间（简化版，使用正态近似）
        import math
        if total > 30:
            se = math.sqrt((accuracy_rate / 100) * (1 - accuracy_rate / 100) / total)
            ci_lower = (accuracy_rate / 100 - 1.96 * se) * 100
            ci_upper = (accuracy_rate / 100 + 1.96 * se) * 100
            confidence_level = {
                'lower': max(0, round(ci_lower, 2)),
                'upper': min(100, round(ci_upper, 2)),
            }
        else:
            confidence_level = None

        # 识别直觉模式（哪些类型更准确）
        analytics = DeviationAnalytics(user=self.user)
        type_accuracy = analytics.get_intuition_score_by_type()

        # 找出高准确率和低准确率的类型
        patterns = {
            'strong_areas': [t for t in type_accuracy if t['accuracy_rate'] >= 60],
            'weak_areas': [t for t in type_accuracy if t['accuracy_rate'] < 40 and t['verified'] >= 5],
        }

        return {
            'total_decisions': total,
            'correct_count': correct,
            'wrong_count': total - correct,
            'accuracy_rate': round(accuracy_rate, 2),
            'confidence_level': confidence_level,
            'patterns': patterns,
            'type_breakdown': type_accuracy,
        }

    def get_intuition_recommendations(self) -> List[Dict]:
        """
        获取直觉决策建议

        Returns:
            基于历史数据的决策建议列表
        """
        profile = self.get_intuition_profile()
        recommendations = []

        # 基于准确率给出建议
        if profile['accuracy_rate'] is None:
            recommendations.append({
                'type': 'info',
                'title': '数据不足',
                'message': '验证的偏差记录不足，建议持续记录和验证更多决策偏差。',
                'action': '继续记录偏差日志',
            })
        elif profile['accuracy_rate'] >= 70:
            recommendations.append({
                'type': 'success',
                'title': '直觉准确率高',
                'message': f'您的直觉决策准确率达到{profile["accuracy_rate"]}%，表明您的主观判断质量较高。',
                'action': '继续保持并记录更多决策',
            })
        elif profile['accuracy_rate'] <= 40:
            recommendations.append({
                'type': 'warning',
                'title': '直觉准确率较低',
                'message': f'您的直觉决策准确率为{profile["accuracy_rate"]}%，建议更多参考系统信号。',
                'action': '减少主观干预，增加系统执行',
            })

        # 基于类型给出建议
        patterns = profile.get('patterns', {})
        if patterns.get('strong_areas'):
            area_names = ', '.join([a['deviation_type_display'] for a in patterns['strong_areas'][:2]])
            recommendations.append({
                'type': 'info',
                'title': '优势决策领域',
                'message': f'您在"{area_names}"类型的决策上表现较好，可以更多发挥这些方面的直觉。',
            })

        if patterns.get('weak_areas'):
            area_names = ', '.join([a['deviation_type_display'] for a in patterns['weak_areas'][:2]])
            recommendations.append({
                'type': 'danger',
                'title': '需要改进的领域',
                'message': f'您在"{area_names}"类型的决策上准确率较低，建议谨慎决策或更多依赖系统信号。',
            })

        return recommendations
