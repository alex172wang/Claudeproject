# -*- coding: utf-8 -*-
"""
参数配置页面

提供完整的L1-L4指标参数、策略权重、数据源等配置管理。
支持按颗粒度对齐的参数配置。
"""

import os
import json
from datetime import datetime
from typing import Dict, Any, List

import dash
from dash import dcc, html, Input, Output, State
import dash_bootstrap_components as dbc

# 导入主题配置
try:
    from ..config import THEME
except ImportError:
    # 绝对导入备用
    import sys
    import os
    dashboard_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if dashboard_dir not in sys.path:
        sys.path.insert(0, dashboard_dir)
    from config import THEME

# 导入 Django 设置
try:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'quant_system.settings')
    import django
    django.setup()
    from django.conf import settings as django_settings
    FRED_API_KEY = django_settings.QUANT_SYSTEM.get('data_sources', {}).get('fred', {}).get('api_key', '')
except Exception:
    FRED_API_KEY = ''


# ============================================================================
# 配置数据定义（与 YAML 结构对齐）
# ============================================================================

DEFAULT_INDICATORS_CONFIG = {
    "L1": {
        "name": "L1 趋势层",
        "description": "趋势方向与动量强度",
        "indicators": {
            "L1-01": {
                "name": "复合斜率动量",
                "description": "30日斜率×R²(0.6) + 15日斜率×R²(0.4)",
                "params": {
                    "long_window": {"type": "int", "default": 30, "min": 10, "max": 60, "step": 5, "desc": "长周期窗口"},
                    "short_window": {"type": "int", "default": 15, "min": 5, "max": 30, "step": 5, "desc": "短周期窗口"},
                    "long_weight": {"type": "float", "default": 0.6, "min": 0.3, "max": 0.8, "step": 0.1, "desc": "长周期权重"},
                    "short_weight": {"type": "float", "default": 0.4, "min": 0.2, "max": 0.7, "step": 0.1, "desc": "短周期权重"},
                }
            },
            "L1-02": {
                "name": "EMA趋势过滤",
                "description": "收盘价 > EMA(N) 为多头环境",
                "params": {
                    "period": {"type": "int", "default": 120, "min": 60, "max": 250, "step": 10, "desc": "EMA周期"},
                }
            },
            "L1-03": {
                "name": "趋势加速度",
                "description": "复合斜率动量的一阶差分（动量的动量）",
                "params": {
                    "diff_window": {"type": "int", "default": 5, "min": 3, "max": 10, "step": 1, "desc": "差分窗口"},
                }
            },
            "L1-04": {
                "name": "价格通道位置",
                "description": "(Close - N日最低) / (N日最高 - N日最低)",
                "params": {
                    "period": {"type": "int", "default": 60, "min": 20, "max": 120, "step": 10, "desc": "通道周期"},
                }
            },
            "L1-05": {
                "name": "FRED趋势共振",
                "description": "美10Y国债收益率斜率 + 美元指数DXY斜率",
                "params": {
                    "yield_slope_window": {"type": "int", "default": 30, "min": 10, "max": 60, "step": 5, "desc": "收益率斜率窗口"},
                    "dxy_slope_window": {"type": "int", "default": 30, "min": 10, "max": 60, "step": 5, "desc": "美元指数斜率窗口"},
                }
            },
        }
    },
    "L2": {
        "name": "L2 结构层",
        "description": "趋势品质与结构健康度",
        "indicators": {
            "L2-01": {
                "name": "Hurst指数",
                "description": "R/S分析法，衡量趋势持续性品质",
                "params": {
                    "window": {"type": "int", "default": 60, "min": 30, "max": 120, "step": 10, "desc": "Hurst计算窗口"},
                }
            },
            "L2-02": {
                "name": "波动率结构比",
                "description": "短期实现波动率 / 长期实现波动率",
                "params": {
                    "short_window": {"type": "int", "default": 5, "min": 3, "max": 10, "step": 1, "desc": "短期窗口"},
                    "long_window": {"type": "int", "default": 30, "min": 20, "max": 60, "step": 5, "desc": "长期窗口"},
                }
            },
            "L2-03": {
                "name": "成交量形态分歧",
                "description": "价格新高时成交量相对MA(20)的偏离度",
                "params": {
                    "volume_ma_period": {"type": "int", "default": 20, "min": 10, "max": 60, "step": 5, "desc": "成交量MA周期"},
                }
            },
            "L2-04": {
                "name": "回撤分形维度",
                "description": "最大回撤序列的Hurst指数（回撤是否有自相似性）",
                "params": {
                    "rolling_window": {"type": "int", "default": 120, "min": 60, "max": 252, "step": 20, "desc": "滚动窗口"},
                }
            },
            "L2-05": {
                "name": "K线实体比",
                "description": "N日内实体占比均值（实体/振幅），衡量趋势纯净度",
                "params": {
                    "period": {"type": "int", "default": 20, "min": 5, "max": 60, "step": 5, "desc": "计算周期"},
                }
            },
            "L2-06": {
                "name": "波动率自相关",
                "description": "日收益率绝对值的ACF(1)，衡量波动率聚集程度",
                "params": {
                    "lag": {"type": "int", "default": 1, "min": 1, "max": 5, "step": 1, "desc": "滞后阶数"},
                    "window": {"type": "int", "default": 30, "min": 20, "max": 90, "step": 10, "desc": "计算窗口"},
                }
            },
        }
    },
    "L3": {
        "name": "L3 共振层",
        "description": "跨市场/跨资产的协同性",
        "indicators": {
            "L3-01": {
                "name": "滚动相关性矩阵",
                "description": "候选池内所有资产两两滚动Pearson相关系数",
                "params": {
                    "window": {"type": "int", "default": 60, "min": 20, "max": 120, "step": 5, "desc": "滚动窗口"},
                }
            },
            "L3-02": {
                "name": "相关性变速",
                "description": "L3-01的一阶差分，捕捉相关性瓦解/收敛速度",
                "params": {
                    "diff_window": {"type": "int", "default": 5, "min": 3, "max": 10, "step": 1, "desc": "差分窗口"},
                }
            },
            "L3-03": {
                "name": "PCA第一主成分解释率",
                "description": "候选池收益率矩阵PCA，PC1方差解释比",
                "params": {
                    "window": {"type": "int", "default": 60, "min": 20, "max": 120, "step": 5, "desc": "PCA窗口"},
                }
            },
            "L3-04": {
                "name": "跨市场动量一致性",
                "description": "A股/港股/美股/商品同方向动量占比",
                "params": {
                    "slope_window": {"type": "int", "default": 30, "min": 10, "max": 60, "step": 5, "desc": "斜率计算窗口"},
                }
            },
            "L3-05": {
                "name": "宏观-资产共振度",
                "description": "FRED指标（10Y利率、CPI、PMI）与资产收益的滚动相关",
                "params": {
                    "window": {"type": "int", "default": 90, "min": 30, "max": 252, "step": 10, "desc": "滚动窗口"},
                }
            },
            "L3-06": {
                "name": "板块轮动速度",
                "description": "候选池内排名变化的标准差（排名越稳定，轮动越慢）",
                "params": {
                    "rolling_weeks": {"type": "int", "default": 4, "min": 2, "max": 12, "step": 1, "desc": "滚动周数"},
                }
            },
        }
    },
    "L4": {
        "name": "L4 缺口层",
        "description": "尾部风险与市场微观结构",
        "indicators": {
            "L4-01": {
                "name": "隐含-实现波动率价差",
                "description": "50ETF期权IV - 标的30d实现波动率",
                "params": {
                    "option_type": {"type": "select", "default": "ATM", "options": ["ATM", "OTM"], "desc": "期权类型"},
                    "maturity": {"type": "select", "default": "nearest", "options": ["nearest", "monthly"], "desc": "到期日选择"},
                }
            },
            "L4-02": {
                "name": "期权偏度",
                "description": "25Δ看跌IV - 25Δ看涨IV（恐惧的不对称性）",
                "params": {
                    "delta_put": {"type": "int", "default": 25, "min": 10, "max": 40, "step": 5, "desc": "看跌期权Delta"},
                    "delta_call": {"type": "int", "default": 25, "min": 10, "max": 40, "step": 5, "desc": "看涨期权Delta"},
                    "maturity": {"type": "select", "default": "monthly", "options": ["nearest", "monthly"], "desc": "到期日选择"},
                }
            },
            "L4-03": {
                "name": "认沽认购比",
                "description": "看跌期权成交量 / 看涨期权成交量",
                "params": {
                    "type": {"type": "select", "default": "volume", "options": ["volume", "oi"], "desc": "使用成交量或持仓量"},
                }
            },
            "L4-04": {
                "name": "流动性缺口",
                "description": "买一卖一价差/中间价的滚动均值",
                "params": {
                    "window": {"type": "int", "default": 20, "min": 5, "max": 60, "step": 5, "desc": "滚动窗口"},
                }
            },
            "L4-05": {
                "name": "尾部风险度量",
                "description": "滚动N日收益率的峰度（尾巴有多肥）",
                "params": {
                    "window": {"type": "int", "default": 60, "min": 30, "max": 252, "step": 10, "desc": "滚动窗口"},
                }
            },
            "L4-06": {
                "name": "跳空缺口频率",
                "description": "N日内跳空幅度>1%的天数占比",
                "params": {
                    "window": {"type": "int", "default": 30, "min": 10, "max": 90, "step": 5, "desc": "观察窗口"},
                    "gap_threshold": {"type": "float", "default": 0.01, "min": 0.005, "max": 0.05, "step": 0.005, "desc": "跳空阈值"},
                }
            },
            "L4-07": {
                "name": "FRED压力合成",
                "description": "美联储资产负债表变化率 + 信用利差(BAA-AAA)趋势",
                "params": {
                    "fed_balance_sheet": {"type": "string", "default": "WALCL", "desc": "美联储资产负债表代码"},
                    "credit_spread_baa": {"type": "string", "default": "BAA", "desc": "BAA信用利差代码"},
                    "credit_spread_aaa": {"type": "string", "default": "AAA", "desc": "AAA信用利差代码"},
                }
            },
        }
    },
}

