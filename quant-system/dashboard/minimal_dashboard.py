#!/usr/bin/env python3
"""
最简版 Dashboard - 用于测试
"""
import os
import sys
from datetime import datetime

# 添加项目路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 初始化 Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'quant_system.settings')
import django
django.setup()

import dash
from dash import dcc, html, Input, Output
import dash_bootstrap_components as dbc

# 主题
THEME = {
    'bg_dark': '#1a1a2e',
    'bg_card': '#16213e',
    'text': '#eaeaea',
}

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.DARKLY],
)

app.title = "测试 Dashboard"

# 测试数据获取
def get_test_data():
    from portfolio.models import ETF
    count = ETF.objects.count()
    etfs = list(ETF.objects.values('code', 'name'))
    return {'count': count, 'etfs': etfs}

# 布局
app.layout = html.Div(
    style={'backgroundColor': THEME['bg_dark'], 'minHeight': '100vh', 'padding': '20px'},
    children=[
        html.H1("测试 Dashboard", style={'color': THEME['text']}),
        html.Div(id='test-output', style={'color': THEME['text'], 'marginTop': '20px'}),
        dcc.Interval(
            id='interval',
            interval=2000,
            n_intervals=0
        )
    ]
)

@app.callback(
    Output('test-output', 'children'),
    [Input('interval', 'n_intervals')]
)
def update_test(n):
    data = get_test_data()
    return html.Div([
        html.H3(f"ETF 数量: {data['count']}"),
        html.H4("ETF 列表:"),
        html.Ul([html.Li(f"{etf['code']} - {etf['name']}") for etf in data['etfs']]),
        html.P(f"更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    ])

if __name__ == '__main__':
    print("=" * 60)
    print("最简版测试 Dashboard")
    print("=" * 60)
    print("访问: http://localhost:8051")
    print("=" * 60)
    app.run(debug=True, host='0.0.0.0', port=8051)
