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
from ..config import THEME


def create_realtime_tab() -> html.Div:
    """创建实时监控标签页"""

    return html.Div([
        # 第一行：ETF 价格卡片
        dbc.Row([
            dbc.Col(create_etf_price_card('510300', '沪深300ETF', 4.125, 0.015, 0.36), width=3),
            dbc.Col(create_etf_price_card('510500', '中证500ETF', 6.823, -0.023, -0.34), width=3),
            dbc.Col(create_etf_price_card('518880', '黄金ETF', 3.956, 0.008, 0.20), width=3),
            dbc.Col(create_etf_price_card('159949', '创业板ETF', 1.234, 0.012, 0.98), width=3),
        ], className="mb-4"),

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
