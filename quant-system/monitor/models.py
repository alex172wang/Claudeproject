"""
监控模型定义
包含监控策略、信号记录、健康检查等模型
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings
import json


class MonitorStrategy(models.Model):
    """
    监控策略
    定义一个实盘监控的策略配置
    """

    # 基本信息
    name = models.CharField(
        '策略名称',
        max_length=200,
        help_text='监控策略的名称'
    )
    description = models.TextField(
        '策略描述',
        blank=True,
        help_text='策略的详细描述'
    )
    strategy_code = models.SlugField(
        '策略代码',
        max_length=50,
        unique=True,
        help_text='策略的唯一标识代码'
    )

    # 关联品种池
    pool = models.ForeignKey(
        'portfolio.Pool',
        on_delete=models.CASCADE,
        related_name='monitor_strategies',
        verbose_name='品种池',
        help_text='监控使用的品种池'
    )

    # 策略类型
    STRATEGY_TYPE_CHOICES = [
        ('rotation', 'ETF轮动'),
        ('permanent', '永久组合'),
        ('thematic', '主题仓位'),
    ]
    strategy_type = models.CharField(
        '策略类型',
        max_length=20,
        choices=STRATEGY_TYPE_CHOICES,
        help_text='监控策略的类型'
    )

    # 执行频率
    FREQUENCY_CHOICES = [
        ('intraday_10min', '盘中10分钟'),
        ('daily_1445', '每日14:45'),
        ('weekly', '每周'),
        ('monthly', '每月'),
    ]
    frequency = models.CharField(
        '执行频率',
        max_length=20,
        choices=FREQUENCY_CHOICES,
        help_text='策略信号计算频率'
    )

    # 权重配置（可选，覆盖默认）
    weight_config = models.JSONField(
        '权重配置',
        default=dict,
        blank=True,
        help_text='L1-L4权重配置，如{"L1": 0.35, "L2": 0.25}'
    )

    # 阈值配置（可选）
    threshold_config = models.JSONField(
        '阈值配置',
        default=dict,
        blank=True,
        help_text='各指标的阈值配置'
    )

    # 特殊规则
    entry_rules = models.JSONField(
        '入场规则',
        default=dict,
        blank=True,
        help_text='入场条件规则'
    )
    exit_rules = models.JSONField(
        '出场规则',
        default=dict,
        blank=True,
        help_text='出场条件规则'
    )

    # 风险控制
    risk_limits = models.JSONField(
        '风险限制',
        default=dict,
        blank=True,
        help_text='风险控制参数，如{"max_position": 1, "stop_loss": 0.05}'
    )

    # 通知配置
    notification_config = models.JSONField(
        '通知配置',
        default=dict,
        blank=True,
        help_text='信号通知配置'
    )

    # 状态
    is_active = models.BooleanField(
        '是否启用',
        default=True,
        help_text='策略是否处于监控状态'
    )
    is_running = models.BooleanField(
        '是否运行中',
        default=False,
        help_text='策略是否正在执行'
    )

    # 时间戳
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    last_run_at = models.DateTimeField('最后运行时间', null=True, blank=True)

    # 创建者
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='创建者'
    )

    class Meta:
        verbose_name = '监控策略'
        verbose_name_plural = '监控策略'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.strategy_code} - {self.name}"

    @property
    def signal_count(self):
        """获取信号数量"""
        return self.signals.count()

    @property
    def latest_signal(self):
        """获取最新信号"""
        return self.signals.first()

    def get_weight_config(self):
        """获取完整的权重配置（合并默认和覆盖）"""
        # 这里应该从配置文件中读取默认权重
        default_weights = {
            'L1': 0.40,
            'L2': 0.20,
            'L3': 0.20,
            'L4': 0.20,
        }
        # 用配置覆盖默认值
        weights = default_weights.copy()
        weights.update(self.weight_config)
        return weights


class Signal(models.Model):
    """
    交易信号
    记录策略生成的买卖信号
    """

    # 关联策略
    strategy = models.ForeignKey(
        MonitorStrategy,
        on_delete=models.CASCADE,
        related_name='signals',
        verbose_name='所属策略'
    )

    # 信号时间
    timestamp = models.DateTimeField(
        '信号时间',
        help_text='信号生成的时间'
    )
    trade_date = models.DateField(
        '交易日期',
        help_text='信号对应的交易日期'
    )

    # 信号类型
    SIGNAL_TYPE_CHOICES = [
        ('buy', '买入'),
        ('sell', '卖出'),
        ('add', '加仓'),
        ('reduce', '减仓'),
        ('hold', '持有'),
        ('switch', '切换'),
    ]
    signal_type = models.CharField(
        '信号类型',
        max_length=20,
        choices=SIGNAL_TYPE_CHOICES,
        help_text='信号的操作类型'
    )

    # 涉及品种
    from_etf = models.ForeignKey(
        'portfolio.ETF',
        on_delete=models.CASCADE,
        related_name='signals_from',
        verbose_name='卖出品种',
        null=True,
        blank=True,
        help_text='卖出的ETF品种'
    )
    to_etf = models.ForeignKey(
        'portfolio.ETF',
        on_delete=models.CASCADE,
        related_name='signals_to',
        verbose_name='买入品种',
        null=True,
        blank=True,
        help_text='买入的ETF品种'
    )

    # 价格和数量
    price = models.DecimalField(
        '价格',
        max_digits=12,
        decimal_places=4,
        null=True,
        blank=True,
        help_text='建议成交价格'
    )
    quantity = models.IntegerField(
        '数量',
        null=True,
        blank=True,
        help_text='建议成交数量'
    )
    amount = models.DecimalField(
        '金额',
        max_digits=20,
        decimal_places=4,
        null=True,
        blank=True,
        help_text='建议成交金额'
    )

    # 信号得分（L1-L4各层得分和综合得分）
    l1_score = models.DecimalField(
        'L1得分',
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='趋势层得分（0-100）'
    )
    l2_score = models.DecimalField(
        'L2得分',
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='结构层得分（0-100）'
    )
    l3_score = models.DecimalField(
        'L3得分',
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='共振层得分（0-100）'
    )
    l4_score = models.DecimalField(
        'L4得分',
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='缺口层得分（0-100，反向计分）'
    )
    composite_score = models.DecimalField(
        '综合得分',
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='加权综合得分（0-100）'
    )

    # 各层详细数据
    score_details = models.JSONField(
        '得分详情',
        default=dict,
        blank=True,
        help_text='各层指标的详细计算结果'
    )

    # 信号状态
    STATUS_CHOICES = [
        ('pending', '待执行'),
        ('executed', '已执行'),
        ('expired', '已过期'),
        ('cancelled', '已取消'),
    ]
    status = models.CharField(
        '信号状态',
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        help_text='信号的当前状态'
    )

    # 执行结果
    executed_at = models.DateTimeField('执行时间', null=True, blank=True)
    executed_price = models.DecimalField(
        '执行价格',
        max_digits=12,
        decimal_places=4,
        null=True,
        blank=True
    )
    pnl = models.DecimalField(
        '盈亏',
        max_digits=20,
        decimal_places=4,
        null=True,
        blank=True,
        help_text='该信号的盈亏金额'
    )

    # 元数据
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    notes = models.TextField('备注', blank=True)

    class Meta:
        verbose_name = '交易信号'
        verbose_name_plural = '交易信号'
        ordering = ['-timestamp', '-created_at']

    def __str__(self):
        return f"{self.strategy.name} - {self.get_signal_type_display()} - {self.trade_date}"

    @property
    def holding_period(self):
        """计算持仓周期（针对已执行的交易）"""
        if self.executed_at and self.timestamp:
            return (self.executed_at - self.timestamp).days
        return None

    def to_dict(self):
        """转换为字典格式（用于API返回）"""
        return {
            'id': self.id,
            'strategy': self.strategy.name,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'trade_date': self.trade_date.isoformat() if self.trade_date else None,
            'signal_type': self.signal_type,
            'signal_type_display': self.get_signal_type_display(),
            'from_etf': self.from_etf.code if self.from_etf else None,
            'to_etf': self.to_etf.code if self.to_etf else None,
            'price': float(self.price) if self.price else None,
            'quantity': self.quantity,
            'amount': float(self.amount) if self.amount else None,
            'composite_score': float(self.composite_score) if self.composite_score else None,
            'l1_score': float(self.l1_score) if self.l1_score else None,
            'l2_score': float(self.l2_score) if self.l2_score else None,
            'l3_score': float(self.l3_score) if self.l3_score else None,
            'l4_score': float(self.l4_score) if self.l4_score else None,
            'status': self.status,
            'status_display': self.get_status_display(),
        }


class HealthCheckLog(models.Model):
    """
    健康检查日志
    记录系统健康状态检查结果
    """

    # 检查类型
    CHECK_TYPE_CHOICES = [
        ('data_source', '数据源检查'),
        ('calculation', '指标计算检查'),
        ('signal', '信号生成检查'),
        ('database', '数据库检查'),
        ('notification', '通知服务检查'),
    ]
    check_type = models.CharField(
        '检查类型',
        max_length=20,
        choices=CHECK_TYPE_CHOICES,
        help_text='健康检查的类型'
    )

    # 检查状态
    STATUS_CHOICES = [
        ('healthy', '健康'),
        ('warning', '警告'),
        ('critical', '严重'),
        ('unknown', '未知'),
    ]
    status = models.CharField(
        '状态',
        max_length=20,
        choices=STATUS_CHOICES,
        help_text='检查结果状态'
    )

    # 检查详情
    message = models.TextField(
        '检查消息',
        blank=True,
        help_text='检查结果的详细消息'
    )
    details = models.JSONField(
        '详细信息',
        default=dict,
        blank=True,
        help_text='检查的详细数据'
    )

    # 响应时间
    response_time_ms = models.IntegerField(
        '响应时间(ms)',
        null=True,
        blank=True,
        help_text='检查的响应时间（毫秒）'
    )

    # 时间戳
    checked_at = models.DateTimeField('检查时间', auto_now_add=True)

    class Meta:
        verbose_name = '健康检查日志'
        verbose_name_plural = '健康检查日志'
        ordering = ['-checked_at']

    def __str__(self):
        return f"{self.get_check_type_display()} - {self.get_status_display()} - {self.checked_at}"


class AlertRule(models.Model):
    """
    预警规则
    定义监控预警的触发条件和通知方式
    """

    name = models.CharField(
        '规则名称',
        max_length=200,
        help_text='预警规则的名称'
    )
    description = models.TextField(
        '规则描述',
        blank=True,
        help_text='规则的详细描述'
    )
    rule_code = models.SlugField(
        '规则代码',
        max_length=50,
        unique=True,
        help_text='规则的唯一标识代码'
    )

    # 触发条件
    condition_type = models.CharField(
        '条件类型',
        max_length=50,
        help_text='触发条件的类型（如score_drop、drawdown_spike等）'
    )
    condition_params = models.JSONField(
        '条件参数',
        default=dict,
        help_text='触发条件的参数'
    )

    # 严重级别
    SEVERITY_CHOICES = [
        ('info', '信息'),
        ('warning', '警告'),
        ('critical', '严重'),
    ]
    severity = models.CharField(
        '严重级别',
        max_length=20,
        choices=SEVERITY_CHOICES,
        default='warning',
        help_text='预警的严重程度'
    )

    # 通知配置
    notification_channels = models.JSONField(
        '通知渠道',
        default=list,
        help_text='通知渠道列表（如feishu、email、sms）'
    )
    notification_template = models.TextField(
        '通知模板',
        blank=True,
        help_text='通知消息的模板'
    )

    # 冷却时间
    cooldown_minutes = models.IntegerField(
        '冷却时间（分钟）',
        default=60,
        help_text='同一规则的重复触发间隔'
    )

    # 状态
    is_active = models.BooleanField(
        '是否启用',
        default=True,
        help_text='规则是否生效'
    )

    # 元数据
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='创建者'
    )

    class Meta:
        verbose_name = '预警规则'
        verbose_name_plural = '预警规则'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.rule_code} - {self.name}"


class AlertLog(models.Model):
    """
    预警日志
    记录触发的预警事件
    """

    # 关联规则
    rule = models.ForeignKey(
        AlertRule,
        on_delete=models.CASCADE,
        related_name='alert_logs',
        verbose_name='触发规则',
        null=True,
        blank=True
    )

    # 策略（可选）
    strategy = models.ForeignKey(
        MonitorStrategy,
        on_delete=models.CASCADE,
        related_name='alert_logs',
        verbose_name='关联策略',
        null=True,
        blank=True
    )

    # 预警内容
    title = models.CharField(
        '预警标题',
        max_length=200,
        help_text='预警的标题'
    )
    message = models.TextField(
        '预警消息',
        help_text='预警的详细内容'
    )
    severity = models.CharField(
        '严重级别',
        max_length=20,
        choices=AlertRule.SEVERITY_CHOICES,
        help_text='预警的严重程度'
    )

    # 触发数据
    trigger_data = models.JSONField(
        '触发数据',
        default=dict,
        help_text='触发预警时的相关数据'
    )

    # 通知状态
    NOTIFICATION_STATUS_CHOICES = [
        ('pending', '待发送'),
        ('sent', '已发送'),
        ('failed', '发送失败'),
        ('skipped', '已跳过'),
    ]
    notification_status = models.CharField(
        '通知状态',
        max_length=20,
        choices=NOTIFICATION_STATUS_CHOICES,
        default='pending',
        help_text='通知发送状态'
    )
    notification_channels = models.JSONField(
        '通知渠道',
        default=list,
        help_text='实际使用的通知渠道'
    )
    notification_sent_at = models.DateTimeField(
        '通知发送时间',
        null=True,
        blank=True
    )
    notification_error = models.TextField(
        '通知错误',
        blank=True,
        help_text='通知发送失败的错误信息'
    )

    # 处理状态
    is_acknowledged = models.BooleanField(
        '是否确认',
        default=False,
        help_text='是否已被人工确认'
    )
    acknowledged_at = models.DateTimeField(
        '确认时间',
        null=True,
        blank=True
    )
    acknowledged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='acknowledged_alerts',
        verbose_name='确认人'
    )

    # 元数据
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '预警日志'
        verbose_name_plural = '预警日志'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['severity', 'created_at']),
            models.Index(fields=['notification_status', 'created_at']),
            models.Index(fields=['is_acknowledged', 'created_at']),
        ]

    def __str__(self):
        return f"{self.title} - {self.get_severity_display()} - {self.created_at}"

    def acknowledge(self, user, notes=''):
        """确认预警"""
        self.is_acknowledged = True
        self.acknowledged_at = datetime.now()
        self.acknowledged_by = user
        if notes:
            self.notes = notes
        self.save()

    def retry_notification(self):
        """重试通知发送"""
        self.notification_status = 'pending'
        self.notification_error = ''
        self.save()
