"""
回测模型定义
包含回测任务、回测结果、绩效指标等模型
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings
import json


class BacktestTask(models.Model):
    """
    回测任务
    定义一个回测任务的配置和参数
    """

    # 任务基本信息
    name = models.CharField(
        '任务名称',
        max_length=200,
        help_text='回测任务的名称'
    )
    description = models.TextField(
        '任务描述',
        blank=True,
        help_text='回测任务的详细描述'
    )
    task_code = models.SlugField(
        '任务代码',
        max_length=50,
        unique=True,
        help_text='任务的唯一标识代码'
    )

    # 关联品种池
    pool = models.ForeignKey(
        'portfolio.Pool',
        on_delete=models.CASCADE,
        related_name='backtest_tasks',
        verbose_name='品种池',
        help_text='回测使用的品种池'
    )

    # 策略类型
    STRATEGY_CHOICES = [
        ('rotation', 'ETF轮动'),
        ('permanent', '永久组合'),
        ('thematic', '主题仓位'),
        ('custom', '自定义策略'),
    ]
    strategy_type = models.CharField(
        '策略类型',
        max_length=20,
        choices=STRATEGY_CHOICES,
        help_text='回测使用的策略类型'
    )

    # 回测时间范围
    start_date = models.DateField(
        '开始日期',
        help_text='回测开始日期'
    )
    end_date = models.DateField(
        '结束日期',
        help_text='回测结束日期'
    )

    # 样本内外分割
    in_sample_ratio = models.DecimalField(
        '样本内比例',
        max_digits=3,
        decimal_places=2,
        default=0.70,
        validators=[MinValueValidator(0.5), MaxValueValidator(0.9)],
        help_text='样本内数据占比（默认70%）'
    )

    # 初始资金
    initial_capital = models.DecimalField(
        '初始资金',
        max_digits=20,
        decimal_places=4,
        default=1000000,
        help_text='回测初始资金'
    )

    # 交易成本
    commission_rate = models.DecimalField(
        '佣金率',
        max_digits=6,
        decimal_places=5,
        default=0.001,
        help_text='交易佣金率（默认0.1%）'
    )
    slippage = models.DecimalField(
        '滑点',
        max_digits=6,
        decimal_places=5,
        default=0.001,
        help_text='滑点（默认0.1%）'
    )

    # 权重覆盖（可选，覆盖默认权重）
    weight_override = models.JSONField(
        '权重覆盖',
        default=dict,
        blank=True,
        help_text='覆盖默认权重配置，如{"L1": 0.35, "L2": 0.25}'
    )

    # 阈值覆盖（可选）
    threshold_override = models.JSONField(
        '阈值覆盖',
        default=dict,
        blank=True,
        help_text='覆盖默认阈值配置'
    )

    # 状态
    STATUS_CHOICES = [
        ('pending', '等待中'),
        ('running', '运行中'),
        ('completed', '已完成'),
        ('failed', '失败'),
        ('cancelled', '已取消'),
    ]
    status = models.CharField(
        '任务状态',
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        help_text='回测任务当前状态'
    )

    # 时间戳
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    started_at = models.DateTimeField('开始时间', null=True, blank=True)
    completed_at = models.DateTimeField('完成时间', null=True, blank=True)

    # 创建者
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='创建者'
    )

    class Meta:
        verbose_name = '回测任务'
        verbose_name_plural = '回测任务'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.task_code} - {self.name}"

    @property
    def duration(self):
        """计算回测持续时间"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    @property
    def in_sample_end_date(self):
        """计算样本内结束日期"""
        if not self.start_date or not self.end_date:
            return None
        total_days = (self.end_date - self.start_date).days
        in_sample_days = int(total_days * float(self.in_sample_ratio))
        return self.start_date + pd.Timedelta(days=in_sample_days)

    def get_result(self):
        """获取回测结果"""
        try:
            return self.results.get(is_valid=True)
        except BacktestResult.DoesNotExist:
            return None