DEFAULT_STRATEGY_WEIGHTS = {
    "rotation": {
        "name": "ETF轮动策略",
        "description": "周度执行，选出最强趋势品种",
        "weights": {
            "L1": {"label": "趋势层(L1)", "value": 0.40, "min": 0.2, "max": 0.6, "step": 0.05},
            "L2": {"label": "结构层(L2)", "value": 0.20, "min": 0.1, "max": 0.4, "step": 0.05},
            "L3": {"label": "共振层(L3)", "value": 0.20, "min": 0.1, "max": 0.4, "step": 0.05},
            "L4": {"label": "缺口层(L4)", "value": 0.20, "min": 0.1, "max": 0.4, "step": 0.05},
        }
    },
    "permanent": {
        "name": "永久组合策略",
        "description": "月度再平衡，固定股债金现配比",
        "weights": {
            "L1": {"label": "趋势层(L1)", "value": 0.15, "min": 0.05, "max": 0.30, "step": 0.05},
            "L2": {"label": "结构层(L2)", "value": 0.20, "min": 0.10, "max": 0.35, "step": 0.05},
            "L3": {"label": "共振层(L3)", "value": 0.35, "min": 0.20, "max": 0.50, "step": 0.05},
            "L4": {"label": "缺口层(L4)", "value": 0.30, "min": 0.15, "max": 0.45, "step": 0.05},
        },
        "allocation": {
            "equity": {"label": "权益类", "value": 0.40, "min": 0.30, "max": 0.60, "step": 0.05},
            "bond": {"label": "债券类", "value": 0.25, "min": 0.15, "max": 0.40, "step": 0.05},
            "gold": {"label": "黄金类", "value": 0.20, "min": 0.10, "max": 0.35, "step": 0.05},
            "cash": {"label": "现金类", "value": 0.15, "min": 0.05, "max": 0.30, "step": 0.05},
        }
    },
    "thematic": {
        "name": "主题仓位策略",
        "description": "事件驱动，基于主题轮动入场",
        "weights": {
            "L1": {"label": "趋势层(L1)", "value": 0.35, "min": 0.20, "max": 0.50, "step": 0.05},
            "L2": {"label": "结构层(L2)", "value": 0.25, "min": 0.15, "max": 0.40, "step": 0.05},
            "L3": {"label": "共振层(L3)", "value": 0.15, "min": 0.05, "max": 0.30, "step": 0.05},
            "L4": {"label": "缺口层(L4)", "value": 0.25, "min": 0.15, "max": 0.40, "step": 0.05},
        }
    }
}

