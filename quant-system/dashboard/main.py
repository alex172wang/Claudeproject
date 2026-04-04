"""
量化交易系统仪表板

提供实时监控、回测结果展示、策略信号监控、风险监控等功能。
"""

import os
import sys
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

import dash
from dash import dcc, html, dash_table, Input, Output, State, callback_context
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

# 添加项目路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# 导入配置
from .config import THEME

# 导入数据适配器（带延迟加载保护）
overview_data_adapter = None

def get_overview_data_adapter():
    """获取数据适配器（延迟导入避免循环导入）"""
    global overview_data_adapter
    if overview_data_adapter is None:
        try:
            from .data_adapter_v2 import overview_data_adapter as adapter
            overview_data_adapter = adapter
        except ImportError:
            from data_adapter_v2 import overview_data_adapter as adapter
            overview_data_adapter = adapter
    return overview_data_adapter

# 导入页面模块
from .pages import (
    create_realtime_tab,
    create_backtest_tab,
    create_signals_tab,
    create_risk_tab,
    create_instruments_tab,
    create_config_tab,
    register_config_callbacks,
)

# 创建 Dash 应用
def create_app() -> dash.Dash:
    """创建并配置 Dash 应用"""

    app = dash.Dash(
        __name__,
        external_stylesheets=[dbc.themes.DARKLY],
        suppress_callback_exceptions=True,
        meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
    )

    app.title = "量化交易系统 - 实时监控仪表板"

    # 设置布局
    app.layout = create_layout()

    # 注册回调
    register_callbacks(app)
    register_config_callbacks(app)

    return app


def create_layout() -> html.Div:
    """创建应用布局"""

    return html.Div(
        style={'backgroundColor': THEME['bg_dark'], 'minHeight': '100vh'},
        children=[
            # 顶部导航栏
            create_navbar(),

            # 标签页容器
            dcc.Tabs(
                id='main-tabs',
                value='overview',
                className='custom-tabs',
                children=[
                    dcc.Tab(label='总览', value='overview', className='custom-tab'),
                    dcc.Tab(label='实时监控', value='realtime', className='custom-tab'),
                    dcc.Tab(label='回测分析', value='backtest', className='custom-tab'),
                    dcc.Tab(label='策略信号', value='signals', className='custom-tab'),
                    dcc.Tab(label='风险控制', value='risk', className='custom-tab'),
                    dcc.Tab(label='品种维护', value='instruments', className='custom-tab'),
                    dcc.Tab(label='参数配置', value='config', className='custom-tab'),
                ],
            ),

            # 内容区域
            html.Div(
                id='tab-content',
                style={'padding': '20px'},
            ),

            # 刷新间隔（用于实时数据更新）
            dcc.Interval(
                id='interval-component',
                interval=5*1000,  # 5秒刷新一次
                n_intervals=0,
            ),

            # 存储组件
            dcc.Store(id='store-backtest-results'),
            dcc.Store(id='store-realtime-data'),
            dcc.Store(id='store-signals'),
            dcc.Store(id='store-risk-data'),
        ]
    )


def create_navbar() -> dbc.Navbar:
    """创建顶部导航栏"""

    return dbc.Navbar(
        dbc.Container(
            [
                dbc.NavbarBrand(
                    [
                        html.I(className="fas fa-chart-line", style={'marginRight': '10px'}),
                        "量化交易系统"
                    ],
                    href="#",
                    className="ms-2",
                    style={'fontSize': '1.5rem', 'fontWeight': 'bold'},
                ),
                dbc.Nav(
                    [
                        dbc.NavItem(dbc.NavLink("系统状态:", href="#")),
                        dbc.NavItem(
                            html.Span(
                                "● 运行中",
                                style={
                                    'color': '#28a745',
                                    'fontWeight': 'bold',
                                    'padding': '8px 15px',
                                }
                            )
                        ),
                        dbc.NavItem(
                            html.Span(
                                id='current-time',
                                style={
                                    'color': THEME['text_muted'],
                                    'padding': '8px 15px',
                                }
                            )
                        ),
                    ],
                    className="ms-auto",
                    navbar=True,
                ),
            ],
            fluid=True,
        ),
        color="dark",
        dark=True,
        className="mb-4",
        style={'backgroundColor': THEME['bg_card']},
    )


