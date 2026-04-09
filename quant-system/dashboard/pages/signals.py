"""
策略信号页面 - 展示L1-L4多维量化指标
使用真实ETF数据从mootdx获取
"""

import dash
from dash import dcc, html, dash_table, callback_context
from dash.dependencies import Input, Output, State
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入 API 数据适配器
try:
    from dashboard.data_adapter_api import get_api_data_adapter
    data_adapter = get_api_data_adapter()
    DATA_SOURCE = "api"
except Exception as e:
    print(f"[Signals] API 数据适配器加载失败: {e}")
    data_adapter = None
    DATA_SOURCE = "mock"

print(f"[Signals] 数据源: {DATA_SOURCE}")

# ETF代码映射
ETF_MAP = {
    '510300': {'name': '沪深300ETF', 'category': '宽基'},
    '510500': {'name': '中证500ETF', 'category': '宽基'},
    '159915': {'name': '创业板ETF', 'category': '宽基'},
    '588000': {'name': '科创50ETF', 'category': '科技'},
    '518880': {'name': '黄金ETF', 'category': '商品'},
    '513500': {'name': '标普500ETF', 'category': '跨境'},
    '159920': {'name': '恒生ETF', 'category': '跨境'},
}

# 布局定义
def create_layout():
    """创建页面布局"""
    return dbc.Container([
        # 页面标题
        dbc.Row([
            dbc.Col([
                html.H2([
                    html.I(className="fas fa-signal me-2"),
                    "策略信号 - 多维量化指标体系"
                ], className="mb-3"),
                html.P([
                    "基于L1趋势/L2结构/L3共振/L4缺口四维框架的实时信号生成系统",
                    html.Br(),
                    html.Small(f"数据源: {'mootdx实时数据' if DATA_SOURCE == 'real' else '模拟数据'}", className="text-muted")
                ], className="text-muted mb-4"),
            ], width=12)
        ]),

        # 控制面板
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H5("ETF选择", className="card-title"),
                        dcc.Dropdown(
                            id='etf-selector',
                            options=[{'label': f"{code} - {info['name']}", 'value': code}
                                    for code, info in ETF_MAP.items()],
                            value='510300',
                            placeholder="选择ETF",
                            className="mb-3",
                            style={'backgroundColor': '#2d2d2d', 'color': 'white'},
                        ),
                        html.Label("时间范围:", className="form-label"),
                        dcc.Slider(
                            id='days-slider',
                            min=30,
                            max=252,
                            step=30,
                            value=60,
                            marks={30: '1月', 60: '2月', 90: '3月', 180: '6月', 252: '1年'},
                        ),
                        html.Br(),
                        dbc.Button(
                            [html.I(className="fas fa-refresh me-2"), "刷新数据"],
                            id="refresh-btn",
                            color="primary",
                            className="mt-3"
                        ),
                        dcc.Interval(id='interval-component', interval=30000, n_intervals=0),  # 30秒刷新
                    ])
                ], className="h-100 shadow-sm")
            ], width=3),

            # 信号状态卡片
            dbc.Col([
                dbc.Row([
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H6("L1 趋势层", className="text-primary"),
                                html.H3(id='l1-score', children="--"),
                                html.Small(id='l1-status', children="计算中...", className="text-muted")
                            ], className="text-center")
                        ], className="shadow-sm border-primary border-top-0 border-end-0 border-bottom-0 border-3")
                    ], width=3),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H6("L2 结构层", className="text-success"),
                                html.H3(id='l2-score', children="--"),
                                html.Small(id='l2-status', children="计算中...", className="text-muted")
                            ], className="text-center")
                        ], className="shadow-sm border-success border-top-0 border-end-0 border-bottom-0 border-3")
                    ], width=3),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H6("L3 共振层", className="text-warning"),
                                html.H3(id='l3-score', children="--"),
                                html.Small(id='l3-status', children="计算中...", className="text-muted")
                            ], className="text-center")
                        ], className="shadow-sm border-warning border-top-0 border-end-0 border-bottom-0 border-3")
                    ], width=3),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H6("L4 缺口层", className="text-danger"),
                                html.H3(id='l4-score', children="--"),
                                html.Small(id='l4-status', children="计算中...", className="text-muted")
                            ], className="text-center")
                        ], className="shadow-sm border-danger border-top-0 border-end-0 border-bottom-0 border-3")
                    ], width=3),
                ], className="g-3")
            ], width=9)
        ], className="mb-4"),

        # 综合评分区域
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([html.H5("四维评分矩阵", className="mb-0")]),
                    dbc.CardBody([
                        dcc.Graph(id='score-radar', style={'height': '400px'})
                    ])
                ], className="shadow-sm h-100")
            ], width=6),
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([html.H5("趋势与成交量", className="mb-0")]),
                    dbc.CardBody([
                        dcc.Graph(id='price-chart', style={'height': '400px'})
                    ])
                ], className="shadow-sm h-100")
            ], width=6),
        ], className="mb-4"),

        # 策略信号表格
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.H5("策略信号详情", className="mb-0 d-inline"),
                        dbc.Badge(id='signal-count', color="primary", className="ms-2")
                    ]),
                    dbc.CardBody([
                        dash_table.DataTable(
                            id='signals-table',
                            columns=[
                                {'name': '代码', 'id': 'code'},
                                {'name': '名称', 'id': 'name'},
                                {'name': 'L1趋势', 'id': 'l1_score'},
                                {'name': 'L2结构', 'id': 'l2_score'},
                                {'name': 'L3共振', 'id': 'l3_score'},
                                {'name': 'L4缺口', 'id': 'l4_score'},
                                {'name': '综合分', 'id': 'total_score'},
                                {'name': '信号', 'id': 'signal'},
                            ],
                            data=[],
                            style_table={'overflowX': 'auto'},
                            style_cell={'textAlign': 'center', 'padding': '10px'},
                            style_header={
                                'backgroundColor': 'rgb(230, 230, 230)',
                                'fontWeight': 'bold'
                            },
                            style_data_conditional=[
                                {
                                    'if': {'filter_query': '{signal} = "强烈买入"'},
                                    'backgroundColor': '#d4edda',
                                    'color': '#155724'
                                },
                                {
                                    'if': {'filter_query': '{signal} = "买入"'},
                                    'backgroundColor': '#d1ecf1',
                                    'color': '#0c5460'
                                },
                                {
                                    'if': {'filter_query': '{signal} = "卖出"'},
                                    'backgroundColor': '#f8d7da',
                                    'color': '#721c24'
                                },
                                {
                                    'if': {'filter_query': '{signal} = "强烈卖出"'},
                                    'backgroundColor': '#ff6b6b',
                                    'color': 'white'
                                },
                            ]
                        )
                    ])
                ], className="shadow-sm")
            ], width=12)
        ]),

        # 存储组件
        dcc.Store(id='current-data'),
        dcc.Store(id='calculated-scores'),

    ], fluid=True, className="py-4")


