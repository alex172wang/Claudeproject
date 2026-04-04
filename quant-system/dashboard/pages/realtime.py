"""
实时监控页面

提供实时行情监控、价格走势图、成交量监控等功能。
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

# 导入数据适配器
try:
    from ..data_adapter_v2 import data_adapter_v2
except ImportError:
    from data_adapter_v2 import data_adapter_v2


def get_etf_list() -> list:
    """获取ETF列表，优先从mootdx获取真实数据"""
    try:
        if data_adapter_v2 and data_adapter_v2._connected:
            df = data_adapter_v2.get_etf_list_real()
            if df is not None and not df.empty:
                # 转换为字典列表
                etf_list = []
                for _, row in df.head(20).iterrows():  # 取前20个
                    etf_list.append({
                        'code': str(row.get('code', '')),
                        'name': str(row.get('name', f"ETF{row.get('code', '')}")),
                        'market': str(row.get('market', 'SH'))
                    })
                return etf_list
    except Exception as e:
        print(f"[Realtime] 获取ETF列表失败: {e}")

    # 返回默认列表
    return [
        {'code': '510300', 'name': '沪深300ETF', 'market': 'SH'},
        {'code': '510500', 'name': '中证500ETF', 'market': 'SH'},
        {'code': '159915', 'name': '创业板ETF', 'market': 'SZ'},
        {'code': '518880', 'name': '黄金ETF', 'market': 'SH'},
        {'code': '588000', 'name': '科创50ETF', 'market': 'SH'},
        {'code': '513500', 'name': '标普500ETF', 'market': 'SH'},
        {'code': '513100', 'name': '纳斯达克ETF', 'market': 'SH'},
        {'code': '511010', 'name': '国债ETF', 'market': 'SH'},
    ]


def fetch_etf_realtime_data(etf_list: list) -> list:
    """获取ETF实时数据"""
    result = []
    try:
        if data_adapter_v2 and data_adapter_v2._connected:
            codes = [etf['code'] for etf in etf_list]
            df_quotes = data_adapter_v2.get_realtime_quotes_real(codes)

            if df_quotes is not None and not df_quotes.empty:
                for etf in etf_list:
                    code = etf['code']
                    quote_row = df_quotes[df_quotes['code'] == code]

                    if not quote_row.empty:
                        row = quote_row.iloc[0]
                        price = float(row.get('price', 0))
                        change = float(row.get('change', 0))
                        change_pct = (change / (price - change)) * 100 if (price - change) != 0 else 0
                    else:
                        price, change_pct = get_price_from_history(code)

                    result.append({
                        'code': code,
                        'name': etf['name'],
                        'price': price,
                        'change': change_pct,
                    })
                return result
    except Exception as e:
        print(f"[Realtime] 获取实时数据失败: {e}")

    # 从历史数据获取
    for etf in etf_list:
        price, change_pct = get_price_from_history(etf['code'])
        result.append({
            'code': etf['code'],
            'name': etf['name'],
            'price': price,
            'change': change_pct,
        })
    return result


def get_price_from_history(code: str) -> tuple:
    """从历史数据获取最新价格和变化率"""
    try:
        if data_adapter_v2:
            df = data_adapter_v2.get_etf_price_real(code, days=5)
            if df is not None and not df.empty and 'close' in df.columns:
                latest_price = float(df['close'].iloc[-1])
                if len(df) >= 2:
                    prev_price = float(df['close'].iloc[-2])
                    change_pct = ((latest_price - prev_price) / prev_price) * 100 if prev_price != 0 else 0
                else:
                    change_pct = 0
                return latest_price, change_pct
    except Exception as e:
        print(f"[Realtime] 获取历史价格失败 {code}: {e}")
    return 0.0, 0.0


# 全局ETF数据缓存
_etf_data_cache = {
    'list': [],
    'realtime_data': [],
    'last_update': None
}


def get_cached_etf_data():
    """获取缓存的ETF数据（带1分钟缓存）"""
    global _etf_data_cache
    from datetime import datetime

    now = datetime.now()
    if (_etf_data_cache['last_update'] is None or
        (now - _etf_data_cache['last_update']).seconds > 60):
        # 刷新缓存
        _etf_data_cache['list'] = get_etf_list()
        _etf_data_cache['realtime_data'] = fetch_etf_realtime_data(_etf_data_cache['list'])
        _etf_data_cache['last_update'] = now
        print(f"[Realtime] ETF数据缓存已刷新，共 {len(_etf_data_cache['list'])} 个ETF")

    return _etf_data_cache['realtime_data']


def create_realtime_tab() -> html.Div:
    """创建实时监控标签页"""

    # 获取ETF数据（优先真实数据）
    etf_data = get_cached_etf_data()

    # 创建ETF价格卡片（使用真实数据）
    etf_cards = []
    for etf in etf_data[:8]:  # 最多显示8个
        etf_cards.append(
            dbc.Col(
                create_etf_price_card(
                    etf['code'],
                    etf['name'],
                    etf['price'],
                    etf['change'] / 100,  # 转换为小数
                    etf['change']
                ),
                width=3
            )
        )

    # 补齐到8个卡片（如果数据不足）
    while len(etf_cards) < 8:
        idx = len(etf_cards)
        default_etfs = [
            {'code': '510300', 'name': '沪深300ETF', 'price': 4.125, 'change': 0.36},
            {'code': '510500', 'name': '中证500ETF', 'price': 6.823, 'change': -0.34},
            {'code': '518880', 'name': '黄金ETF', 'price': 3.956, 'change': 0.20},
            {'code': '159915', 'name': '创业板ETF', 'price': 1.234, 'change': 0.98},
            {'code': '588000', 'name': '科创50ETF', 'price': 1.156, 'change': 0.45},
            {'code': '513500', 'name': '标普500ETF', 'price': 2.345, 'change': 0.12},
            {'code': '513100', 'name': '纳斯达克ETF', 'price': 4.567, 'change': 0.78},
            {'code': '511010', 'name': '国债ETF', 'price': 1.089, 'change': 0.05},
        ]
        if idx < len(default_etfs):
            etf = default_etfs[idx]
            etf_cards.append(
                dbc.Col(
                    create_etf_price_card(
                        etf['code'],
                        etf['name'],
                        etf['price'],
                        etf['change'] / 100,
                        etf['change']
                    ),
                    width=3
                )
            )
        else:
            break

    return html.Div([
        # 第一行：ETF 价格卡片
        dbc.Row(etf_cards, className="mb-4"),

        # 第二行：实时走势图 + 买卖盘
        dbc.Row([
            dbc.Col(
                dbc.Card(
                    [
                        dbc.CardHeader([
                            html.H5("实时走势", className="mb-0"),
                            dbc.ButtonGroup([
                                dbc.Button("分时", size="sm", color="primary", active=True),
                                dbc.Button("5日", size="sm", color="outline-secondary"),
                                dbc.Button("日K", size="sm", color="outline-secondary"),
                                dbc.Button("周K", size="sm", color="outline-secondary"),
                            ], size="sm"),
                        ], className="d-flex justify-content-between align-items-center"),
                        dbc.CardBody(
                            dcc.Graph(
                                id='realtime-price-chart',
                                config={'displayModeBar': True},
                                style={'height': '400px'},
                            )
                        ),
                    ],
                    style={'backgroundColor': THEME['bg_card']},
                ),
                width=8,
            ),
            dbc.Col(
                dbc.Card(
                    [
                        dbc.CardHeader(html.H5("买卖盘", className="mb-0")),
                        dbc.CardBody(
                            html.Div(id='order-book-container', children=[
                                create_order_book_row('卖5', 4.128, 12500, 'sell'),
                                create_order_book_row('卖4', 4.127, 8700, 'sell'),
                                create_order_book_row('卖3', 4.126, 15200, 'sell'),
                                create_order_book_row('卖2', 4.125, 23100, 'sell'),
                                create_order_book_row('卖1', 4.124, 18900, 'sell'),
                                html.Hr(style={'borderColor': THEME['border'], 'margin': '10px 0'}),
                                create_order_book_row('买1', 4.123, 21200, 'buy'),
                                create_order_book_row('买2', 4.122, 16800, 'buy'),
                                create_order_book_row('买3', 4.121, 9500, 'buy'),
                                create_order_book_row('买4', 4.120, 7200, 'buy'),
                                create_order_book_row('买5', 4.119, 11300, 'buy'),
                            ])
                        ),
                    ],
                    style={'backgroundColor': THEME['bg_card']},
                ),
                width=4,
            ),
        ], className="mb-4"),

        # 第三行：成交明细 + 板块热力图
        dbc.Row([
            dbc.Col(
                dbc.Card(
                    [
                        dbc.CardHeader([
                            html.H5("成交明细", className="mb-0"),
                            dbc.Button("导出", size="sm", color="outline-primary"),
                        ], className="d-flex justify-content-between align-items-center"),
                        dbc.CardBody(
                            dash_table.DataTable(
                                id='trade-history-table',
                                columns=[
                                    {'name': '时间', 'id': 'time'},
                                    {'name': '方向', 'id': 'direction'},
                                    {'name': '价格', 'id': 'price'},
                                    {'name': '数量', 'id': 'volume'},
                                ],
                                data=[
                                    {'time': '14:32:15', 'direction': '买盘', 'price': '4.124', 'volume': '1500'},
                                    {'time': '14:32:12', 'direction': '卖盘', 'price': '4.125', 'volume': '800'},
                                    {'time': '14:32:08', 'direction': '买盘', 'price': '4.124', 'volume': '2300'},
                                    {'time': '14:32:05', 'direction': '买盘', 'price': '4.123', 'volume': '1200'},
                                    {'time': '14:32:01', 'direction': '卖盘', 'price': '4.125', 'volume': '500'},
                                ],
                                style_header={
                                    'backgroundColor': THEME['bg_light'],
                                    'fontWeight': 'bold',
                                },
                                style_cell={
                                    'backgroundColor': THEME['bg_card'],
                                    'color': THEME['text'],
                                    'textAlign': 'center',
                                },
                                style_data_conditional=[
                                    {
                                        'if': {'filter_query': '{direction} = "买盘"'},
                                        'color': '#28a745',
                                    },
                                    {
                                        'if': {'filter_query': '{direction} = "卖盘"'},
                                        'color': '#dc3545',
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
                        dbc.CardHeader(html.H5("板块热力图", className="mb-0")),
                        dbc.CardBody(
                            dcc.Graph(
                                id='sector-heatmap',
                                config={'displayModeBar': False},
                                style={'height': '300px'},
                            )
                        ),
                    ],
                    style={'backgroundColor': THEME['bg_card']},
                ),
                width=6,
            ),
        ]),
    ])


def create_etf_price_card(symbol: str, name: str, price: float, change: float, change_pct: float) -> dbc.Card:
    """创建ETF价格卡片"""

    is_up = change >= 0
    color = '#28a745' if is_up else '#dc3545'
    arrow = '▲' if is_up else '▼'
    sign = '+' if is_up else ''

    return dbc.Card(
        [
            dbc.CardBody([
                html.Div([
                    html.Span(name, style={
                        'color': THEME['text_muted'],
                        'fontSize': '0.85rem',
                    }),
                    html.Span(symbol, style={
                        'color': THEME['text_muted'],
                        'fontSize': '0.75rem',
                        'marginLeft': '8px',
                    }),
                ]),
                html.Div([
                    html.Span(f"{price:.3f}", style={
                        'fontSize': '1.8rem',
                        'fontWeight': 'bold',
                        'color': color,
                    }),
                ], style={'margin': '8px 0'}),
                html.Div([
                    html.Span(f"{arrow} {sign}{change:.3f}", style={
                        'color': color,
                        'fontSize': '0.9rem',
                        'fontWeight': 'bold',
                        'marginRight': '10px',
                    }),
                    html.Span(f"{sign}{change_pct:.2f}%", style={
                        'color': color,
                        'fontSize': '0.9rem',
                    }),
                ]),
            ])
        ],
        style={
            'backgroundColor': THEME['bg_card'],
            'border': f'1px solid {THEME["border"]}',
            'height': '100%',
        }
    )


def create_order_book_row(label: str, price: float, volume: int, side: str) -> html.Div:
    """创建买卖盘行"""

    color = '#28a745' if side == 'buy' else '#dc3545'

    return html.Div([
        html.Span(label, style={
            'width': '40px',
            'color': THEME['text_muted'],
            'fontSize': '0.85rem',
        }),
        html.Span(f"{price:.3f}", style={
            'flex': '1',
            'textAlign': 'center',
            'color': color,
            'fontWeight': 'bold',
            'fontSize': '0.95rem',
        }),
        html.Span(f"{volume:,}", style={
            'width': '80px',
            'textAlign': 'right',
            'color': THEME['text_muted'],
            'fontSize': '0.85rem',
        }),
    ], style={
        'display': 'flex',
        'alignItems': 'center',
        'padding': '4px 8px',
        'borderRadius': '4px',
        ':hover': {
            'backgroundColor': THEME['bg_light'],
        }
    })


def register_realtime_callbacks(app):
    """注册实时监控页面的回调函数"""
    from dash import Input, Output
    from datetime import datetime

    @app.callback(
        Output('current-time', 'children'),
        [Input('interval-component', 'n_intervals')]
    )
    def update_time(n):
        """更新当前时间"""
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
