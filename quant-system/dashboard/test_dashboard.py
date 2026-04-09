"""
测试专用简化版 Dashboard

不依赖外部数据服务，用于 E2E 测试
"""
import os
import sys
from datetime import datetime

import dash
from dash import dcc, html, Input, Output
import dash_bootstrap_components as dbc

# 添加项目路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 初始化 Django (轻量级，不启动数据同步)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'quant_system.settings')
os.environ['DJANGO_ALLOW_ASYNC_UNSAFE'] = 'true'

import django
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
}

# 创建 Dash 应用
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.DARKLY],
    suppress_callback_exceptions=True,
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
)

app.title = "量化交易系统 - 实时监控"


def create_navbar():
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


# 布局
app.layout = html.Div(
    style={'backgroundColor': THEME['bg_dark'], 'minHeight': '100vh'},
    children=[
        create_navbar(),

        dbc.Container([
            # 第一行：ETF列表
            dbc.Row([
                dbc.Col([
                    html.H4("ETF 列表", style={'color': THEME['text'], 'marginBottom': '20px'}),
                    html.Div(id='etf-cards-container', children=[
                        dbc.Card(
                            dbc.CardBody([
                                html.H5([html.Strong("510300"), " - 沪深300ETF"], className="card-title"),
                                html.H3("4.454", style={'color': THEME['danger'], 'fontWeight': 'bold'}),
                                html.Div([
                                    html.Span("↓ -0.035 (-0.78%)", style={'color': THEME['danger'], 'fontWeight': 'bold'}),
                                ]),
                            ]),
                            style={'backgroundColor': THEME['bg_card'], 'border': f'1px solid {THEME["border"]}', 'marginBottom': '15px'},
                        ),
                        dbc.Card(
                            dbc.CardBody([
                                html.H5([html.Strong("159915"), " - 创业板ETF"], className="card-title"),
                                html.H3("3.141", style={'color': THEME['danger'], 'fontWeight': 'bold'}),
                                html.Div([
                                    html.Span("↓ -0.023 (-0.73%)", style={'color': THEME['danger'], 'fontWeight': 'bold'}),
                                ]),
                            ]),
                            style={'backgroundColor': THEME['bg_card'], 'border': f'1px solid {THEME["border"]}', 'marginBottom': '15px'},
                        ),
                    ]),
                ], width=4),

                # 第二列：K线图
                dbc.Col([
                    html.H4("K线图", style={'color': THEME['text'], 'marginBottom': '20px'}),
                    dcc.Dropdown(
                        id='etf-selector',
                        options=[
                            {'label': '510300 - 沪深300ETF', 'value': '510300'},
                            {'label': '159915 - 创业板ETF', 'value': '159915'},
                        ],
                        value='510300',
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
                    html.Div(
                        "K线图区域（测试模式）",
                        style={
                            'height': '500px',
                            'backgroundColor': THEME['bg_card'],
                            'display': 'flex',
                            'alignItems': 'center',
                            'justifyContent': 'center',
                            'color': THEME['text_muted'],
                        }
                    ),
                ], width=8),
            ]),

            # 刷新间隔
            dcc.Interval(
                id='interval-component',
                interval=5*1000,
                n_intervals=0,
            ),
        ], fluid=True),
    ]
)


@app.callback(
    Output('current-time', 'children'),
    [Input('interval-component', 'n_intervals')]
)
def update_time(n):
    """更新当前时间"""
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


if __name__ == '__main__':
    print("=" * 60)
    print("量化交易系统 - 测试版Dashboard")
    print("=" * 60)
    print(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n正在启动Dash服务器...")
    print("访问地址: http://localhost:8050")
    print("=" * 60)

    app.run(debug=True, host='0.0.0.0', port=8050)
