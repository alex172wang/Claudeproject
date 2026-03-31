"""
投资组合模型定义
包含ETF品种、品种池、池成员等模型
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class ETF(models.Model):
    """
    ETF品种定义
    存储所有ETF的基础信息
    """

    # 代码和名称
    code = models.CharField(
        'ETF代码',
        max_length=10,
        primary_key=True,
        help_text='ETF代码，如510300'
    )
    name = models.CharField(
        'ETF名称',
        max_length=100,
        help_text='ETF名称，如沪深300ETF'
    )

    # 市场信息
    MARKET_CHOICES = [
        ('SH', '上海证券交易所'),
        ('SZ', '深圳证券交易所'),
    ]
    market = models.CharField(
        '所属市场',
        max_length=2,
        choices=MARKET_CHOICES,
        help_text='ETF上市市场'
    )

    # ETF分类
    CATEGORY_CHOICES = [
        ('equity', '权益型'),
        ('bond', '债券型'),
        ('commodity', '商品型'),
        ('money_market', '货币市场型'),
        ('cross_border', '跨境型'),
        ('sector', '行业主题型'),
    ]
    category = models.CharField(
        'ETF类别',
        max_length=20,
        choices=CATEGORY_CHOICES,
        help_text='ETF基金类别'
    )

    # 跟踪信息
    tracking_index = models.CharField(
        '跟踪指数',
        max_length=100,
        blank=True,
        help_text='ETF跟踪的指数名称'
    )
    tracking_index_code = models.CharField(
        '跟踪指数代码',
        max_length=20,
        blank=True,
        help_text='跟踪指数代码'
    )

    # 管理信息
    fund_manager = models.CharField(
        '基金管理人',
        max_length=100,
        blank=True,
        help_text='ETF管理人'
    )
    expense_ratio = models.DecimalField(
        '管理费率',
        max_digits=5,
        decimal_places=4,
        null=True,
        blank=True,
        help_text='年化管理费率'
    )

    # 状态
    is_active = models.BooleanField(
        '是否活跃',
        default=True,
        help_text='ETF是否在交易'
    )
    list_date = models.DateField(
        '上市日期',
        null=True,
        blank=True,
        help_text='ETF上市日期'
    )

    # 元数据
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = 'ETF品种'
        verbose_name_plural = 'ETF品种'
        ordering = ['code']

    def __str__(self):
        return f"{self.code} - {self.name}"

    @property
    def market_display(self):
        """获取市场显示名称"""
        return dict(self.MARKET_CHOICES).get(self.market, self.market)

    @property
    def category_display(self):
        """获取类别显示名称"""
        return dict(self.CATEGORY_CHOICES).get(self.category, self.category)


class Pool(models.Model):
    """
    品种池定义
    定义一个可供策略使用的ETF组合
    """

    # 池基本信息
    code = models.CharField(
        '池代码',
        max_length=20,
        primary_key=True,
        help_text='品种池唯一标识'
    )
    name = models.CharField(
        '池名称',
        max_length=100,
        help_text='品种池显示名称'
    )
    description = models.TextField(
        '池描述',
        blank=True,
        help_text='品种池的详细描述'
    )

    # 池用途
    PURPOSE_CHOICES = [
        ('rotation', 'ETF轮动'),
        ('permanent', '永久组合'),
        ('thematic', '主题仓位'),
        ('custom', '自定义'),
    ]
    purpose = models.CharField(
        '池用途',
        max_length=20,
        choices=PURPOSE_CHOICES,
        help_text='品种池的使用目的'
    )

    # 池配置
    asset_classes = models.JSONField(
        '资产类别配置',
        default=dict,
        blank=True,
        help_text='各资产类别的目标配置比例，如{"equity": 0.4, "bond": 0.3}'
    )

    # 状态
    is_active = models.BooleanField(
        '是否启用',
        default=True,
        help_text='品种池是否可用'
    )
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '品种池'
        verbose_name_plural = '品种池'
        ordering = ['code']

    def __str__(self):
        return f"{self.code} - {self.name}"

    @property
    def member_count(self):
        """获取池成员数量"""
        return self.members.count()

    @property
    def purpose_display(self):
        """获取用途显示名称"""
        return dict(self.PURPOSE_CHOICES).get(self.purpose, self.purpose)


class PoolMember(models.Model):
    """
    品种池成员
    定义池中包含的ETF及其权重、阈值等参数
    """

    # 关联
    pool = models.ForeignKey(
        Pool,
        on_delete=models.CASCADE,
        related_name='members',
        verbose_name='所属池'
    )
    etf = models.ForeignKey(
        ETF,
        on_delete=models.CASCADE,
        related_name='pool_memberships',
        verbose_name='ETF品种'
    )

    # 权重和配置
    weight = models.DecimalField(
        '目标权重',
        max_digits=5,
        decimal_places=4,
        default=0.0,
        validators=[MinValueValidator(0), MaxValueValidator(1)],
        help_text='该ETF在池中的目标配置比例（0-1）'
    )

    # 阈值配置
    thresholds = models.JSONField(
        '阈值配置',
        default=dict,
        blank=True,
        help_text='该ETF的自定义阈值配置，如{"L1-02": {"ema_period": 60}}'
    )

    # 筛选条件
    filters = models.JSONField(
        '筛选条件',
        default=dict,
        blank=True,
        help_text='该ETF的筛选条件，如{"min_volume": 1000000, "min_price": 1.0}'
    )

    # 顺序
    order = models.PositiveIntegerField(
        '排序',
        default=0,
        help_text='池中显示顺序'
    )

    # 状态
    is_active = models.BooleanField(
        '是否启用',
        default=True,
        help_text='该成员是否参与计算'
    )
    notes = models.TextField(
        '备注',
        blank=True,
        help_text='该成员的备注说明'
    )
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '池成员'
        verbose_name_plural = '池成员'
        ordering = ['pool', 'order', 'etf']
        unique_together = ['pool', 'etf']  # 一个池中同一只ETF只能出现一次

    def __str__(self):
        return f"{self.pool.code} - {self.etf.code} ({self.weight:.2%})"

    @property
    def etf_name(self):
        """获取ETF名称"""
        return self.etf.name

    @property
    def etf_category(self):
        """获取ETF类别"""
        return self.etf.category


class ETFPrice(models.Model):
    """
    ETF历史价格数据
    用于本地缓存和快速查询
    """

    etf = models.ForeignKey(
        ETF,
        on_delete=models.CASCADE,
        related_name='prices',
        verbose_name='ETF'
    )
    date = models.DateField('日期')

    # 价格数据
    open_price = models.DecimalField('开盘价', max_digits=12, decimal_places=4)
    high_price = models.DecimalField('最高价', max_digits=12, decimal_places=4)
    low_price = models.DecimalField('最低价', max_digits=12, decimal_places=4)
    close_price = models.DecimalField('收盘价', max_digits=12, decimal_places=4)

    # 成交量和成交额
    volume = models.BigIntegerField('成交量', default=0)
    amount = models.DecimalField('成交额', max_digits=20, decimal_places=4, null=True, blank=True)

    # 复权因子
    adj_factor = models.DecimalField('复权因子', max_digits=12, decimal_places=6, default=1.0)

    # 元数据
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = 'ETF价格数据'
        verbose_name_plural = 'ETF价格数据'
        ordering = ['etf', '-date']
        unique_together = ['etf', 'date']
        indexes = [
            models.Index(fields=['etf', 'date']),
            models.Index(fields=['date']),
        ]

    def __str__(self):
        return f"{self.etf.code} - {self.date} - 收盘价:{self.close_price}"

    @property
    def price_change(self):
        """计算涨跌额"""
        # 这里应该查询前一日收盘价，简单实现
        return None

    @property
    def price_change_pct(self):
        """计算涨跌幅百分比"""
        # 这里应该查询前一日收盘价
        return None

    @classmethod
    def get_latest_price(cls, etf_code: str):
        """
        获取最新价格

        Args:
            etf_code: ETF代码

        Returns:
            ETFPrice: 最新的价格记录
        """
        try:
            return cls.objects.filter(etf__code=etf_code).first()
        except Exception:
            return None

    @classmethod
    def get_price_series(
        cls,
        etf_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ):
        """
        获取价格序列

        Args:
            etf_code: ETF代码
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            QuerySet: 价格记录集合
        """
        queryset = cls.objects.filter(etf__code=etf_code)

        if start_date:
            queryset = queryset.filter(date__gte=start_date)
        if end_date:
            queryset = queryset.filter(date__lte=end_date)

        return queryset.order_by('date')
