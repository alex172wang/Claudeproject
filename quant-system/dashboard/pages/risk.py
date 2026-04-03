"""
风险控制监控页面

提供实时风险监控、风险告警、风险历史等功能。
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any

import dash_bootstrap_components as dbc
from dash import html, dcc, dash_table
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

# 导入主题配置
try:
    from ..config import THEME
except ImportError:
    # 绝对导入备用
    import sys
    import os
    dashboard_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if dashboard_dir not in sys.path:
        sys.path.insert(0, dashboard_dir)
    from config import THEME


def create_risk_tab() -> html.Div:
    """创建风险控制监控标签页"""

    return html.Div([
        # 第一行：风险概览卡片
        dbc.Row([
            dbc.Col(create_risk_overview_card("整体风险等级", "中等", "#ffc107", "建议关注"), width=3),
            dbc.Col(create_risk_overview_card("仓位使用率", "68.5%", "#28a745", "正常范围"), width=3),
            dbc.Col(create_risk_overview_card("日回撤", "-1.23%", "#28a745", "在限额内"), width=3),
            dbc.Col(create_risk_overview_card("未处理告警", "2", "#ffc107", "需要关注"), width=3),
        ], className="mb-4"),

        # 第二行：风险限额监控
        dbc.Row([
            dbc.Col(
                dbc.Card(
                    [
                        dbc.CardHeader([
                            html.H5("风险限额监控", className="mb-0"),
                            dbc.Button("配置规则", size="sm", color="outline-primary"),
                        ], className="d-flex justify-content-between align-items-center"),
                        dbc.CardBody([
                            create_risk_limit_bar("单日最大损失", "-1.23%", "-5.00%", 24.6, "success"),
                            html.Br(),
                            create_risk_limit_bar("最大回撤", "-8.50%", "-15.00%", 56.7, "success"),
                            html.Br(),
                            create_risk_limit_bar("单仓位占比", "18.5%", "25.00%", 74.0, "warning"),
                            html.Br(),
                            create_risk_limit_bar("总仓位使用", "68.5%", "80.00%", 85.6, "warning"),
                            html.Br(),
                            create_risk_limit_bar("波动率(20日)", "12.3%", "20.00%", 61.5, "success"),
                        ]),
                    ],
                    style={'backgroundColor': THEME['bg_card']},
                ),
                width=6,
            ),
            dbc.Col(
                dbc.Card(
                    [
                        dbc.CardHeader(html.H5("风险指标历史趋势", className="mb-0")),
                        dbc.CardBody(
                            dcc.Graph(
                                id='risk-metrics-history',
                                config={'displayModeBar': True},
                                style={'height': '380px'},
                                figure=create_risk_history_chart(),
                            )
                        ),
                    ],
                    style={'backgroundColor': THEME['bg_card']},
                ),
                width=6,
            ),
        ], className="mb-4"),

        # 第三行：风险告警列表
        dbc.Row([
            dbc.Col(
                dbc.Card(
                    [
                        dbc.CardHeader([
                            html.H5("风险告警列表", className="mb-0"),
                            dbc.ButtonGroup([
                                dbc.Button("全部", size="sm", color="primary", active=True),
                                dbc.Button("未处理", size="sm", color="outline-secondary"),
                                dbc.Button("已处理", size="sm", color="outline-secondary"),
                            ], size="sm"),
                        ], className="d-flex justify-content-between align-items-center"),
                        dbc.CardBody(
                            dash_table.DataTable(
                                id='risk-alerts-table',
                                columns=[
                                    {'name': '时间', 'id': 'time'},
                                    {'name': '级别', 'id': 'level'},
                                    {'name': '类型', 'id': 'type'},
                                    {'name': '描述', 'id': 'description'},
                                    {'name': '当前值', 'id': 'current'},
                                    {'name': '阈值', 'id': 'threshold'},
                                    {'name': '状态', 'id': 'status'},
                                    {'name': '操作', 'id': 'action'},
                                ],
                                data=[
                                    {'time': '2024-03-30 14:32:15', 'level': '警告', 'type': '仓位风险', 'description': '单仓位占比接近上限', 'current': '18.5%', 'threshold': '20%', 'status': '未处理', 'action': '查看'},
                                    {'time': '2024-03-30 14:28:03', 'level': '提示', 'type': '波动率', 'description': '20日波动率较前期上升', 'current': '12.3%', 'threshold': '15%', 'status': '已处理', 'action': '查看'},
                                    {'time': '2024-03-30 10:15:22', 'level': '严重', 'type': '日损失', 'description': '单日损失超过设定阈值', 'current': '-3.2%', 'threshold': '-2.5%', 'status': '已处理', 'action': '查看'},
                                    {'time': '2024-03-29 15:45:10', 'level': '警告', 'type': '回撤', 'description': '当前回撤接近最大回撤限制', 'current': '-8.5%', 'threshold': '-10%', 'status': '已处理', 'action': '查看'},
                                ],
                                style_header={
                                    'backgroundColor': THEME['bg_light'],
                                    'fontWeight': 'bold',
                                    'border': f'1px solid {THEME["border"]}',
                                },
                                style_cell={
                                    'backgroundColor': THEME['bg_card'],
                                    'color': THEME['text'],
                                    'border': f'1px solid {THEME["border"]}',
                                    'textAlign': 'center',
                                    'fontSize': '0.85rem',
                                },
                                style_data_conditional=[
                                    {
                                        'if': {'filter_query': '{level} = "严重"'},
                                        'backgroundColor': 'rgba(220, 53, 69, 0.3)',
                                        'color': '#dc3545',
                                        'fontWeight': 'bold',
                                    },
                                    {
                                        'if': {'filter_query': '{level} = "警告"'},
                                        'backgroundColor': 'rgba(255, 193, 7, 0.3)',
                                        'color': '#ffc107',
                                    },
                                    {
                                        'if': {'filter_query': '{status} = "未处理"'},
                                        'fontWeight': 'bold',
                                    },
                                ],
                                page_size=10,
                            )
                        ),
                    ],
                    style={'backgroundColor': THEME['bg_card']},
                ),
                width=12,
            ),
        ]),
    ])


def create_risk_overview_card(title: str, value: str, color: str, status: str) -> dbc.Card:
    """创建风险概览卡片"""

    return dbc.Card(
        [
            dbc.CardBody([
                html.H6(title, style={'color': THEME['text_muted'], 'marginBottom': '5px'}),
                html.H3(
                    value,
                    style={
                        'fontWeight': 'bold',
                        'color': color,
                        'margin': '10px 0',
                    }
                ),
                html.Small(
                    status,
                    style={'color': THEME['text_muted']},
                ),
            ])
        ],
        style={
            'backgroundColor': THEME['bg_card'],
            'border': f'1px solid {color}',
            'textAlign': 'center',
        }
    )


def create_risk_limit_bar(name: str, current: str, limit: str, percentage: float, status: str) -> html.Div:
    """创建风险限额进度条"""

    colors = {
        'success': '#28a745',
        'warning': '#ffc107',
        'danger': '#dc3545',
    }
    color = colors.get(status, '#5c6370')

    return html.Div([
        dbc.Row([
            dbc.Col(html.Span(name, style={'color': THEME['text'], 'fontSize': '0.9rem'}), width=3),
            dbc.Col([
                dbc.Progress(
                    value=percentage,
                    color=status,
                    style={'height': '20px', 'backgroundColor': THEME['bg_light']},
                ),
            ], width=4),
            dbc.Col([
                html.Span(f"{current} / {limit}", style={'color': color, 'fontSize': '0.85rem', 'fontWeight': 'bold'}),
            ], width=3),
            dbc.Col([
                html.Span(f"{percentage:.1f}%", style={'color': THEME['text_muted'], 'fontSize': '0.85rem'}),
            ], width=2),
        ], align="center"),
    ])


def create_risk_history_chart() -> go.Figure:
    """创建风险指标历史趋势图"""

    dates = pd.date_range(start='2024-01-01', end='2024-03-30', freq='D')
    np.random.seed(42)

    drawdown = np.cumsum(np.random.normal(0, 0.5, len(dates))) - 5
    volatility = 10 + np.cumsum(np.random.normal(0, 0.1, len(dates)))
    var_95 = -5 + np.cumsum(np.random.normal(0, 0.2, len(dates)))

    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.1,
        subplot_titles=('回撤与VaR', '波动率'),
    )

    fig.add_trace(
        go.Scatter(
            x=dates, y=drawdown,
            mode='lines',
            name='回撤',
            line=dict(color='#e94560', width=1.5),
            fill='tozeroy',
            fillcolor='rgba(233, 69, 96, 0.2)',
        ),
        row=1, col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=dates, y=var_95,
            mode='lines',
            name='VaR(95%)',
            line=dict(color='#ffc107', width=1.5, dash='dash'),
        ),
        row=1, col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=dates, y=volatility,
            mode='lines',
            name='波动率',
            line=dict(color='#00d9ff', width=1.5),
            fill='tozeroy',
            fillcolor='rgba(0, 217, 255, 0.1)',
        ),
        row=2, col=1,
    )

    fig.add_hline(y=15, line_dash="dash", line_color="#e94560", line_width=1, row=2, col=1)

    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor=THEME['bg_card'],
        plot_bgcolor=THEME['bg_card'],
        font=dict(color=THEME['text']),
        showlegend=True,
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        margin=dict(l=50, r=50, t=80, b=50),
        hovermode='x unified',
        height=400,
    )

    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor=THEME['border'])
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor=THEME['border'])

    return fig