# 回调函数注册
def register_callbacks(app):
    """注册回调函数"""

    @app.callback(
        [Output('current-data', 'data'),
         Output('l1-score', 'children'),
         Output('l1-status', 'children'),
         Output('l2-score', 'children'),
         Output('l2-status', 'children'),
         Output('l3-score', 'children'),
         Output('l3-status', 'children'),
         Output('l4-score', 'children'),
         Output('l4-status', 'children')],
        [Input('etf-selector', 'value'),
         Input('days-slider', 'value'),
         Input('refresh-btn', 'n_clicks'),
         Input('interval-component', 'n_intervals')]
    )
    def update_data(selected_etf, days, n_clicks, n_intervals):
        """更新数据和计算指标"""
        ctx = callback_context
        triggered_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else None

        # 获取数据
        df = get_etf_data(selected_etf, days)

        if df is None or df.empty:
            return None, "--", "无数据", "--", "无数据", "--", "无数据", "--", "无数据"

        # 计算各层得分
        l1_score, l1_status = calculate_l1_score(df)
        l2_score, l2_status = calculate_l2_score(df)
        l3_score, l3_status = calculate_l3_score(df)
        l4_score, l4_status = calculate_l4_score(df)

        # 存储数据
        data = {
            'etf': selected_etf,
            'days': days,
            'df': df.to_dict('records'),
            'l1': l1_score,
            'l2': l2_score,
            'l3': l3_score,
            'l4': l4_score
        }

        return (data,
                f"{l1_score:.1f}", l1_status,
                f"{l2_score:.1f}", l2_status,
                f"{l3_score:.1f}", l3_status,
                f"{l4_score:.1f}", l4_status)

    @app.callback(
        [Output('score-radar', 'figure'),
         Output('price-chart', 'figure'),
         Output('signals-table', 'data'),
         Output('signal-count', 'children')],
        [Input('current-data', 'data')]
    )
    def update_charts(data):
        """更新图表和表格"""
        if data is None:
            return {}, {}, [], "0个信号"

        # 雷达图
        radar_fig = create_radar_chart(data)

        # 价格图
        price_fig = create_price_chart(data)

        # 信号表格数据
        table_data = generate_signals_table()

        return radar_fig, price_fig, table_data, f"{len(table_data)}个信号"


