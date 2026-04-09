"""
交易记录Dashboard页面
用于展示和管理手动交易记录
"""

import dash
from dash import dcc, html, dash_table, Input, Output, State, callback_context
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import pandas as pd

from django.utils import timezone
from django.db.models import Sum, Count, Avg, Q

from ...journal.models import TradeRecord, Position
from ...portfolio.models import ETF


# 主题配置（与charts.py保持一致）
THEME = {
    'bg_dark': '#1a1a2e',
    'bg_card': '#16213e',
    'bg_light': '#0f3460',
    'primary': '#e94560',
    'secondary': '#00d9ff',
    'accent': '#ffd700',
    'success': '#28a745',
    'warning': '#ffc107',
    'danger': '#dc3545',
    'text': '#ffffff',
    'text_muted': '#a0a0a0',
    'border': '#2a2a4a',
}


def create_layout():
    """创建页面布局"""
    return dbc.Container([
        # 标题栏
        dbc.Row([
            dbc.Col([
                html.H2("交易记录管理", className="mb-0"),
                html.P("手动记录和追踪您的实际交易执行情况",
                       className="text-muted mb-0")
            ], width=8),
            dbc.Col([
                dbc.Button(
                    [html.I(className="fas fa-plus me-2"), "录入交易"],
                    id="btn-add-trade",
                    color="primary",
                    className="w-100"
                )
            ], width=4, className="d-flex align-items-center"),
        ], className="mb-4"),

        # 统计卡片
        dbc.Row(id="trade-stats-cards", className="mb-4"),

        # 主内容区
        dbc.Row([
            # 左侧：筛选和图表
            dbc.Col([
                # 筛选面板
                dbc.Card([
                    dbc.CardHeader([html.I(className="fas fa-filter me-2"), "筛选条件"]),
                    dbc.CardBody([
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("品种"),
                                dcc.Dropdown(
                                    id="filter-etf",
                                    options=[],
                                    placeholder="选择品种",
                                    multi=True,
                                    className="dash-dropdown",
                                    style={'backgroundColor': '#2d2d2d', 'color': 'white'},
                                )
                            ], width=6),
                            dbc.Col([
                                dbc.Label("操作类型"),
                                dcc.Dropdown(
                                    id="filter-action",
                                    options=[
                                        {'label': '买入', 'value': 'buy'},
                                        {'label': '卖出', 'value': 'sell'},
                                        {'label': '加仓', 'value': 'add'},
                                        {'label': '减仓', 'value': 'reduce'},
                                    ],
                                    placeholder="选择操作",
                                    multi=True,
                                    style={'backgroundColor': '#2d2d2d', 'color': 'white'},
                                )
                            ], width=6),
                        ], className="mb-3"),
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("时间范围"),
                                dcc.DatePickerRange(
                                    id='filter-date-range',
                                    start_date_placeholder_text='开始日期',
                                    end_date_placeholder_text='结束日期',
                                    display_format='YYYY-MM-DD',
                                    style={'backgroundColor': '#2d2d2d', 'color': 'white'},
                                )
                            ], width=12),
                        ], className="mb-3"),
                        dbc.Row([
                            dbc.Col([
                                dbc.Checklist(
                                    options=[{"label": "仅显示与信号不一致的记录", "value": 1}],
                                    id="filter-mismatch-only",
                                    switch=True
                                )
                            ], width=12),
                        ]),
                    ])
                ], className="mb-3"),

                # 图表
                dbc.Card([
                    dbc.CardHeader([html.I(className="fas fa-chart-pie me-2"), "交易分析"]),
                    dbc.CardBody([
                        dcc.Tabs([
                            dcc.Tab(label="按品种", children=[
                                dcc.Graph(id="chart-by-etf", config={'displayModeBar': False})
                            ]),
                            dcc.Tab(label="按时间", children=[
                                dcc.Graph(id="chart-by-time", config={'displayModeBar': False})
                            ]),
                            dcc.Tab(label="信号匹配", children=[
                                dcc.Graph(id="chart-signal-match", config={'displayModeBar': False})
                            ]),
                        ])
                    ])
                ]),
            ], width=4),

            # 右侧：交易列表
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        dbc.Row([
                            dbc.Col([
                                html.Span([html.I(className="fas fa-list me-2"), "交易记录"])
                            ], width=6),
                            dbc.Col([
                                dbc.ButtonGroup([
                                    dbc.Button("导出", id="btn-export", size="sm", color="secondary"),
                                    dbc.Button("批量删除", id="btn-batch-delete", size="sm", color="danger"),
                                ])
                            ], width=6, className="text-end"),
                        ])
                    ]),
                    dbc.CardBody([
                        # 数据表格
                        dash_table.DataTable(
                            id='trade-table',
                            columns=[
                                {'name': '时间', 'id': 'trade_time'},
                                {'name': '品种', 'id': 'etf'},
                                {'name': '操作', 'id': 'action'},
                                {'name': '数量', 'id': 'quantity'},
                                {'name': '价格', 'id': 'price'},
                                {'name': '金额', 'id': 'total_amount'},
                                {'name': '信号一致', 'id': 'match_signal'},
                                {'name': '操作', 'id': 'actions'},
                            ],
                            data=[],
                            row_selectable='multi',
                            selected_rows=[],
                            page_action='native',
                            page_size=15,
                            style_table={'overflowX': 'auto'},
                            style_cell={'textAlign': 'left', 'padding': '10px'},
                            style_header={
                                'backgroundColor': THEME['bg_card'],
                                'color': THEME['text'],
                                'fontWeight': 'bold',
                                'border': f'1px solid {THEME["border"]}',
                            },
                            style_data={
                                'backgroundColor': THEME['bg_dark'],
                                'color': THEME['text'],
                                'border': f'1px solid {THEME["border"]}',
                            },
                            style_data_conditional=[
                                {
                                    'if': {'column_id': 'action', 'filter_query': '{action} eq "买入"'},
                                    'color': THEME['success'],
                                },
                                {
                                    'if': {'column_id': 'action', 'filter_query': '{action} eq "卖出"'},
                                    'color': THEME['danger'],
                                },
                            ],
                        ),
                    ])
                ])
            ], width=8),
        ]),

        # 录入交易模态框
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle("录入交易记录")),
            dbc.ModalBody(id="modal-trade-form"),
            dbc.ModalFooter([
                dbc.Button("取消", id="btn-modal-cancel", color="secondary"),
                dbc.Button("保存", id="btn-modal-save", color="primary"),
            ]),
        ], id="modal-add-trade", size="lg", is_open=False),

        # 数据存储
        dcc.Store(id='store-trade-data'),
        dcc.Store(id='store-selected-rows'),

    ], fluid=True, className="py-4")


