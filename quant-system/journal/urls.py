"""
journal 模块 URL 配置
交易记录、偏差日志相关路由
"""

from django.urls import path

from . import views

app_name = 'journal'

urlpatterns = [
    # 交易记录列表
    path('trades/',
         views.TradeRecordListView.as_view(),
         name='trade_record_list'),

    # 交易记录详情
    path('trades/<int:pk>/',
         views.TradeRecordDetailView.as_view(),
         name='trade_record_detail'),

    # 创建交易记录
    path('trades/create/',
         views.TradeRecordCreateView.as_view(),
         name='trade_record_create'),

    # 编辑交易记录
    path('trades/<int:pk>/edit/',
         views.TradeRecordUpdateView.as_view(),
         name='trade_record_update'),

    # 删除交易记录
    path('trades/<int:pk>/delete/',
         views.TradeRecordDeleteView.as_view(),
         name='trade_record_delete'),

    # API: 交易统计
    path('api/trades/stats/',
         views.TradeRecordStatsView.as_view(),
         name='trade_record_stats'),

    # API: 快速记录交易
    path('api/trades/quick-log/',
         views.QuickTradeLogView.as_view(),
         name='quick_trade_log'),
]