def get_etf_data(code, days):
    """获取ETF数据"""
    global data_adapter

    if data_adapter:
        try:
            df = data_adapter.get_etf_kline(code, days)
            if df is not None and not df.empty:
                return df
        except Exception as e:
            print(f"[Signals] 获取API数据失败: {e}")

    # 使用模拟数据
    return generate_mock_data(code, days)


def generate_mock_data(code, days):
    """获取模拟数据（当API不可用时）"""
    # 不再生成随机数据，返回空DataFrame
    return pd.DataFrame(columns=['date', 'open', 'high', 'low', 'close', 'volume'])


def calculate_l1_score(df):
    """计算L1趋势层得分 (0-100)"""
    if df is None or len(df) < 30:
        return 50, "数据不足"

    closes = df['close'].values

    # 计算短期和长期趋势
    short_ma = np.mean(closes[-20:])
    long_ma = np.mean(closes[-60:]) if len(closes) >= 60 else np.mean(closes)

    # 价格在均线之上为多头趋势
    current_price = closes[-1]

    # 趋势强度计算 (-1 到 1)
    trend_strength = (current_price - long_ma) / long_ma * 5  # 放大系数
    trend_strength = np.clip(trend_strength, -1, 1)

    # 转换为 0-100 分
    score = int((trend_strength + 1) * 50)

    if score >= 70:
        status = "强势上涨"
    elif score >= 55:
        status = "温和上涨"
    elif score >= 45:
        status = "震荡整理"
    elif score >= 30:
        status = "温和下跌"
    else:
        status = "弱势下跌"

    return score, status


def calculate_l2_score(df):
    """计算L2结构层得分 (0-100)"""
    if df is None or len(df) < 20:
        return 50, "数据不足"

    closes = df['close'].values
    volumes = df['volume'].values if 'volume' in df.columns else None

    # 计算波动率 (标准差/均值)
    returns = np.diff(closes) / closes[:-1]
    volatility = np.std(returns) * np.sqrt(252)  # 年化波动率

    # 波动率评分 (低波动率得分高，代表结构稳定)
    # 10%以下为优秀，30%以上为差
    vol_score = max(0, 100 - (volatility - 0.10) * 500)
    vol_score = np.clip(vol_score, 0, 100)

    # 趋势质量：使用价格与均线的偏离度
    ma20 = np.mean(closes[-20:])
    deviation = abs(closes[-1] - ma20) / ma20
    quality_score = max(0, 100 - deviation * 1000)

    # 综合得分
    score = int(vol_score * 0.5 + quality_score * 0.5)

    if score >= 75:
        status = "结构优秀"
    elif score >= 60:
        status = "结构良好"
    elif score >= 40:
        status = "结构一般"
    else:
        status = "结构较差"

    return score, status


def calculate_l3_score(df):
    """计算L3共振层得分 (0-100) - 相对市场强度"""
    if df is None or len(df) < 20:
        return 50, "数据不足"

    closes = df['close'].values

    # 计算收益率
    returns = (closes[-1] - closes[-20]) / closes[-20] if len(closes) >= 20 else 0

    # 将收益率转换为评分 (-20%到+20%映射到0-100)
    score = int((returns + 0.20) / 0.40 * 100)
    score = np.clip(score, 0, 100)

    if score >= 75:
        status = "强于市场"
    elif score >= 60:
        status = "温和领先"
    elif score >= 40:
        status = "与市场同步"
    elif score >= 25:
        status = "温和落后"
    else:
        status = "弱于市场"

    return score, status


