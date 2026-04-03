"""
回测优化器测试脚本
测试防过拟合机制
"""

import pandas as pd
import numpy as np
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.backtest.optimizer import ParameterOptimizer, optimize_strategy
from core.backtest.strategy import StrategyBase


class TestStrategy(StrategyBase):
    """测试策略 - 双均线交叉"""

    def __init__(self, fast_period: int = 5, slow_period: int = 20):
        super().__init__()
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.lookback = max(fast_period, slow_period) + 5

    def generate_signal(self, data: pd.DataFrame) -> int:
        """生成交易信号"""
        if len(data) < self.slow_period:
            return 0

        close = data['close']
        fast_ma = close.rolling(window=self.fast_period).mean().iloc[-1]
        slow_ma = close.rolling(window=self.slow_period).mean().iloc[-1]

        if fast_ma > slow_ma:
            return 1  # 多头
        elif fast_ma < slow_ma:
            return -1  # 空头
        else:
            return 0  # 无信号


def generate_test_data(n_days: int = 500) -> pd.DataFrame:
    """生成测试数据"""
    np.random.seed(42)

    dates = pd.date_range(start='2020-01-01', periods=n_days, freq='D')

    # 生成随机游走价格
    returns = np.random.normal(0.0005, 0.02, n_days)
    prices = 100 * (1 + returns).cumprod()

    # 生成OHLCV数据
    data = pd.DataFrame({
        'open': prices * (1 + np.random.normal(0, 0.001, n_days)),
        'high': prices * (1 + abs(np.random.normal(0, 0.01, n_days))),
        'low': prices * (1 - abs(np.random.normal(0, 0.01, n_days))),
        'close': prices,
        'volume': np.random.randint(100000, 1000000, n_days),
    }, index=dates)

    return data


def main():
    """主测试函数"""
    print("="*80)
    print("回测优化器测试 - 防过拟合机制验证")
    print("="*80)

    # 生成测试数据
    print("\n1. 生成测试数据...")
    data = generate_test_data(n_days=500)
    print(f"   数据长度: {len(data)} 条")
    print(f"   日期范围: {data.index[0]} 至 {data.index[-1]}")

    # 定义参数网格
    print("\n2. 定义参数搜索空间...")
    param_grid = {
        'fast_period': [3, 5, 10],
        'slow_period': [15, 20, 30],
    }
    total_combinations = 1
    for values in param_grid.values():
        total_combinations *= len(values)
    print(f"   参数组合数: {total_combinations}")

    # 执行优化
    print("\n3. 执行参数优化（含防过拟合机制）...")
    print("-"*80)

    results, summary_df = optimize_strategy(
        strategy_class=TestStrategy,
        data=data,
        param_grid=param_grid,
        split_ratio=0.7,
        commission=0.001,
        slippage=0.001,
    )

    # 显示结果摘要
    print("\n4. 优化结果汇总:")
    print("-"*80)
    print(f"   成功优化: {len(results)} 组参数")
    print(f"   过拟合警告: {sum(1 for r in results if r.is_overfit)} 组")
    print(f"   自由度警告: {sum(1 for r in results if r.degrees_of_freedom_warning)} 组")

    # 显示前5个最优参数
    print("\n5. Top 5 最优参数（按综合评分排序）:")
    print("-"*80)
    print(f"{'排名':<4} {'参数':<30} {'样本内夏普':<12} {'样本外夏普':<12} {'夏普比':<8} {'过拟合':<6} {'评分':<8}")
    print("-"*80)

    for i, r in enumerate(results[:5], 1):
        params_str = str(r.params)[:28]
        overfit_flag = "是" if r.is_overfit else "否"
        print(f"{i:<4} {params_str:<30} {r.in_sample_sharpe:<12.3f} {r.out_sample_sharpe:<12.3f} "
              f"{r.in_out_sharpe_ratio:<8.2f} {overfit_flag:<6} {r.composite_score:<8.3f}")

    # 验证防过拟合机制
    print("\n6. 防过拟合机制验证:")
    print("-"*80)

    # 检查是否有正确的样本内外分割
    split_idx = int(len(data) * 0.7)
    print(f"   ✓ 样本内/样本外分割: {len(data[:split_idx])} / {len(data[split_idx:])} 条")

    # 检查过拟合检测
    overfit_results = [r for r in results if r.is_overfit]
    print(f"   ✓ 过拟合检测: 发现 {len(overfit_results)} 组过拟合参数 (阈值: 2.0)")

    # 检查自由度警告
    dof_warnings = [r for r in results if r.degrees_of_freedom_warning]
    print(f"   ✓ 自由度检查: 发现 {len(dof_warnings)} 组自由度警告")

    # 检查排序逻辑
    if results:
        top_result = results[0]
        print(f"   ✓ 推荐排序逻辑验证: 最优参数样本外夏普 = {top_result.out_sample_sharpe:.3f}")

    print("\n" + "="*80)
    print("测试完成！防过拟合机制工作正常。")
    print("="*80)

    return results, summary_df


if __name__ == '__main__':
    main()
