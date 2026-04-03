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


class TradeRecord(models.Model):
    """
    交易记录
    用于手动记录实际交易执行情况
    """

    # 关联信号（如果基于系统信号执行）
    related_signal = models.ForeignKey(
        'monitor.Signal',
        on_delete=models.SET_NULL,
        related_name='trade_records',
        verbose_name='关联信号',
        null=True,
        blank=True
    )

    # 关联偏差记录（如果不匹配信号）
    related_deviation = models.ForeignKey(
        DeviationLog,
        on_delete=models.SET_NULL,
        related_name='trade_records',
        verbose_name='关联偏差记录',
        null=True,
        blank=True
    )

    # 交易时间
    trade_time = models.DateTimeField(
        '交易时间',
        default=timezone.now,
        help_text='实际交易发生的时间'
    )

    # 交易日期（用于查询）
    trade_date = models.DateField(
        '交易日期',
        help_text='对应的交易日期'
    )

    # 操作类型
    ACTION_CHOICES = [
        ('buy', '买入'),
        ('sell', '卖出'),
        ('add', '加仓'),
        ('reduce', '减仓'),
    ]
    action = models.CharField(
        '操作类型',
        max_length=20,
        choices=ACTION_CHOICES,
        help_text='交易操作类型'
    )

    # 品种
    etf = models.ForeignKey(
        'portfolio.ETF',
        on_delete=models.CASCADE,
        related_name='trade_records',
        verbose_name='品种'
    )

    # 数量
    quantity = models.PositiveIntegerField(
        '数量（股）',
        help_text='交易数量'
    )

    # 成交价格
    price = models.DecimalField(
        '成交价（元）',
        max_digits=10,
        decimal_places=4,
        help_text='实际成交价格'
    )

    # 手续费
    commission = models.DecimalField(
        '手续费（元）',
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text='交易手续费'
    )

    # 总金额（自动计算）
    total_amount = models.DecimalField(
        '总金额（元）',
        max_digits=15,
        decimal_places=2,
        help_text='总成交金额（含手续费）'
    )

    # 是否与信号一致
    match_signal = models.BooleanField(
        '与信号一致',
        default=True,
        help_text='是否与系统信号一致'
    )

    # 偏差说明（如果不一致）
    deviation_note = models.TextField(
        '偏差说明',
        blank=True,
        help_text='如果与信号不一致，说明原因'
    )

    # 交易备注
    note = models.TextField(
        '交易备注',
        blank=True,
        help_text='其他备注信息'
    )

    # 创建和更新信息
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_trade_records',
        verbose_name='创建人'
    )
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='updated_trade_records',
        verbose_name='更新人',
        null=True,
        blank=True
    )
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '交易记录'
        verbose_name_plural = '交易记录'
        ordering = ['-trade_time']
        indexes = [
            models.Index(fields=['-trade_time']),
            models.Index(fields=['etf', '-trade_time']),
            models.Index(fields=['action', '-trade_time']),
            models.Index(fields=['match_signal', '-trade_time']),
        ]

    def __str__(self):
        return f"{self.trade_date} - {self.get_action_display()} - {self.etf.code} - {self.quantity}股"

    def save(self, *args, **kwargs):
        """保存时自动计算交易日期和总金额"""
        if not self.trade_date:
            self.trade_date = self.trade_time.date()

        # 自动计算总金额
        self.total_amount = (self.price * self.quantity) + (self.commission or 0)

        super().save(*args, **kwargs)

    def get_action_color(self):
        """获取操作类型的颜色标识"""
        color_map = {
            'buy': 'success',
            'sell': 'danger',
            'add': 'info',
            'reduce': 'warning',
        }
        return color_map.get(self.action, 'secondary')

    def calculate_pnl(self):
        """计算该笔交易的盈亏（需要持仓信息）"""
        # TODO: 根据持仓成本计算盈亏
        pass