def calculate_l4_score(df):
    """计算L4缺口层得分 (0-100) - 风险度量"""
    if df is None or len(df) < 20:
        return 50, "数据不足"

    closes = df['close'].values
    highs = df['high'].values if 'high' in df.columns else closes
    lows = df['low'].values if 'low' in df.columns else closes

    # 计算ATR (平均真实波幅)
    tr1 = highs[-20:] - lows[-20:]
    tr2 = np.abs(highs[-20:] - np.roll(closes[-20:], 1))
    tr3 = np.abs(lows[-20:] - np.roll(closes[-20:], 1))
    tr = np.maximum(np.maximum(tr1, tr2[1:]), tr3[1:])
    atr = np.mean(tr)

    # ATR百分比
    atr_pct = atr / closes[-1]

    # 风险评分 (低ATR=高分，代表风险小)
    # 2%以下为优秀，8%以上为差
    score = int(100 - (atr_pct - 0.02) / 0.06 * 100)
    score = np.clip(score, 0, 100)

    if score >= 80:
        status = "风险很低"
    elif score >= 65:
        status = "风险可控"
    elif score >= 45:
        status = "中等风险"
    elif score >= 30:
        status = "风险较高"
    else:
        status = "风险很高"

    return score, status


def create_radar_chart(data):
    """创建雷达图"""
    categories = ['L1趋势', 'L2结构', 'L3共振', 'L4风险']

    values = [
        data.get('l1', 50),
        data.get('l2', 50),
        data.get('l3', 50),
        data.get('l4', 50)
    ]

    # 闭合雷达图
    values += values[:1]
    categories += categories[:1]

    fig = go.Figure(data=go.Scatterpolar(
        r=values,
        theta=categories,
        fill='toself',
        fillcolor='rgba(66, 133, 244, 0.3)',
        line=dict(color='#4285f4', width=2),
        name='当前评分'
    ))

    fig.add_trace(go.Scatterpolar(
        r=[70, 70, 70, 70, 70],
        theta=categories,
        line=dict(color='red', width=1, dash='dash'),
        name='优秀线(70)',
        fill=None
    ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                tickmode='linear',
                tick0=0,
                dtick=20
            )
        ),
        showlegend=True,
        legend=dict(orientation='h', yanchor='bottom', y=-0.2),
        margin=dict(l=40, r=40, t=40, b=40),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )

    return fig


def create_price_chart(data):
    """创建价格和成交量图表"""
    df_records = data.get('df', [])
    if not df_records:
        return go.Figure()

    df = pd.DataFrame(df_records)
    df['date'] = pd.to_datetime(df['date'])

    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.7, 0.3],
        subplot_titles=('价格走势', '成交量')
    )

    # K线图
    fig.add_trace(go.Candlestick(
        x=df['date'],
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        name='K线',
        increasing_line_color='#dc3545',  # A股：红涨
        decreasing_line_color='#28a745'   # A股：绿跌
    ), row=1, col=1)

    # 添加均线
    if len(df) >= 20:
        df['ma20'] = df['close'].rolling(window=20).mean()
        fig.add_trace(go.Scatter(
            x=df['date'],
            y=df['ma20'],
            mode='lines',
            name='MA20',
            line=dict(color='#2196f3', width=1.5)
        ), row=1, col=1)

    if len(df) >= 60:
        df['ma60'] = df['close'].rolling(window=60).mean()
        fig.add_trace(go.Scatter(
            x=df['date'],
            y=df['ma60'],
            mode='lines',
            name='MA60',
            line=dict(color='#ff9800', width=1.5)
        ), row=1, col=1)

    # 成交量
    colors = ['#26a69a' if df['close'].iloc[i] >= df['open'].iloc[i] else '#ef5350'
              for i in range(len(df))]

    fig.add_trace(go.Bar(
        x=df['date'],
        y=df['volume'],
        name='成交量',
        marker_color=colors,
        opacity=0.8
    ), row=2, col=1)

    fig.update_layout(
        title=f"{data.get('etf', 'Unknown')} 技术分析",
        showlegend=True,
        legend=dict(orientation='h', yanchor='bottom', y=1.02),
        xaxis_rangeslider_visible=False,
        margin=dict(l=40, r=40, t=60, b=40),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=500
    )

    fig.update_yaxes(title_text="价格", row=1, col=1)
    fig.update_yaxes(title_text="成交量", row=2, col=1)
    fig.update_xaxes(title_text="日期", row=2, col=1)

    return fig