DEFAULT_DATA_SOURCE_CONFIG = {
    "mootdx": {
        "name": "mootdx 通达信数据",
        "enabled": True,
        "params": {
            "bestip": {"type": "bool", "default": True, "desc": "自动选择最优IP"},
            "timeout": {"type": "int", "default": 30, "min": 10, "max": 120, "step": 10, "desc": "连接超时(秒)"},
        }
    },
    "akshare": {
        "name": "AKShare 财经数据",
        "enabled": True,
        "params": {
            "timeout": {"type": "int", "default": 30, "min": 10, "max": 120, "step": 10, "desc": "请求超时(秒)"},
        }
    },
    "fred": {
        "name": "FRED 宏观数据",
        "enabled": True,
        "params": {
            "api_key": {"type": "string", "default": FRED_API_KEY, "desc": "FRED API Key"},
            "timeout": {"type": "int", "default": 30, "min": 10, "max": 120, "step": 10, "desc": "请求超时(秒)"},
        }
    }
}

DEFAULT_BACKTEST_CONFIG = {
    "commission": {"type": "float", "default": 0.001, "min": 0.0001, "max": 0.005, "step": 0.0001, "desc": "交易成本(单边)"},
    "slippage": {"type": "float", "default": 0.0005, "min": 0.0001, "max": 0.002, "step": 0.0001, "desc": "滑点"},
    "in_sample_ratio": {"type": "float", "default": 0.7, "min": 0.5, "max": 0.9, "step": 0.05, "desc": "样本内比例"},
    "min_holding_days": {"type": "int", "default": 5, "min": 1, "max": 20, "step": 1, "desc": "最小持有天数"},
    "overfitting_threshold": {"type": "float", "default": 2.0, "min": 1.0, "max": 5.0, "step": 0.5, "desc": "过拟合警告阈值"},
}


