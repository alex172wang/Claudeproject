"""
回测结果可视化模块

提供回测结果的可视化图表生成，包括：
- 权益曲线与回撤
- 收益分布
- 滚动指标
- 交易分析图表
"""

from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.figure import Figure
from matplotlib.axes import Axes
import seaborn as sns

# 设置样式
sns.set_style("whitegrid")
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


class BacktestVisualizer:
    """
    回测可视化器

    为回测结果生成各种可视化图表
    """

    def __init__(self, result: Any):
        """
        初始化可视化器

        Args:
            result: BacktestResult实例
        """
        self.result = result
        self.fig_size = (14, 8)

    def plot_equity_curve(
        self,
        benchmark: Optional[pd.Series] = None,
        show_drawdown: bool = True,
        save_path: Optional[str] = None
    ) -> Figure:
        """
        绘制权益曲线与回撤

        Args:
            benchmark: 基准曲线（可选）
            show_drawdown: 是否显示回撤图
            save_path: 保存路径（可选）

        Returns:
            Figure: matplotlib图表对象
        """
        if show_drawdown:
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=self.fig_size,
                                           gridspec_kw={'height_ratios': [3, 1]})
        else:
            fig, ax1 = plt.subplots(figsize=self.fig_size)
            ax2 = None

        # 权益曲线
        equity = self.result.equity_curve
        ax1.plot(equity.index, equity.values, label='策略权益', linewidth=2, color='#2196F3')

        # 基准曲线
        if benchmark is not None:
            # 归一化基准
            normalized_benchmark = benchmark / benchmark.iloc[0] * self.result.config.initial_capital
            ax1.plot(normalized_benchmark.index, normalized_benchmark.values,
                    label='基准', linewidth=1.5, linestyle='--', color='#757575')

        # 初始资金线
        ax1.axhline(y=self.result.config.initial_capital, color='gray',
                   linestyle=':', alpha=0.5, label='初始资金')

        ax1.set_title('权益曲线', fontsize=14, fontweight='bold')
        ax1.set_xlabel('日期')
        ax1.set_ylabel('资产价值')
        ax1.legend(loc='upper left')
        ax1.grid(True, alpha=0.3)
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)

        # 回撤图
        if show_drawdown and ax2 is not None:
            # 计算回撤
            cumulative = (1 + self.result.returns).cumprod()
            running_max = cumulative.expanding().max()
            drawdown = (cumulative - running_max) / running_max * 100

            ax2.fill_between(drawdown.index, drawdown.values, 0,
                           color='#F44336', alpha=0.3, label='回撤')
            ax2.plot(drawdown.index, drawdown.values, color='#D32F2F', linewidth=1)

            # 最大回撤标记
            max_dd_idx = drawdown.idxmin()
            max_dd_val = drawdown.min()
            ax2.scatter([max_dd_idx], [max_dd_val], color='red', s=100, zorder=5)
            ax2.annotate(f'最大回撤: {max_dd_val:.1f}%',
                        xy=(max_dd_idx, max_dd_val),
                        xytext=(10, -20), textcoords='offset points',
                        bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.5),
                        arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0'))

            ax2.set_title('回撤 (%)', fontsize=12)
            ax2.set_xlabel('日期')
            ax2.set_ylabel('回撤幅度 (%)')
            ax2.legend()
            ax2.grid(True, alpha=0.3)
            ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
            plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"图表已保存至: {save_path}")

        return fig

    def plot_return_distribution(self, save_path: Optional[str] = None) -> Figure:
        """
        绘制收益分布图

        Args:
            save_path: 保存路径（可选）

        Returns:
            Figure: matplotlib图表对象
        """
        returns = self.result.returns * 100  # 转换为百分比

        fig, axes = plt.subplots(2, 2, figsize=(14, 10))

        # 1. 直方图 + KDE
        ax1 = axes[0, 0]
        returns.hist(bins=50, ax=ax1, density=True, alpha=0.7, color='#2196F3', edgecolor='black')
        returns.plot.kde(ax=ax1, color='#D32F2F', linewidth=2, label='KDE')
        ax1.axvline(returns.mean(), color='green', linestyle='--', linewidth=2, label=f'均值: {returns.mean():.2f}%')
        ax1.axvline(returns.median(), color='orange', linestyle='--', linewidth=2, label=f'中位数: {returns.median():.2f}%')
        ax1.set_title('日收益率分布', fontsize=12, fontweight='bold')
        ax1.set_xlabel('收益率 (%)')
        ax1.set_ylabel('密度')
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # 2. Q-Q图
        ax2 = axes[0, 1]
        from scipy import stats
        stats.probplot(returns.dropna(), dist="norm", plot=ax2)
        ax2.set_title('Q-Q图 (正态性检验)', fontsize=12, fontweight='bold')
        ax2.grid(True, alpha=0.3)

        # 3. 月度收益热力图
        ax3 = axes[1, 0]
        monthly_returns = self.result.daily_stats['total_value'].resample('M').last().pct_change() * 100
        monthly_returns = monthly_returns.dropna()

        if len(monthly_returns) > 0:
            # 创建月度透视表
            monthly_df = pd.DataFrame({
                'year': monthly_returns.index.year,
                'month': monthly_returns.index.month,
                'return': monthly_returns.values
            })

            pivot = monthly_df.pivot(index='year', columns='month', values='return')
            pivot.columns = ['1月', '2月', '3月', '4月', '5月', '6月',
                           '7月', '8月', '9月', '10月', '11月', '12月']

            sns.heatmap(pivot, annot=True, fmt='.1f', cmap='RdYlGn', center=0,
                     ax=ax3, cbar_kws={'label': '收益率 (%)'})
            ax3.set_title('月度收益率热力图 (%)', fontsize=12, fontweight='bold')

        # 4. 滚动统计
        ax4 = axes[1, 1]
        rolling_window = 30
        if len(self.result.returns) >= rolling_window:
            rolling_mean = self.result.returns.rolling(window=rolling_window).mean() * 252 * 100
            rolling_std = self.result.returns.rolling(window=rolling_window).std() * np.sqrt(252) * 100
            rolling_sharpe = rolling_mean / rolling_std

            ax4.plot(rolling_sharpe.index, rolling_sharpe.values, label='滚动夏普', linewidth=1.5)
            ax4.axhline(rolling_sharpe.mean(), color='red', linestyle='--', label=f'均值: {rolling_sharpe.mean():.2f}')
            ax4.fill_between(rolling_sharpe.index, rolling_sharpe, 0, alpha=0.3)
            ax4.set_title(f'{rolling_window}日滚动夏普比率', fontsize=12, fontweight='bold')
            ax4.set_xlabel('日期')
            ax4.set_ylabel('夏普比率')
            ax4.legend()
            ax4.grid(True, alpha=0.3)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"图表已保存至: {save_path}")

        return fig


def main():
    """主函数"""
    print("回测引擎可视化示例")
    print("="*60)

    # 创建示例结果
    from core.backtest.results import create_default_result
    result = create_default_result()

    # 创建可视化器
    visualizer = BacktestVisualizer(result)

    # 绘制权益曲线
    print("\n1. 绘制权益曲线...")
    fig1 = visualizer.plot_equity_curve(save_path='equity_curve.png')
    print("权益曲线已保存至: equity_curve.png")

    # 绘制收益分布
    print("\n2. 绘制收益分布...")
    fig2 = visualizer.plot_return_distribution(save_path='return_distribution.png')
    print("收益分布已保存至: return_distribution.png")

    print("\n可视化示例完成!")


if __name__ == '__main__':
    main()