def generate_signals_table():
    """生成信号表格数据"""
    signals = []

    # 为每个ETF计算信号
    for code, info in ETF_MAP.items():
        # 获取数据
        df = get_etf_data(code, 60)

        if df is None or df.empty:
            continue

        # 计算各层得分
        l1, _ = calculate_l1_score(df)
        l2, _ = calculate_l2_score(df)
        l3, _ = calculate_l3_score(df)
        l4, _ = calculate_l4_score(df)

        # 综合得分 (加权)
        total = l1 * 0.40 + l2 * 0.20 + l3 * 0.20 + l4 * 0.20

        # 信号判断
        if total >= 75 and l1 >= 60:
            signal = "强烈买入"
        elif total >= 60 and l1 >= 50:
            signal = "买入"
        elif total <= 35 or l4 <= 30:
            signal = "卖出"
        elif total <= 25:
            signal = "强烈卖出"
        else:
            signal = "持有"

        signals.append({
            'code': code,
            'name': info['name'],
            'l1_score': round(l1, 1),
            'l2_score': round(l2, 1),
            'l3_score': round(l3, 1),
            'l4_score': round(l4, 1),
            'total_score': round(total, 1),
            'signal': signal
        })

    # 按综合得分排序
    signals.sort(key=lambda x: x['total_score'], reverse=True)

    return signals


# 页面布局实例
layout = create_layout()


def create_signal_overview_card(title: str, score: int, status: str, color: str) -> dbc.Card:
    """创建信号概览卡片"""
    return dbc.Card(
        dbc.CardBody([
            html.H6(title, className="text-muted mb-2"),
            html.H3(f"{score}", style={'color': color, 'fontWeight': 'bold'}),
            html.Small(status, className="text-muted"),
        ]),
        className="text-center shadow-sm",
        style={'borderLeft': f'4px solid {color}'}
    )


def create_signals_tab():
    """
    兼容函数：为 dashboard/main.py 提供接口
    返回策略信号监控标签页的内容
    """
    return html.Div([
        # 标题区域
        dbc.Row([
            dbc.Col([
                html.H4([
                    html.I(className="fas fa-signal me-2"),
                    "策略信号监控"
                ], className="mb-2"),
                html.P("基于L1-L4多维量化指标体系的实时信号生成系统",
                       className="text-muted mb-0"),
            ], width=12)
        ], className="mb-4"),

        # 使用说明提示
        dbc.Row([
            dbc.Col([
                dbc.Alert([
                    html.H6([
                        html.I(className="fas fa-info-circle me-2"),
                        "新版策略信号页面已启用"
                    ], className="alert-heading"),
                    html.P([
                        "策略信号功能已迁移至独立的信号分析页面。",
                        html.Br(),
                        "新页面提供更完整的L1-L4指标分析、雷达图可视化和实时信号生成。"
                    ], className="mb-2"),
                    html.Hr(),
                    html.P([
                        dbc.Button(
                            [html.I(className="fas fa-external-link-alt me-2"), "访问新版信号页面"],
                            color="primary",
                            href="/signals",
                            external_link=True,
                        ),
                    ], className="mb-0"),
                ], color="info", dismissable=True),
            ], width=12)
        ], className="mb-4"),

        # 简化版指标卡片
        dbc.Row([
            dbc.Col(create_signal_overview_card("L1趋势层", 75, "强势", "#28a745"), width=3),
            dbc.Col(create_signal_overview_card("L2结构层", 62, "中性偏多", "#ffc107"), width=3),
            dbc.Col(create_signal_overview_card("L3共振层", 58, "中性", "#5c6370"), width=3),
            dbc.Col(create_signal_overview_card("L4缺口层", 70, "偏多", "#17a2b8"), width=3),
        ], className="mb-4"),

    ])