class Position(models.Model):
    """
    持仓记录
    用于追踪当前持仓和持仓成本
    """

    # 用户
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='positions',
        verbose_name='用户'
    )

    # 品种
    etf = models.ForeignKey(
        'portfolio.ETF',
        on_delete=models.CASCADE,
        related_name='positions',
        verbose_name='品种'
    )

    # 持仓数量
    quantity = models.IntegerField(
        '持仓数量',
        default=0,
        help_text='正数为多头，负数为空头'
    )

    # 平均成本
    avg_cost = models.DecimalField(
        '平均成本',
        max_digits=10,
        decimal_places=4,
        default=0,
        help_text='持仓平均成本'
    )

    # 总成本
    total_cost = models.DecimalField(
        '总成本',
        max_digits=15,
        decimal_places=2,
        default=0,
        help_text='持仓总成本'
    )

    # 当前市值（需要外部更新）
    market_value = models.DecimalField(
        '市值',
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='当前市值'
    )

    # 未实现盈亏
    unrealized_pnl = models.DecimalField(
        '未实现盈亏',
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='未实现盈亏'
    )

    # 未实现收益率
    unrealized_pnl_pct = models.DecimalField(
        '未实现收益率(%)',
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        help_text='未实现收益率百分比'
    )

    # 首次建仓时间
    first_trade_time = models.DateTimeField(
        '首次建仓时间',
        null=True,
        blank=True
    )

    # 最后交易时间
    last_trade_time = models.DateTimeField(
        '最后交易时间',
        null=True,
        blank=True
    )

    # 是否活跃
    is_active = models.BooleanField(
        '是否活跃',
        default=True,
        help_text='是否还有持仓'
    )

    # 元数据
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '持仓'
        verbose_name_plural = '持仓'
        ordering = ['-updated_at']
        unique_together = ['user', 'etf']
        indexes = [
            models.Index(fields=['user', '-updated_at']),
            models.Index(fields=['etf', '-updated_at']),
            models.Index(fields=['is_active', '-updated_at']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.etf.code} - {self.quantity}股 - 成本{self.avg_cost}"

    def update_from_trade(self, trade_record):
        """
        根据交易记录更新持仓
        """
        if trade_record.action == 'buy':
            # 买入：增加持仓，更新平均成本
            total_cost = (self.avg_cost * self.quantity) + (trade_record.price * trade_record.quantity)
            self.quantity += trade_record.quantity
            self.avg_cost = total_cost / self.quantity if self.quantity > 0 else 0
        elif trade_record.action == 'sell':
            # 卖出：减少持仓，保持平均成本不变
            self.quantity -= trade_record.quantity
            if self.quantity <= 0:
                self.quantity = 0
                self.avg_cost = 0
                self.is_active = False
        elif trade_record.action == 'add':
            # 加仓：同买入
            total_cost = (self.avg_cost * self.quantity) + (trade_record.price * trade_record.quantity)
            self.quantity += trade_record.quantity
            self.avg_cost = total_cost / self.quantity if self.quantity > 0 else 0
        elif trade_record.action == 'reduce':
            # 减仓：同卖出
            self.quantity -= trade_record.quantity
            if self.quantity <= 0:
                self.quantity = 0
                self.avg_cost = 0
                self.is_active = False

        # 更新总成本和时间
        self.total_cost = self.avg_cost * self.quantity
        self.last_trade_time = trade_record.trade_time
        if not self.first_trade_time:
            self.first_trade_time = trade_record.trade_time

        # 如果持仓不为0，设置为活跃
        if self.quantity > 0:
            self.is_active = True

        self.save()

    def update_market_value(self, current_price):
        """
        更新市值和盈亏
        """
        if self.quantity > 0 and current_price:
            self.market_value = Decimal(str(current_price)) * self.quantity
            self.unrealized_pnl = self.market_value - self.total_cost
            if self.total_cost > 0:
                self.unrealized_pnl_pct = (self.unrealized_pnl / self.total_cost) * 100
            self.save()

    def get_position_summary(self):
        """
        获取持仓摘要
        """
        return {
            'etf_code': self.etf.code,
            'etf_name': self.etf.name,
            'quantity': self.quantity,
            'avg_cost': float(self.avg_cost),
            'total_cost': float(self.total_cost),
            'market_value': float(self.market_value) if self.market_value else None,
            'unrealized_pnl': float(self.unrealized_pnl) if self.unrealized_pnl else None,
            'unrealized_pnl_pct': float(self.unrealized_pnl_pct) if self.unrealized_pnl_pct else None,
            'is_active': self.is_active,
        }

