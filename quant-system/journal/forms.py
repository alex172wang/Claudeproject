"""
交易记录表单
用于手动交易记录的录入和编辑
"""

from django import forms
from django.utils import timezone
from decimal import Decimal

from portfolio.models import ETF
from monitor.models import Signal
from .models import DecisionLog, DeviationLog, TradeRecord, Position


class TradeRecordForm(forms.ModelForm):
    """
    交易记录表单
    用于手动录入实际交易执行情况
    """

    # 关联信号（可选，如果基于系统信号执行）
    related_signal = forms.ModelChoiceField(
        queryset=Signal.objects.filter(is_active=True),
        required=False,
        label='关联信号',
        widget=forms.Select(attrs={
            'class': 'form-select',
            'data-placeholder': '选择关联的系统信号（可选）'
        })
    )

    # 交易时间
    trade_time = forms.DateTimeField(
        label='交易时间',
        initial=timezone.now,
        widget=forms.DateTimeInput(attrs={
            'class': 'form-control',
            'type': 'datetime-local'
        })
    )

    # 操作类型
    ACTION_CHOICES = [
        ('buy', '买入'),
        ('sell', '卖出'),
        ('add', '加仓'),
        ('reduce', '减仓'),
    ]
    action = forms.ChoiceField(
        label='操作类型',
        choices=ACTION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    # 品种
    etf = forms.ModelChoiceField(
        queryset=ETF.objects.filter(is_active=True),
        label='品种',
        widget=forms.Select(attrs={
            'class': 'form-select',
            'data-placeholder': '选择ETF品种'
        })
    )

    # 数量
    quantity = forms.IntegerField(
        label='数量（股）',
        min_value=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '输入交易数量'
        })
    )

    # 价格
    price = forms.DecimalField(
        label='成交价（元）',
        max_digits=10,
        decimal_places=4,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '输入成交价格',
            'step': '0.0001'
        })
    )

    # 手续费
    commission = forms.DecimalField(
        label='手续费（元）',
        max_digits=10,
        decimal_places=2,
        initial=0,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '输入手续费'
        })
    )

    # 是否与信号一致
    match_signal = forms.BooleanField(
        label='与系统信号一致',
        initial=True,
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )

    # 偏差说明（如果不一致）
    deviation_note = forms.CharField(
        label='偏差说明',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': '如果与信号不一致，请说明原因（如：直觉判断、资金限制、风险控制等）'
        })
    )

    # 交易备注
    note = forms.CharField(
        label='交易备注',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': '其他需要记录的备注信息'
        })
    )

    class Meta:
        model = TradeRecord
        fields = [
            'related_signal', 'trade_time', 'action', 'etf', 'quantity',
            'price', 'commission', 'match_signal', 'deviation_note', 'note'
        ]

    def clean(self):
        """表单验证"""
        cleaned_data = super().clean()
        match_signal = cleaned_data.get('match_signal')
        deviation_note = cleaned_data.get('deviation_note')
        related_signal = cleaned_data.get('related_signal')

        # 如果选择了关联信号但与信号不一致，必须填写偏差说明
        if related_signal and not match_signal and not deviation_note:
            self.add_error('deviation_note', '与信号不一致时，必须填写偏差说明')

        return cleaned_data


class DeviationLogForm(forms.ModelForm):
    """
    偏差日志表单
    用于记录系统决策与实际执行的偏差
    """

    class Meta:
        model = DeviationLog
        fields = [
            'system_decision', 'actual_decision', 'deviation_type',
            'description', 'reason', 'verification_result', 'verification_notes'
        ]
        widgets = {
            'system_decision': forms.Select(attrs={'class': 'form-select'}),
            'actual_decision': forms.Select(attrs={'class': 'form-select'}),
            'deviation_type': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': '描述偏差的详细情况'
            }),
            'reason': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': '说明产生偏差的原因（主观/客观）'
            }),
            'verification_result': forms.Select(attrs={'class': 'form-select'}),
            'verification_notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': '验证过程的详细记录'
            }),
        }


class QuickDeviationLogForm(forms.Form):
    """
    快速偏差记录表单
    用于快速记录与系统信号的执行偏差
    """

    signal = forms.ModelChoiceField(
        queryset=Signal.objects.filter(is_active=True),
        label='关联信号',
        widget=forms.Select(attrs={
            'class': 'form-select',
            'data-placeholder': '选择系统生成的信号'
        })
    )

    DEVIATION_TYPE_CHOICES = [
        ('override', '人工覆盖'),
        ('delayed', '延迟执行'),
        ('skipped', '跳过交易'),
        ('modified', '修改参数'),
        ('additional', '额外交易'),
    ]
    deviation_type = forms.ChoiceField(
        label='偏差类型',
        choices=DEVIATION_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    reason = forms.CharField(
        label='偏差原因',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': '说明为什么偏离系统信号（如：直觉判断、资金限制、风险控制、对信号不认同等）'
        })
    )

    actual_action = forms.ChoiceField(
        label='实际操作',
        choices=TradeRecordForm.ACTION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    etf = forms.ModelChoiceField(
        queryset=ETF.objects.filter(is_active=True),
        label='品种',
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    quantity = forms.IntegerField(
        label='数量',
        min_value=0,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '实际交易数量'
        })
    )

    price = forms.DecimalField(
        label='成交价格',
        max_digits=10,
        decimal_places=4,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '实际成交价格',
            'step': '0.0001'
        })
    )

    note = forms.CharField(
        label='补充说明',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': '其他需要记录的信息'
        })
    )

    def clean(self):
        """表单验证"""
        cleaned_data = super().clean()
        actual_action = cleaned_data.get('actual_action')
        etf = cleaned_data.get('etf')
        quantity = cleaned_data.get('quantity')
        price = cleaned_data.get('price')

        # 如果是交易操作（买入/卖出/加仓/减仓），必须填写交易详情
        if actual_action in ['buy', 'sell', 'add', 'reduce']:
            if not etf:
                self.add_error('etf', '交易操作必须选择品种')
            if not quantity:
                self.add_error('quantity', '交易操作必须填写数量')
            if not price:
                self.add_error('price', '交易操作必须填写价格')

        return cleaned_data