class BacktestResult(models.Model):
    """
    回测结果
    存储回测任务的执行结果和绩效指标
    """

    # 关联任务
    task = models.ForeignKey(
        BacktestTask,
        on_delete=models.CASCADE,
        related_name='results',
        verbose_name='回测任务'
    )

    # 样本类型
    SAMPLE_CHOICES = [
        ('in_sample', '样本内'),
        ('out_of_sample', '样本外'),
        ('full', '全量'),
    ]
    sample_type = models.CharField(
        '样本类型',
        max_length=20,
        choices=SAMPLE_CHOICES,
        help_text='结果对应的样本类型'
    )

    # 有效性
    is_valid = models.BooleanField(
        '是否有效',
        default=True,
        help_text='此结果是否有效（未被覆盖）'
    )

    # ============== 收益指标 ==============
    total_return = models.DecimalField(
        '总收益率',
        max_digits=15,
        decimal_places=8,
        null=True,
        blank=True,
        help_text='回测期间总收益率'
    )
    annualized_return = models.DecimalField(
        '年化收益率',
        max_digits=15,
        decimal_places=8,
        null=True,
        blank=True,
        help_text='年化收益率'
    )
    benchmark_return = models.DecimalField(
        '基准收益率',
        max_digits=15,
        decimal_places=8,
        null=True,
        blank=True,
        help_text='基准指数收益率'
    )
    excess_return = models.DecimalField(
        '超额收益',
        max_digits=15,
        decimal_places=8,
        null=True,
        blank=True,
        help_text='超越基准的收益'
    )

    # ============== 风险指标 ==============
    volatility = models.DecimalField(
        '波动率',
        max_digits=15,
        decimal_places=8,
        null=True,
        blank=True,
        help_text='年化波动率'
    )
    max_drawdown = models.DecimalField(
        '最大回撤',
        max_digits=15,
        decimal_places=8,
        null=True,
        blank=True,
        help_text='最大回撤幅度'
    )
    max_drawdown_period = models.IntegerField(
        '最大回撤持续期',
        null=True,
        blank=True,
        help_text='最大回撤持续的天数'
    )
    var_95 = models.DecimalField(
        'VaR(95%)',
        max_digits=15,
        decimal_places=8,
        null=True,
        blank=True,
        help_text='95%置信区间的VaR'
    )

    # ============== 风险调整指标 ==============
    sharpe_ratio = models.DecimalField(
        '夏普比率',
        max_digits=15,
        decimal_places=8,
        null=True,
        blank=True,
        help_text='年化夏普比率'
    )
    sortino_ratio = models.DecimalField(
        '索提诺比率',
        max_digits=15,
        decimal_places=8,
        null=True,
        blank=True,
        help_text='索提诺比率'
    )
    calmar_ratio = models.DecimalField(
        '卡玛比率',
        max_digits=15,
        decimal_places=8,
        null=True,
        blank=True,
        help_text='卡玛比率'
    )
    treynor_ratio = models.DecimalField(
        '特雷诺比率',
        max_digits=15,
        decimal_places=8,
        null=True,
        blank=True,
        help_text='特雷诺比率'
    )

    # ============== 交易统计 ==============
    total_trades = models.IntegerField(
        '总交易次数',
        null=True,
        blank=True,
        help_text='回测期间总交易次数'
    )
    winning_trades = models.IntegerField(
        '盈利交易次数',
        null=True,
        blank=True,
        help_text='盈利的交易次数'
    )
    losing_trades = models.IntegerField(
        '亏损交易次数',
        null=True,
        blank=True,
        help_text='亏损的交易次数'
    )
    win_rate = models.DecimalField(
        '胜率',
        max_digits=7,
        decimal_places=4,
        null=True,
        blank=True,
        help_text='盈利交易占比'
    )
    profit_factor = models.DecimalField(
        '盈亏比',
        max_digits=15,
        decimal_places=8,
        null=True,
        blank=True,
        help_text='总盈利/总亏损'
    )
    avg_trade_return = models.DecimalField(
        '平均交易收益',
        max_digits=15,
        decimal_places=8,
        null=True,
        blank=True,
        help_text='每次交易的平均收益'
    )
    avg_winning_trade = models.DecimalField(
        '平均盈利',
        max_digits=15,
        decimal_places=8,
        null=True,
        blank=True,
        help_text='盈利交易的平均收益'
    )
    avg_losing_trade = models.DecimalField(
        '平均亏损',
        max_digits=15,
        decimal_places=8,
        null=True,
        blank=True,
        help_text='亏损交易的平均亏损'
    )

    # ============== 过拟合检测 ==============
    is_overfitted = models.BooleanField(
        '是否过拟合',
        default=False,
        help_text='是否检测到过拟合'
    )
    in_out_sharpe_ratio = models.DecimalField(
        '样本内外夏普比',
        max_digits=15,
        decimal_places=8,
        null=True,
        blank=True,
        help_text='样本内夏普/样本外夏普'
    )
    parameter_count = models.IntegerField(
        '参数数量',
        null=True,
        blank=True,
        help_text='策略参数组合数'
    )
    out_of_sample_trades = models.IntegerField(
        '样本外交易次数',
        null=True,
        blank=True,
        help_text='样本外期间的实际交易次数'
    )

    # ============== 详细数据（JSON存储）=============
    equity_curve = models.JSONField(
        '权益曲线',
        default=list,
        blank=True,
        help_text='每日权益值序列'
    )
    drawdown_series = models.JSONField(
        '回撤序列',
        default=list,
        blank=True,
        help_text='每日回撤值序列'
    )
    trade_list = models.JSONField(
        '交易记录',
        default=list,
        blank=True,
        help_text='详细交易记录列表'
    )
    monthly_returns = models.JSONField(
        '月度收益',
        default=dict,
        blank=True,
        help_text='月度收益率统计'
    )
    rolling_metrics = models.JSONField(
        '滚动指标',
        default=dict,
        blank=True,
        help_text='滚动窗口计算的各项指标'
    )

    # 元数据
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    notes = models.TextField('备注', blank=True)

    class Meta:
        verbose_name = '回测结果'
        verbose_name_plural = '回测结果'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.task.name} - {self.get_sample_type_display()} - 夏普:{self.sharpe_ratio}"

    @property
    def total_days(self):
        """计算回测总天数"""
        if self.equity_curve and len(self.equity_curve) > 0:
            return len(self.equity_curve)
        return None

    @property
    def profitable_months(self):
        """计算盈利月数"""
        if not self.monthly_returns:
            return 0
        return sum(1 for ret in self.monthly_returns.values() if ret > 0)

    @property
    def get_risk_level(self):
        """
        根据夏普比率判断风险等级
        """
        if self.sharpe_ratio is None:
            return 'unknown'

        sharpe = float(self.sharpe_ratio)
        if sharpe >= 2.0:
            return 'excellent'
        elif sharpe >= 1.5:
            return 'good'
        elif sharpe >= 1.0:
            return 'acceptable'
        elif sharpe >= 0.5:
            return 'poor'
        else:
            return 'bad'

    def get_consecutive_stats(self):
        """
        计算连续盈亏统计
        """
        if not self.trade_list:
            return {'max_consecutive_wins': 0, 'max_consecutive_losses': 0}

        wins = [t for t in self.trade_list if t.get('pnl', 0) > 0]
        losses = [t for t in self.trade_list if t.get('pnl', 0) <= 0]

        # 计算最大连续次数（简化实现）
        max_consecutive_wins = len(wins)  # 实际应该按时间顺序计算
        max_consecutive_losses = len(losses)

        return {
            'max_consecutive_wins': max_consecutive_wins,
            'max_consecutive_losses': max_consecutive_losses
        }

    def generate_summary_report(self):
        """
        生成回测摘要报告
        """
        return {
            'task_name': self.task.name,
            'strategy_type': self.task.get_strategy_type_display(),
            'sample_type': self.get_sample_type_display(),
            'date_range': f"{self.task.start_date} to {self.task.end_date}",

            # 收益指标
            'total_return': float(self.total_return) if self.total_return else None,
            'annualized_return': float(self.annualized_return) if self.annualized_return else None,
            'excess_return': float(self.excess_return) if self.excess_return else None,

            # 风险指标
            'volatility': float(self.volatility) if self.volatility else None,
            'max_drawdown': float(self.max_drawdown) if self.max_drawdown else None,

            # 风险调整指标
            'sharpe_ratio': float(self.sharpe_ratio) if self.sharpe_ratio else None,
            'sortino_ratio': float(self.sortino_ratio) if self.sortino_ratio else None,
            'calmar_ratio': float(self.calmar_ratio) if self.calmar_ratio else None,

            # 交易统计
            'total_trades': self.total_trades,
            'win_rate': float(self.win_rate) if self.win_rate else None,
            'profit_factor': float(self.profit_factor) if self.profit_factor else None,

            # 过拟合检测
            'is_overfitted': self.is_overfitted,
            'in_out_sharpe_ratio': float(self.in_out_sharpe_ratio) if self.in_out_sharpe_ratio else None,
        }
