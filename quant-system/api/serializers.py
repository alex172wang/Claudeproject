"""
API 序列化器
"""

from rest_framework import serializers
from portfolio.models import ETF
from backtest.models import BacktestTask, BacktestResult
from journal.models import DecisionLog, DeviationLog


class ETFSerializer(serializers.ModelSerializer):
    """ETF 序列化器"""

    category_display = serializers.CharField(source='get_category_display', read_only=True)
    market_display = serializers.CharField(source='get_market_display', read_only=True)

    class Meta:
        model = ETF
        fields = [
            'code', 'name', 'category', 'category_display',
            'market', 'market_display', 'tracking_index',
            'is_active', 'created_at', 'updated_at'
        ]


class ETFPriceSerializer(serializers.Serializer):
    """ETF 价格数据序列化器"""
    code = serializers.CharField()
    name = serializers.CharField()
    current_price = serializers.DecimalField(max_digits=10, decimal_places=3)
    change = serializers.DecimalField(max_digits=10, decimal_places=3)
    change_percent = serializers.DecimalField(max_digits=6, decimal_places=2)
    volume = serializers.IntegerField()
    turnover = serializers.DecimalField(max_digits=15, decimal_places=2)
    update_time = serializers.DateTimeField()


class KlineDataSerializer(serializers.Serializer):
    """K线数据序列化器"""
    date = serializers.DateField()
    open = serializers.DecimalField(max_digits=10, decimal_places=3)
    high = serializers.DecimalField(max_digits=10, decimal_places=3)
    low = serializers.DecimalField(max_digits=10, decimal_places=3)
    close = serializers.DecimalField(max_digits=10, decimal_places=3)
    volume = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=15, decimal_places=2, required=False)


class PortfolioSummarySerializer(serializers.Serializer):
    """投资组合汇总序列化器"""
    total_assets = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_return = serializers.DecimalField(max_digits=10, decimal_places=2)
    sharpe_ratio = serializers.DecimalField(max_digits=5, decimal_places=2)
    max_drawdown = serializers.DecimalField(max_digits=5, decimal_places=2)
    update_time = serializers.DateTimeField()


class PositionSerializer(serializers.Serializer):
    """持仓序列化器"""
    code = serializers.CharField()
    name = serializers.CharField()
    quantity = serializers.IntegerField()
    avg_price = serializers.DecimalField(max_digits=10, decimal_places=3)
    current_price = serializers.DecimalField(max_digits=10, decimal_places=3)
    market_value = serializers.DecimalField(max_digits=15, decimal_places=2)
    pnl = serializers.DecimalField(max_digits=15, decimal_places=2)
    pnl_percent = serializers.DecimalField(max_digits=6, decimal_places=2)


# Backtest Serializers
class BacktestTaskSerializer(serializers.ModelSerializer):
    """回测任务序列化器"""

    class Meta:
        model = BacktestTask
        fields = '__all__'


class BacktestResultSerializer(serializers.ModelSerializer):
    """回测结果序列化器"""

    class Meta:
        model = BacktestResult
        fields = '__all__'


# Monitor Serializers (简化版)
class SignalSerializer(serializers.Serializer):
    """信号序列化器（简化）"""
    id = serializers.IntegerField()
    code = serializers.CharField()
    name = serializers.CharField()
    signal_type = serializers.CharField()
    status = serializers.CharField()
    generated_at = serializers.DateTimeField()


class AlertSerializer(serializers.Serializer):
    """预警序列化器（简化）"""
    id = serializers.IntegerField()
    title = serializers.CharField()
    message = serializers.CharField()
    severity = serializers.CharField()
    created_at = serializers.DateTimeField()
    is_acknowledged = serializers.BooleanField()


# Journal Serializers
class DecisionLogSerializer(serializers.ModelSerializer):
    """决策日志序列化器"""

    class Meta:
        model = DecisionLog
        fields = '__all__'


class DeviationLogSerializer(serializers.ModelSerializer):
    """偏差日志序列化器"""

    class Meta:
        model = DeviationLog
        fields = '__all__'
