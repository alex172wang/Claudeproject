"""
偏差日志管理后台配置
"""

from django.contrib import admin
from .models import DecisionLog, DeviationLog


@admin.register(DecisionLog)
class DecisionLogAdmin(admin.ModelAdmin):
    """决策日志管理后台"""
    list_display = [
        'timestamp', 'trade_date', 'decision_type',
        'action', 'from_etf', 'to_etf', 'execution_status'
    ]
    list_filter = ['decision_type', 'action', 'execution_status']
    search_fields = ['decision_rationale', 'override_reason']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'trade_date'

    fieldsets = (
        ('时间信息', {
            'fields': ('timestamp', 'trade_date')
        }),
        ('决策类型', {
            'fields': ('decision_type', 'signal', 'strategy')
        }),
        ('决策内容', {
            'fields': (
                'action', 'from_etf', 'to_etf',
                'quantity', 'price', 'decision_rationale'
            )
        }),
        ('执行信息', {
            'fields': (
                'execution_status', 'executed_at', 'executed_by'
            )
        }),
        ('人工干预', {
            'fields': (
                'is_manual_override', 'override_reason', 'overridden_by'
            )
        }),
        ('元数据', {
            'fields': ('created_at', 'updated_at', 'scores_at_decision'),
            'classes': ('collapse',)
        }),
    )


@admin.register(DeviationLog)
class DeviationLogAdmin(admin.ModelAdmin):
    """偏差日志管理后台"""
    list_display = [
        'timestamp', 'trade_date', 'deviation_type',
        'system_action', 'actual_action', 'verification_result'
    ]
    list_filter = ['deviation_type', 'verification_result']
    search_fields = ['description', 'reason', 'verification_notes']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'trade_date'

    fieldsets = (
        ('基本信息', {
            'fields': ('system_decision', 'actual_decision', 'timestamp', 'trade_date')
        }),
        ('偏差详情', {
            'fields': (
                'deviation_type', 'description', 'reason',
                'system_action', 'actual_action',
                'system_target', 'actual_target'
            )
        }),
        ('逆向验证', {
            'fields': (
                'verification_deadline', 'verification_result',
                'verification_notes', 'verified_at', 'verified_by'
            )
        }),
        ('盈亏对比', {
            'fields': (
                'system_pnl', 'actual_pnl', 'pnl_difference'
            )
        }),
        ('元数据', {
            'fields': ('created_at', 'updated_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )
