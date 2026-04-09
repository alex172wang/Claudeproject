"""
回测分析页面

提供回测结果展示、策略对比、绩效分析等功能。
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
    import sys
    import os
    dashboard_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if dashboard_dir not in sys.path:
        sys.path.insert(0, dashboard_dir)
    from config import THEME

# 数据适配器由其他模块处理，本页面使用模拟数据


def create_backtest_tab() -> html.Div:
    """创建回测分析标签页"""

    return html.Div([
        # 第一行：回测配置选择
        dbc.Row([
            dbc.Col(
                dbc.Card(
                    [
                        dbc.CardHeader(html.H5("回测配置", className="mb-0")),
                        dbc.CardBody([
                            dbc.Row([
                                dbc.Col([
                                    dbc.Label("策略选择"),
                                    dcc.Dropdown(
                                        id='backtest-strategy-select',
                                        options=[
                                            {'label': 'ETF轮动策略', 'value': 'etf_rotation'},
                                            {'label': '永久组合策略', 'value': 'permanent_portfolio'},
                                            {'label': '主题仓位策略', 'value': 'thematic'},
                                        ],
                                        value='etf_rotation',
                                        style={'backgroundColor': '#2d2d2d', 'color': 'white'},
                                    ),
                                ], width=3),
                                dbc.Col([
                                    dbc.Label("起始日期"),
                                    dcc.DatePickerSingle(
                                        id='backtest-start-date',
                                        date='2023-01-01',
                                        style={'backgroundColor': '#2d2d2d', 'color': 'white'},
                                    ),
                                ], width=2),
                                dbc.Col([
                                    dbc.Label("结束日期"),
                                    dcc.DatePickerSingle(
                                        id='backtest-end-date',
                                        date='2024-03-30',
                                        style={'backgroundColor': '#2d2d2d', 'color': 'white'},
                                    ),
                                ], width=2),
                                dbc.Col([
                                    dbc.Label("初始资金"),
                                    dbc.Input(
                                        id='backtest-initial-capital',
                                        type='number',
                                        value=1000000,
                                        style={'backgroundColor': '#2d2d2d', 'color': 'white'},
                                    ),
                                ], width=2),
                                dbc.Col([
                                    html.Br(),
                                    dbc.Button(
                                        "运行回测",
                                        id='backtest-run-btn',
                                        color='primary',
                                        className='mt-2',
                                    ),
                                ], width=1),
                            ]),
                        ]),
                    ],
                    style={'backgroundColor': THEME['bg_card']},
                ),
                width=12,
            ),
        ], className="mb-4"),

        # 第二行：关键绩效指标
        dbc.Row([
            dbc.Col(create_kpi_card("总收益率", "--", "--", True), width=2),
            dbc.Col(create_kpi_card("年化收益", "--", "--", True), width=2),
            dbc.Col(create_kpi_card("夏普比率", "--", "--", True), width=2),
            dbc.Col(create_kpi_card("最大回撤", "--", "--", False), width=2),
            dbc.Col(create_kpi_card("胜率", "--", "--", True), width=2),
            dbc.Col(create_kpi_card("盈亏比", "--", "--", True), width=2),
        ], className="mb-4"),

        # 第三行：权益曲线 + 回撤
        dbc.Row([
            dbc.Col(
                dbc.Card(
                    [
                        dbc.CardHeader([
                            html.H5("权益曲线与回撤", className="mb-0"),
                            dbc.ButtonGroup([
                                dbc.Button("1M", size="sm", color="outline-secondary"),
                                dbc.Button("3M", size="sm", color="outline-secondary"),
                                dbc.Button("6M", size="sm", color="outline-secondary"),
                                dbc.Button("1Y", size="sm", color="outline-primary"),
                                dbc.Button("ALL", size="sm", color="outline-secondary"),
                            ], size="sm"),
                        ], className="d-flex justify-content-between align-items-center"),
                        dbc.CardBody(
                            dcc.Graph(
                                id='backtest-equity-chart',
                                config={'displayModeBar': True},
                                style={'height': '400px'},
                                figure=create_backtest_equity_chart(),
                            )
                        ),
                    ],
                    style={'backgroundColor': THEME['bg_card']},
                ),
                width=12,
            ),
        ], className="mb-4"),

        # 第四行：月度收益热力图 + 收益分布
        dbc.Row([
            dbc.Col(
                dbc.Card(
                    [
                        dbc.CardHeader(html.H5("月度收益热力图", className="mb-0")),
                        dbc.CardBody(
                            dcc.Graph(
                                id='backtest-monthly-heatmap',
                                config={'displayModeBar': False},
                                style={'height': '350px'},
                                figure=create_monthly_heatmap(),
                            )
                        ),
                    ],
                    style={'backgroundColor': THEME['bg_card']},
                ),
                width=6,
            ),
            dbc.Col(
                dbc.Card(
                    [
                        dbc.CardHeader(html.H5("收益分布", className="mb-0")),
                        dbc.CardBody(
                            dcc.Graph(
                                id='backtest-return-dist',
                                config={'displayModeBar': False},
                                style={'height': '350px'},
                                figure=create_return_distribution(),
                            )
                        ),
                    ],
                    style={'backgroundColor': THEME['bg_card']},
                ),
                width=6,
            ),
        ], className="mb-4"),

        # 第五行：交易记录表格
        dbc.Row([
            dbc.Col(
                dbc.Card(
                    [
                        dbc.CardHeader([
                            html.H5("交易记录", className="mb-0"),
                            dbc.Button("导出CSV", size="sm", color="outline-primary"),
                        ], className="d-flex justify-content-between align-items-center"),
                        dbc.CardBody(
                            dash_table.DataTable(
                                id='backtest-trade-table',
                                columns=[
                                    {'name': '日期', 'id': 'date'},
                                    {'name': '方向', 'id': 'direction'},
                                    {'name': '标的', 'id': 'symbol'},
                                    {'name': '名称', 'id': 'name'},
                                    {'name': '价格', 'id': 'price'},
                                    {'name': '数量', 'id': 'quantity'},
                                    {'name': '金额', 'id': 'amount'},
                                    {'name': '佣金', 'id': 'commission'},
                                    {'name': '盈亏', 'id': 'pnl'},
                                ],
                                data=[
                                    # 暂无回测交易记录
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
                                        'if': {'filter_query': '{direction} = "买入"'},
                                        'color': '#28a745',
                                        'fontWeight': 'bold',
                                    },
                                    {
                                        'if': {'filter_query': '{direction} = "卖出"'},
                                        'color': '#dc3545',
                                        'fontWeight': 'bold',
                                    },
                                    {
                                        'if': {'filter_query': '{pnl} contains +'},
                                        'color': '#dc3545',  # A股：红涨
                                    },
                                    {
                                        'if': {'filter_query': '{pnl} contains -'},
                                        'color': '#28a745',  # A股：绿跌
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


def create_kpi_card(title: str, value: str, change: str, positive: bool) -> dbc.Card:
    """创建KPI指标卡片"""

    color = '#dc3545' if positive else '#28a745'  # A股：红涨绿跌
    arrow = '↑' if positive else '↓'

    return dbc.Card(
        [
            dbc.CardBody([
                html.H6(title, style={'color': THEME['text_muted'], 'marginBottom': '8px'}),
                html.H4(value, style={'fontWeight': 'bold', 'marginBottom': '4px'}),
                html.Small(
                    f"{arrow} {change}",
                    style={'color': color, 'fontWeight': 'bold'}
                ),
            ])
        ],
        style={
            'backgroundColor': THEME['bg_card'],
            'border': f'1px solid {THEME["border"]}',
            'textAlign': 'center',
        }
    )


def create_backtest_equity_chart() -> go.Figure:
    """创建回测权益曲线图"""
    # 暂无真实回测数据，返回空图表
    fig = go.Figure()
    fig.add_annotation(
        text="暂无回测数据",
        xref="paper", yref="paper",
        x=0.5, y=0.5,
        showarrow=False,
        font=dict(size=16, color=THEME['text_muted']),
    )
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor=THEME['bg_card'],
        plot_bgcolor=THEME['bg_card'],
        font=dict(color=THEME['text']),
        showlegend=False,
        margin=dict(l=50, r=50, t=50, b=50),
    )
    return fig


def create_monthly_heatmap() -> go.Figure:
    """创建月度收益热力图"""
    # 暂无真实回测数据，返回空图表
    fig = go.Figure()
    fig.add_annotation(
        text="暂无回测数据",
        xref="paper", yref="paper",
        x=0.5, y=0.5,
        showarrow=False,
        font=dict(size=16, color=THEME['text_muted']),
    )
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor=THEME['bg_card'],
        plot_bgcolor=THEME['bg_card'],
        font=dict(color=THEME['text']),
        showlegend=False,
        margin=dict(l=50, r=50, t=30, b=50),
    )
    return fig


def create_return_distribution() -> go.Figure:
    """创建收益分布图"""
    # 暂无真实回测数据，返回空图表
    fig = go.Figure()
    fig.add_annotation(
        text="暂无回测数据",
        xref="paper", yref="paper",
        x=0.5, y=0.5,
        showarrow=False,
        font=dict(size=16, color=THEME['text_muted']),
    )
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor=THEME['bg_card'],
        plot_bgcolor=THEME['bg_card'],
        font=dict(color=THEME['text']),
        showlegend=False,
        margin=dict(l=50, r=50, t=30, b=50),
        xaxis_title='日收益率 (%)',
        yaxis_title='频次',
    )
    return fig
