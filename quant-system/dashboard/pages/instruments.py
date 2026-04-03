"""
品种维护页面

提供ETF品种管理、品种池管理、池成员维护等功能。
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

import dash_bootstrap_components as dbc
from dash import html, dcc, dash_table, Input, Output, State, callback_context
import plotly.graph_objects as go
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

# 导入数据适配器
try:
    from ..data_adapter_v2 import data_adapter_v2
except ImportError:
    from data_adapter_v2 import data_adapter_v2


# ============ 数据获取函数 ============

def get_real_etf_list() -> list:
    """获取真实ETF列表，优先从mootdx获取"""
    try:
        if data_adapter_v2 and data_adapter_v2._connected:
            df = data_adapter_v2.get_etf_list_real()
            if df is not None and not df.empty and len(df) > 10:
                # 转换为字典列表
                etf_list = []
                for _, row in df.iterrows():
                    code = str(row.get('code', ''))
                    if code:
                        etf_list.append({
                            'code': code,
                            'name': str(row.get('name', f"ETF{code}")),
                            'market': str(row.get('market', 'SH')),
                            'category': categorize_etf(code),
                            'tracking_index': '',
                            'fund_manager': '',
                            'is_active': True,
                            'list_date': ''
                        })
                print(f"[Instruments] 从mootdx获取 {len(etf_list)} 个ETF")
                return etf_list
    except Exception as e:
        print(f"[Instruments] 获取真实ETF列表失败: {e}")

    # 返回默认列表
    return get_default_etf_list()


def categorize_etf(code: str) -> str:
    """根据代码分类ETF"""
    cross_border = ['513', '1596', '1597', '1598']
    commodity = ['518']
    bond = ['511']

    if any(code.startswith(p) for p in cross_border):
        return 'cross_border'
    elif any(code.startswith(p) for p in commodity):
        return 'commodity'
    elif any(code.startswith(p) for p in bond):
        return 'bond'
    else:
        return 'equity'


def get_default_etf_list() -> list:
    """获取默认ETF列表"""
    return [
        {'code': '510300', 'name': '沪深300ETF', 'market': 'SH', 'category': 'equity', 'tracking_index': '沪深300指数', 'fund_manager': '华泰柏瑞', 'is_active': True, 'list_date': '2012-05-28'},
        {'code': '510050', 'name': '上证50ETF', 'market': 'SH', 'category': 'equity', 'tracking_index': '上证50指数', 'fund_manager': '华夏基金', 'is_active': True, 'list_date': '2005-02-23'},
        {'code': '510500', 'name': '中证500ETF', 'market': 'SH', 'category': 'equity', 'tracking_index': '中证500指数', 'fund_manager': '南方基金', 'is_active': True, 'list_date': '2013-03-15'},
        {'code': '159915', 'name': '创业板ETF', 'market': 'SZ', 'category': 'equity', 'tracking_index': '创业板指数', 'fund_manager': '易方达', 'is_active': True, 'list_date': '2011-12-09'},
        {'code': '588000', 'name': '科创50ETF', 'market': 'SH', 'category': 'equity', 'tracking_index': '科创50指数', 'fund_manager': '华夏基金', 'is_active': True, 'list_date': '2020-11-16'},
        {'code': '513500', 'name': '标普500ETF', 'market': 'SH', 'category': 'cross_border', 'tracking_index': '标普500指数', 'fund_manager': '博时基金', 'is_active': True, 'list_date': '2016-12-01'},
        {'code': '513100', 'name': '纳斯达克ETF', 'market': 'SH', 'category': 'cross_border', 'tracking_index': '纳斯达克100指数', 'fund_manager': '国泰基金', 'is_active': True, 'list_date': '2013-04-25'},
        {'code': '518880', 'name': '黄金ETF', 'market': 'SH', 'category': 'commodity', 'tracking_index': '上海黄金交易所AU99.99', 'fund_manager': '华安基金', 'is_active': True, 'list_date': '2013-07-29'},
        {'code': '511010', 'name': '国债ETF', 'market': 'SH', 'category': 'bond', 'tracking_index': '上证5年期国债指数', 'fund_manager': '国泰基金', 'is_active': True, 'list_date': '2013-03-25'},
    ]


# ============ 模拟数据（实际应来自Django模型或API） ============

# ETF品种数据
ETF_DATA = [
    {'code': '510300', 'name': '沪深300ETF', 'market': 'SH', 'category': 'equity', 'tracking_index': '沪深300指数', 'fund_manager': '华泰柏瑞', 'is_active': True, 'list_date': '2012-05-28'},
    {'code': '510050', 'name': '上证50ETF', 'market': 'SH', 'category': 'equity', 'tracking_index': '上证50指数', 'fund_manager': '华夏基金', 'is_active': True, 'list_date': '2005-02-23'},
    {'code': '510500', 'name': '中证500ETF', 'market': 'SH', 'category': 'equity', 'tracking_index': '中证500指数', 'fund_manager': '南方基金', 'is_active': True, 'list_date': '2013-03-15'},
    {'code': '159915', 'name': '创业板ETF', 'market': 'SZ', 'category': 'equity', 'tracking_index': '创业板指数', 'fund_manager': '易方达', 'is_active': True, 'list_date': '2011-12-09'},
    {'code': '588000', 'name': '科创50ETF', 'market': 'SH', 'category': 'equity', 'tracking_index': '科创50指数', 'fund_manager': '华夏基金', 'is_active': True, 'list_date': '2020-11-16'},
    {'code': '513500', 'name': '标普500ETF', 'market': 'SH', 'category': 'cross_border', 'tracking_index': '标普500指数', 'fund_manager': '博时基金', 'is_active': True, 'list_date': '2016-12-01'},
    {'code': '513100', 'name': '纳斯达克ETF', 'market': 'SH', 'category': 'cross_border', 'tracking_index': '纳斯达克100指数', 'fund_manager': '国泰基金', 'is_active': True, 'list_date': '2013-04-25'},
    {'code': '518880', 'name': '黄金ETF', 'market': 'SH', 'category': 'commodity', 'tracking_index': '上海黄金交易所AU99.99', 'fund_manager': '华安基金', 'is_active': True, 'list_date': '2013-07-29'},
    {'code': '511010', 'name': '国债ETF', 'market': 'SH', 'category': 'bond', 'tracking_index': '上证5年期国债指数', 'fund_manager': '国泰基金', 'is_active': True, 'list_date': '2013-03-25'},
]

# 品种池数据
POOL_DATA = [
    {'code': 'rotation_pool', 'name': 'ETF周度轮动品种池', 'purpose': 'rotation', 'description': '核心宽基ETF池，用于周度轮动策略，包含沪深300、上证50、中证500、创业板等主要宽基指数ETF', 'member_count': 6, 'is_active': True, 'created_at': '2024-01-15'},
    {'code': 'permanent_pool', 'name': '永久组合品种池', 'purpose': 'permanent', 'description': '哈利·布朗永久组合实现池，包含权益、债券、黄金、现金四大类资产', 'member_count': 6, 'is_active': True, 'created_at': '2024-01-15'},
    {'code': 'thematic_pool', 'name': '主题仓位品种池', 'purpose': 'thematic', 'description': '主题/行业ETF池，用于主题仓位策略，包含新能源、芯片、5G、消费等主题', 'member_count': 11, 'is_active': True, 'created_at': '2024-01-15'},
    {'code': 'option_underlying_pool', 'name': '期权标的池', 'purpose': 'rotation', 'description': '场内ETF期权标的池，包含50ETF和300ETF，用于L4缺口层指标计算', 'member_count': 2, 'is_active': True, 'created_at': '2024-02-01'},
    {'code': 'money_market_pool', 'name': '货币基金池', 'purpose': 'permanent', 'description': '货币市场基金ETF池，作为现金等价物，用于防御性配置', 'member_count': 2, 'is_active': True, 'created_at': '2024-02-01'},
]

# 类别和用途映射
CATEGORY_CHOICES = {
    'equity': '权益型',
    'bond': '债券型',
    'commodity': '商品型',
    'money_market': '货币市场型',
    'cross_border': '跨境型',
    'sector': '行业主题型',
}

PURPOSE_CHOICES = {
    'rotation': 'ETF轮动',
    'permanent': '永久组合',
    'thematic': '主题仓位',
    'custom': '自定义',
}

MARKET_CHOICES = {
    'SH': '上交所',
    'SZ': '深交所',
}


def create_instruments_tab() -> html.Div:
    """创建品种维护标签页"""

    return html.Div([
        # 第一行：统计卡片
        dbc.Row([
            dbc.Col(create_stat_card("ETF品种", len(ETF_DATA), "个", "#00d9ff"), width=3),
            dbc.Col(create_stat_card("品种池", len(POOL_DATA), "个", "#28a745"), width=3),
            dbc.Col(create_stat_card("池成员总数", sum(p['member_count'] for p in POOL_DATA), "个", "#ffc107"), width=3),
            dbc.Col(create_stat_card("活跃品种", sum(1 for e in ETF_DATA if e['is_active']), "个", "#e94560"), width=3),
        ], className="mb-4"),

        # 第二行：ETF品种表格
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.H5("ETF品种管理", className="mb-0"),
                        dbc.ButtonGroup([
                            dbc.Button("新增ETF", size="sm", color="primary", id="btn-add-etf"),
                            dbc.Button("批量导入", size="sm", color="outline-secondary"),
                            dbc.Button("导出CSV", size="sm", color="outline-secondary"),
                        ], size="sm"),
                    ], className="d-flex justify-content-between align-items-center"),
                    dbc.CardBody(
                        dash_table.DataTable(
                            id='etf-table',
                            columns=[
                                {'name': '代码', 'id': 'code'},
                                {'name': '名称', 'id': 'name'},
                                {'name': '市场', 'id': 'market'},
                                {'name': '类别', 'id': 'category'},
                                {'name': '跟踪指数', 'id': 'tracking_index'},
                                {'name': '基金管理人', 'id': 'fund_manager'},
                                {'name': '状态', 'id': 'is_active'},
                                {'name': '上市日期', 'id': 'list_date'},
                            ],
                            data=[{
                                **etf,
                                'market': MARKET_CHOICES.get(etf['market'], etf['market']),
                                'category': CATEGORY_CHOICES.get(etf['category'], etf['category']),
                                'is_active': '✓ 活跃' if etf['is_active'] else '✗ 停用',
                            } for etf in ETF_DATA],
                            style_header={
                                'backgroundColor': THEME['bg_light'],
                                'fontWeight': 'bold',
                                'border': f'1px solid {THEME["border"]}',
                            },
                            style_cell={
                                'backgroundColor': THEME['bg_card'],
                                'color': THEME['text'],
                                'border': f'1px solid {THEME["border"]}',
                                'textAlign': 'left',
                                'fontSize': '0.85rem',
                                'padding': '8px 12px',
                            },
                            style_data_conditional=[
                                {
                                    'if': {'filter_query': '{is_active} = "✓ 活跃"'},
                                    'color': '#28a745',
                                },
                                {
                                    'if': {'filter_query': '{is_active} = "✗ 停用"'},
                                    'color': '#dc3545',
                                },
                            ],
                            row_selectable='single',
                            selected_rows=[],
                            page_size=15,
                            style_table={'overflowX': 'auto'},
                        )
                    ),
                ], style={'backgroundColor': THEME['bg_card']}, className="mb-4"),
            ], width=12),
        ]),

        # 第三行：品种池表格
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.H5("品种池管理", className="mb-0"),
                        dbc.ButtonGroup([
                            dbc.Button("新增池", size="sm", color="primary"),
                            dbc.Button("编辑成员", size="sm", color="outline-secondary"),
                            dbc.Button("复制池", size="sm", color="outline-secondary"),
                        ], size="sm"),
                    ], className="d-flex justify-content-between align-items-center"),
                    dbc.CardBody(
                        dash_table.DataTable(
                            id='pool-table',
                            columns=[
                                {'name': '池代码', 'id': 'code'},
                                {'name': '池名称', 'id': 'name'},
                                {'name': '用途', 'id': 'purpose'},
                                {'name': '成员数', 'id': 'member_count'},
                                {'name': '描述', 'id': 'description'},
                                {'name': '状态', 'id': 'is_active'},
                                {'name': '创建日期', 'id': 'created_at'},
                            ],
                            data=[{
                                **pool,
                                'purpose': PURPOSE_CHOICES.get(pool['purpose'], pool['purpose']),
                                'is_active': '✓ 启用' if pool['is_active'] else '✗ 停用',
                                'description': pool['description'][:50] + '...' if len(pool['description']) > 50 else pool['description'],
                            } for pool in POOL_DATA],
                            style_header={
                                'backgroundColor': THEME['bg_light'],
                                'fontWeight': 'bold',
                                'border': f'1px solid {THEME["border"]}',
                            },
                            style_cell={
                                'backgroundColor': THEME['bg_card'],
                                'color': THEME['text'],
                                'border': f'1px solid {THEME["border"]}',
                                'textAlign': 'left',
                                'fontSize': '0.85rem',
                                'padding': '8px 12px',
                            },
                            style_data_conditional=[
                                {
                                    'if': {'filter_query': '{is_active} = "✓ 启用"'},
                                    'color': '#28a745',
                                },
                            ],
                            row_selectable='single',
                            selected_rows=[],
                            page_size=10,
                            style_table={'overflowX': 'auto'},
                        )
                    ),
                ], style={'backgroundColor': THEME['bg_card']}),
            ], width=12),
        ]),
    ])


def create_stat_card(title: str, value: int, unit: str, color: str) -> dbc.Card:
    """创建统计卡片"""

    return dbc.Card(
        [
            dbc.CardBody([
                html.H6(title, style={'color': THEME['text_muted'], 'marginBottom': '8px'}),
                html.Div([
                    html.H3(
                        str(value),
                        style={
                            'fontWeight': 'bold',
                            'color': color,
                            'margin': '0',
                            'display': 'inline-block',
                        }
                    ),
                    html.Span(
                        unit,
                        style={
                            'color': THEME['text_muted'],
                            'fontSize': '0.9rem',
                            'marginLeft': '5px',
                        }
                    ),
                ]),
            ])
        ],
        style={
            'backgroundColor': THEME['bg_card'],
            'border': f'1px solid {THEME["border"]}',
            'textAlign': 'center',
        }
    )


# 回调函数将在 dashboard/main.py 中注册
def register_instruments_callbacks(app):
    """注册品种维护页面的回调函数"""

    @app.callback(
        [Output('etf-table', 'data'),
         Output('pool-table', 'data')],
        [Input('interval-component', 'n_intervals')]
    )
    def refresh_tables(n):
        """刷新表格数据"""
        # 这里可以添加从后端API获取真实数据的逻辑
        etf_data = [{
            **etf,
            'market': MARKET_CHOICES.get(etf['market'], etf['market']),
            'category': CATEGORY_CHOICES.get(etf['category'], etf['category']),
            'is_active': '✓ 活跃' if etf['is_active'] else '✗ 停用',
        } for etf in ETF_DATA]

        pool_data = [{
            **pool,
            'purpose': PURPOSE_CHOICES.get(pool['purpose'], pool['purpose']),
            'is_active': '✓ 启用' if pool['is_active'] else '✗ 停用',
            'description': pool['description'][:50] + '...' if len(pool['description']) > 50 else pool['description'],
        } for pool in POOL_DATA]

        return etf_data, pool_data
