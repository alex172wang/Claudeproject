"""
AI 助手组件

右下角悬浮球 + 聊天窗口
"""

import os
import sys
from datetime import datetime
from typing import List, Dict, Any

import dash
from dash import html, dcc, Input, Output, State, callback_context
import dash_bootstrap_components as dbc

# 主题配置
try:
    from ..config import THEME
except ImportError:
    import sys
    import os
    dashboard_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if dashboard_dir not in sys.path:
        sys.path.insert(0, dashboard_dir)
    from config import THEME


# 消息类型
class MessageType:
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    ERROR = "error"


def create_ai_assistant_container() -> html.Div:
    """
    创建 AI 助手容器（包含悬浮球和聊天窗口）
    """

    return html.Div(
        id='ai-assistant-container',
        style={
            'position': 'fixed',
            'bottom': '20px',
            'right': '20px',
            'z-index': '9999',
        },
        children=[
            # 聊天窗口（默认隐藏）
            create_chat_window(),

            # 悬浮球按钮
            create_floating_ball(),
        ],
    )


def create_floating_ball() -> html.Div:
    """创建悬浮球按钮"""

    return html.Div(
        id='ai-assistant-floating-ball',
        children=[
            dbc.Button(
                [
                    html.I(className="fas fa-robot", style={'fontSize': '1.5rem'}),
                ],
                id='ai-assistant-toggle',
                color='primary',
                size='lg',
                style={
                    'width': '60px',
                    'height': '60px',
                    'borderRadius': '50%',
                    'boxShadow': '0 4px 12px rgba(0, 0, 0, 0.3)',
                    'display': 'flex',
                    'alignItems': 'center',
                    'justifyContent': 'center',
                },
            ),
        ],
        style={
            'cursor': 'pointer',
        }
    )


def create_chat_window() -> html.Div:
    """创建聊天窗口"""

    return html.Div(
        id='ai-assistant-chat-window',
        style={
            'display': 'none',  # 默认隐藏
            'width': '380px',
            'height': '520px',
            'backgroundColor': THEME['bg_card'],
            'borderRadius': '12px',
            'boxShadow': '0 8px 32px rgba(0, 0, 0, 0.4)',
            'marginBottom': '15px',
            'flexDirection': 'column',
            'overflow': 'hidden',
        },
        children=[
            # 标题栏
            html.Div(
                style={
                    'backgroundColor': '#00d9ff',
                    'padding': '12px 15px',
                    'display': 'flex',
                    'justifyContent': 'space-between',
                    'alignItems': 'center',
                },
                children=[
                    html.Div(
                        [
                            html.Span('🤖', style={'marginRight': '8px', 'fontSize': '1.2rem'}),
                            html.Span('AI 品种管理器', style={'fontWeight': 'bold', 'fontSize': '1rem'}),
                        ]
                    ),
                    dbc.Button(
                        html.I(className="fas fa-times"),
                        id='ai-assistant-close',
                        size='sm',
                        color='link',
                        style={'color': '#000'},
                    ),
                ]
            ),

            # 欢迎信息
            html.Div(
                id='ai-welcome-message',
                style={
                    'padding': '15px',
                    'backgroundColor': THEME['bg_card'],
                    'borderBottom': f'1px solid {THEME["border"]}',
                    'fontSize': '0.85rem',
                    'color': THEME['text_muted'],
                },
                children=[
                    html.Div('👋 您好！我是 AI 品种管理器'),
                    html.Div('我可以帮您管理 ETF 品种和品种池', style={'marginTop': '5px'}),
                    html.Div(
                        [html.Span('💡 ', style={'color': '#00d9ff'}), '输入"帮助"查看支持的操作'],
                        style={'marginTop': '8px', 'fontSize': '0.8rem'}
                    ),
                ]
            ),

            # 消息列表
            html.Div(
                id='ai-assistant-messages',
                style={
                    'flex': '1',
                    'overflow-y': 'auto',
                    'padding': '15px',
                    'display': 'flex',
                    'flexDirection': 'column',
                    'gap': '10px',
                }
            ),

            # 输入区域
            html.Div(
                style={
                    'padding': '12px',
                    'borderTop': f'1px solid {THEME["border"]}',
                    'backgroundColor': THEME['bg_light'],
                },
                children=[
                    dbc.InputGroup(
                        [
                            dbc.Input(
                                id='ai-assistant-input',
                                placeholder='输入您的需求...',
                                style={'backgroundColor': THEME['bg_card'], 'color': THEME['text']},
                            ),
                            dbc.Button(
                                html.I(className="fas fa-paper-plane"),
                                id='ai-assistant-send',
                                color='primary',
                                style={'padding': '0 15px'},
                            ),
                        ],
                        size='sm',
                    ),
                    html.Div(
                        '示例：添加 ETF 510300 | 创建品种池 | 查看轮动池成员',
                        style={
                            'fontSize': '0.7rem',
                            'color': THEME['text_muted'],
                            'marginTop': '5px',
                            'textAlign': 'center',
                        }
                    ),
                ]
            ),
        ],
    )


