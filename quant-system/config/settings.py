# -*- coding: utf-8 -*-
"""
全局配置文件

包含项目路径、日志配置、数据源设置等全局参数。
"""

import os
from pathlib import Path
from datetime import datetime

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent

# 项目配置
PROJECT_CONFIG = {
    'name': 'quant-system',
    'version': '1.0.0',
    'description': '多维量化交易系统',
    'author': 'Quant Team',
    'created_at': '2024-01-01',
}

# 日志配置
LOGGING_CONFIG = {
    'level': 'INFO',  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'date_format': '%Y-%m-%d %H:%M:%S',
    'file_prefix': 'quant_system',
    'max_bytes': 10 * 1024 * 1024,  # 10MB
    'backup_count': 5,
}

# 数据配置
DATA_CONFIG = {
    # 数据目录
    'raw_data_path': PROJECT_ROOT / 'data' / 'raw',
    'processed_data_path': PROJECT_ROOT / 'data' / 'processed',

    # 数据源配置
    'mootdx': {
        'enabled': True,
        'bestip': True,  # 自动选择最优服务器
        'timeout': 30,
    },
    'akshare': {
        'enabled': True,
        'timeout': 30,
    },
    'fred': {
        'enabled': True,
        'api_key': os.getenv('FRED_API_KEY', ''),  # 从环境变量读取
        'timeout': 30,
    },

    # 数据更新频率（分钟）
    'update_intervals': {
        'daily': 60 * 24,  # 日线数据：每天
        'intraday': 5,    # 日内数据：5分钟
    },
}

# 确保数据目录存在
DATA_CONFIG['raw_data_path'].mkdir(parents=True, exist_ok=True)
DATA_CONFIG['processed_data_path'].mkdir(parents=True, exist_ok=True)

# 回测配置
BACKTEST_CONFIG = {
    'initial_capital': 1000000,  # 初始资金：100万
    'commission': 0.001,         # 佣金：0.1%
    'slippage': 0.001,          # 滑点：0.1%
    'position_sizing': 'equal',  # 仓位管理：等权重
}

# 策略默认参数
STRATEGY_CONFIG = {
    'etf_rotation': {
        'weights': {'L1': 0.4, 'L2': 0.2, 'L3': 0.2, 'L4': 0.2},
        'rebalance_freq': 'W',  # 周度调仓
        'top_n': 1,  # 持有前1名
        'pool': ['159920', '513500', '518880', '159949'],  # 候选池
    },
    'permanent_portfolio': {
        'weights': {'L1': 0.15, 'L2': 0.2, 'L3': 0.35, 'L4': 0.3},
        'rebalance_freq': 'M',  # 月度调仓
        'threshold': 0.05,  # 偏离阈值5%
        'targets': {
            'equity': 0.4,    # 权益 40%
            'bond': 0.25,     # 债券 25%
            'gold': 0.2,      # 黄金 20%
            'cash': 0.15,     # 现金 15%
        },
    },
    'thematic_position': {
        'weights': {'L1': 0.35, 'L2': 0.25, 'L3': 0.15, 'L4': 0.25},
        'entry_threshold': 70,   # 入场阈值
        'exit_threshold': 30,    # 出场阈值
        'max_position': 0.2,     # 最大仓位20%
        'stop_loss': 0.08,       # 止损8%
    },
}
