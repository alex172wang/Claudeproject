"""
偏差日志模型定义
包含决策偏差记录、逆向验证、复盘笔记等模型
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings
import json


class DecisionLog(models.Model):
    """
    决策日志
    记录系统决策和人工干预的完整历史
    """

    # 决策时间
    timestamp = models.DateTimeField(
        '决策时间',
        help_text='决策发生的时间'
    )
    trade_date = models.DateField(
        '交易日期',
        help_text='对应的交易日期'
    )

    # 决策类型
    DECISION_TYPE_CHOICES = [
        ('system', '系统决策'),
        ('manual', '人工干预'),
        ('override', '系统覆盖人工'),
        ('deviation', '偏差决策'),
    ]
    decision_type = models.CharField(
        '决策类型',
        max_length=20,
        choices=DECISION_TYPE_CHOICES,
        help_text='决策的来源类型'
    )

    # 关联信号
    signal = models.ForeignKey(
        'monitor.Signal',
        on_delete=models.SET_NULL,
        related_name='decision_logs',
        verbose_name='关联信号',
        null=True,
        blank=True
    )

    # 关联策略
    strategy = models.ForeignKey(
        'monitor.MonitorStrategy',
        on_delete=models.SET_NULL,
        related_name='decision_logs',
        verbose_name='关联策略',
        null=True,
        blank=True
    )

    # 决策内容
    ACTION_CHOICES = [
        ('buy', '买入'),
        ('sell', '卖出'),
        ('add', '加仓'),
        ('reduce', '减仓'),
        ('hold', '持有'),
        ('switch', '切换'),
        ('none', '无操作'),
    ]
    action = models.CharField(
        '操作',
        max_length=20,
        choices=ACTION_CHOICES,
        help_text='决策的操作类型'
    )

    from_etf = models.ForeignKey(
        'portfolio.ETF',
        on_delete=models.SET_NULL,
        related_name='decision_logs_from',
        verbose_name='卖出品种',
        null=True,
        blank=True
    )
    to_etf = models.ForeignKey(
        'portfolio.ETF',
        on_delete=models.SET_NULL,
        related_name='decision_logs_to',
        verbose_name='买入品种',
        null=True,
        blank=True
    )

    quantity = models.IntegerField(
        '数量',
        null=True,
        blank=True,
        help_text='建议交易数量'
    )
    price = models.DecimalField(
        '价格',
        max_digits=12,
        decimal_places=4,
        null=True,
        blank=True,
        help_text='建议成交价格'
    )

    # 决策依据
    decision_rationale = models.TextField(
        '决策依据',
        blank=True,
        help_text='做出此决策的理由'
    )
    scores_at_decision = models.JSONField(
        '当时得分',
        default=dict,
        blank=True,
        help_text='决策时各层得分情况'
    )

    # 执行状态
    EXECUTION_STATUS_CHOICES = [
        ('pending', '待执行'),
        ('executed', '已执行'),
        ('rejected', '已拒绝'),
        ('expired', '已过期'),
    ]
    execution_status = models.CharField(
        '执行状态',
        max_length=20,
        choices=EXECUTION_STATUS_CHOICES,
        default='pending',
        help_text='决策的执行状态'
    )

    executed_at = models.DateTimeField('执行时间', null=True, blank=True)
    executed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='executed_decisions',
        verbose_name='执行人',
        null=True,
        blank=True
    )

    # 人工干预标记
    is_manual_override = models.BooleanField(
        '是否人工干预',
        default=False,
        help_text='是否有人工干预此决策'
    )
    override_reason = models.TextField(
        '干预原因',
        blank=True,
        help_text='人工干预的原因'
    )
    overridden_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='overridden_decisions',
        verbose_name='干预人',
        null=True,
        blank=True
    )

    # 元数据
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '决策日志'
        verbose_name_plural = '决策日志'
        ordering = ['-timestamp', '-created_at']

    def __str__(self):
        return f"{self.get_decision_type_display()} - {self.get_action_display()} - {self.trade_date}"


class DeviationLog(models.Model):
    """
    偏差日志
    记录系统决策与实际决策的偏差，用于逆向验证
    """

    # 关联决策日志
    system_decision = models.ForeignKey(
        DecisionLog,
        on_delete=models.CASCADE,
        related_name='deviation_as_system',
        verbose_name='系统决策',
        help_text='系统建议的决策'
    )
    actual_decision = models.ForeignKey(
        DecisionLog,
        on_delete=models.CASCADE,
        related_name='deviation_as_actual',
        verbose_name='实际决策',
        null=True,
        blank=True,
        help_text='实际执行的决策'
    )

    # 偏差时间
    timestamp = models.DateTimeField('偏差时间', auto_now_add=True)
    trade_date = models.DateField('交易日期')

    # 偏差类型
    DEVIATION_TYPE_CHOICES = [
        ('override', '人工覆盖'),
        ('delayed', '延迟执行'),
        ('skipped', '跳过交易'),
        ('modified', '修改参数'),
        ('additional', '额外交易'),
        ('no_deviation', '无偏差'),
    ]
    deviation_type = models.CharField(
        '偏差类型',
        max_length=20,
        choices=DEVIATION_TYPE_CHOICES,
        help_text='偏差的类型'
    )

    # 偏差详情
    description = models.TextField(
        '偏差描述',
        help_text='偏差的详细描述'
    )
    reason = models.TextField(
        '偏差原因',
        help_text='产生偏差的主观/客观原因'
    )

    # 决策对比
    system_action = models.CharField(
        '系统操作',
        max_length=20,
        choices=DecisionLog.ACTION_CHOICES,
        help_text='系统建议的操作'
    )
    actual_action = models.CharField(
        '实际操作',
        max_length=20,
        choices=DecisionLog.ACTION_CHOICES,
        null=True,
        blank=True,
        help_text='实际执行的操作'
    )

    # 品种对比
    system_target = models.ForeignKey(
        'portfolio.ETF',
        on_delete=models.SET_NULL,
        related_name='deviation_system_targets',
        verbose_name='系统目标品种',
        null=True,
        blank=True
    )
    actual_target = models.ForeignKey(
        'portfolio.ETF',
        on_delete=models.SET_NULL,
        related_name='deviation_actual_targets',
        verbose_name='实际目标品种',
        null=True,
        blank=True
    )

    # 逆向验证结果（在偏离发生后的验证周期内记录）
    verification_deadline = models.DateField(
        '验证截止日期',
        null=True,
        blank=True,
        help_text='需要完成验证的日期'
    )
    verification_result = models.CharField(
        '验证结果',
        max_length=20,
        choices=[
            ('pending', '待验证'),
            ('correct', '判断正确'),
            ('wrong', '判断错误'),
            ('uncertain', '无法确定'),
        ],
        default='pending',
        help_text='逆向验证的结果'
    )
    verification_notes = models.TextField(
        '验证备注',
        blank=True,
        help_text='验证过程的详细记录'
    )
    verified_at = models.DateTimeField(
        '验证时间',
        null=True,
        blank=True
    )
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_deviations',
        verbose_name='验证人'
    )

    # 结果对比
    system_pnl = models.DecimalField(
        '系统决策盈亏',
        max_digits=20,
        decimal_places=4,
        null=True,
        blank=True,
        help_text='如果按系统决策执行的实际盈亏'
    )
    actual_pnl = models.DecimalField(
        '实际决策盈亏',
        max_digits=20,
        decimal_places=4,
        null=True,
        blank=True,
        help_text='实际执行的盈亏'
    )
    pnl_difference = models.DecimalField(
        '盈亏差异',
        max_digits=20,
        decimal_places=4,
        null=True,
        blank=True,
        help_text='实际盈亏 - 系统盈亏（负值表示偏离导致亏损）'
    )

    # 元数据
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_deviations',
        verbose_name='记录人'
    )

    class Meta:
        verbose_name = '偏差日志'
        verbose_name_plural = '偏差日志'
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.get_deviation_type_display()} - {self.trade_date} - {self.verification_result}"

    def complete_verification(self, result, notes='', verified_by=None):
        """完成验证"""
        self.verification_result = result
        self.verification_notes = notes
        self.verified_at = datetime.now()
        self.verified_by = verified_by
        self.save()

    def calculate_pnl_difference(self):
        """计算盈亏差异"""
        if self.system_pnl is not None and self.actual_pnl is not None:
            self.pnl_difference = self.actual_pnl - self.system_pnl
            self.save()
