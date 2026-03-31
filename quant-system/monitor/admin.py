"""
实盘监控管理后台配置
"""

from django.contrib import admin
from .models import MonitorStrategy, Signal, HealthCheckLog, AlertRule, AlertLog


@admin.register(MonitorStrategy)
class MonitorStrategyAdmin(admin.ModelAdmin):
    """监控策略管理后台"""
    list_display = [
        'name', 'strategy_type', 'frequency', 'pool',
        'is_active', 'is_running', 'last_run_at'
    ]
    list_filter = ['strategy_type', 'frequency', 'is_active', 'is_running']
    search_fields = ['name', 'strategy_code', 'description']
    readonly_fields = ['created_at', 'updated_at', 'last_run_at']

    fieldsets = (
        ('基本信息', {
            'fields': ('name', 'description', 'strategy_code')
        }),
        ('策略配置', {
            'fields': ('pool', 'strategy_type', 'frequency')
        }),
        ('权重和阈值配置', {
            'fields': ('weight_config', 'threshold_config'),
            'classes': ('collapse',)
        }),
        ('交易规则', {
            'fields': ('entry_rules', 'exit_rules', 'risk_limits'),
            'classes': ('collapse',)
        }),
        ('通知配置', {
            'fields': ('notification_config',),
            'classes': ('collapse',)
        }),
        ('状态', {
            'fields': ('is_active', 'is_running', 'created_by')
        }),
        ('元数据', {
            'fields': ('created_at', 'updated_at', 'last_run_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Signal)
class SignalAdmin(admin.ModelAdmin):
    """交易信号管理后台"""
    list_display = [
        'strategy', 'signal_type', 'trade_date', 'status',
        'composite_score', 'from_etf', 'to_etf'
    ]
    list_filter = ['signal_type', 'status', 'trade_date']
    search_fields = ['strategy__name', 'notes']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'trade_date'

    fieldsets = (
        ('基本信息', {
            'fields': ('strategy', 'timestamp', 'trade_date', 'signal_type', 'status')
        }),
        ('交易信息', {
            'fields': (
                'from_etf', 'to_etf', 'price', 'quantity', 'amount'
            )
        }),
        ('得分详情', {
            'fields': (
                'composite_score', 'l1_score', 'l2_score', 'l3_score', 'l4_score',
                'score_details'
            ),
            'classes': ('collapse',)
        }),
        ('执行结果', {
            'fields': (
                'executed_at', 'executed_price', 'pnl'
            )
        }),
        ('元数据', {
            'fields': ('created_at', 'updated_at', 'notes'),
            'classes': ('collapse',)
        }),
    )


@admin.register(HealthCheckLog)
class HealthCheckLogAdmin(admin.ModelAdmin):
    """健康检查日志管理后台"""
    list_display = [
        'check_type', 'status', 'message',
        'response_time_ms', 'checked_at'
    ]
    list_filter = ['check_type', 'status']
    readonly_fields = ['checked_at']
    date_hierarchy = 'checked_at'

    fieldsets = (
        ('基本信息', {
            'fields': ('check_type', 'status', 'message')
        }),
        ('详细信息', {
            'fields': ('details', 'response_time_ms'),
            'classes': ('collapse',)
        }),
        ('时间', {
            'fields': ('checked_at',)
        }),
    )


@admin.register(AlertRule)
class AlertRuleAdmin(admin.ModelAdmin):
    """预警规则管理后台"""
    list_display = [
        'name', 'condition_type', 'severity',
        'is_active', 'created_at'
    ]
    list_filter = ['condition_type', 'severity', 'is_active']
    search_fields = ['name', 'rule_code', 'description']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('基本信息', {
            'fields': ('name', 'description', 'rule_code')
        }),
        ('触发条件', {
            'fields': ('condition_type', 'condition_params', 'severity')
        }),
        ('通知配置', {
            'fields': ('notification_channels', 'notification_template')
        }),
        ('控制参数', {
            'fields': ('cooldown_minutes',)
        }),
        ('状态', {
            'fields': ('is_active', 'created_by')
        }),
        ('元数据', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(AlertLog)
class AlertLogAdmin(admin.ModelAdmin):
    """预警日志管理后台"""
    list_display = [
        'title', 'severity', 'status',
        'strategy', 'created_at', 'is_acknowledged'
    ]
    list_filter = ['severity', 'status', 'is_acknowledged']
    search_fields = ['title', 'message', 'strategy__name']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('基本信息', {
            'fields': ('rule', 'strategy', 'title', 'message', 'severity')
        }),
        ('触发数据', {
            'fields': ('trigger_data',)
        }),
        ('通知状态', {
            'fields': (
                'notification_status', 'notification_channels',
                'notification_sent_at', 'notification_error'
            )
        }),
        ('确认信息', {
            'fields': (
                'is_acknowledged', 'acknowledged_at', 'acknowledged_by'
            )
        }),
        ('元数据', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