# ============================================================================
# 配置文件管理
# ============================================================================

CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config_files')
os.makedirs(CONFIG_DIR, exist_ok=True)

def get_config_path(config_type: str) -> str:
    """获取配置文件路径"""
    return os.path.join(CONFIG_DIR, f"{config_type}_config.json")

def load_config(config_type: str, default_config: Dict) -> Dict:
    """加载配置，如果不存在则返回默认配置"""
    config_path = get_config_path(config_type)
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
                # 合并默认值和加载的配置（处理新增字段）
                return merge_configs(default_config, loaded)
        except Exception as e:
            print(f"[Config] 加载配置失败: {e}")
    return default_config

def save_config(config_type: str, config: Dict) -> bool:
    """保存配置到文件"""
    try:
        config_path = get_config_path(config_type)
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"[Config] 保存配置失败: {e}")
        return False

def merge_configs(default: Dict, loaded: Dict) -> Dict:
    """递归合并配置，保留默认值中的新增字段"""
    result = {}
    for key, default_val in default.items():
        if key in loaded:
            if isinstance(default_val, dict) and isinstance(loaded[key], dict):
                result[key] = merge_configs(default_val, loaded[key])
            else:
                result[key] = loaded[key]
        else:
            result[key] = default_val
    return result


# ============================================================================
# 页面布局创建
# ============================================================================

