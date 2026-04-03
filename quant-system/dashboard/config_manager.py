# -*- coding: utf-8 -*-
"""
配置管理器

提供统一的配置管理接口，支持从文件加载、内存缓存和默认值回退。
"""

import os
import json
from typing import Dict, Any, Optional
from pathlib import Path


# 配置文件存储目录
CONFIG_DIR = Path(__file__).parent / "config_files"
CONFIG_DIR.mkdir(exist_ok=True)


class ConfigManager:
    """配置管理器"""

    # 默认配置（首次运行时作为模板）
    DEFAULT_INDICATORS_CONFIG = {
        "L1-01": {
            "name": "复合斜率动量",
            "long_window": 30,
            "short_window": 15,
            "long_weight": 0.6,
            "short_weight": 0.4,
        },
        "L1-02": {"period": 120},
        "L1-03": {"diff_window": 5},
        "L1-04": {"period": 60},
        "L1-05": {"yield_slope_window": 30, "dxy_slope_window": 30},
        "L2-01": {"window": 60},
        "L2-02": {"short_window": 5, "long_window": 30},
        "L2-03": {"volume_ma_period": 20},
        "L2-04": {"rolling_window": 120},
        "L2-05": {"period": 20},
        "L2-06": {"lag": 1, "window": 30},
        "L3-01": {"window": 60},
        "L3-02": {"diff_window": 5},
        "L3-03": {"window": 60},
        "L3-04": {"slope_window": 30},
        "L3-05": {"window": 90},
        "L3-06": {"rolling_weeks": 4},
        "L4-01": {"option_type": "ATM", "maturity": "nearest"},
        "L4-02": {"delta_put": 25, "delta_call": 25, "maturity": "monthly"},
        "L4-03": {"type": "volume"},
        "L4-04": {"window": 20},
        "L4-05": {"window": 60},
        "L4-06": {"window": 30, "gap_threshold": 0.01},
        "L4-07": {
            "fed_balance_sheet": "WALCL",
            "credit_spread_baa": "BAA",
            "credit_spread_aaa": "AAA",
        },
    }

    DEFAULT_STRATEGY_WEIGHTS = {
        "rotation": {"L1": 0.40, "L2": 0.20, "L3": 0.20, "L4": 0.20},
        "permanent": {"L1": 0.15, "L2": 0.20, "L3": 0.35, "L4": 0.30},
        "thematic": {"L1": 0.35, "L2": 0.25, "L3": 0.15, "L4": 0.25},
    }

    DEFAULT_BACKTEST_CONFIG = {
        "commission": 0.001,
        "slippage": 0.0005,
        "in_sample_ratio": 0.7,
        "min_holding_days": 5,
        "overfitting_threshold": 2.0,
    }

    def __init__(self):
        """初始化配置管理器"""
        self._cache: Dict[str, Any] = {}
        self._load_all()

    def _get_config_path(self, name: str) -> Path:
        """获取配置文件路径"""
        return CONFIG_DIR / f"{name}.json"

    def _load_all(self):
        """加载所有配置到内存缓存"""
        for name in ["indicators", "strategy_weights", "backtest"]:
            self._load_single(name)

    def _load_single(self, name: str):
        """加载单个配置"""
        path = self._get_config_path(name)
        if path.exists():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    self._cache[name] = json.load(f)
                return
            except Exception as e:
                print(f"[ConfigManager] 加载 {name} 配置失败: {e}")

        # 使用默认值
        self._cache[name] = self._get_default(name)

    def _get_default(self, name: str) -> dict:
        """获取默认配置"""
        defaults = {
            "indicators": self.DEFAULT_INDICATORS_CONFIG,
            "strategy_weights": self.DEFAULT_STRATEGY_WEIGHTS,
            "backtest": self.DEFAULT_BACKTEST_CONFIG,
        }
        return defaults.get(name, {})

    def save(self, name: str, config: dict):
        """保存配置"""
        path = self._get_config_path(name)
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            self._cache[name] = config
            return True
        except Exception as e:
            print(f"[ConfigManager] 保存 {name} 配置失败: {e}")
            return False

    def get(self, name: str, key: str = None, default=None):
        """获取配置值"""
        config = self._cache.get(name, {})
        if key is None:
            return config
        return config.get(key, default)

    def get_indicator_param(self, indicator_id: str, param_name: str, default=None):
        """获取指标参数"""
        indicator_config = self._cache.get("indicators", {}).get(indicator_id, {})
        return indicator_config.get(param_name, default)

    def get_strategy_weights(self, strategy_type: str) -> dict:
        """获取策略权重"""
        return self._cache.get("strategy_weights", {}).get(strategy_type, {})

    def get_backtest_config(self) -> dict:
        """获取回测配置"""
        return self._cache.get("backtest", {})

    def reset_to_default(self, name: str):
        """重置配置为默认值"""
        path = self._get_config_path(name)
        if path.exists():
            path.unlink()
        self._cache[name] = self._get_default(name)
        return self._cache[name]


# 全局配置管理器实例
config_manager = ConfigManager()
