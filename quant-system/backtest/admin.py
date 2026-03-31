"""
回测管理后台配置
"""

from django.contrib import admin
from .models import BacktestTask, BacktestResult


@admin.register(BacktestTask)
class BacktestTaskAdmin(admin.ModelAdmin):
    """回测任务管理后台"""
    list_display = [
        'name', 'strategy_type', 'status', 'pool',
        'start_date', 'end_date', 'is_active'
    ]
    list_filter = ['strategy_type', 'status', 'is_active', 'strategy_type']
    search_fields = ['name', 'task_code', 'description']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'start_date'

    fieldsets = (
        ('基本信息', {
            'fields': ('name', 'description', 'task_code')
        }),
        ('策略配置', {
            'fields': ('pool', 'strategy_type')
        }),
        ('回测参数', {
            'fields': (
                'start_date', 'end_date', 'in_sample_ratio',
                'initial_capital', 'commission_rate', 'slippage'
            )
        }),
        ('自定义配置', {
            'fields': ('weight_override', 'threshold_override'),
            'classes': ('collapse',)
        }),
        ('状态', {
            'fields': ('status', 'is_active', 'created_by')
        }),
        ('元数据', {
            'fields': ('created_at', 'updated_at', 'started_at', 'completed_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(BacktestResult)
class BacktestResultAdmin(admin.ModelAdmin):
    """回测结果管理后台"""
    list_display = [
        'task', 'sample_type', 'is_valid',
        'total_return', 'sharpe_ratio', 'max_drawdown',
        'is_overfitted'
    ]
    list_filter = ['sample_type', 'is_valid', 'is_overfitted']
    search_fields = ['task__name', 'task__task_code']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('基本信息', {
            'fields': ('task', 'sample_type', 'is_valid')
        }),
        ('收益指标', {
            'fields': (
                'total_return', 'annualized_return',
                'benchmark_return', 'excess_return'
            )
        }),
        ('风险指标', {
            'fields': (
                'volatility', 'max_drawdown', 'max_drawdown_period',
                'var_95'
            )
        }),
        ('风险调整指标', {
            'fields': (
                'sharpe_ratio', 'sortino_ratio',
                'calmar_ratio', 'treynor_ratio'
            )
        }),
        ('交易统计', {
            'fields': (
                'total_trades', 'winning_trades', 'losing_trades',
                'win_rate', 'profit_factor', 'avg_trade_return'
            )
        }),
        ('过拟合检测', {
            'fields': (
                'is_overfitted', 'in_out_sharpe_ratio',
                'parameter_count', 'out_of_sample_trades'
            )
        }),
        ('详细数据', {
            'fields': (
                'equity_curve', 'drawdown_series',
                'trade_list', 'monthly_returns', 'rolling_metrics'
            ),
            'classes': ('collapse',)
        }),
        ('元数据', {
            'fields': ('created_at', 'updated_at', 'notes'),
            'classes': ('collapse',)
        }),
    )