def create_config_tab() -> html.Div:
    """创建配置页面主布局"""

    return html.Div([
        # 顶部导航
        dbc.Row([
            dbc.Col([
                html.H4("参数配置中心", className="mb-0"),
                html.Small("管理所有指标参数、策略权重和数据源配置", className="text-muted"),
            ], width=8),
            dbc.Col([
                dbc.ButtonGroup([
                    dbc.Button("保存所有配置", id="btn-save-all-config", color="success", className="me-2"),
                    dbc.Button("重置默认值", id="btn-reset-config", color="outline-warning"),
                ])
            ], width=4, className="text-end"),
        ], className="mb-4"),

        # 配置主区域 - 使用Tabs组织
        dbc.Tabs([
            # Tab 1: L1-L4 指标参数
            dbc.Tab(label="指标参数", tab_id="tab-indicators", children=[
                create_indicators_config_panel()
            ]),

            # Tab 2: 策略权重
            dbc.Tab(label="策略权重", tab_id="tab-strategies", children=[
                create_strategies_config_panel()
            ]),

            # Tab 3: 数据源配置
            dbc.Tab(label="数据源", tab_id="tab-data-sources", children=[
                create_data_sources_config_panel()
            ]),

            # Tab 4: 回测参数
            dbc.Tab(label="回测参数", tab_id="tab-backtest", children=[
                create_backtest_config_panel()
            ]),
        ], id="config-tabs", active_tab="tab-indicators"),

        # 状态提示区域
        html.Div(id="config-save-status", className="mt-3"),

        # 存储当前配置的状态
        dcc.Store(id="store-indicators-config", data={}),
        dcc.Store(id="store-strategies-config", data={}),
        dcc.Store(id="store-data-sources-config", data={}),
        dcc.Store(id="store-backtest-config", data={}),

    ], style={'backgroundColor': THEME['bg_dark'], 'padding': '20px', 'minHeight': '100vh'})


def create_indicators_config_panel() -> html.Div:
    """创建指标参数配置面板"""

    # 构建L1-L4各层的配置界面
    layer_tabs = []
    for layer_code, layer_info in DEFAULT_INDICATORS_CONFIG.items():
        indicator_accordions = []

        for ind_code, ind_info in layer_info["indicators"].items():
            # 构建参数输入控件
            param_inputs = []
            for param_name, param_def in ind_info["params"].items():
                input_id = f"input-{ind_code}-{param_name}"

                if param_def["type"] == "int":
                    control = dbc.Input(
                        id=input_id,
                        type="number",
                        value=param_def["default"],
                        min=param_def.get("min", 0),
                        max=param_def.get("max", 1000),
                        step=param_def.get("step", 1),
                        style={'backgroundColor': '#2d2d2d', 'color': 'white'},
                    )
                elif param_def["type"] == "float":
                    control = dbc.Input(
                        id=input_id,
                        type="number",
                        value=param_def["default"],
                        min=param_def.get("min", 0),
                        max=param_def.get("max", 10),
                        step=param_def.get("step", 0.01),
                        style={'backgroundColor': '#2d2d2d', 'color': 'white'},
                    )
                elif param_def["type"] == "select":
                    control = dbc.Select(
                        id=input_id,
                        options=[{"label": opt, "value": opt} for opt in param_def["options"]],
                        value=param_def["default"],
                        style={'backgroundColor': '#2d2d2d', 'color': 'white'},
                    )
                elif param_def["type"] == "string":
                    control = dbc.Input(
                        id=input_id,
                        type="text",
                        value=param_def["default"],
                        style={'backgroundColor': '#2d2d2d', 'color': 'white'},
                    )
                else:
                    control = dbc.Input(
                        id=input_id,
                        type="text",
                        value=str(param_def["default"]),
                        style={'backgroundColor': '#2d2d2d', 'color': 'white'},
                    )

                param_inputs.append(
                    dbc.Row([
                        dbc.Col(html.Small(param_def["desc"], className="text-muted"), width=4),
                        dbc.Col(control, width=8),
                    ], className="mb-2")
                )

            # 创建accordion项
            accordion_item = dbc.AccordionItem(
                [
                    html.P(ind_info["description"], className="text-muted small mb-3"),
                    html.H6("参数配置", className="mb-3"),
                ] + param_inputs,
                title=f"{ind_code} - {ind_info['name']}",
                item_id=ind_code,
            )
            indicator_accordions.append(accordion_item)

        # 创建层的tab
        layer_tab = dbc.Tab(
            label=f"{layer_code} - {layer_info['name']}",
            children=[
                html.Div([
                    html.P(layer_info["description"], className="text-muted mb-3"),
                    dbc.Accordion(
                        indicator_accordions,
                        start_collapsed=True,
                        always_open=False,
                    ),
                ], className="p-3")
            ],
            tab_id=f"tab-{layer_code}"
        )
        layer_tabs.append(layer_tab)

    return html.Div([
        html.H5("L1-L4 指标参数配置", className="mb-3"),
        dbc.Tabs(layer_tabs, id="indicator-layer-tabs"),
    ], className="p-3")


