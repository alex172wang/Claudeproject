"""
信号执行状态追踪模块

用于追踪系统信号的执行状态，关联实际交易记录
"""

from django.db import models
from django.db.models import Q, Count, Avg, Sum
from django.utils import timezone
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from decimal import Decimal

from .models import Signal
from journal.models import TradeRecord, DeviationLog


class SignalExecutionTracker:
    """
    信号执行追踪器
    用于追踪和管理信号的执行生命周期
    """

    # 执行状态定义
    EXEC_STATUS_PENDING = 'pending'
    EXEC_STATUS_EXECUTED = 'executed'
    EXEC_STATUS_PARTIAL = 'partial'
    EXEC_STATUS_SKIPPED = 'skipped'
    EXEC_STATUS_EXPIRED = 'expired'

    EXEC_STATUS_CHOICES = [
        (EXEC_STATUS_PENDING, '待执行'),
        (EXEC_STATUS_EXECUTED, '已执行'),
        (EXEC_STATUS_PARTIAL, '部分执行'),
        (EXEC_STATUS_SKIPPED, '已跳过'),
        (EXEC_STATUS_EXPIRED, '已过期'),
    ]

    def __init__(self, signal: Signal):
        """
        初始化追踪器

        Args:
            signal: 要追踪的信号对象
        """
        self.signal = signal

    def get_execution_status(self) -> Dict:
        """
        获取信号的执行状态

        Returns:
            执行状态详情
        """
        # 查找关联的交易记录
        trade_records = TradeRecord.objects.filter(
            related_signal=self.signal
        ).order_by('trade_time')

        # 计算执行状态
        total_suggested_quantity = self._get_suggested_quantity()
        total_executed_quantity = sum([t.quantity for t in trade_records])

        # 确定状态
        if not trade_records:
            status = self.EXEC_STATUS_PENDING
            status_display = '待执行'
        elif total_executed_quantity >= total_suggested_quantity:
            status = self.EXEC_STATUS_EXECUTED
            status_display = '已执行'
        elif total_executed_quantity > 0:
            status = self.EXEC_STATUS_PARTIAL
            status_display = '部分执行'
        else:
            status = self.EXEC_STATUS_SKIPPED
            status_display = '已跳过'

        # 检查是否过期
        expiry_time = self.signal.timestamp + timedelta(hours=24)
        if timezone.now() > expiry_time and status == self.EXEC_STATUS_PENDING:
            status = self.EXEC_STATUS_EXPIRED
            status_display = '已过期'

        return {
            'status': status,
            'status_display': status_display,
            'signal_id': self.signal.id,
            'signal_timestamp': self.signal.timestamp,
            'suggested_action': self.signal.signal_type,
            'suggested_quantity': total_suggested_quantity,
            'executed_quantity': total_executed_quantity,
            'execution_progress': (
                (total_executed_quantity / total_suggested_quantity * 100)
                if total_suggested_quantity > 0 else 0
            ),
            'trade_records': [
                {
                    'id': t.id,
                    'trade_time': t.trade_time,
                    'action': t.action,
                    'quantity': t.quantity,
                    'price': float(t.price),
                    'total_amount': float(t.total_amount),
                    'match_signal': t.match_signal,
                }
                for t in trade_records
            ],
            'expiry_time': expiry_time,
            'time_remaining': self._format_time_remaining(expiry_time),
        }

    def _get_suggested_quantity(self) -> int:
        """获取信号建议的数量"""
        # 从信号的额外信息中获取建议数量
        # 如果信号模型有quantity字段则直接使用
        if hasattr(self.signal, 'suggested_quantity'):
            return self.signal.suggested_quantity or 0
        return 0

    def _format_time_remaining(self, expiry_time: datetime) -> str:
        """格式化剩余时间"""
        remaining = expiry_time - timezone.now()
        if remaining.total_seconds() <= 0:
            return "已过期"

        hours = int(remaining.total_seconds() // 3600)
        minutes = int((remaining.total_seconds() % 3600) // 60)

        if hours > 0:
            return f"剩余 {hours}小时{minutes}分钟"
        else:
            return f"剩余 {minutes}分钟"

    def create_execution_reminder(self) -> Dict:
        """
        创建执行提醒

        Returns:
            提醒信息
        """
        status = self.get_execution_status()

        if status['status'] == self.EXEC_STATUS_PENDING:
            return {
                'level': 'warning',
                'title': '待执行信号',
                'message': (
                    f"信号【{self.signal.signal_type} {self.signal.etf.code}】"
                    f"等待执行，{status['time_remaining']}"
                ),
                'action': '立即录入交易',
                'signal_id': self.signal.id,
            }
        elif status['status'] == self.EXEC_STATUS_PARTIAL:
            return {
                'level': 'info',
                'title': '部分执行',
                'message': (
                    f"信号【{self.signal.signal_type} {self.signal.etf.code}】"
                    f"已部分执行（{status['execution_progress']:.0f}%）"
                ),
                'action': '继续录入',
                'signal_id': self.signal.id,
            }

        return None


class SignalExecutionAnalytics:
    """
    信号执行分析器
    用于分析信号执行情况的整体统计
    """

    def __init__(self, user=None, start_date=None, end_date=None):
        """
        初始化分析器

        Args:
            user: 指定用户
            start_date: 开始日期
            end_date: 结束日期
        """
        self.user = user
        self.start_date = start_date or (timezone.now() - timedelta(days=90))
        self.end_date = end_date or timezone.now()

    def get_overall_stats(self) -> Dict:
        """
        获取整体执行统计

        Returns:
            整体统计数据
        """
        # 信号统计
        signal_query = Signal.objects.filter(
            timestamp__date__gte=self.start_date,
            timestamp__date__lte=self.end_date
        )

        if self.user:
            signal_query = signal_query.filter(created_by=self.user)

        total_signals = signal_query.count()

        # 执行统计
        execution_stats = self._get_execution_breakdown(signal_query)

        # 时间效率分析
        time_efficiency = self._get_time_efficiency_stats(signal_query)

        # 偏差统计
        deviation_stats = self._get_deviation_stats()

        return {
            'period': {
                'start': self.start_date.strftime('%Y-%m-%d'),
                'end': self.end_date.strftime('%Y-%m-%d'),
            },
            'signals': {
                'total': total_signals,
                'by_type': list(signal_query.values('signal_type').annotate(
                    count=Count('id')
                )),
            },
            'execution': execution_stats,
            'time_efficiency': time_efficiency,
            'deviation': deviation_stats,
        }

    def _get_execution_breakdown(self, signal_query) -> Dict:
        """获取执行细分统计"""
        # 为每个信号计算执行状态
        executed_count = 0
        partial_count = 0
        pending_count = 0
        skipped_count = 0

        for signal in signal_query[:1000]:  # 限制数量避免性能问题
            tracker = SignalExecutionTracker(signal)
            status = tracker.get_execution_status()

            if status['status'] == SignalExecutionTracker.EXEC_STATUS_EXECUTED:
                executed_count += 1
            elif status['status'] == SignalExecutionTracker.EXEC_STATUS_PARTIAL:
                partial_count += 1
            elif status['status'] == SignalExecutionTracker.EXEC_STATUS_PENDING:
                pending_count += 1
            elif status['status'] == SignalExecutionTracker.EXEC_STATUS_SKIPPED:
                skipped_count += 1

        total = executed_count + partial_count + pending_count + skipped_count

        return {
            'total_analyzed': total,
            'executed': executed_count,
            'partial': partial_count,
            'pending': pending_count,
            'skipped': skipped_count,
            'execution_rate': (executed_count / total * 100) if total > 0 else 0,
            'partial_rate': (partial_count / total * 100) if total > 0 else 0,
        }

    def _get_time_efficiency_stats(self, signal_query) -> Dict:
        """获取时间效率统计"""
        # 计算信号到执行的平均时间
        avg_response_time = None
        response_time_distribution = []

        # 获取有执行记录的信号
        executed_signals = TradeRecord.objects.filter(
            related_signal__in=signal_query,
        ).values('related_signal').annotate(
            first_trade_time=Min('trade_time')
        )

        # 计算响应时间
        response_times = []
        for exec_info in executed_signals:
            try:
                signal = Signal.objects.get(id=exec_info['related_signal'])
                response_time = (
                    exec_info['first_trade_time'] - signal.timestamp
                ).total_seconds() / 3600  # 转换为小时
                response_times.append(response_time)
            except Signal.DoesNotExist:
                continue

        if response_times:
            avg_response_time = sum(response_times) / len(response_times)

            # 分布统计
            distribution = {
                'within_1h': len([t for t in response_times if t <= 1]),
                'within_4h': len([t for t in response_times if 1 < t <= 4]),
                'within_24h': len([t for t in response_times if 4 < t <= 24]),
                'over_24h': len([t for t in response_times if t > 24]),
            }
            response_time_distribution = distribution

        return {
            'avg_response_time_hours': round(avg_response_time, 2) if avg_response_time else None,
            'response_time_distribution': response_time_distribution,
            'total_executed_signals': len(response_times),
        }

    def _get_deviation_stats(self) -> Dict:
        """获取偏差统计"""
        # 查询偏差记录
        deviation_query = DeviationLog.objects.filter(
            timestamp__date__gte=self.start_date,
            timestamp__date__lte=self.end_date
        )

        if self.user:
            deviation_query = deviation_query.filter(created_by=self.user)

        total_deviations = deviation_query.count()

        # 验证统计
        verified_stats = deviation_query.aggregate(
            verified_count=Count(
                Case(
                    When(verification_result__in=['correct', 'wrong'], then=1),
                    output_field=IntegerField()
                )
            ),
            correct_count=Count(
                Case(
                    When(verification_result='correct', then=1),
                    output_field=IntegerField()
                )
            ),
        )

        verified_count = verified_stats['verified_count'] or 0
        correct_count = verified_stats['correct_count'] or 0

        accuracy = (correct_count / verified_count * 100) if verified_count > 0 else 0

        # 按类型统计
        type_stats = deviation_query.values('deviation_type').annotate(
            count=Count('id')
        ).order_by('-count')

        # 盈亏统计
        pnl_stats = deviation_query.aggregate(
            total_pnl_diff=Sum('pnl_difference'),
            avg_pnl_diff=Avg('pnl_difference'),
        )

        return {
            'total_deviations': total_deviations,
            'verification': {
                'verified_count': verified_count,
                'correct_count': correct_count,
                'accuracy_rate': round(accuracy, 2),
                'pending_verification': total_deviations - verified_count,
            },
            'by_type': list(type_stats),
            'pnl_stats': {
                'total_pnl_diff': float(pnl_stats['total_pnl_diff'] or 0),
                'avg_pnl_diff': float(pnl_stats['avg_pnl_diff'] or 0),
            },
        }


class DeviationVerificationWorkflow:
    """
    偏差验证工作流
    提供偏差验证的完整流程支持
    """

    @staticmethod
    def create_verification_task(deviation: DeviationLog) -> Dict:
        """
        创建验证任务

        Args:
            deviation: 偏差记录

        Returns:
            验证任务信息
        """
        # 计算验证截止日期（默认7天后）
        verification_deadline = deviation.timestamp + timedelta(days=7)

        # 创建任务
        return {
            'deviation_id': deviation.id,
            'deviation_type': deviation.deviation_type,
            'system_action': deviation.system_action,
            'actual_action': deviation.actual_action,
            'system_target': str(deviation.system_target) if deviation.system_target else None,
            'actual_target': str(deviation.actual_target) if deviation.actual_target else None,
            'created_at': deviation.timestamp,
            'verification_deadline': verification_deadline,
            'status': 'pending',
        }

    @staticmethod
    def complete_verification(
        deviation: DeviationLog,
        result: str,
        notes: str,
        verified_by=None
    ) -> Dict:
        """
        完成偏差验证

        Args:
            deviation: 偏差记录
            result: 验证结果（'correct', 'wrong', 'uncertain'）
            notes: 验证备注
            verified_by: 验证人

        Returns:
            验证完成信息
        """
        # 调用模型的完成验证方法
        deviation.complete_verification(
            result=result,
            notes=notes,
            verified_by=verified_by
        )

        # 计算盈亏差异
        deviation.calculate_pnl_difference()

        return {
            'deviation_id': deviation.id,
            'verification_result': result,
            'verified_at': deviation.verified_at,
            'verified_by': str(verified_by) if verified_by else None,
        }

    @staticmethod
    def batch_create_verification_tasks(
        user=None,
        start_date=None,
        end_date=None
    ) -> List[Dict]:
        """
        批量创建验证任务

        Args:
            user: 指定用户
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            验证任务列表
        """
        # 查询待验证的偏差记录
        query = DeviationLog.objects.filter(
            verification_result='pending'
        )

        if user:
            query = query.filter(created_by=user)
        if start_date:
            query = query.filter(timestamp__date__gte=start_date)
        if end_date:
            query = query.filter(timestamp__date__lte=end_date)

        tasks = []
        for deviation in query:
            task = DeviationVerificationWorkflow.create_verification_task(deviation)
            tasks.append(task)

        return tasks
