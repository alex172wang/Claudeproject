"""
回测结果存储与管理

提供回测结果的存储、加载、可视化和导出功能。
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
import json
import pickle

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.figure import Figure
import seaborn as sns


@dataclass
class BacktestResult:
    """
    回测结果数据类

    存储完整回测结果，包括每日统计、交易记录、绩效指标等。
    """

    # 回测配置
    config: Any = None

    # 时间序列数据
    daily_stats: pd.DataFrame = field(default_factory=lambda: pd.DataFrame())

    # 交易记录
    trades: List[Any] = field(default_factory=list)
    orders: List[Any] = field(default_factory=list)

    # 经纪商实例（用于获取最终状态）
    broker: Any = None

    # 计算后的指标（延迟计算）
    _performance_metrics: Optional[Dict[str, Any]] = None
    _equity_curve: Optional[pd.Series] = None
    _returns: Optional[pd.Series] = None

    def __post_init__(self):
        """初始化后处理"""
        if not self.daily_stats.empty and 'date' in self.daily_stats.columns:
            self.daily_stats.set_index('date', inplace=True)

    @property
    def equity_curve(self) -> pd.Series:
        """权益曲线"""
        if self._equity_curve is None:
            if 'total_value' in self.daily_stats.columns:
                self._equity_curve = self.daily_stats['total_value']
            elif self.broker:
                self._equity_curve = pd.Series(
                    [self.config.initial_capital, self.broker.total_value],
                    index=[self.config.start_date, self.config.end_date]
                )
        return self._equity_curve

    @property
    def returns(self) -> pd.Series:
        """日收益率序列"""
        if self._returns is None:
            self._returns = self.equity_curve.pct_change().dropna()
        return self._returns

    @property
    def final_value(self) -> float:
        """最终资产价值"""
        if self.broker:
            return self.broker.total_value
        elif not self.daily_stats.empty and 'total_value' in self.daily_stats.columns:
            return self.daily_stats['total_value'].iloc[-1]
        return self.config.initial_capital

    @property
    def total_return(self) -> float:
        """总收益率"""
        return (self.final_value / self.config.initial_capital) - 1

    @property
    def annual_return(self) -> float:
        """年化收益率"""
        n_days = len(self.returns)
        if n_days == 0:
            return 0.0
        n_years = n_days / 252
        if n_years <= 0:
            return 0.0
        return (1 + self.total_return) ** (1 / n_years) - 1

    @property
    def volatility(self) -> float:
        """年化波动率"""
        return self.returns.std() * np.sqrt(252)

    @property
    def max_drawdown(self) -> float:
        """最大回撤"""
        cumulative = (1 + self.returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        return drawdown.min()

    @property
    def sharpe_ratio(self) -> float:
        """夏普比率"""
        if self.volatility == 0:
            return 0.0
        risk_free_rate = 0.03  # 假设3%无风险利率
        return (self.annual_return - risk_free_rate) / self.volatility

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'config': {
                'start_date': self.config.start_date,
                'end_date': self.config.end_date,
                'initial_capital': self.config.initial_capital,
            },
            'summary': {
                'final_value': self.final_value,
                'total_return': self.total_return,
                'annual_return': self.annual_return,
                'volatility': self.volatility,
                'max_drawdown': self.max_drawdown,
                'sharpe_ratio': self.sharpe_ratio,
            },
            'daily_stats_shape': self.daily_stats.shape,
            'trade_count': len(self.trades),
        }

    def save(self, filepath: str):
        """
        保存回测结果

        Args:
            filepath: 保存路径（支持.pkl, .json, .csv）
        """
        path = Path(filepath)

        if path.suffix == '.pkl':
            with open(path, 'wb') as f:
                pickle.dump(self, f)

        elif path.suffix == '.json':
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

        elif path.suffix == '.csv':
            # 保存每日统计
            self.daily_stats.to_csv(path)

        else:
            raise ValueError(f"不支持的文件格式: {path.suffix}")

    @classmethod
    def load(cls, filepath: str) -> 'BacktestResult':
        """
        加载回测结果

        Args:
            filepath: 文件路径

        Returns:
            BacktestResult: 回测结果实例
        """
        path = Path(filepath)

        if path.suffix == '.pkl':
            with open(path, 'rb') as f:
                return pickle.load(f)
        else:
            raise ValueError(f"不支持的文件格式: {path.suffix}")


def create_default_result() -> BacktestResult:
    """创建默认回测结果（用于测试）"""
    # 创建模拟权益曲线
    dates = pd.date_range('2023-01-01', '2023-12-31', freq='B')
    np.random.seed(42)
    returns = np.random.normal(0.0003, 0.015, len(dates))
    equity = 1000000 * (1 + returns).cumprod()

    daily_stats = pd.DataFrame({
        'total_value': equity,
        'cash': equity * 0.1,
        'position_value': equity * 0.9,
    }, index=dates)

    config = type('Config', (), {
        'start_date': '2023-01-01',
        'end_date': '2023-12-31',
        'initial_capital': 1000000.0,
    })()

    return BacktestResult(
        config=config,
        daily_stats=daily_stats,
        trades=[],
        orders=[],
        broker=None
    )