def create_strategies_config_panel() -> html.Div:
    """创建策略权重配置面板"""

    strategy_cards = []
    for strategy_code, strategy_info in DEFAULT_STRATEGY_WEIGHTS.items():
        # 构建权重滑块
        weight_sliders = []
        for layer_code, weight_def in strategy_info["weights"].items():
            slider_id = f"slider-{strategy_code}-{layer_code}"
            weight_sliders.append(
                dbc.Row([
                    dbc.Col([
                        html.Label(weight_def["label"], className="fw-bold"),
                        html.Div(id=f"{slider_id}-value", className="text-primary fw-bold"),
                    ], width=3),
                    dbc.Col([
                        dcc.Slider(
                            id=slider_id,
                            min=weight_def["min"],
                            max=weight_def["max"],
                            step=weight_def["step"],
                            value=weight_def["value"],
                            marks={round(v, 2): str(round(v, 2)) for v in
                                   [weight_def["min"], (weight_def["min"]+weight_def["max"])/2, weight_def["max"]]},
                        ),
                    ], width=9),
                ], className="mb-3")
            )

        # 永久组合额外显示资产配置
        allocation_section = html.Div()
        if strategy_code == "permanent" and "allocation" in strategy_info:
            allocation_sliders = []
            for asset_code, asset_def in strategy_info["allocation"].items():
                slider_id = f"slider-{strategy_code}-alloc-{asset_code}"
                allocation_sliders.append(
                    dbc.Row([
                        dbc.Col([
                            html.Label(asset_def["label"], className="fw-bold text-success"),
                            html.Div(id=f"{slider_id}-value", className="text-success fw-bold"),
                        ], width=3),
                        dbc.Col([
                            dcc.Slider(
                                id=slider_id,
                                min=asset_def["min"],
                                max=asset_def["max"],
                                step=asset_def["step"],
                                value=asset_def["value"],
                                marks={round(v, 2): str(round(v, 2)) for v in
                                       [asset_def["min"], (asset_def["min"]+asset_def["max"])/2, asset_def["max"]]},
                            ),
                        ], width=9),
                    ], className="mb-3")
                )
            allocation_section = html.Div([
                html.Hr(),
                html.H6("资产配置比例", className="text-success mb-3"),
                html.Div(allocation_sliders),
            ])

        # 创建策略卡片
        card = dbc.Card([
            dbc.CardHeader([
                html.H5(strategy_info["name"], className="mb-0"),
                html.Small(strategy_info["description"], className="text-muted"),
            ]),
            dbc.CardBody([
                html.H6("L1-L4 权重配置", className="mb-3"),
                html.Div(weight_sliders),
                allocation_section,
            ]),
        ], className="mb-4")
        strategy_cards.append(card)

    return html.Div([
        html.H5("策略权重配置", className="mb-3"),
        html.Div(strategy_cards),
    ], className="p-3")


