"""
Dashboard图表组件

封装ECharts/Plotly图表组件，用于Dashboard可视化
"""

from typing import Dict, List, Optional, Any, Tuple, Union
from datetime import datetime, timedelta
import json

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
import pandas as pd
import numpy as np

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


def create_price_chart(
    price_data: pd.DataFrame,
    pool_name: str = "候选池",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    normalize: bool = True,
) -> go.Figure:
    """
    创建品种走势图（多线图）

    Args:
        price_data: 价格数据DataFrame，列为各品种，行为日期
        pool_name: 品种池名称
        start_date: 开始日期
        end_date: 结束日期
        normalize: 是否归一化（从100开始）

    Returns:
        go.Figure: Plotly图表对象
    """
    # 过滤日期范围
    if start_date:
        price_data = price_data[price_data.index >= start_date]
    if end_date:
        price_data = price_data[price_data.index <= end_date]

    fig = go.Figure()

    # 颜色方案
    colors = [
        '#00d9ff', '#e94560', '#ffd700', '#ff6b9d',
        '#c792ea', '#82aaff', '#f78c6c', '#4ec9b0'
    ]

    for i, column in enumerate(price_data.columns):
        prices = price_data[column]

        # 归一化
        if normalize and len(prices) > 0:
            normalized = (prices / prices.iloc[0]) * 100
        else:
            normalized = prices

        fig.add_trace(go.Scatter(
            x=normalized.index,
            y=normalized,
            mode='lines',
            name=column,
            line=dict(
                color=colors[i % len(colors)],
                width=2,
            ),
            hovertemplate='<b>%{fullData.name}</b><br>' +
                         '日期: %{x|%Y-%m-%d}<br>' +
                         '价格: %{y:.2f}<extra></extra>',
        ))

    fig.update_layout(
        template='plotly_dark',
        title=dict(
            text=f'{pool_name} 品种走势图',
            font=dict(size=18, color=THEME['text']),
            x=0.5,
        ),
        paper_bgcolor=THEME['bg_card'],
        plot_bgcolor=THEME['bg_card'],
        font=dict(color=THEME['text']),
        showlegend=True,
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='center',
            x=0.5,
            bgcolor='rgba(0,0,0,0.3)',
        ),
        margin=dict(l=50, r=50, t=80, b=50),
        hovermode='x unified',
        xaxis=dict(
            showgrid=True,
            gridwidth=1,
            gridcolor=THEME['border'],
            zeroline=False,
        ),
        yaxis=dict(
            showgrid=True,
            gridwidth=1,
            gridcolor=THEME['border'],
            zeroline=False,
            title='归一化价格',
        ),
    )

    return fig


