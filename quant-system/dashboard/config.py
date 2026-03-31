"""
仪表板配置

包含主题、颜色等全局配置，避免循环导入。
"""

# 深色主题配置
THEME = {
    'bg_dark': '#1a1a2e',
    'bg_card': '#16213e',
    'bg_light': '#0f3460',
    'accent': '#e94560',
    'accent_green': '#00d9ff',
    'text': '#eee',
    'text_muted': '#aaa',
    'border': '#2a2a4a',
}

# 图表默认配置
CHART_CONFIG = {
    'displayModeBar': False,
    'displaylogo': False,
    'modeBarButtonsToRemove': ['pan2d', 'select2d', 'lasso2d', 'autoScale2d'],
}

# 更新间隔（毫秒）
REFRESH_INTERVALS = {
    'fast': 3 * 1000,      # 3秒 - 实时价格
    'normal': 5 * 1000,    # 5秒 - 普通数据
    'slow': 30 * 1000,     # 30秒 - 较慢的数据
}

# 风险等级颜色
RISK_COLORS = {
    'low': '#28a745',
    'medium': '#ffc107',
    'high': '#fd7e14',
    'critical': '#dc3545',
}

# 方向颜色
DIRECTION_COLORS = {
    'up': '#28a745',
    'down': '#dc3545',
    'neutral': '#6c757d',
}