def create_data_sources_config_panel() -> html.Div:
    """创建数据源配置面板"""

    source_cards = []
    for source_code, source_info in DEFAULT_DATA_SOURCE_CONFIG.items():
        # 构建参数输入
        param_inputs = []
        for param_name, param_def in source_info["params"].items():
            input_id = f"input-source-{source_code}-{param_name}"

            if param_def["type"] == "bool":
                control = dbc.Checklist(
                    options=[{"label": param_def["desc"], "value": True}],
                    value=[True] if param_def["default"] else [],
                    id=input_id,
                    inline=True,
                    switch=True,
                )
            elif param_def["type"] == "int":
                control = dbc.Input(
                    id=input_id,
                    type="number",
                    value=param_def["default"],
                    min=param_def.get("min", 0),
                    max=param_def.get("max", 1000),
                    step=param_def.get("step", 1),
                )
            elif param_def["type"] == "string":
                control = dbc.Input(
                    id=input_id,
                    type="text",
                    value=param_def["default"],
                    placeholder=param_def["desc"],
                    style={'backgroundColor': '#2d2d2d', 'color': 'white'},
                )
            else:
                control = dbc.Input(
                    id=input_id,
                    type="text",
                    value=str(param_def["default"]),
                    style={'backgroundColor': '#2d2d2d', 'color': 'white'},
                )

            param_inputs.append(
                dbc.Row([
                    dbc.Col(html.Label(param_def["desc"], className="fw-bold"), width=4),
                    dbc.Col(control, width=8),
                ], className="mb-3")
            )

        # 数据源卡片
        card = dbc.Card([
            dbc.CardHeader([
                dbc.Row([
                    dbc.Col([
                        html.H5(source_info["name"], className="mb-0"),
                    ], width=8),
                    dbc.Col([
                        dbc.Switch(
                            id=f"switch-source-{source_code}",
                            label="启用",
                            value=source_info["enabled"],
                        ),
                    ], width=4, className="text-end"),
                ]),
            ]),
            dbc.CardBody(param_inputs),
        ], className="mb-4")
        source_cards.append(card)

    return html.Div([
        html.H5("数据源配置", className="mb-3"),
        html.Div(source_cards),
    ], className="p-3")


def create_backtest_config_panel() -> html.Div:
    """创建回测参数配置面板"""

    # 构建回测参数输入
    param_inputs = []
    for param_name, param_def in DEFAULT_BACKTEST_CONFIG.items():
        input_id = f"input-backtest-{param_name}"

        if param_def["type"] == "float":
            control = dbc.Input(
                id=input_id,
                type="number",
                value=param_def["default"],
                min=param_def.get("min", 0),
                max=param_def.get("max", 1),
                step=param_def.get("step", 0.0001),
            )
        elif param_def["type"] == "int":
            control = dbc.Input(
                id=input_id,
                type="number",
                value=param_def["default"],
                min=param_def.get("min", 0),
                max=param_def.get("max", 100),
                step=param_def.get("step", 1),
                style={'backgroundColor': '#2d2d2d', 'color': 'white'},
            )
        else:
            control = dbc.Input(
                id=input_id,
                type="text",
                value=str(param_def["default"]),
                style={'backgroundColor': '#2d2d2d', 'color': 'white'},
            )

        # 转换为百分比显示
        display_value = param_def["default"]
        if param_name in ["commission", "slippage"] and param_def["type"] == "float":
            display_desc = f"{param_def['desc']} (默认: {param_def['default']*100:.2f}%)"
        else:
            display_desc = f"{param_def['desc']} (默认: {display_value})"

        param_inputs.append(
            dbc.Row([
                dbc.Col([
                    html.Label(display_desc, className="fw-bold"),
                ], width=4),
                dbc.Col([control], width=8),
            ], className="mb-4")
        )

    return html.Div([
        html.H5("回测参数配置", className="mb-3"),
        dbc.Card([
            dbc.CardHeader([
                html.H6("交易成本与约束", className="mb-0"),
            ]),
            dbc.CardBody(param_inputs),
        ], className="mb-4"),

        # 说明文字
        dbc.Alert([
            html.H6("配置说明", className="alert-heading"),
            html.Ul([
                html.Li("佣金和滑点设置为单边费率，回测时会自动计算双边成本"),
                html.Li("样本内比例用于划分训练集和测试集，防止过拟合"),
                html.Li("最小持有天数控制交易频率，避免过度交易"),
                html.Li("过拟合警告阈值：当 样本内夏普/样本外夏普 > 阈值 时触发警告"),
            ]),
        ], color="info"),
    ], className="p-3")