def create_radar_chart(
    four_d_score: Dict[str, Any],
    etf_name: str = "",
    show_details: bool = True,
) -> go.Figure:
    """
    创建L1-L4四维雷达图

    Args:
        four_d_score: 四维评分数据字典
        etf_name: ETF名称
        show_details: 是否显示详细指标

    Returns:
        go.Figure: Plotly图表对象
    """
    # 提取各层得分
    categories = ['L1\n趋势层', 'L2\n结构层', 'L3\n共振层', 'L4\n缺口层']

    # 从字典中提取分数
    if isinstance(four_d_score, dict):
        values = [
            four_d_score.get('L1', {}).get('score', 50),
            four_d_score.get('L2', {}).get('score', 50),
            four_d_score.get('L3', {}).get('score', 50),
            four_d_score.get('L4', {}).get('score', 50),
        ]
    else:
        # 如果是对象
        values = [
            getattr(four_d_score, 'L1_score', 50),
            getattr(four_d_score, 'L2_score', 50),
            getattr(four_d_score, 'L3_score', 50),
            getattr(four_d_score, 'L4_score', 50),
        ]

    fig = go.Figure()

    # 添加实际得分
    fig.add_trace(go.Scatterpolar(
        r=values + [values[0]],  # 闭合
        theta=categories + [categories[0]],
        fill='toself',
        fillcolor='rgba(0, 217, 255, 0.3)',
        line=dict(color='#00d9ff', width=2),
        name='当前得分',
        hovertemplate='<b>%{theta}</b><br>得分: %{r:.1f}<extra></extra>',
    ))

    # 添加参考线（50分）
    fig.add_trace(go.Scatterpolar(
        r=[50, 50, 50, 50, 50],
        theta=categories + [categories[0]],
        fill=None,
        line=dict(color='#5c6370', width=1, dash='dash'),
        name='中性线(50)',
        hovertemplate='中性线: 50<extra></extra>',
    ))

    # 添加优秀线（75分）
    fig.add_trace(go.Scatterpolar(
        r=[75, 75, 75, 75, 75],
        theta=categories + [categories[0]],
        fill=None,
        line=dict(color='#28a745', width=1, dash='dot'),
        name='优秀线(75)',
        hovertemplate='优秀线: 75<extra></extra>',
    ))

    fig.update_layout(
        template='plotly_dark',
        title=dict(
            text=f'{etf_name} L1-L4四维评分雷达图' if etf_name else 'L1-L4四维评分雷达图',
            font=dict(size=16, color=THEME['text']),
            x=0.5,
        ),
        paper_bgcolor=THEME['bg_card'],
        font=dict(color=THEME['text']),
        showlegend=True,
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=-0.15,
            xanchor='center',
            x=0.5,
            bgcolor='rgba(0,0,0,0.3)',
        ),
        margin=dict(l=80, r=80, t=80, b=80),
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                tickmode='linear',
                tick0=0,
                dtick=25,
                tickfont=dict(color=THEME['text_muted']),
                gridcolor=THEME['border'],
            ),
            angularaxis=dict(
                tickfont=dict(size=12, color=THEME['text']),
                gridcolor=THEME['border'],
            ),
            bgcolor=THEME['bg_card'],
        ),
    )

    return fig


def create_risk_gauge(
    l4_score: float,
    etf_name: str = "",
) -> go.Figure:
    """
    创建L4风险状态仪表盘
    
    Args:
        l4_score: L4层得分（0-100，高分表示低风险）
        etf_name: ETF名称
        
    Returns:
        go.Figure: Plotly图表对象
    """
    # 确定风险等级
    if l4_score >= 70:
        risk_level = "平静"
        risk_color = "#28a745"
        bar_color = "green"
    elif l4_score >= 50:
        risk_level = "隐忧"
        risk_color = "#ffc107"
        bar_color = "yellow"
    else:
        risk_level = "恐慌"
        risk_color = "#dc3545"
        bar_color = "red"
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=l4_score,
        number={
            'font': {'size': 40, 'color': THEME['text']},
            'suffix': '',
        },
        delta={
            'reference': 50,
            'position': "top",
            'font': {'size': 20},
        },
        title={
            'text': f"<b>{etf_name}</b><br><span style='color:{risk_color};font-size:24px'>{risk_level}</span>" if etf_name else f"<span style='color:{risk_color};font-size:24px'>{risk_level}</span>",
            'font': {'size': 16, 'color': THEME['text']},
        },
        gauge={
            'axis': {
                'range': [0, 100],
                'tickwidth': 2,
                'tickcolor': THEME['text_muted'],
                'tickmode': 'linear',
                'tick0': 0,
                'dtick': 25,
            },
            'bar': {'color': bar_color, 'thickness': 0.75},
            'bgcolor': THEME['bg_dark'],
            'borderwidth': 2,
            'bordercolor': THEME['border'],
            'steps': [
                {'range': [0, 30], 'color': 'rgba(220, 53, 69, 0.3)'},
                {'range': [30, 50], 'color': 'rgba(255, 193, 7, 0.3)'},
                {'range': [50, 70], 'color': 'rgba(40, 167, 69, 0.2)'},
                {'range': [70, 100], 'color': 'rgba(40, 167, 69, 0.4)'},
            ],
            'threshold': {
                'line': {'color': THEME['primary'], 'width': 3},
                'thickness': 0.8,
                'value': 50,
            },
        },
    ))
    
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor=THEME['bg_card'],
        font=dict(color=THEME['text']),
        margin=dict(l=30, r=30, t=80, b=30),
    )
    
    return fig