# ==================== 回调函数 ====================

def register_callbacks(app):
    """注册回调函数"""

    @app.callback(
        Output('trade-stats-cards', 'children'),
        Input('store-trade-data', 'data')
    )
    def update_stats_cards(data):
        """更新统计卡片"""
        # 这里应该从后端API获取统计数据
        # 现在使用示例数据

        stats = [
            {
                'title': '本月交易',
                'value': '12笔',
                'change': '+3',
                'color': 'primary',
                'icon': 'exchange-alt'
            },
            {
                'title': '总金额',
                'value': '¥128,500',
                'change': '+15.3%',
                'color': 'success',
                'icon': 'money-bill-wave'
            },
            {
                'title': '信号匹配率',
                'value': '85%',
                'change': '+5%',
                'color': 'info',
                'icon': 'check-circle'
            },
            {
                'title': '直觉胜率',
                'value': '68%',
                'change': '-2%',
                'color': 'warning',
                'icon': 'brain'
            },
        ]

        cards = []
        for stat in stats:
            cards.append(
                dbc.Col(
                    dbc.Card([
                        dbc.CardBody([
                            html.Div([
                                html.I(className=f"fas fa-{stat['icon']} fa-2x"),
                            ], className="float-end text-muted"),
                            html.H4(stat['value'], className="mt-2"),
                            html.P(stat['title'], className="text-muted mb-1"),
                            html.Small([
                                html.I(className=f"fas fa-arrow-{'up' if '+' in stat['change'] else 'down'} me-1"),
                                stat['change']
                            ], className=f"text-{'success' if '+' in stat['change'] else 'danger'}"),
                        ])
                    ], className=f"border-start border-4 border-{stat['color']}"),
                    width=3
                )
            )

        return cards

    @app.callback(
        [Output('modal-add-trade', 'is_open'),
         Output('modal-trade-form', 'children')],
        [Input('btn-add-trade', 'n_clicks'),
         Input('btn-modal-cancel', 'n_clicks')],
        prevent_initial_call=True
    )
    def toggle_modal(add_clicks, cancel_clicks):
        """切换模态框显示"""
        ctx = callback_context
        if not ctx.triggered:
            return False, ""

        button_id = ctx.triggered[0]['prop_id'].split('.')[0]

        if button_id == 'btn-add-trade':
            # 返回表单HTML
            # 这里应该使用Django的form渲染
            form_html = html.Div([
                dbc.Form([
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("关联信号", html_for="related_signal"),
                            dcc.Dropdown(
                                id="related_signal",
                                options=[],
                                placeholder="选择关联的系统信号（可选）",
                                style={'backgroundColor': '#2d2d2d', 'color': 'white'},
                            ),
                        ], width=6),
                        dbc.Col([
                            dbc.Label("交易时间", html_for="trade_time"),
                            dbc.Input(
                                type="datetime-local",
                                id="trade_time",
                                value=datetime.now().strftime('%Y-%m-%dT%H:%M'),
                                style={'backgroundColor': '#2d2d2d', 'color': 'white'},
                            ),
                        ], width=6),
                    ], className="mb-3"),

                    dbc.Row([
                        dbc.Col([
                            dbc.Label("操作类型*", html_for="action"),
                            dcc.Dropdown(
                                id="action",
                                options=[
                                    {'label': '买入', 'value': 'buy'},
                                    {'label': '卖出', 'value': 'sell'},
                                    {'label': '加仓', 'value': 'add'},
                                    {'label': '减仓', 'value': 'reduce'},
                                ],
                                placeholder="选择操作类型",
                                style={'backgroundColor': '#2d2d2d', 'color': 'white'},
                            ),
                        ], width=6),
                        dbc.Col([
                            dbc.Label("品种*", html_for="etf"),
                            dcc.Dropdown(
                                id="etf",
                                options=[],  # 从后端加载
                                placeholder="选择ETF品种",
                                style={'backgroundColor': '#2d2d2d', 'color': 'white'},
                            ),
                        ], width=6),
                    ], className="mb-3"),

                    dbc.Row([
                        dbc.Col([
                            dbc.Label("数量*", html_for="quantity"),
                            dbc.Input(
                                type="number",
                                id="quantity",
                                placeholder="输入交易数量",
                                min=1,
                                style={'backgroundColor': '#2d2d2d', 'color': 'white'},
                            ),
                        ], width=4),
                        dbc.Col([
                            dbc.Label("成交价格*", html_for="price"),
                            dbc.Input(
                                type="number",
                                id="price",
                                placeholder="输入成交价格",
                                step=0.0001,
                                style={'backgroundColor': '#2d2d2d', 'color': 'white'},
                            ),
                        ], width=4),
                        dbc.Col([
                            dbc.Label("手续费", html_for="commission"),
                            dbc.Input(
                                type="number",
                                id="commission",
                                placeholder="输入手续费",
                                value=0,
                                style={'backgroundColor': '#2d2d2d', 'color': 'white'},
                            ),
                        ], width=4),
                    ], className="mb-3"),

                    dbc.Row([
                        dbc.Col([
                            dbc.Checklist(
                                options=[{"label": "与系统信号一致", "value": True}],
                                id="match_signal",
                                value=[True],
                                switch=True
                            ),
                        ], width=12),
                    ], className="mb-3"),

                    # 偏差说明（条件显示）
                    html.Div(id="deviation-note-container", children=[
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("偏差说明*", html_for="deviation_note"),
                                dbc.Textarea(
                                    id="deviation_note",
                                    placeholder="说明为什么与系统信号不一致（如：直觉判断、资金限制、风险控制等）",
                                    rows=3
                                ),
                            ], width=12),
                        ]),
                    ], style={"display": "none"}),

                    dbc.Row([
                        dbc.Col([
                            dbc.Label("交易备注", html_for="note"),
                            dbc.Textarea(
                                id="note",
                                placeholder="其他需要记录的备注信息",
                                rows=2
                            ),
                        ], width=12),
                    ]),
                ])
            ])
            return True, form_html

        return False, ""

    @app.callback(
        Output("deviation-note-container", "style"),
        [Input("match_signal", "value")]
    )
    def toggle_deviation_note(match_signal):
        """切换偏差说明显示"""
        if match_signal and True in match_signal:
            return {"display": "none"}
        return {"display": "block"}
