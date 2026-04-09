"""
实时监控页面

提供实时行情监控、价格走势图、成交量监控等功能。
使用 API 数据适配器获取数据。
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

# 导入 API 数据适配器
_api_adapter = None

def get_api_adapter():
    """获取 API 数据适配器（延迟加载）"""
    global _api_adapter
    if _api_adapter is None:
        try:
            from ..data_adapter_api import get_api_data_adapter
            _api_adapter = get_api_data_adapter()
        except ImportError:
            from data_adapter_api import get_api_data_adapter
            _api_adapter = get_api_data_adapter()
    return _api_adapter


def get_etf_list() -> list:
    """获取ETF列表，从API获取"""
    try:
        adapter = get_api_adapter()
        etf_list = adapter.get_etf_list()
        if etf_list:
            return etf_list[:20]  # 取前20个
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
    """获取ETF实时数据，从API获取"""
    result = []
    try:
        adapter = get_api_adapter()
        for etf in etf_list:
            code = etf['code']
            df = adapter.get_etf_price_real(code)
            if df is not None and not df.empty:
                row = df.iloc[0]
                price = float(row.get('current_price', 0))
                change = float(row.get('change', 0))
                change_pct = float(row.get('change_percent', 0))
            else:
                price, change_pct = get_price_from_history(code)
                change = 0

            result.append({
                'code': code,
                'name': etf['name'],
                'price': price,
                'change': change,
                'change_pct': change_pct,
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
            'change': 0,
            'change_pct': change_pct,
        })
    return result


def get_price_from_history(code: str) -> tuple:
    """从历史K线数据获取最新价格和变化率"""
    try:
        adapter = get_api_adapter()
        df = adapter.get_etf_kline(code, days=5)
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
                    etf['change_pct'] / 100 if 'change_pct' in etf else etf.get('change', 0) / 100,
                    etf['change_pct'] if 'change_pct' in etf else etf.get('change', 0)
                ),
                width=3
            )
        )

    # 补齐到8个卡片（如果数据不足）
    # 注意：不再使用硬编码的默认数据，数据不足时显示空白
    while len(etf_cards) < 8:
        break  # 不再补齐默认数据

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
                                html.Div('暂无买卖盘数据', style={'color': THEME['text_muted'], 'textAlign': 'center', 'padding': '50px'})
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
                                data=[],  # 暂无真实成交数据
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
                                        'color': '#dc3545',  # A股：红涨
                                    },
                                    {
                                        'if': {'filter_query': '{direction} = "卖盘"'},
                                        'color': '#28a745',  # A股：绿跌
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
    color = '#dc3545' if is_up else '#28a745'  # A股：红涨绿跌
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

    color = '#dc3545' if side == 'buy' else '#28a745'  # A股：红涨绿跌

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