def create_overview_tab() -> html.Div:
    """创建总览标签页"""

    # 获取数据适配器
    adapter = get_overview_data_adapter()

    # 获取真实数据
    portfolio_summary = adapter.get_portfolio_summary()
    today_summary = adapter.get_today_summary()

    return html.Div([
        # 关键指标卡片行
        dbc.Row([
            # 总资产
            dbc.Col(
                create_metric_card(
                    title="总资产",
                    value=f"¥{portfolio_summary['total_assets']:,.2f}",
                    change=f"+{portfolio_summary['total_return']:.2f}%",
                    change_positive=portfolio_summary['total_return'] > 0,
                    icon="💰",
                ),
                width=3,
            ),
            # 今日收益
            dbc.Col(
                create_metric_card(
                    title="今日收益",
                    value=f"+¥{today_summary['today_pnl']:,.2f}",
                    change=f"+{today_summary['today_return']:.2f}%",
                    change_positive=True,
                    icon="📈",
                ),
                width=3,
            ),
            # 累计收益
            dbc.Col(
                create_metric_card(
                    title="累计收益",
                    value=f"+¥{portfolio_summary['total_assets'] - 1000000:,.2f}",
                    change=f"+{portfolio_summary['total_return']:.2f}%",
                    change_positive=portfolio_summary['total_return'] > 0,
                    icon="🏆",
                ),
                width=3,
            ),
            # 夏普比率
            dbc.Col(
                create_metric_card(
                    title="夏普比率",
                    value=f"{portfolio_summary['sharpe_ratio']:.2f}",
                    change="+0.12",
                    change_positive=True,
                    icon="⚖️",
                ),
                width=3,
            ),
        ], className="mb-4"),

        # 第二行：图表
        dbc.Row([
            # 权益曲线
            dbc.Col(
                dbc.Card(
                    [
                        dbc.CardHeader([
                            html.H5("权益曲线", className="mb-0"),
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
                                id='overview-equity-curve',
                                config={'displayModeBar': False},
                                style={'height': '350px'},
                            )
                        ),
                    ],
                    style={'backgroundColor': THEME['bg_card']},
                ),
                width=8,
            ),
            # 持仓分布
            dbc.Col(
                dbc.Card(
                    [
                        dbc.CardHeader(html.H5("持仓分布", className="mb-0")),
                        dbc.CardBody(
                            dcc.Graph(
                                id='overview-position-pie',
                                config={'displayModeBar': False},
                                style={'height': '350px'},
                            )
                        ),
                    ],
                    style={'backgroundColor': THEME['bg_card']},
                ),
                width=4,
            ),
        ], className="mb-4"),

        # 第三行：策略表现表格 + 最近交易
        dbc.Row([
            dbc.Col(
                dbc.Card(
                    [
                        dbc.CardHeader(html.H5("策略表现", className="mb-0")),
                        dbc.CardBody(
                            dash_table.DataTable(
                                id='overview-strategy-table',
                                columns=[
                                    {'name': '策略', 'id': 'strategy'},
                                    {'name': '状态', 'id': 'status'},
                                    {'name': '权重', 'id': 'weight'},
                                    {'name': '收益', 'id': 'return'},
                                    {'name': '回撤', 'id': 'drawdown'},
                                    {'name': '夏普', 'id': 'sharpe'},
                                ],
                                data=adapter.get_strategy_performance(),
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
                                },
                                style_data_conditional=[
                                    {
                                        'if': {'filter_query': '{status} = "运行中"'},
                                        'color': '#28a745',
                                        'fontWeight': 'bold',
                                    },
                                    {
                                        'if': {'filter_query': '{status} = "待机"'},
                                        'color': '#ffc107',
                                    },
                                ],
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
                        dbc.CardHeader([
                            html.H5("最近交易", className="mb-0"),
                            dbc.Button("查看全部", size="sm", color="outline-primary"),
                        ], className="d-flex justify-content-between align-items-center"),
                        dbc.CardBody(
                            dash_table.DataTable(
                                id='overview-recent-trades',
                                columns=[
                                    {'name': '时间', 'id': 'time'},
                                    {'name': '类型', 'id': 'type'},
                                    {'name': '标的', 'id': 'symbol'},
                                    {'name': '价格', 'id': 'price'},
                                    {'name': '数量', 'id': 'quantity'},
                                    {'name': '盈亏', 'id': 'pnl'},
                                ],
                                data=overview_data_adapter.get_recent_trades(),
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
                                },
                                style_data_conditional=[
                                    {
                                        'if': {'filter_query': '{type} = "买入"'},
                                        'color': '#28a745',
                                    },
                                    {
                                        'if': {'filter_query': '{type} = "卖出"'},
                                        'color': '#dc3545',
                                    },
                                    {
                                        'if': {'filter_query': '{pnl} contains +'},
                                        'color': '#28a745',
                                        'fontWeight': 'bold',
                                    },
                                    {
                                        'if': {'filter_query': '{pnl} contains -'},
                                        'color': '#dc3545',
                                        'fontWeight': 'bold',
                                    },
                                ],
                            )
                        ),
                    ],
                    style={'backgroundColor': THEME['bg_card']},
                ),
                width=6,
            ),
        ]),
    ])


def create_metric_card(title: str, value: str, change: str, change_positive: bool, icon: str) -> dbc.Card:
    """创建指标卡片"""

    change_color = '#28a745' if change_positive else '#dc3545'
    arrow = '↑' if change_positive else '↓'

    return dbc.Card(
        [
            dbc.CardBody([
                html.Div([
                    html.Span(icon, style={'fontSize': '2rem', 'marginRight': '10px'}),
                    html.Span(title, style={'color': THEME['text_muted'], 'fontSize': '0.9rem'}),
                ]),
                html.H3(
                    value,
                    style={
                        'margin': '10px 0',
                        'fontWeight': 'bold',
                        'color': THEME['text'],
                    }
                ),
                html.Span(
                    f"{arrow} {change}",
                    style={
                        'color': change_color,
                        'fontWeight': 'bold',
                        'fontSize': '0.9rem',
                    }
                ),
            ])
        ],
        style={
            'backgroundColor': THEME['bg_card'],
            'border': f'1px solid {THEME["border"]}',
            'height': '100%',
        }
    )


