"""
偏差日志Dashboard页面
用于可视化展示L5偏差日志的统计分析和验证管理
"""

import dash
from dash import dcc, html, dash_table, Input, Output, State, callback_context
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import pandas as pd

# 主题配置
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
                html.H2("偏差日志与验证", className="mb-0"),
                html.P("记录和分析决策偏差，验证直觉准确率",
                       className="text-muted mb-0")
            ], width=8),
            dbc.Col([
                dbc.Button(
                    [html.I(className="fas fa-clipboard-check me-2"), "待验证偏差"],
                    id="btn-pending-verifications",
                    color="warning",
                    className="w-100"
                )
            ], width=4, className="d-flex align-items-center"),
        ], className="mb-4"),

        # 直觉胜率卡片
        dbc.Row(id="intuition-score-cards", className="mb-4"),

        # 主内容区
        dbc.Tabs([
            # Tab 1: 概览
            dbc.Tab(label="概览", children=[
                dbc.Row([
                    # 左侧：统计数据
                    dbc.Col([
                        dbc.Card([
                            dbc.CardHeader([html.I(className="fas fa-chart-pie me-2"), "偏差统计"]),
                            dbc.CardBody([
                                dcc.Graph(id="deviation-type-chart", config={'displayModeBar': False}),
                            ])
                        ], className="mb-3"),

                        dbc.Card([
                            dbc.CardHeader([html.I(className="fas fa-check-double me-2"), "验证状态"]),
                            dbc.CardBody([
                                dcc.Graph(id="verification-status-chart", config={'displayModeBar': False}),
                            ])
                        ]),
                    ], width=5),

                    # 右侧：时间序列和盈亏
                    dbc.Col([
                        dbc.Card([
                            dbc.CardHeader([html.I(className="fas fa-calendar-alt me-2"), "偏差趋势"]),
                            dbc.CardBody([
                                dcc.Graph(id="deviation-trend-chart", config={'displayModeBar': False}),
                            ])
                        ], className="mb-3"),

                        dbc.Card([
                            dbc.CardHeader([html.I(className="fas fa-dollar-sign me-2"), "盈亏差异"]),
                            dbc.CardBody([
                                dcc.Graph(id="pnl-difference-chart", config={'displayModeBar': False}),
                            ])
                        ]),
                    ], width=7),
                ]),
            ]),

            # Tab 2: 偏差类型分析
            dbc.Tab(label="类型分析", children=[
                dbc.Row([
                    dbc.Col([
                        dbc.Card([
                            dbc.CardHeader([html.I(className="fas fa-th-large me-2"), "各类型直觉胜率"]),
                            dbc.CardBody([
                                dcc.Graph(id="type-accuracy-chart", config={'displayModeBar': False}),
                            ])
                        ], className="mb-3"),
                    ], width=6),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardHeader([html.I(className="fas fa-list-alt me-2"), "类型详情"]),
                            dbc.CardBody(id="type-details-table")
                        ], className="mb-3"),
                    ], width=6),
                ]),

                dbc.Row([
                    dbc.Col([
                        dbc.Card([
                            dbc.CardHeader([html.I(className="fas fa-calendar-week me-2"), "类型趋势"]),
                            dbc.CardBody([
                                dcc.Graph(id="type-trend-chart", config={'displayModeBar': False}),
                            ])
                        ]),
                    ], width=12),
                ]),
            ]),

            # Tab 3: 待验证列表
            dbc.Tab(label="待验证", children=[
                dbc.Row([
                    dbc.Col([
                        dbc.Card([
                            dbc.CardHeader([
                                dbc.Row([
                                    dbc.Col([
                                        html.Span([html.I(className="fas fa-clock me-2"), "待验证偏差"])
                                    ], width=6),
                                    dbc.Col([
                                        dbc.Badge("3个待验证", color="warning", className="me-2"),
                                        dbc.Badge("1个即将过期", color="danger"),
                                    ], width=6, className="text-end"),
                                ])
                            ]),
                            dbc.CardBody([
                                dash_table.DataTable(
                                    id='pending-verification-table',
                                    columns=[
                                        {'name': '偏差时间', 'id': 'timestamp'},
                                        {'name': '类型', 'id': 'deviation_type'},
                                        {'name': '系统建议', 'id': 'system_action'},
                                        {'name': '您的操作', 'id': 'actual_action'},
                                        {'name': '剩余时间', 'id': 'time_remaining'},
                                        {'name': '操作', 'id': 'actions'},
                                    ],
                                    data=[
                                        {
                                            'timestamp': '2026-03-25 14:30',
                                            'deviation_type': '跳过交易',
                                            'system_action': '买入 510300',
                                            'actual_action': '未执行',
                                            'time_remaining': '1天',
                                            'actions': '[立即验证]'
                                        },
                                        {
                                            'timestamp': '2026-03-26 10:15',
                                            'deviation_type': '人工覆盖',
                                            'system_action': '买入 510500',
                                            'actual_action': '卖出',
                                            'time_remaining': '2天',
                                            'actions': '[立即验证]'
                                        },
                                    ],
                                    style_table={'overflowX': 'auto'},
                                    style_cell={'textAlign': 'left', 'padding': '10px'},
                                    style_header={
                                        'backgroundColor': THEME['bg_card'],
                                        'color': THEME['text'],
                                        'fontWeight': 'bold',
                                    },
                                    style_data={
                                        'backgroundColor': THEME['bg_dark'],
                                        'color': THEME['text'],
                                    },
                                ),
                            ])
                        ]),
                    ], width=12),
                ]),
            ]),

            # Tab 4: 验证历史
            dbc.Tab(label="验证历史", children=[
                dbc.Row([
                    dbc.Col([
                        dbc.Card([
                            dbc.CardHeader([html.I(className="fas fa-history me-2"), "验证历史记录"]),
                            dbc.CardBody([
                                dash_table.DataTable(
                                    id='verification-history-table',
                                    columns=[
                                        {'name': '验证时间', 'id': 'verified_at'},
                                        {'name': '偏差类型', 'id': 'deviation_type'},
                                        {'name': '验证结果', 'id': 'verification_result'},
                                        {'name': '盈亏差异', 'id': 'pnl_difference'},
                                        {'name': '查看', 'id': 'view'},
                                    ],
                                    data=[],
                                    page_action='native',
                                    page_size=10,
                                ),
                            ])
                        ]),
                    ], width=12),
                ]),
            ]),
        ], className="mb-4"),

        # 验证模态框
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle("完成偏差验证")),
            dbc.ModalBody(id="modal-verification-content"),
            dbc.ModalFooter([
                dbc.Button("取消", id="btn-verification-cancel", color="secondary"),
                dbc.Button("提交验证", id="btn-verification-submit", color="primary"),
            ]),
        ], id="modal-verification", size="lg", is_open=False),

    ], fluid=True, className="py-4")