def create_message_bubble(message_type: str, content: str, timestamp: str = None) -> html.Div:
    """创建消息气泡"""

    if timestamp is None:
        timestamp = datetime.now().strftime('%H:%M')

    is_user = message_type == MessageType.USER

    return html.Div(
        style={
            'display': 'flex',
            'flexDirection': 'column' if not is_user else 'row-reverse',
            'alignItems': 'flex-start' if not is_user else 'flex-end',
            'maxWidth': '85%',
            'alignSelf': 'flex-end' if is_user else 'flex-start',
        },
        children=[
            # 头像
            html.Div(
                style={
                    'width': '28px',
                    'height': '28px',
                    'borderRadius': '50%',
                    'backgroundColor': '#00d9ff' if not is_user else '#e94560',
                    'display': 'flex',
                    'alignItems': 'center',
                    'justifyContent': 'center',
                    'marginLeft': '8px' if not is_user else '0',
                    'marginRight': '8px' if is_user else '0',
                    'fontSize': '0.8rem',
                    'flexShrink': '0',
                },
                children='🤖' if not is_user else '👤'
            ),

            # 消息内容
            html.Div(
                style={
                    'backgroundColor': THEME['bg_light'] if not is_user else '#00d9ff',
                    'color': THEME['text'] if not is_user else '#000',
                    'padding': '10px 14px',
                    'borderRadius': '12px',
                    'fontSize': '0.85rem',
                    'lineHeight': '1.4',
                    'whiteSpace': 'pre-wrap',
                    'wordBreak': 'break-word',
                },
                children=content
            ),
        ]
    )


def register_ai_assistant_callbacks(app: dash.Dash):
    """注册 AI 助手回调函数"""

    @app.callback(
        [Output('ai-assistant-chat-window', 'style'),
         Output('ai-assistant-floating-ball', 'style')],
        [Input('ai-assistant-toggle', 'n_clicks'),
         Input('ai-assistant-close', 'n_clicks')],
        [State('ai-assistant-chat-window', 'style'),
         State('ai-assistant-floating-ball', 'style')],
    )
    def toggle_chat_window(n_toggle, n_close, current_window_style, current_ball_style):
        """切换聊天窗口显示状态"""
        ctx = callback_context

        if not ctx.triggered:
            return current_window_style, current_ball_style

        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]

        if trigger_id == 'ai-assistant-toggle':
            # 切换显示状态
            is_visible = current_window_style.get('display', 'none') != 'none'
            new_window_style = current_window_style.copy()
            new_window_style['display'] = 'none' if is_visible else 'flex'

            new_ball_style = current_ball_style.copy()
            new_ball_style['opacity'] = '0.3' if not is_visible else '1'

            return new_window_style, new_ball_style

        elif trigger_id == 'ai-assistant-close':
            # 关闭聊天窗口
            new_window_style = current_window_style.copy()
            new_window_style['display'] = 'none'

            new_ball_style = current_ball_style.copy()
            new_ball_style['opacity'] = '1'

            return new_window_style, new_ball_style

        return current_window_style, current_ball_style

    @app.callback(
        [Output('ai-assistant-messages', 'children'),
         Output('ai-assistant-input', 'value')],
        [Input('ai-assistant-send', 'n_clicks'),
         Input('ai-assistant-input', 'n_submit')],
        [State('ai-assistant-input', 'value'),
         State('ai-assistant-messages', 'children')],
    )
    def send_message(n_clicks, n_submit, input_value, current_messages):
        """发送消息并获取AI响应"""
        ctx = callback_context

        if not ctx.triggered:
            return current_messages, ''

        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]

        if trigger_id not in ['ai-assistant-send', 'ai-assistant-input']:
            return current_messages, input_value

        if not input_value or not input_value.strip():
            return current_messages, input_value

        user_message = input_value.strip()

        # 添加用户消息
        new_messages = current_messages.copy() if current_messages else []
        new_messages.append(
            create_message_bubble(MessageType.USER, user_message)
        )

        # 调用 AI API 获取响应
        try:
            import requests
            response = requests.post(
                'http://127.0.0.1:8000/api/ai/manager/',
                json={'text': user_message},
                timeout=15
            )
            if response.status_code == 200:
                result = response.json()
                ai_message = result.get('message', '处理完成')
                ai_response = create_message_bubble(
                    MessageType.ASSISTANT,
                    ai_message
                )
                new_messages.append(ai_response)
        except requests.exceptions.Timeout:
            error_response = create_message_bubble(
                MessageType.ERROR,
                '请求超时，请稍后重试'
            )
            new_messages.append(error_response)
        except Exception as e:
            error_response = create_message_bubble(
                MessageType.ERROR,
                f'请求失败: {str(e)}'
            )
            new_messages.append(error_response)

        return new_messages, ''
