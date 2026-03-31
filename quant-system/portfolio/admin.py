"""
投资组合管理后台配置
"""

from django.contrib import admin
from .models import ETF, Pool, PoolMember, ETFPrice


@admin.register(ETF)
class ETFAdmin(admin.ModelAdmin):
    """ETF管理后台"""
    list_display = [
        'code', 'name', 'market', 'category',
        'fund_manager', 'is_active', 'list_date'
    ]
    list_filter = ['market', 'category', 'is_active', 'fund_manager']
    search_fields = ['code', 'name', 'tracking_index', 'fund_manager']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('基本信息', {
            'fields': ('code', 'name', 'market', 'category')
        }),
        ('跟踪信息', {
            'fields': ('tracking_index', 'tracking_index_code')
        }),
        ('管理信息', {
            'fields': ('fund_manager', 'expense_ratio', 'list_date')
        }),
        ('状态', {
            'fields': ('is_active',)
        }),
        ('元数据', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Pool)
class PoolAdmin(admin.ModelAdmin):
    """品种池管理后台"""
    list_display = [
        'code', 'name', 'purpose', 'member_count',
        'is_active', 'created_at'
    ]
    list_filter = ['purpose', 'is_active']
    search_fields = ['code', 'name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('基本信息', {
            'fields': ('code', 'name', 'description', 'purpose')
        }),
        ('配置', {
            'fields': ('asset_classes',)
        }),
        ('状态', {
            'fields': ('is_active',)
        }),
        ('元数据', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def member_count(self, obj):
        """获取成员数量"""
        return obj.member_count
    member_count.short_description = '成员数量'


@admin.register(PoolMember)
class PoolMemberAdmin(admin.ModelAdmin):
    """池成员管理后台"""
    list_display = [
        'pool', 'etf', 'weight', 'order',
        'is_active', 'created_at'
    ]
    list_filter = ['pool', 'is_active', 'etf__category']
    search_fields = ['pool__name', 'pool__code', 'etf__code', 'etf__name']
    readonly_fields = ['created_at', 'updated_at']
    autocomplete_fields = ['pool', 'etf']

    fieldsets = (
        ('关联', {
            'fields': ('pool', 'etf')
        }),
        ('配置', {
            'fields': ('weight', 'order', 'thresholds', 'filters')
        }),
        ('状态', {
            'fields': ('is_active', 'notes')
        }),
        ('元数据', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ETFPrice)
class ETFPriceAdmin(admin.ModelAdmin):
    """ETF价格数据管理后台"""
    list_display = [
        'etf', 'date', 'close_price', 'volume',
        'adj_factor'
    ]
    list_filter = ['etf__market', 'etf__category']
    search_fields = ['etf__code', 'etf__name']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'date'

    fieldsets = (
        ('关联', {
            'fields': ('etf',)
        }),
        ('日期', {
            'fields': ('date',)
        }),
        ('价格', {
            'fields': ('open_price', 'high_price', 'low_price', 'close_price')
        }),
        ('成交', {
            'fields': ('volume', 'amount')
        }),
        ('复权', {
            'fields': ('adj_factor',)
        }),
        ('元数据', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
