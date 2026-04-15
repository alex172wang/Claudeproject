"""
品种维护页面

提供ETF品种管理、品种池管理、池成员维护等手动操作功能。
"""

import os
from datetime import datetime
from typing import List, Dict, Any, Optional

import dash_bootstrap_components as dbc
from dash import html, dcc, dash_table, Input, Output, State, callback_context, ALL, MATCH
import pandas as pd

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

# API 基础路径
API_BASE = "http://127.0.0.1:8000/api"


# ============ 工具函数 ============

def get_api_client():
    """获取 API 客户端（延迟加载）"""
    try:
        import requests
        return requests
    except ImportError:
        return None


def api_get(endpoint: str) -> Optional[dict]:
    """GET 请求"""
    client = get_api_client()
    if not client:
        return None
    try:
        resp = client.get(f"{API_BASE}/{endpoint}", timeout=5)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        print(f"[API GET Error] {endpoint}: {e}")
    return None


def api_post(endpoint: str, data: dict) -> Optional[dict]:
    """POST 请求"""
    client = get_api_client()
    if not client:
        return None
    try:
        resp = client.post(f"{API_BASE}/{endpoint}/", json=data, timeout=10)
        if resp.status_code in [200, 201]:
            return resp.json()
        else:
            print(f"[API POST Error] {endpoint}: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"[API POST Error] {endpoint}: {e}")
    return None


def api_delete(endpoint: str, data: dict = None) -> Optional[dict]:
    """DELETE 请求"""
    client = get_api_client()
    if not client:
        return None
    try:
        resp = client.delete(f"{API_BASE}/{endpoint}/", json=data, timeout=10)
        if resp.status_code in [200, 204]:
            return resp.json() if resp.content else {"success": True}
        else:
            print(f"[API DELETE Error] {endpoint}: {resp.status_code}")
    except Exception as e:
        print(f"[API DELETE Error] {endpoint}: {e}")
    return None


def create_etf_via_api(code: str, name: str, market: str, category: str) -> Optional[dict]:
    """通过 API 创建 ETF"""
    client = get_api_client()
    if not client:
        return None
    try:
        resp = client.post(f"{API_BASE}/portfolio/etfs/", json={
            'code': code, 'name': name, 'market': market, 'category': category
        }, timeout=10)
        if resp.status_code in [200, 201]:
            return resp.json()
        else:
            print(f"[Create ETF Error] {resp.status_code}: {resp.text}")
            return {'success': False, 'error': resp.text}
    except Exception as e:
        print(f"[Create ETF Error] {e}")
        return None


def refresh_etf_data() -> List[dict]:
    """刷新 ETF 数据"""
    client = get_api_client()
    if not client:
        return []
    try:
        resp = client.get(f"{API_BASE}/portfolio/etfs/", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            # 处理分页格式
            if 'results' in data:
                return data['results']
            return data
    except Exception as e:
        print(f"[API GET ETF Error]: {e}")
    return []


def refresh_pool_data() -> List[dict]:
    """刷新品种池数据 - 使用模拟数据，后续实现"""
    # TODO: 后续添加真实的品种池 API
    return []


# ============ 页面组件 ============

def create_instruments_tab() -> html.Div:
    """创建品种维护标签页"""

    return html.Div([
        # 统计卡片行
        dbc.Row([
            dbc.Col(create_stat_card("ETF品种", "etf-count", "#00d9ff"), width=3),
            dbc.Col(create_stat_card("品种池", "pool-count", "#28a745"), width=3),
            dbc.Col(create_stat_card("池成员", "member-count", "#ffc107"), width=3),
            dbc.Col(create_stat_card("活跃状态", "active-status", "#e94560"), width=3),
        ], className="mb-4"),

        # 刷新按钮
        dbc.Row([
            dbc.Col([
                dbc.ButtonGroup([
                    dbc.Button([html.I(className="fas fa-sync-alt mr-1"), " 刷新数据"],
                               id="btn-refresh-all", color="outline-secondary", size="sm"),
                    dbc.Button([html.I(className="fas fa-plus mr-1"), " 新增ETF"],
                               id="btn-open-add-etf-modal", color="primary", size="sm"),
                    dbc.Button([html.I(className="fas fa-trash-alt mr-1"), " 批量删除ETF"],
                               id="btn-open-batch-delete-modal", color="danger", size="sm"),
                ]),
            ], width="auto"),
        ], className="mb-3"),

        # ETF 品种管理表格
        dbc.Card([
            dbc.CardHeader([
                html.H5("ETF品种管理", className="mb-0 d-inline-block"),
                html.Span(id="etf-count-badge", className="badge badge-primary ml-2"),
            ]),
            dbc.CardBody([
                dash_table.DataTable(
                    id='etf-table',
                    columns=[
                        {'name': '选择', 'id': 'select', 'presentation': 'checkbox'},
                        {'name': '代码', 'id': 'code'},
                        {'name': '名称', 'id': 'name'},
                        {'name': '市场', 'id': 'market'},
                        {'name': '类别', 'id': 'category'},
                        {'name': '状态', 'id': 'is_active'},
                        {'name': '操作', 'id': 'actions', 'presentation': 'html'},
                    ],
                    data=[],
                    style_header={
                        'backgroundColor': THEME['bg_light'],
                        'fontWeight': 'bold',
                        'border': f'1px solid {THEME["border"]}',
                        'color': THEME['text'],
                    },
                    style_cell={
                        'backgroundColor': THEME['bg_card'],
                        'color': THEME['text'],
                        'border': f'1px solid {THEME["border"]}',
                        'textAlign': 'center',
                        'fontSize': '0.85rem',
                        'padding': '6px 8px',
                    },
                    style_data_conditional=[
                        {
                            'if': {'filter_query': '{is_active} = "活跃"'},
                            'color': '#28a745',
                        },
                        {
                            'if': {'filter_query': '{is_active} = "停用"'},
                            'color': '#dc3545',
                        },
                    ],
                    row_selectable='multi',
                    selected_rows=[],
                    page_size=20,
                    style_table={'overflowX': 'auto'},
                ),
            ]),
        ], style={'backgroundColor': THEME['bg_card']}, className="mb-4"),

        # 品种池管理
        dbc.Card([
            dbc.CardHeader([
                html.H5("品种池管理", className="mb-0 d-inline-block"),
                dbc.ButtonGroup([
                    dbc.Button([html.I(className="fas fa-plus mr-1"), " 新增池"],
                               id="btn-open-add-pool-modal", color="primary", size="sm"),
                    dbc.Button([html.I(className="fas fa-edit mr-1"), " 编辑池"],
                               id="btn-open-edit-pool-modal", color="outline-secondary", size="sm"),
                    dbc.Button([html.I(className="fas fa-trash-alt mr-1"), " 删除池"],
                               id="btn-open-delete-pool-modal", color="danger", size="sm"),
                ], className="float-right"),
            ]),
            dbc.CardBody([
                dash_table.DataTable(
                    id='pool-table',
                    columns=[
                        {'name': '代码', 'id': 'code'},
                        {'name': '名称', 'id': 'name'},
                        {'name': '用途', 'id': 'purpose'},
                        {'name': '成员数', 'id': 'member_count'},
                        {'name': '描述', 'id': 'description'},
                        {'name': '状态', 'id': 'is_active'},
                        {'name': '创建日期', 'id': 'created_at'},
                        {'name': '操作', 'id': 'actions', 'presentation': 'html'},
                    ],
                    data=[],
                    style_header={
                        'backgroundColor': THEME['bg_light'],
                        'fontWeight': 'bold',
                        'border': f'1px solid {THEME["border"]}',
                        'color': THEME['text'],
                    },
                    style_cell={
                        'backgroundColor': THEME['bg_card'],
                        'color': THEME['text'],
                        'border': f'1px solid {THEME["border"]}',
                        'textAlign': 'center',
                        'fontSize': '0.85rem',
                        'padding': '6px 8px',
                    },
                    style_data_conditional=[
                        {
                            'if': {'filter_query': '{is_active} = "启用"'},
                            'color': '#28a745',
                        },
                        {
                            'if': {'filter_query': '{is_active} = "停用"'},
                            'color': '#dc3545',
                        },
                    ],
                    row_selectable='single',
                    selected_rows=[],
                    page_size=15,
                    style_table={'overflowX': 'auto'},
                ),
            ]),
        ], style={'backgroundColor': THEME['bg_card']}),

        # 提示消息
        html.Div(id='instruments-toast-container'),

        # ============ 模态框 ============

        # 新增 ETF 模态框
        create_add_etf_modal(),

        # 批量删除 ETF 模态框
        create_batch_delete_modal(),

        # 新增池模态框
        create_add_pool_modal(),

        # 删除池模态框
        create_delete_pool_modal(),

        # 池成员管理模态框
        create_pool_members_modal(),

    ], id='instruments-content')


def create_stat_card(title: str, element_id: str, color: str) -> dbc.Card:
    """创建统计卡片"""
    return dbc.Card([
        dbc.CardBody([
            html.H6(title, style={'color': THEME['text_muted'], 'marginBottom': '5px'}),
            html.H3(id=element_id, style={'color': color, 'fontWeight': 'bold', 'margin': '0'}),
        ])
    ], style={'backgroundColor': THEME['bg_card'], 'border': f'1px solid {THEME["border"]}'})


def create_add_etf_modal() -> dbc.Modal:
    """新增 ETF 模态框"""
    return dbc.Modal([
        dbc.ModalHeader("新增 ETF 品种"),
        dbc.ModalBody([
            dbc.Form([
                html.Div([
                    dbc.Label("ETF 代码"),
                    dbc.Input(id="add-etf-code", placeholder="例如：510300", maxLength=6),
                    dbc.FormText("请输入6位ETF代码"),
                ]),
                html.Div([
                    dbc.Label("ETF 名称"),
                    dbc.Input(id="add-etf-name", placeholder="例如：沪深300ETF"),
                ]),
                html.Div([
                    dbc.Label("市场"),
                    dbc.Select(id="add-etf-market", options=[
                        {'label': '上交所 (SH)', 'value': 'SH'},
                        {'label': '深交所 (SZ)', 'value': 'SZ'},
                    ], value='SH'),
                ]),
                html.Div([
                    dbc.Label("类别"),
                    dbc.Select(id="add-etf-category", options=[
                        {'label': '权益型', 'value': 'equity'},
                        {'label': '债券型', 'value': 'bond'},
                        {'label': '商品型', 'value': 'commodity'},
                        {'label': '货币市场型', 'value': 'money_market'},
                        {'label': '跨境型', 'value': 'cross_border'},
                        {'label': '行业主题型', 'value': 'sector'},
                    ], value='equity'),
                ]),
            ]),
        ]),
        dbc.ModalFooter([
            dbc.Button("取消", id="btn-cancel-add-etf", color="secondary"),
            dbc.Button("确认添加", id="btn-confirm-add-etf", color="primary"),
        ]),
    ], id="add-etf-modal", backdrop=True, autofocus=False)


def create_batch_delete_modal() -> dbc.Modal:
    """批量删除 ETF 模态框"""
    return dbc.Modal([
        dbc.ModalHeader("批量删除 ETF"),
        dbc.ModalBody([
            html.P("请输入要删除的 ETF 代码，多个代码用逗号或换行分隔："),
            dbc.Textarea(id="batch-delete-codes", placeholder="例如：\n510300\n510500\n159915", rows=6),
            html.Div(id="batch-delete-preview", className="mt-3"),
        ]),
        dbc.ModalFooter([
            dbc.Button("取消", id="btn-cancel-batch-delete", color="secondary"),
            dbc.Button("确认删除", id="btn-confirm-batch-delete", color="danger"),
        ]),
    ], id="batch-delete-modal", backdrop=True, autofocus=False)


def create_add_pool_modal() -> dbc.Modal:
    """新增池模态框"""
    return dbc.Modal([
        dbc.ModalHeader("新增品种池"),
        dbc.ModalBody([
            dbc.Form([
                html.Div([
                    dbc.Label("池代码"),
                    dbc.Input(id="add-pool-code", placeholder="例如：rotation_pool"),
                    dbc.FormText("建议使用有意义的代码，如 rotation_pool"),
                ]),
                html.Div([
                    dbc.Label("池名称"),
                    dbc.Input(id="add-pool-name", placeholder="例如：ETF轮动池"),
                ]),
                html.Div([
                    dbc.Label("用途"),
                    dbc.Select(id="add-pool-purpose", options=[
                        {'label': 'ETF轮动', 'value': 'rotation'},
                        {'label': '永久组合', 'value': 'permanent'},
                        {'label': '主题仓位', 'value': 'thematic'},
                        {'label': '自定义', 'value': 'custom'},
                    ], value='custom'),
                ]),
                html.Div([
                    dbc.Label("描述"),
                    dbc.Textarea(id="add-pool-description", placeholder="品种池描述（可选）", rows=3),
                ]),
            ]),
        ]),
        dbc.ModalFooter([
            dbc.Button("取消", id="btn-cancel-add-pool", color="secondary"),
            dbc.Button("确认创建", id="btn-confirm-add-pool", color="primary"),
        ]),
    ], id="add-pool-modal", backdrop=True, autofocus=False)


def create_delete_pool_modal() -> dbc.Modal:
    """删除池模态框"""
    return dbc.Modal([
        dbc.ModalHeader("删除品种池", id="delete-pool-header"),
        dbc.ModalBody([
            html.P("确定要删除以下品种池吗？此操作将同时移除所有成员。"),
            html.Div(id="delete-pool-info", style={'color': '#dc3545'}),
            dbc.Input(id="delete-pool-code", type="hidden"),
        ]),
        dbc.ModalFooter([
            dbc.Button("取消", id="btn-cancel-delete-pool", color="secondary"),
            dbc.Button("确认删除", id="btn-confirm-delete-pool", color="danger"),
        ]),
    ], id="delete-pool-modal", backdrop=True, autofocus=False)


def create_pool_members_modal() -> dbc.Modal:
    """池成员管理模态框"""
    return dbc.Modal([
        dbc.ModalHeader("池成员管理", id="pool-members-header"),
        dbc.ModalBody([
            html.Div(id="pool-members-info", className="mb-3"),
            dbc.Row([
                dbc.Col([
                    html.H6("添加成员"),
                    dbc.InputGroup([
                        dbc.Input(id="add-member-code", placeholder="ETF代码，如 510300"),
                        dbc.InputGroupText(
                            dbc.Button("添加", id="btn-add-pool-member", color="success", size="sm"),
                        ),
                    ]),
                ], width=6),
                dbc.Col([
                    html.H6("批量添加"),
                    dbc.InputGroup([
                        dbc.Textarea(id="batch-add-members", placeholder="多个代码，逗号或换行分隔", rows=2),
                        dbc.InputGroupText(
                            dbc.Button("批量添加", id="btn-batch-add-members", color="primary", size="sm"),
                        ),
                    ]),
                ], width=6),
            ], className="mb-3"),
            html.H6("当前成员"),
            dash_table.DataTable(
                id='pool-members-table',
                columns=[
                    {'name': 'ETF代码', 'id': 'etf_code'},
                    {'name': 'ETF名称', 'id': 'etf_name'},
                    {'name': '权重', 'id': 'weight'},
                    {'name': '状态', 'id': 'is_active'},
                    {'name': '操作', 'id': 'actions', 'presentation': 'html'},
                ],
                data=[],
                style_header={
                    'backgroundColor': THEME['bg_light'],
                    'fontWeight': 'bold',
                    'border': f'1px solid {THEME["border"]}',
                    'color': THEME['text'],
                },
                style_cell={
                    'backgroundColor': THEME['bg_card'],
                    'color': THEME['text'],
                    'border': f'1px solid {THEME["border"]}',
                    'textAlign': 'center',
                    'fontSize': '0.8rem',
                },
                row_selectable='multi',
                page_size=10,
            ),
        ]),
        dbc.ModalFooter([
            dbc.Button("关闭", id="btn-close-pool-members", color="secondary"),
        ]),
    ], id="pool-members-modal", size="lg", backdrop=True, autofocus=False)


# ============ 回调函数 ============

def register_instruments_callbacks(app):
    """注册品种维护页面的回调函数"""

    # 刷新所有数据
    @app.callback(
        [Output('etf-table', 'data'),
         Output('pool-table', 'data'),
         Output('etf-count', 'children'),
         Output('pool-count', 'children'),
         Output('member-count', 'children'),
         Output('active-status', 'children')],
        [Input('btn-refresh-all', 'n_clicks'),
         Input('interval-component', 'n_intervals')]
    )
    def refresh_all_data(n_clicks, n_intervals):
        """刷新所有数据"""
        etf_data = refresh_etf_data()
        pool_data = refresh_pool_data()

        # 计算成员总数
        total_members = sum(p.get('member_count', 0) for p in pool_data)
        active_etfs = sum(1 for e in etf_data if e.get('is_active', True))

        # 格式化 ETF 数据
        etf_rows = []
        for e in etf_data:
            etf_rows.append({
                'code': e.get('code', ''),
                'name': e.get('name', ''),
                'market': e.get('market', ''),
                'category': e.get('category_display', e.get('category', '')),
                'is_active': '活跃' if e.get('is_active', True) else '停用',
                'actions': f'''
                    <button class="btn btn-sm btn-outline-danger" onclick="deleteEtf('{e.get('code', '')}')">
                        <i class="fas fa-trash"></i>
                    </button>
                ''',
            })

        # 格式化池数据
        pool_rows = []
        for p in pool_data:
            pool_rows.append({
                'code': p.get('code', ''),
                'name': p.get('name', ''),
                'purpose': p.get('purpose_display', p.get('purpose', '')),
                'member_count': p.get('member_count', 0),
                'description': (p.get('description', '')[:30] + '...') if len(p.get('description', '')) > 30 else p.get('description', ''),
                'is_active': '启用' if p.get('is_active', True) else '停用',
                'created_at': p.get('created_at', '')[:10] if p.get('created_at') else '',
                'actions': f'''
                    <button class="btn btn-sm btn-outline-info" onclick="openPoolMembers('{p.get('code', '')}', '{p.get('name', '')}')">
                        <i class="fas fa-users"></i>
                    </button>
                ''',
            })

        return etf_rows, pool_rows, len(etf_rows), len(pool_rows), total_members, f"{active_etfs}/{len(etf_rows)}"

    # 打开新增 ETF 模态框
    @app.callback(
        Output('add-etf-modal', 'is_open'),
        [Input('btn-open-add-etf-modal', 'n_clicks'),
         Input('btn-cancel-add-etf', 'n_clicks'),
         Input('btn-confirm-add-etf', 'n_clicks')],
        [State('add-etf-modal', 'is_open')]
    )
    def toggle_add_etf_modal(n_open, n_cancel, n_confirm, is_open):
        if n_open or n_cancel or n_confirm:
            return not is_open
        return is_open

    # 确认新增 ETF
    @app.callback(
        [Output('instruments-toast-container', 'children'),
         Output('add-etf-modal', 'is_open')],
        [Input('btn-confirm-add-etf', 'n_clicks')],
        [State('add-etf-code', 'value'),
         State('add-etf-name', 'value'),
         State('add-etf-market', 'value'),
         State('add-etf-category', 'value')],
        prevent_initial_call=True,
    )
    def confirm_add_etf(n_clicks, code, name, market, category):
        if not n_clicks or not code:
            return html.Div(), False

        code = code.strip()
        if not name:
            name = f"ETF{code}"

        result = create_etf_via_api(code, name, market, category)

        if result and (result.get('success') or result.get('code')):
            toast = dbc.Toast(
                f"成功添加 ETF {code} {name}",
                id="etf-added-toast",
                header="操作成功",
                icon="success",
                duration=3000,
                is_open=True,
                style={'position': 'fixed', 'top': '70px', 'right': '20px', 'zIndex': 9999},
            )
        else:
            error_msg = result.get('error', '添加失败') if result else '网络错误'
            toast = dbc.Toast(
                error_msg,
                id="etf-error-toast",
                header="操作失败",
                icon="danger",
                duration=5000,
                is_open=True,
                style={'position': 'fixed', 'top': '70px', 'right': '20px', 'zIndex': 9999},
            )

        return toast, False

    # 打开批量删除模态框
    @app.callback(
        Output('batch-delete-modal', 'is_open'),
        [Input('btn-open-batch-delete-modal', 'n_clicks'),
         Input('btn-cancel-batch-delete', 'n_clicks'),
         Input('btn-confirm-batch-delete', 'n_clicks')],
        [State('batch-delete-modal', 'is_open')]
    )
    def toggle_batch_delete_modal(n_open, n_cancel, n_confirm, is_open):
        if n_open or n_cancel or n_confirm:
            return not is_open
        return is_open

    # 确认批量删除
    @app.callback(
        [Output('instruments-toast-container', 'children'),
         Output('batch-delete-modal', 'is_open')],
        [Input('btn-confirm-batch-delete', 'n_clicks')],
        [State('batch-delete-codes', 'value')],
        prevent_initial_call=True,
    )
    def confirm_batch_delete(n_clicks, codes_text):
        if not n_clicks or not codes_text:
            return html.Div(), False

        # 解析代码
        codes = []
        for line in codes_text.replace(',', '\n').split('\n'):
            code = line.strip()
            if code and len(code) == 6 and code.isdigit():
                codes.append(code)

        if not codes:
            toast = dbc.Toast(
                "没有有效的 ETF 代码",
                header="操作失败",
                icon="danger",
                duration=3000,
                is_open=True,
                style={'position': 'fixed', 'top': '70px', 'right': '20px', 'zIndex': 9999},
            )
            return toast, False

        # 逐个删除
        success_count = 0
        fail_count = 0
        for code in codes:
            result = api_delete(f"instruments/etfs/{code}")
            if result and result.get('success'):
                success_count += 1
            else:
                fail_count += 1

        toast = dbc.Toast(
            f"成功删除 {success_count} 个 ETF，失败 {fail_count} 个",
            header="批量删除完成",
            icon="success" if fail_count == 0 else "warning",
            duration=4000,
            is_open=True,
            style={'position': 'fixed', 'top': '70px', 'right': '20px', 'zIndex': 9999},
        )
        return toast, False

    # 打开新增池模态框
    @app.callback(
        Output('add-pool-modal', 'is_open'),
        [Input('btn-open-add-pool-modal', 'n_clicks'),
         Input('btn-cancel-add-pool', 'n_clicks'),
         Input('btn-confirm-add-pool', 'n_clicks')],
        [State('add-pool-modal', 'is_open')]
    )
    def toggle_add_pool_modal(n_open, n_cancel, n_confirm, is_open):
        if n_open or n_cancel or n_confirm:
            return not is_open
        return is_open

    # 确认新增池
    @app.callback(
        [Output('instruments-toast-container', 'children'),
         Output('add-pool-modal', 'is_open')],
        [Input('btn-confirm-add-pool', 'n_clicks')],
        [State('add-pool-code', 'value'),
         State('add-pool-name', 'value'),
         State('add-pool-purpose', 'value'),
         State('add-pool-description', 'value')],
        prevent_initial_call=True,
    )
    def confirm_add_pool(n_clicks, code, name, purpose, description):
        if not n_clicks or not code or not name:
            return html.Div(), False

        code = code.strip()
        name = name.strip()

        result = api_post("instruments/pools", {
            'code': code,
            'name': name,
            'purpose': purpose,
            'description': description or '',
        })

        if result and result.get('success'):
            toast = dbc.Toast(
                f"成功创建品种池 {name}",
                header="操作成功",
                icon="success",
                duration=3000,
                is_open=True,
                style={'position': 'fixed', 'top': '70px', 'right': '20px', 'zIndex': 9999},
            )
        else:
            toast = dbc.Toast(
                result.get('error', '创建失败') if result else '网络错误',
                header="操作失败",
                icon="danger",
                duration=5000,
                is_open=True,
                style={'position': 'fixed', 'top': '70px', 'right': '20px', 'zIndex': 9999},
            )

        return toast, False

    # 打开删除池模态框
    @app.callback(
        [Output('delete-pool-modal', 'is_open'),
         Output('delete-pool-info', 'children')],
        [Input('btn-open-delete-pool-modal', 'n_clicks'),
         Input('btn-cancel-delete-pool', 'n_clicks'),
         Input('btn-confirm-delete-pool', 'n_clicks')],
        [State('pool-table', 'selected_rows'),
         State('pool-table', 'data')]
    )
    def toggle_delete_pool_modal(n_open, n_cancel, n_confirm, selected_rows, table_data):
        ctx = callback_context
        if not ctx.triggered:
            return False, ""

        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]

        if trigger_id == 'btn-open-delete-pool-modal':
            if not selected_rows:
                return False, "请先选择要删除的品种池"
            pool = table_data[selected_rows[0]]
            return True, f"池名称：{pool['name']} (代码：{pool['code']})"

        return False, ""

    # 确认删除池
    @app.callback(
        [Output('instruments-toast-container', 'children'),
         Output('delete-pool-modal', 'is_open', allow_duplicate=True)],
        [Input('btn-confirm-delete-pool', 'n_clicks')],
        [State('pool-table', 'selected_rows'),
         State('pool-table', 'data')],
        prevent_initial_call=True,
    )
    def confirm_delete_pool(n_clicks, selected_rows, table_data):
        if not n_clicks or not selected_rows:
            return html.Div(), False

        pool = table_data[selected_rows[0]]
        code = pool['code']

        result = api_delete(f"instruments/pools/{code}")

        if result and result.get('success'):
            toast = dbc.Toast(
                f"成功删除品种池 {pool['name']}",
                header="操作成功",
                icon="success",
                duration=3000,
                is_open=True,
                style={'position': 'fixed', 'top': '70px', 'right': '20px', 'zIndex': 9999},
            )
        else:
            toast = dbc.Toast(
                result.get('error', '删除失败') if result else '网络错误',
                header="操作失败",
                icon="danger",
                duration=5000,
                is_open=True,
                style={'position': 'fixed', 'top': '70px', 'right': '20px', 'zIndex': 9999},
            )

        return toast, False

    # 关闭池成员模态框（打开由 JavaScript 负责）
    @app.callback(
        Output('pool-members-modal', 'is_open'),
        [Input('btn-close-pool-members', 'n_clicks')],
        [State('pool-members-modal', 'is_open')]
    )
    def toggle_pool_members_modal(n_close, is_open):
        if n_close:
            return False
        return is_open

    # 更新池成员数据
    @app.callback(
        [Output('pool-members-header', 'children'),
         Output('pool-members-info', 'children'),
         Output('pool-members-table', 'data')],
        [Input('pool-members-modal', 'is_open'),
         Input('btn-add-pool-member', 'n_clicks'),
         Input('btn-batch-add-members', 'n_clicks')],
        [State('pool-table', 'selected_rows'),
         State('pool-table', 'data'),
         State('add-member-code', 'value'),
         State('batch-add-members', 'value')]
    )
    def update_pool_members(is_open, n_add, n_batch_add, selected_rows, table_data, single_code, batch_codes):
        ctx = callback_context
        if not ctx.triggered:
            return "", html.Div(), []

        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]

        if not is_open or not selected_rows:
            return "", html.Div(), []

        pool = table_data[selected_rows[0]]
        pool_code = pool['code']

        # 处理添加成员
        if trigger_id == 'btn-add-pool-member' and single_code:
            api_post(f"instruments/pools/{pool_code}/members", {'etf_code': single_code.strip()})

        # 处理批量添加
        if trigger_id == 'btn-batch-add-members' and batch_codes:
            codes = [c.strip() for c in batch_codes.replace(',', '\n').split('\n') if c.strip()]
            for code in codes:
                api_post(f"instruments/pools/{pool_code}/members", {'etf_code': code})

        # 获取最新成员列表
        members_result = api_get(f"instruments/pools/{pool_code}/members")
        members = members_result.get('data', []) if members_result else []

        header = html.H5([html.I(className="fas fa-users mr-2"), f"池成员管理 - {pool['name']}"])
        info = html.Div([
            html.Strong(f"池代码：{pool_code}"),
            html.Span(f" | 成员数：{len(members)}", className="ml-2"),
        ])

        member_rows = []
        for m in members:
            member_rows.append({
                'etf_code': m.get('etf_code', ''),
                'etf_name': m.get('etf_name', ''),
                'weight': m.get('weight', 0),
                'is_active': '活跃' if m.get('is_active', True) else '停用',
                'actions': f'''
                    <button class="btn btn-sm btn-outline-danger" onclick="removePoolMember('{pool_code}', '{m.get('etf_code', '')}')">
                        <i class="fas fa-user-minus"></i>
                    </button>
                ''',
            })

        return header, info, member_rows

    # 添加池成员（单个）
    @app.callback(
        Output('add-member-code', 'value'),
        [Input('btn-add-pool-member', 'n_clicks')],
        [State('add-member-code', 'value')],
        prevent_initial_call=True,
    )
    def clear_member_input(n_clicks, value):
        if n_clicks:
            return ''
        return value

    # 添加池成员（批量）
    @app.callback(
        Output('batch-add-members', 'value'),
        [Input('btn-batch-add-members', 'n_clicks')],
        [State('batch-add-members', 'value')],
        prevent_initial_call=True,
    )
    def clear_batch_member_input(n_clicks, value):
        if n_clicks:
            return ''
        return value