def register_callbacks(app):
    """注册回调函数"""

    @app.callback(
        Output('intuition-score-cards', 'children'),
        Input('url', 'pathname')
    )
    def update_intuition_cards(pathname):
        """更新直觉胜率卡片"""
        # 这里应该从后端API获取数据
        # 现在使用示例数据

        cards = [
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H3("68%", className="text-warning mb-2"),
                        html.P("总体直觉胜率", className="text-muted mb-1"),
                        html.Small([
                            html.I(className="fas fa-arrow-up me-1"),
                            "较上月 +3%"
                        ], className="text-success"),
                    ])
                ], className="border-start border-4 border-warning h-100")
            ], width=3),

            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H3("72%", className="text-success mb-2"),
                        html.P("人工覆盖准确率", className="text-muted mb-1"),
                        html.Small("优势领域", className="text-info"),
                    ])
                ], className="border-start border-4 border-success h-100")
            ], width=3),

            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H3("45%", className="text-danger mb-2"),
                        html.P("修改参数准确率", className="text-muted mb-1"),
                        html.Small("需改进", className="text-warning"),
                    ])
                ], className="border-start border-4 border-danger h-100")
            ], width=3),

            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H3("+¥2,350", className="text-success mb-2"),
                        html.P("累计盈亏差异", className="text-muted mb-1"),
                        html.Small("因偏离多盈利", className="text-success"),
                    ])
                ], className="border-start border-4 border-info h-100")
            ], width=3),
        ]

        return cards
