"""
Dashboard UI组件

提供可复用的UI组件，如指标卡片、状态徽章等
"""

from typing import Dict, List, Optional, Any, Union
from datetime import datetime

import dash_bootstrap_components as dbc
from dash import html

# 导入主题配置
try:
    from ..config import THEME
except ImportError:
    # 默认主题
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


def create_metric_card(
    title: str,
    value: str,
    change: str = "",
    change_positive: bool = True,
    icon: str = "📊",
    footer: Optional[str] = None,
) -> dbc.Card:
    """
    创建指标卡片

    Args:
        title: 标题
        value: 数值
        change: 变化值
        change_positive: 是否为正向变化
        icon: 图标
        footer: 底部文本

    Returns:
        dbc.Card: Dash Bootstrap Card组件
    """
    change_color = '#28a745' if change_positive else '#dc3545'
    arrow = '↑' if change_positive else '↓'

    card_body = [
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
    ]

    if change:
        card_body.append(
            html.Span(
                f"{arrow} {change}",
                style={
                    'color': change_color,
                    'fontWeight': 'bold',
                    'fontSize': '0.9rem',
                }
            )
        )

    children = [dbc.CardBody(card_body)]

    if footer:
        children.append(
            dbc.CardFooter(
                footer,
                style={
                    'backgroundColor': 'rgba(0,0,0,0.2)',
                    'borderTop': f'1px solid {THEME["border"]}',
                    'fontSize': '0.8rem',
                    'color': THEME['text_muted'],
                }
            )
        )

    return dbc.Card(
        children,
        style={
            'backgroundColor': THEME['bg_card'],
            'border': f'1px solid {THEME["border"]}',
            'height': '100%',
        }
    )


def create_kpi_card(
    title: str,
    value: str,
    change: str = "",
    positive: bool = True,
) -> dbc.Card:
    """
    创建KPI指标卡片（简化版）

    Args:
        title: 标题
        value: 数值
        change: 变化值
        positive: 是否为正向变化

    Returns:
        dbc.Card: Dash Bootstrap Card组件
    """
    color = '#28a745' if positive else '#dc3545'
    arrow = '↑' if positive else '↓'

    return dbc.Card(
        [
            dbc.CardBody([
                html.H6(title, style={'color': THEME['text_muted'], 'marginBottom': '8px'}),
                html.H4(value, style={'fontWeight': 'bold', 'marginBottom': '4px', 'color': THEME['text']}),
                html.Small(
                    f"{arrow} {change}",
                    style={'color': color, 'fontWeight': 'bold'}
                ) if change else None,
            ])
        ],
        style={
            'backgroundColor': THEME['bg_card'],
            'border': f'1px solid {THEME["border"]}',
            'textAlign': 'center',
        }
    )


def create_status_badge(
    status: str,
    size: str = "md",
) -> dbc.Badge:
    """
    创建状态徽章

    Args:
        status: 状态文本（'运行中', '待机', '错误'等）
        size: 尺寸（'sm', 'md', 'lg'）

    Returns:
        dbc.Badge: Dash Bootstrap Badge组件
    """
    # 根据状态确定颜色
    color_map = {
        '运行中': 'success',
        'active': 'success',
        '待机': 'warning',
        'standby': 'warning',
        '错误': 'danger',
        'error': 'danger',
        '失败': 'danger',
        'failed': 'danger',
        '完成': 'info',
        'completed': 'info',
        '成功': 'success',
        'success': 'success',
    }

    color = color_map.get(status, 'secondary')

    # 尺寸映射
    size_map = {
        'sm': {'fontSize': '0.7rem', 'padding': '0.2em 0.4em'},
        'md': {'fontSize': '0.85rem', 'padding': '0.3em 0.6em'},
        'lg': {'fontSize': '1rem', 'padding': '0.4em 0.8em'},
    }

    style = size_map.get(size, size_map['md'])

    return dbc.Badge(
        status,
        color=color,
        style={
            **style,
            'fontWeight': 'bold',
        }
    )


def create_signal_badge(
    signal: str,
    score: Optional[float] = None,
) -> html.Span:
    """
    创建信号徽章

    Args:
        signal: 信号类型（'买入', '卖出', '持有'等）
        score: 得分

    Returns:
        html.Span: Dash HTML Span组件
    """
    # 根据信号确定颜色
    color_map = {
        '买入': '#28a745',
        'buy': '#28a745',
        '卖出': '#dc3545',
        'sell': '#dc3545',
        '持有': '#ffc107',
        'hold': '#ffc107',
        '看多': '#28a745',
        '看空': '#dc3545',
        '中性': '#ffc107',
    }

    color = color_map.get(signal, '#6c757d')

    children = [signal]
    if score is not None:
        children.append(f" ({score:.1f})")

    return html.Span(
        children,
        style={
            'backgroundColor': color,
            'color': 'white',
            'padding': '0.3em 0.6em',
            'borderRadius': '0.25rem',
            'fontWeight': 'bold',
            'fontSize': '0.85rem',
        }
    )


# 导出所有组件
__all__ = [
    # 图表
    'create_price_chart',
    'create_radar_chart',
    'create_risk_gauge',
    'create_signal_timeline',
    'create_backtest_equity_chart',
    'create_backtest_drawdown_chart',
    'create_monthly_heatmap',
    'create_layer_score_chart',
    # UI组件
    'create_metric_card',
    'create_kpi_card',
    'create_status_badge',
    'create_signal_badge',
]