# 导入数据适配器
try:
    from .data_adapter_v2 import data_adapter_v2
except ImportError:
    from data_adapter_v2 import data_adapter_v2


def register_callbacks(app: dash.Dash) -> None:
    """注册所有回调函数"""

    # 延迟导入以避免循环导入
    from .pages import register_realtime_callbacks as _reg_rtc

    @app.callback(
        Output('tab-content', 'children'),
        [Input('main-tabs', 'value')]
    )
    def render_tab_content(tab: str):
        """根据选中的标签页渲染内容"""
        if tab == 'overview':
            return create_overview_tab()
        elif tab == 'realtime':
            return create_realtime_tab()
        elif tab == 'backtest':
            return create_backtest_tab()
        elif tab == 'signals':
            return create_signals_tab()
        elif tab == 'risk':
            return create_risk_tab()
        elif tab == 'instruments':
            return create_instruments_tab()
        elif tab == 'config':
            return create_config_tab()
        return html.Div("页面未找到")

    @app.callback(
        Output('overview-equity-curve', 'figure'),
        [Input('interval-component', 'n_intervals')]
    )
    def update_equity_curve(n):
        """更新权益曲线图"""
        return create_equity_curve_figure()

    @app.callback(
        Output('overview-position-pie', 'figure'),
        [Input('interval-component', 'n_intervals')]
    )
    def update_position_pie(n):
        """更新持仓分布图"""
        return create_position_pie_figure()

    @app.callback(
        Output('current-time', 'children'),
        [Input('interval-component', 'n_intervals')]
    )
    def update_time(n):
        """更新当前时间"""
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # 注册实时监控页面的回调
    _reg_rtc(app)


def create_equity_curve_figure() -> go.Figure:
    """创建权益曲线图"""
    # 获取数据适配器
    adapter = get_overview_data_adapter()

    # 获取真实数据
    dates, equity_values = adapter.get_equity_curve_data()

    # 转换为 numpy 数组用于计算
    equity = np.array(equity_values)

    # 计算回撤
    rolling_max = np.maximum.accumulate(equity)
    drawdown = (equity - rolling_max) / rolling_max * 100

    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.1,
        row_heights=[0.7, 0.3],
        subplot_titles=('权益曲线', '回撤'),
    )

    # 权益曲线
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=list(equity),
            mode='lines',
            name='总资产',
            line=dict(color='#00d9ff', width=2),
            fill='tozeroy',
            fillcolor='rgba(0, 217, 255, 0.1)',
        ),
        row=1, col=1,
    )

    # 基准线（初始资金）
    initial_capital = equity[0] if len(equity) > 0 else 1000000
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=[initial_capital] * len(dates),
            mode='lines',
            name='初始资金',
            line=dict(color='#e94560', width=1, dash='dash'),
        ),
        row=1, col=1,
    )

    # 回撤
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=drawdown,
            mode='lines',
            name='回撤',
            line=dict(color='#e94560', width=1.5),
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
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='right',
            x=1,
        ),
        margin=dict(l=50, r=50, t=80, b=50),
        hovermode='x unified',
    )

    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor=THEME['border'])
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor=THEME['border'])

    return fig


def create_position_pie_figure() -> go.Figure:
    """创建持仓分布饼图"""

    # 获取数据适配器
    adapter = get_overview_data_adapter()

    # 获取真实持仓数据
    labels, values = adapter.get_position_distribution()
    colors = ['#00d9ff', '#e94560', '#ffd700', '#ff6b9d', '#c792ea', '#5c6370']

    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.5,
        marker=dict(colors=colors, line=dict(color=THEME['bg_card'], width=2)),
        textinfo='label+percent',
        textposition='outside',
        textfont=dict(size=11, color=THEME['text']),
        hovertemplate='<b>%{label}</b><br>金额: ¥%{value:,.0f}<br>占比: %{percent}<extra></extra>',
    )])

    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor=THEME['bg_card'],
        plot_bgcolor=THEME['bg_card'],
        font=dict(color=THEME['text']),
        showlegend=False,
        margin=dict(l=20, r=20, t=20, b=20),
        annotations=[
            dict(
                text=f'<b>总持仓</b><br>¥{sum(values):,.0f}',
                x=0.5,
                y=0.5,
                font_size=14,
                showarrow=False,
                font_color=THEME['text'],
            )
        ],
    )

    return fig


# 创建全局 app 实例（供导入使用）
app = None

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=8050)
else:
    # 模块导入时创建 app
    app = create_app()
