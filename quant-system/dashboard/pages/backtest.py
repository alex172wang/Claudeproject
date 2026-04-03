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

# 导入数据适配器
try:
    from ..data_adapter_v2 import data_adapter_v2
except ImportError:
    from data_adapter_v2 import data_adapter_v2
except ImportError:
    # 绝对导入备用
    import sys
    import os
    dashboard_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if dashboard_dir not in sys.path:
        sys.path.insert(0, dashboard_dir)
    from config import THEME


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
                                        style={'color': '#000'},
                                    ),
                                ], width=3),
                                dbc.Col([
                                    dbc.Label("起始日期"),
                                    dcc.DatePickerSingle(
                                        id='backtest-start-date',
                                        date='2023-01-01',
                                        style={'color': '#000'},
                                    ),
                                ], width=2),
                                dbc.Col([
                                    dbc.Label("结束日期"),
                                    dcc.DatePickerSingle(
                                        id='backtest-end-date',
                                        date='2024-03-30',
                                        style={'color': '#000'},
                                    ),
                                ], width=2),
                                dbc.Col([
                                    dbc.Label("初始资金"),
                                    dbc.Input(
                                        id='backtest-initial-capital',
                                        type='number',
                                        value=1000000,
                                        style={'color': '#000'},
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
            dbc.Col(create_kpi_card("总收益率", "+28.45%", "+2.34%", True), width=2),
            dbc.Col(create_kpi_card("年化收益", "+24.32%", "+1.85%", True), width=2),
            dbc.Col(create_kpi_card("夏普比率", "1.85", "+0.12", True), width=2),
            dbc.Col(create_kpi_card("最大回撤", "-8.23%", "-0.45%", False), width=2),
            dbc.Col(create_kpi_card("胜率", "62.5%", "+2.3%", True), width=2),
            dbc.Col(create_kpi_card("盈亏比", "1.85", "+0.08", True), width=2),
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
                                    {'date': '2024-03-28', 'direction': '买入', 'symbol': '510300', 'name': '沪深300ETF', 'price': '4.125', 'quantity': '5000', 'amount': '20,625.00', 'commission': '20.63', 'pnl': '-'},
                                    {'date': '2024-03-27', 'direction': '卖出', 'symbol': '510500', 'name': '中证500ETF', 'price': '6.823', 'quantity': '3000', 'amount': '20,469.00', 'commission': '20.47', 'pnl': '+1,245.30'},
                                    {'date': '2024-03-26', 'direction': '买入', 'symbol': '518880', 'name': '黄金ETF', 'price': '3.956', 'quantity': '2000', 'amount': '7,912.00', 'commission': '7.91', 'pnl': '-'},
                                    {'date': '2024-03-25', 'direction': '卖出', 'symbol': '159949', 'name': '创业板ETF', 'price': '1.234', 'quantity': '8000', 'amount': '9,872.00', 'commission': '9.87', 'pnl': '-2,110.50'},
                                    {'date': '2024-03-22', 'direction': '买入', 'symbol': '513500', 'name': '纳斯达克ETF', 'price': '2.856', 'quantity': '3500', 'amount': '9,996.00', 'commission': '10.00', 'pnl': '-'},
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
                                        'color': '#28a745',
                                    },
                                    {
                                        'if': {'filter_query': '{pnl} contains -'},
                                        'color': '#dc3545',
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

    color = '#28a745' if positive else '#dc3545'
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

    dates = pd.date_range(start='2023-01-01', end='2024-03-30', freq='D')
    np.random.seed(42)
    returns = np.random.normal(0.0005, 0.012, len(dates))
    equity = 1000000 * (1 + returns).cumprod()

    rolling_max = np.maximum.accumulate(equity)
    drawdown = (equity - rolling_max) / rolling_max * 100

    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.1,
        row_heights=[0.7, 0.3],
    )

    fig.add_trace(
        go.Scatter(
            x=dates, y=equity,
            mode='lines',
            name='总资产',
            line=dict(color='#00d9ff', width=1.5),
            fill='tozeroy',
            fillcolor='rgba(0, 217, 255, 0.1)',
        ),
        row=1, col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=dates, y=[1000000]*len(dates),
            mode='lines',
            name='初始资金',
            line=dict(color='#e94560', width=1, dash='dash'),
        ),
        row=1, col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=dates, y=drawdown,
            mode='lines',
            name='回撤',
            line=dict(color='#e94560', width=1),
            fill='tozeroy',
            fillcolor='rgba(233, 69, 96, 0.2)',
        ),
        row=2, col=1,
    )

    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor=THEME['bg_card'],
        plot_bgcolor=THEME['bg_card'],
        font=dict(color=THEME['text']),
        showlegend=True,
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        margin=dict(l=50, r=50, t=50, b=50),
        hovermode='x unified',
    )

    return fig


def create_monthly_heatmap() -> go.Figure:
    """创建月度收益热力图"""

    months = ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月']
    years = ['2023', '2024']

    np.random.seed(42)
    returns = np.random.uniform(-5, 8, (len(years), len(months)))

    fig = go.Figure(data=go.Heatmap(
        z=returns,
        x=months,
        y=years,
        colorscale=[
            [0, '#dc3545'],
            [0.5, '#5c6370'],
            [1, '#28a745'],
        ],
        text=np.round(returns, 2),
        texttemplate='%{text}%',
        textfont={'size': 12},
        hovertemplate='%{y}年%{x}: %{z:.2f}%<extra></extra>',
    ))

    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor=THEME['bg_card'],
        plot_bgcolor=THEME['bg_card'],
        font=dict(color=THEME['text']),
        margin=dict(l=50, r=50, t=30, b=50),
    )

    return fig


def create_return_distribution() -> go.Figure:
    """创建收益分布图"""

    np.random.seed(42)
    returns = np.random.normal(0.05, 1.2, 250)

    fig = go.Figure()

    fig.add_trace(go.Histogram(
        x=returns,
        nbinsx=30,
        name='日收益率分布',
        marker_color='#00d9ff',
        opacity=0.7,
    ))

    fig.add_vline(x=0, line_dash="dash", line_color="#e94560", line_width=2)

    fig.add_vline(x=np.mean(returns), line_dash="solid", line_color="#28a745", line_width=2,
                  annotation_text="均值", annotation_position="top")

    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor=THEME['bg_card'],
        plot_bgcolor=THEME['bg_card'],
        font=dict(color=THEME['text']),
        margin=dict(l=50, r=50, t=30, b=50),
        xaxis_title='日收益率 (%)',
        yaxis_title='频次',
        showlegend=False,
    )

    return fig
