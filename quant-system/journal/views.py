"""
交易记录视图
用于手动交易记录的增删改查和展示
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.db.models import Sum, Avg, Count, Q
from django.http import JsonResponse
from datetime import datetime, timedelta

from .models import TradeRecord, DecisionLog, DeviationLog
from .forms import TradeRecordForm, QuickDeviationLogForm
from monitor.models import Signal
from portfolio.models import ETF


class TradeRecordListView(LoginRequiredMixin, ListView):
    """
    交易记录列表视图
    """
    model = TradeRecord
    template_name = 'journal/trade_record_list.html'
    context_object_name = 'trade_records'
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset().select_related('etf', 'related_signal', 'created_by')

        # 筛选条件
        etf_code = self.request.GET.get('etf')
        action = self.request.GET.get('action')
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        match_signal = self.request.GET.get('match_signal')

        if etf_code:
            queryset = queryset.filter(etf__code=etf_code)
        if action:
            queryset = queryset.filter(action=action)
        if date_from:
            queryset = queryset.filter(trade_time__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(trade_time__date__lte=date_to)
        if match_signal:
            queryset = queryset.filter(match_signal=(match_signal == 'true'))

        return queryset.order_by('-trade_time')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # 统计数据
        queryset = self.get_queryset()
        context['total_count'] = queryset.count()
        context['total_amount'] = queryset.aggregate(
            total=Sum('total_amount')
        )['total'] or 0

        # 筛选选项
        context['etfs'] = ETF.objects.filter(is_active=True)
        context['action_choices'] = TradeRecordForm.ACTION_CHOICES

        # 筛选参数回显
        context['filter_etf'] = self.request.GET.get('etf', '')
        context['filter_action'] = self.request.GET.get('action', '')
        context['filter_date_from'] = self.request.GET.get('date_from', '')
        context['filter_date_to'] = self.request.GET.get('date_to', '')

        return context


class TradeRecordDetailView(LoginRequiredMixin, DetailView):
    """
    交易记录详情视图
    """
    model = TradeRecord
    template_name = 'journal/trade_record_detail.html'
    context_object_name = 'trade_record'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        trade_record = self.get_object()

        # 关联的偏差记录
        if trade_record.related_deviation:
            context['deviation'] = trade_record.related_deviation

        # 关联的信号详情
        if trade_record.related_signal:
            context['signal'] = trade_record.related_signal

        return context


class TradeRecordCreateView(LoginRequiredMixin, CreateView):
    """
    创建交易记录视图
    """
    model = TradeRecord
    form_class = TradeRecordForm
    template_name = 'journal/trade_record_form.html'
    success_url = reverse_lazy('journal:trade_record_list')

    def get_initial(self):
        """设置初始值"""
        initial = super().get_initial()

        # 从URL参数获取关联信号
        signal_id = self.request.GET.get('signal')
        if signal_id:
            try:
                signal = Signal.objects.get(id=signal_id)
                initial['related_signal'] = signal.id

                # 尝试填充信号建议的操作和品种
                if hasattr(signal, 'suggested_action'):
                    initial['action'] = signal.suggested_action
                if hasattr(signal, 'etf'):
                    initial['etf'] = signal.etf.id
            except Signal.DoesNotExist:
                pass

        return initial

    def form_valid(self, form):
        """表单验证通过后处理"""
        # 设置创建者
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user

        # 自动计算总金额
        form.instance.total_amount = (
            form.instance.price * form.instance.quantity +
            (form.instance.commission or 0)
        )

        # 如果不匹配信号，自动创建偏差记录
        if not form.instance.match_signal and form.instance.related_signal:
            self._create_deviation_log(form.instance)

        return super().form_valid(form)

    def _create_deviation_log(self, trade_record):
        """创建偏差记录"""
        DeviationLog.objects.create(
            system_decision=None,  # 需要关联系统决策
            actual_decision=None,  # 关联到交易记录
            deviation_type='override',  # 默认人工覆盖
            description=f'实际交易与信号不一致: {trade_record.note}',
            reason=trade_record.deviation_note,
            system_action=trade_record.related_signal.suggested_action if trade_record.related_signal else '',
            actual_action=trade_record.action,
            system_target=trade_record.related_signal.etf if trade_record.related_signal else None,
            actual_target=trade_record.etf,
            created_by=trade_record.created_by,
            trade_date=trade_record.trade_time.date()
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '录入交易记录'
        context['submit_label'] = '保存'
        return context


class TradeRecordUpdateView(LoginRequiredMixin, UpdateView):
    """
    编辑交易记录视图
    """
    model = TradeRecord
    form_class = TradeRecordForm
    template_name = 'journal/trade_record_form.html'
    success_url = reverse_lazy('journal:trade_record_list')

    def form_valid(self, form):
        """表单验证通过后处理"""
        form.instance.updated_by = self.request.user

        # 重新计算总金额
        form.instance.total_amount = (
            form.instance.price * form.instance.quantity +
            (form.instance.commission or 0)
        )

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '编辑交易记录'
        context['submit_label'] = '更新'
        return context


class TradeRecordDeleteView(LoginRequiredMixin, DeleteView):
    """
    删除交易记录视图
    """
    model = TradeRecord
    template_name = 'journal/trade_record_confirm_delete.html'
    success_url = reverse_lazy('journal:trade_record_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '删除交易记录'
        return context


# ==================== API Views ====================

class TradeRecordStatsView(LoginRequiredMixin, View):
    """
    交易记录统计API
    """

    def get(self, request, *args, **kwargs):
        """获取交易统计"""
        # 时间范围
        days = int(request.GET.get('days', 30))
        start_date = timezone.now() - timedelta(days=days)

        # 基础查询
        queryset = TradeRecord.objects.filter(
            created_by=request.user,
            trade_time__gte=start_date
        )

        # 统计数据
        stats = {
            'total_trades': queryset.count(),
            'total_amount': float(queryset.aggregate(
                total=Sum('total_amount')
            )['total'] or 0),
            'total_commission': float(queryset.aggregate(
                total=Sum('commission')
            )['total'] or 0),
        }

        # 按操作类型统计
        action_stats = queryset.values('action').annotate(
            count=Count('id'),
            amount=Sum('total_amount')
        )
        stats['by_action'] = list(action_stats)

        # 按品种统计
        etf_stats = queryset.values('etf__code', 'etf__name').annotate(
            count=Count('id'),
            amount=Sum('total_amount')
        )
        stats['by_etf'] = list(etf_stats)

        # 信号匹配统计
        match_stats = queryset.aggregate(
            match_count=Count('id', filter=Q(match_signal=True)),
            mismatch_count=Count('id', filter=Q(match_signal=False))
        )
        stats['signal_match'] = match_stats

        return JsonResponse(stats)


class QuickTradeLogView(LoginRequiredMixin, View):
    """
    快速记录交易API
    用于从信号快速创建交易记录
    """

    def post(self, request, *args, **kwargs):
        """快速记录交易"""
        try:
            # 解析请求数据
            data = json.loads(request.body)

            # 创建交易记录
            trade = TradeRecord.objects.create(
                created_by=request.user,
                updated_by=request.user,
                related_signal_id=data.get('signal_id'),
                trade_time=parse_datetime(data.get('trade_time')) or timezone.now(),
                action=data.get('action'),
                etf_id=data.get('etf_id'),
                quantity=data.get('quantity'),
                price=Decimal(str(data.get('price', 0))),
                commission=Decimal(str(data.get('commission', 0))),
                total_amount=Decimal(str(data.get('quantity', 0))) * Decimal(str(data.get('price', 0)))
                + Decimal(str(data.get('commission', 0))),
                match_signal=data.get('match_signal', True),
                deviation_note=data.get('deviation_note', ''),
                note=data.get('note', '')
            )

            # 如果不匹配信号，创建偏差记录
            if not trade.match_signal and trade.related_signal:
                # 创建偏差记录的逻辑
                pass

            return JsonResponse({
                'success': True,
                'trade_id': trade.id,
                'message': '交易记录创建成功'
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)


# 导入json模块
import json
from django.utils.dateparse import parse_datetime
