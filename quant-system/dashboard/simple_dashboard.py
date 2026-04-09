"""
简化版量化交易系统仪表板

专注于ETF数据展示和实时监控
"""

import os
import sys
import logging
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

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 添加项目路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 初始化 Django
import django
from asgiref.sync import async_to_sync, sync_to_async

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'quant_system.settings')
django.setup()

# 主题配置
THEME = {
    'bg_dark': '#1a1a2e',
    'bg_card': '#16213e',
    'bg_light': '#0f3460',
    'text': '#eaeaea',
    'text_muted': '#a0a0a0',
    'border': '#2a2a4a',
    'primary': '#00d9ff',
    'danger': '#e94560',
    'success': '#28a745',
    'warning': '#ffc107',
    'critical': '#ff0000',
}

# 创建 Dash 应用
logger.info("正在初始化 Dash 应用...")
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.DARKLY],
    suppress_callback_exceptions=True,
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
)

app.title = "量化交易系统 - 实时监控"
logger.info("Dash 应用初始化完成")

# =========================================================================
# 数据获取函数
# =========================================================================

@sync_to_async
def get_etf_list() -> List[Dict]:
    """获取ETF列表"""
    logger.info("[get_etf_list] 开始获取ETF列表...")
    try:
        from portfolio.models import ETF
        etfs = ETF.objects.filter(is_active=True)
        result = [
            {'code': etf.code, 'name': etf.name, 'category': etf.category, 'market': etf.market}
            for etf in etfs
        ]
        logger.info(f"[get_etf_list] 获取到 {len(result)} 个ETF")
        return result
    except Exception as e:
        logger.error(f"[get_etf_list] 获取ETF列表失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return []

@sync_to_async
def get_etf_price(code: str) -> Optional[Dict]:
    """获取ETF实时价格"""
    logger.info(f"[get_etf_price] 获取 {code} 的实时价格...")
    try:
        from data_sync.tasks import get_realtime_quote
        quote = get_realtime_quote(code)
        if quote:
            change_percent = (quote.get('change', 0) / quote.get('prev_close', 1)) * 100 if quote.get('prev_close', 0) != 0 else 0
            result = {
                'code': quote.get('code', code),
                'name': quote.get('name', code),
                'current_price': quote.get('price', 0),
                'change': quote.get('change', 0),
                'change_percent': round(change_percent, 2),
                'volume': quote.get('volume', 0),
                'turnover': quote.get('amount', 0),
                'update_time': datetime.now(),
            }
            logger.info(f"[get_etf_price] {code} 价格: {result['current_price']}")
            return result
        logger.warning(f"[get_etf_price] {code} 没有获取到行情数据")
        return None
    except Exception as e:
        logger.error(f"[get_etf_price] 获取 {code} 价格失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None

@sync_to_async
def get_etf_kline(code: str, days: int = 60) -> pd.DataFrame:
    """获取ETF K线数据"""
    logger.info(f"[get_etf_kline] 获取 {code} 的{days}天K线数据...")
    try:
        from data_sync.sync_service import data_sync_service
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days+10)

        df = data_sync_service.sync_historical_kline(
            code,
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d'),
            'day'
        )

        if df is not None and not df.empty:
            logger.info(f"[get_etf_kline] {code} 获取到 {len(df)} 条K线数据")
            return df
        logger.warning(f"[get_etf_kline] {code} 没有K线数据")
        return pd.DataFrame()
    except Exception as e:
        logger.error(f"[get_etf_kline] 获取 {code} K线数据失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return pd.DataFrame()

def get_portfolio_positions() -> List[Dict]:
    """获取当前持仓"""
    try:
        from portfolio.models import Position
        from django.db.models import Sum

        positions = Position.objects.filter(quantity__gt=0).select_related('etf')
        result = []
        for pos in positions:
            result.append({
                'symbol': pos.etf.code,
                'name': pos.etf.name,
                'quantity': pos.quantity,
                'avg_cost': float(pos.avg_cost),
                'market_value': float(pos.market_value),
            })
        return result
    except Exception as e:
        logger.error(f"[get_portfolio_positions] 获取持仓失败: {e}")
        return []

@sync_to_async
def get_risk_report() -> Dict:
    """获取风控报告"""
    try:
        from core.live.risk.controller import RiskController, TrailingStopRule, OvernightRiskRule, HolidayRiskRule, TrendConsistencyRule, VolatilityAnomalyRule, DailyLossRule, PositionSizeRule

        controller = RiskController()
        # 添加趋势跟踪专用规则
        controller.add_trend_following_rules(max_drawback_pct=0.15)

        # 获取持仓（同步调用，因为已经用了 sync_to_async）
        positions = get_portfolio_positions()
        if not positions:
            return {'status': 'no_positions', 'alerts': [], 'can_trade': True, 'message': '暂无持仓'}

        # 获取实时价格
        from data_sync.tasks import get_realtime_quote
        price_data = {}
        for pos in positions:
            quote = get_realtime_quote(pos['symbol'])
            if quote:
                price_data[pos['symbol']] = {
                    'current': quote.get('price', pos['avg_cost']),
                    'prev_close': quote.get('prev_close', pos['avg_cost']),
                }
                pos['current_price'] = quote.get('price', pos['avg_cost'])
                pos['change'] = quote.get('change', 0)

        # 获取账户总资产
        try:
            from portfolio.models import Account
            account = Account.objects.first()
            total_value = float(account.total_assets) if account else 1000000
        except:
            total_value = 1000000

        # 获取当日盈亏
        daily_pnl = sum(pos.get('change', 0) * pos['quantity'] for pos in positions if 'change' in pos)

        # 构建上下文
        context = {
            'positions': positions,
            'portfolio_value': total_value,
            'daily_pnl': daily_pnl,
            'current_date': datetime.now(),
            'price_data': price_data,
        }

        # 执行风控检查
        report = controller.get_risk_report(context)
        report['positions'] = positions
        return report

    except Exception as e:
        logger.error(f"[get_risk_report] 获取风控报告失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {'status': 'error', 'alerts': [], 'can_trade': True, 'message': str(e)}

# =========================================================================
# 布局组件
# =========================================================================

def create_navbar() -> dbc.Navbar:
    """创建顶部导航栏"""
    return dbc.Navbar(
        dbc.Container(
            [
                dbc.NavbarBrand(
                    [
                        html.I(className="fas fa-chart-line", style={'marginRight': '10px'}),
                        "量化交易系统 - ETF监控"
                    ],
                    href="#",
                    className="ms-2",
                    style={'fontSize': '1.5rem', 'fontWeight': 'bold'},
                ),
                dbc.Nav(
                    [
                        dbc.NavItem(
                            html.Span(
                                "● 运行中",
                                style={
                                    'color': '#28a745',
                                    'fontWeight': 'bold',
                                    'padding': '0px 15px',
                                }
                            ),
                        ),
                        dbc.NavItem(
                            html.Span(
                                id='current-time',
                                style={'color': THEME['text_muted'], 'padding': '0px 15px'},
                            ),
                        ),
                    ],
                    className="ms-auto align-items-center",
                    navbar=True,
                ),
            ],
            fluid=True,
        ),
        color="dark",
        dark=True,
        className="mb-4",
    )

def create_risk_alert_panel(report: Dict) -> html.Div:
    """创建风控预警面板"""
    # 根据状态决定颜色和内容
    if report.get('status') == 'no_positions':
        status_color = THEME['text_muted']
        status_icon = "fas fa-inbox"
        status_text = "暂无持仓"
        alerts = []
    elif report.get('status') == 'error':
        status_color = THEME['warning']
        status_icon = "fas fa-exclamation-triangle"
        status_text = report.get('message', '获取风控数据失败')
        alerts = []
    elif report.get('can_trade', True):
        status_color = THEME['success']
        status_icon = "fas fa-check-circle"
        status_text = "风控正常"
        alerts = report.get('high_risk_alerts', [])
    else:
        status_color = THEME['danger']
        status_icon = "fas fa-times-circle"
        status_text = "禁止交易"
        alerts = report.get('critical_alerts', []) + report.get('high_risk_alerts', [])

    # 构建警告列表
    alert_items = []
    for alert in alerts[:5]:  # 最多显示5条
        alert_items.append(
            html.Div(
                [
                    html.I(className="fas fa-exclamation-circle", style={'marginRight': '8px', 'color': THEME['danger']}),
                    html.Span(alert.get('message', ''), style={'color': THEME['text']}),
                ],
                style={'padding': '5px 0', 'borderBottom': f'1px solid {THEME["border"]}'}
            )
        )

    # 持仓信息
    positions = report.get('positions', [])
    position_info = []
    for pos in positions[:4]:  # 最多显示4个
        change = pos.get('change', 0)
        color = THEME['success'] if change >= 0 else THEME['danger']
        position_info.append(
            html.Div(
                [
                    html.Span(f"{pos['symbol']}", style={'fontWeight': 'bold', 'marginRight': '10px'}),
                    html.Span(f"{pos.get('current_price', 0):.3f}", style={'color': color}),
                    html.Span(f" ({change:+.3f})", style={'color': color, 'fontSize': '0.85em'}),
                ],
                style={'padding': '3px 0'}
            )
        )

    panel_style = {
        'backgroundColor': THEME['bg_card'],
        'border': f'2px solid {status_color}',
        'borderRadius': '10px',
        'padding': '15px',
        'marginBottom': '20px',
    }

    return html.Div(
        [
            # 状态行
            html.Div(
                [
                    html.Div(
                        [
                            html.I(className=status_icon, style={'fontSize': '2rem', 'color': status_color, 'marginRight': '15px'}),
                            html.Div(
                                [
                                    html.H4(status_text, style={'color': status_color, 'margin': '0', 'fontWeight': 'bold'}),
                                    html.Span(f"持仓 {len(positions)} 个品种", style={'color': THEME['text_muted'], 'fontSize': '0.9rem'}) if positions else None,
                                ]
                            ),
                        ],
                        style={'display': 'flex', 'alignItems': 'center'}
                    ),
                    # 持仓快捷查看
                    html.Div(position_info, style={'marginLeft': 'auto', 'textAlign': 'right'}) if position_info else None,
                ],
                style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'marginBottom': '15px' if alert_items else '0'}
            ),
            # 警告列表
            html.Div(alert_items) if alert_items else None,
            # 禁止事项提示
            html.Div(
                [
                    html.Hr(style={'borderColor': THEME['border'], 'margin': '10px 0'}),
                    html.Div(
                        [
                            html.I(className="fas fa-info-circle", style={'marginRight': '8px', 'color': THEME['warning']}),
                            html.Span("当前限制: ", style={'color': THEME['warning'], 'fontWeight': 'bold'}),
                            html.Span(
                                "禁止新开仓 | 建议周五降仓" if not report.get('can_trade', True) else "可正常交易",
                                style={'color': THEME['text']}
                            ),
                        ]
                    ) if alert_items else None,
                ]
            ) if alert_items else None,
        ],
        style=panel_style
    )

def create_etf_card(etf_data: Dict, price_data: Optional[Dict] = None) -> dbc.Card:
    """创建ETF卡片"""
    code = etf_data['code']
    name = etf_data['name']

    if price_data:
        price = price_data['current_price']
        change = price_data['change']
        change_pct = price_data['change_percent']
        color = THEME['success'] if change >= 0 else THEME['danger']
        arrow = '↑' if change >= 0 else '↓'
    else:
        price = 0
        change = 0
        change_pct = 0
        color = THEME['text_muted']
        arrow = '-'

    return dbc.Card(
        dbc.CardBody([
            html.H5([html.Strong(code), " - ", name], className="card-title"),
            html.H3(f"{price:.3f}", style={'color': color, 'fontWeight': 'bold'}),
            html.Div([
                html.Span(f"{arrow} {change:+.3f} ({change_pct:+.2f}%)", style={'color': color, 'fontWeight': 'bold'}),
            ]),
            html.Div(f"成交量: {price_data['volume']:,}" if price_data else "", style={'color': THEME['text_muted'], 'fontSize': '0.9rem', 'marginTop': '10px'}),
        ]),
        style={'backgroundColor': THEME['bg_card'], 'border': f'1px solid {THEME["border"]}', 'marginBottom': '15px'},
    )

async def create_kline_chart(code: str, days: int = 60) -> go.Figure:
    """创建K线图"""
    df = await get_etf_kline(code, days)

    if df.empty or len(df) == 0:
        fig = go.Figure()
        fig.update_layout(
            template='plotly_dark',
            paper_bgcolor=THEME['bg_card'],
            plot_bgcolor=THEME['bg_card'],
            title='暂无数据',
        )
        return fig

    # 确保有date列
    if 'date' not in df.columns and df.index.name == 'datetime':
        df = df.reset_index()
        df['date'] = df['datetime']

    fig = go.Figure(data=[go.Candlestick(
        x=df['date'] if 'date' in df.columns else df.index,
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        name='K线',
    )])

    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor=THEME['bg_card'],
        plot_bgcolor=THEME['bg_card'],
        font=dict(color=THEME['text']),
        title=f'{code} K线图',
        xaxis_rangeslider_visible=False,
        margin=dict(l=50, r=50, t=80, b=50),
    )

    return fig

# =========================================================================
# 主布局
# =========================================================================

app.layout = html.Div(
    style={'backgroundColor': THEME['bg_dark'], 'minHeight': '100vh'},
    children=[
        create_navbar(),

        dbc.Container([
            # 风控预警面板
            html.Div(id='risk-alert-panel'),

            # 第一行：ETF列表
            dbc.Row([
                dbc.Col([
                    html.H4("ETF 列表", style={'color': THEME['text'], 'marginBottom': '20px'}),
                    html.Div(id='etf-cards-container'),
                ], width=4),

                # 第二列：K线图
                dbc.Col([
                    html.H4("K线图", style={'color': THEME['text'], 'marginBottom': '20px'}),
                    dcc.Dropdown(
                        id='etf-selector',
                        options=[],
                        value=None,
                        style={'marginBottom': '15px', 'color': '#000'},
                    ),
                    dcc.Dropdown(
                        id='days-selector',
                        options=[
                            {'label': '7天', 'value': 7},
                            {'label': '30天', 'value': 30},
                            {'label': '60天', 'value': 60},
                            {'label': '180天', 'value': 180},
                        ],
                        value=60,
                        style={'marginBottom': '15px', 'color': '#000'},
                    ),
                    dcc.Graph(id='kline-chart', style={'height': '500px'}),
                ], width=8),
            ]),

            # 刷新间隔
            dcc.Interval(
                id='interval-component',
                interval=5*1000,  # 5秒刷新一次
                n_intervals=0,
            ),
        ], fluid=True),
    ]
)

# =========================================================================
# 回调函数
# =========================================================================

@app.callback(
    Output('current-time', 'children'),
    [Input('interval-component', 'n_intervals')]
)
def update_time(n):
    """更新当前时间"""
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

@app.callback(
    Output('risk-alert-panel', 'children'),
    [Input('interval-component', 'n_intervals')]
)
async def update_risk_alert(n):
    """更新风控预警面板"""
    try:
        report = await get_risk_report()
        return create_risk_alert_panel(report)
    except Exception as e:
        logger.error(f"[update_risk_alert] 更新风控面板失败: {e}")
        return create_risk_alert_panel({'status': 'error', 'message': str(e)})

@app.callback(
    [Output('etf-cards-container', 'children'),
     Output('etf-selector', 'options')],
    [Input('interval-component', 'n_intervals')]
)
async def update_etf_cards(n):
    """更新ETF卡片和下拉选择器"""
    logger.info(f"[update_etf_cards] 回调触发, n={n}")
    try:
        etf_list = await get_etf_list()
        logger.info(f"[update_etf_cards] 收到 {len(etf_list)} 个ETF")

        cards = []
        options = []

        for etf in etf_list:
            price = await get_etf_price(etf['code'])
            cards.append(create_etf_card(etf, price))
            options.append({'label': f"{etf['code']} - {etf['name']}", 'value': etf['code']})

        logger.info(f"[update_etf_cards] 生成 {len(cards)} 个卡片, {len(options)} 个选项")
        return cards, options
    except Exception as e:
        logger.error(f"[update_etf_cards] 回调执行失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return [], []

@app.callback(
    Output('etf-selector', 'value'),
    [Input('etf-selector', 'options')]
)
def set_default_etf(options):
    """设置默认选中的ETF"""
    if options and len(options) > 0:
        return options[0]['value']
    return None

@app.callback(
    Output('kline-chart', 'figure'),
    [Input('etf-selector', 'value'),
     Input('days-selector', 'value')]
)
async def update_kline_chart(code, days):
    """更新K线图"""
    logger.info(f"[update_kline_chart] 回调触发, code={code}, days={days}")
    try:
        if code is None:
            logger.info("[update_kline_chart] 没有选择ETF，返回空图表")
            return go.Figure()
        logger.info(f"[update_kline_chart] 正在创建 {code} 的K线图...")
        return await create_kline_chart(code, days or 60)
    except Exception as e:
        logger.error(f"[update_kline_chart] 回调执行失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return go.Figure()

# 暂时禁用点击回调，避免复杂的异步问题
# ETF 选择通过下拉框完成

# =========================================================================
# 启动（由 run_dashboard.py 调用）
# =========================================================================

if __name__ == '__main__':
    print("=" * 60)
    print("量化交易系统 - 简化版Dashboard")
    print("=" * 60)
    print(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n正在启动Dash服务器...")
    print("访问地址: http://localhost:8050")
    print("=" * 60)

    app.run(debug=True, host='0.0.0.0', port=8050)