# ============================================================================
# 回调函数注册
# ============================================================================

def register_config_callbacks(app: dash.Dash) -> None:
    """注册配置页面的回调函数"""

    # 加载初始配置
    @app.callback(
        Output("store-indicators-config", "data"),
        Output("store-strategies-config", "data"),
        Output("store-data-sources-config", "data"),
        Output("store-backtest-config", "data"),
        Input("config-tabs", "active_tab"),
    )
    def load_all_configs(active_tab):
        """加载所有配置"""
        indicators = load_config("indicators", DEFAULT_INDICATORS_CONFIG)
        strategies = load_config("strategies", DEFAULT_STRATEGY_WEIGHTS)
        data_sources = load_config("data_sources", DEFAULT_DATA_SOURCE_CONFIG)
        backtest = load_config("backtest", DEFAULT_BACKTEST_CONFIG)
        return indicators, strategies, data_sources, backtest

    # 保存所有配置
    @app.callback(
        Output("config-save-status", "children"),
        Input("btn-save-all-config", "n_clicks"),
        State("store-indicators-config", "data"),
        State("store-strategies-config", "data"),
        State("store-data-sources-config", "data"),
        State("store-backtest-config", "data"),
        prevent_initial_call=True,
    )
    def save_all_configs(n_clicks, indicators, strategies, data_sources, backtest):
        """保存所有配置"""
        if not n_clicks:
            return dash.no_update

        results = []
        if save_config("indicators", indicators):
            results.append("指标参数")
        if save_config("strategies", strategies):
            results.append("策略权重")
        if save_config("data_sources", data_sources):
            results.append("数据源")
        if save_config("backtest", backtest):
            results.append("回测参数")

        return dbc.Alert(
            f"✓ 成功保存: {', '.join(results)}",
            color="success",
            dismissable=True,
        )

    # 重置配置
    @app.callback(
        Output("config-save-status", "children", allow_duplicate=True),
        Input("btn-reset-config", "n_clicks"),
        prevent_initial_call=True,
    )
    def reset_configs(n_clicks):
        """重置所有配置为默认值"""
        if not n_clicks:
            return dash.no_update

        # 删除所有配置文件
        for config_type in ["indicators", "strategies", "data_sources", "backtest"]:
            config_path = get_config_path(config_type)
            if os.path.exists(config_path):
                os.remove(config_path)

        return dbc.Alert(
            "✓ 已重置所有配置为默认值，刷新页面后生效",
            color="warning",
            dismissable=True,
        )

    # 策略权重滑块值显示回调
    for strategy_code in ["rotation", "permanent", "thematic"]:
        for layer in ["L1", "L2", "L3", "L4"]:
            @app.callback(
                Output(f"slider-{strategy_code}-{layer}-value", "children"),
                Input(f"slider-{strategy_code}-{layer}", "value"),
            )
            def update_weight_value(value, sc=strategy_code, ly=layer):
                """更新权重值显示"""
                return f"{int(value * 100)}%"

    # 永久组合资产配置滑块值显示
    for asset in ["equity", "bond", "gold", "cash"]:
        @app.callback(
            Output(f"slider-permanent-alloc-{asset}-value", "children"),
            Input(f"slider-permanent-alloc-{asset}", "value"),
        )
        def update_alloc_value(value, ast=asset):
            """更新资产配置值显示"""
            return f"{int(value * 100)}%"


# 导出创建函数
__all__ = ['create_config_tab', 'register_config_callbacks']