def create_signal_timeline(
    signals: List[Dict[str, Any]],
    max_items: int = 20,
) -> html.Div:
    """
    创建最新信号时间线
    
    Args:
        signals: 信号列表，每个信号为字典
        max_items: 最大显示条数
        
    Returns:
        html.Div: Dash HTML Div组件
    """
    if not signals:
        return html.Div(
            "暂无信号",
            style={
                'textAlign': 'center',
                'color': THEME['text_muted'],
                'padding': '20px',
            }
        )
    
    # 限制数量
    signals = signals[:max_items]
    
    # 信号颜色映射
    color_map = {
        '买入': '#28a745',
        '卖出': '#dc3545',
        '持有': '#ffc107',
        '看多': '#28a745',
        '看空': '#dc3545',
        '中性': '#ffc107',
    }
    
    timeline_items = []
    
    for i, signal in enumerate(signals):
        signal_type = signal.get('signal_type', '未知')
        color = color_map.get(signal_type, '#6c757d')
        
        # 时间格式化
        timestamp = signal.get('timestamp', '')
        if isinstance(timestamp, datetime):
            time_str = timestamp.strftime('%m-%d %H:%M')
        else:
            time_str = str(timestamp)[:16] if timestamp else '--'
        
        item = html.Div([
            # 时间轴点和线
            html.Div([
                html.Div(
                    style={
                        'width': '12px',
                        'height': '12px',
                        'borderRadius': '50%',
                        'backgroundColor': color,
                        'border': f'2px solid {THEME["bg_card"]}',
                        'position': 'relative',
                        'zIndex': '2',
                    }
                ),
                # 连接线（除了最后一个）
                html.Div(
                    style={
                        'width': '2px',
                        'flex': '1',
                        'backgroundColor': THEME['border'],
                        'marginTop': '-2px',
                    }
                ) if i < len(signals) - 1 else None,
            ], style={
                'display': 'flex',
                'flexDirection': 'column',
                'alignItems': 'center',
                'width': '30px',
                'minHeight': '60px',
            }),
            
            # 内容
            html.Div([
                # 时间和类型
                html.Div([
                    html.Span(
                        time_str,
                        style={
                            'color': THEME['text_muted'],
                            'fontSize': '0.75rem',
                            'marginRight': '8px',
                        }
                    ),
                    html.Span(
                        signal_type,
                        style={
                            'color': color,
                            'fontWeight': 'bold',
                            'fontSize': '0.85rem',
                        }
                    ),
                ]),
                
                # ETF信息
                html.Div([
                    html.Span(
                        signal.get('etf_name', signal.get('etf_code', '')),
                        style={
                            'color': THEME['text'],
                            'fontWeight': 'bold',
                            'fontSize': '0.9rem',
                            'marginRight': '8px',
                        }
                    ),
                    html.Span(
                        f"得分: {signal.get('score', 0):.1f}",
                        style={
                            'color': THEME['secondary'],
                            'fontSize': '0.8rem',
                        }
                    ) if signal.get('score') else None,
                ], style={'marginTop': '2px'}),
                
                # 附加信息
                html.Div(
                    signal.get('description', ''),
                    style={
                        'color': THEME['text_muted'],
                        'fontSize': '0.8rem',
                        'marginTop': '4px',
                    }
                ) if signal.get('description') else None,
                
            ], style={
                'flex': '1',
                'padding': '8px 12px',
                'backgroundColor': 'rgba(0,0,0,0.2)',
                'borderRadius': '6px',
                'marginBottom': '8px',
            }),
            
        ], style={
            'display': 'flex',
            'alignItems': 'flex-start',
        })
        
        timeline_items.append(item)
    
    return html.Div(
        timeline_items,
        style={
            'padding': '10px',
            'maxHeight': '500px',
            'overflowY': 'auto',
        }
    )


# 导出所有组件
__all__ = [
    'create_metric_card',
    'create_kpi_card',
    'create_status_badge',
    'create_signal_badge',
    'create_signal_timeline',
]