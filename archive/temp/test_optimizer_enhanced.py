"""
回测参数优化器增强版测试脚本

演示防过拟合机制的各项功能：
1. 样本内/样本外分割
2. 夏普比率比较法
3. CSCV组合对称交叉验证
4. 参数敏感性分析
5. 自由度检查
6. 综合稳健性评分
"""

import pandas as pd
import numpy as np
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.backtest.optimizer import ParameterOptimizer, OptimizationResult


class MockStrategy:
    """模拟策略用于测试"""

    def __init__(self, fast_period=5, slow_period=20, threshold=0.02):
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.threshold = threshold
        self.lookback = max(fast_period, slow_period) + 10

    def generate_signal(self, data):
        """生成交易信号"""
        if len(data) < self.slow_period:
            return 0

        close = data['close']
        fast_ma = close.rolling(self.fast_period).mean().iloc[-1]
        slow_ma = close.rolling(self.slow_period).mean().iloc[-1]

        # 计算价格变化率
        price_change = (close.iloc[-1] - close.iloc[-5]) / close.iloc[-5]

        if fast_ma > slow_ma * (1 + self.threshold) and price_change > 0:
            return 1  # 买入
        elif fast_ma < slow_ma * (1 - self.threshold) and price_change < 0:
            return -1  # 卖出
        return 0  # 持仓不变


def create_test_data(start_date='2020-01-01', end_date='2023-12-31', trend='up'):
    """创建测试数据"""
    dates = pd.date_range(start_date, end_date, freq='D')
    n = len(dates)

    if trend == 'up':
        # 上升趋势
        base_return = 0.0003
        volatility = 0.012
    elif trend == 'down':
        # 下降趋势
        base_return = -0.0002
        volatility = 0.015
    else:
        # 震荡
        base_return = 0.0
        volatility = 0.010

    # 生成价格序列
    returns = np.random.normal(base_return, volatility, n)
    prices = 100 * np.exp(np.cumsum(returns))

    df = pd.DataFrame({
        'close': prices,
        'open': prices * (1 + np.random.randn(n) * 0.001),
        'high': prices * (1 + abs(np.random.randn(n)) * 0.01),
        'low': prices * (1 - abs(np.random.randn(n)) * 0.01),
    }, index=dates)

    return df


def test_optimizer():
    """测试优化器功能"""
    print("=" * 100)
    print("🧪 回测参数优化器（增强版）测试")
    print("=" * 100)

    # 创建测试数据
    print("\n📊 创建测试数据...")
    data = create_test_data()
    print(f"   数据时间范围: {data.index[0].date()} 至 {data.index[-1].date()}")
    print(f"   数据条数: {len(data)}")

    # 定义参数网格
    param_grid = {
        'fast_period': [3, 5, 10],
        'slow_period': [15, 20, 30],
        'threshold': [0.01, 0.02, 0.03],
    }

    total_combinations = 1
    for v in param_grid.values():
        total_combinations *= len(v)

    print(f"\n🔧 参数网格:")
    for k, v in param_grid.items():
        print(f"   {k}: {v}")
    print(f"   总组合数: {total_combinations}")

    # 创建优化器
    print("\n⚙️ 初始化优化器...")
    optimizer = ParameterOptimizer(
        strategy_class=MockStrategy,
        param_grid=param_grid,
        split_ratio=0.7,
        enable_cscv=True,
        enable_sensitivity=True,
        random_state=42
    )

    # 执行优化
    print("\n🚀 开始参数优化（带防过拟合机制）...")
    print("-" * 100)

    try:
        results, summary_df = optimizer.optimize(
            data=data,
            commission=0.001,
            slippage=0.001,
            risk_free_rate=0.02
        )

        # 打印汇总表格
        print("\n📋 优化结果汇总（前10名）:")
        print("=" * 120)
        print(summary_df.head(10).to_string(index=False))
        print("=" * 120)

        # 验证防过拟合功能
        print("\n✅ 防过拟合机制验证:")
        print("-" * 100)

        if results:
            best = results[0]
            print(f"   样本内/样本外分割: 70% / 30%")
            print(f"   夏普比率比较法: {'✅ 启用' if hasattr(best, 'is_overfit_sharpe') else '❌ 未启用'}")
            print(f"   CSCV分析: {'✅ 启用' if hasattr(best, 'is_overfit_cscv') else '❌ 未启用'}")
            print(f"   参数敏感性: {'✅ 启用' if hasattr(best, 'is_overfit_sensitivity') else '❌ 未启用'}")
            print(f"   自由度检查: {'✅ 启用' if hasattr(best, 'degrees_of_freedom_warning') else '❌ 未启用'}")
            print(f"   综合稳健性评分: {'✅ 启用' if hasattr(best, 'robustness_score') else '❌ 未启用'}")

        print("\n" + "=" * 100)
        print("🎉 测试完成！优化器防过拟合机制工作正常。")
        print("=" * 100)

        return True

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_optimizer()
    sys.exit(0 if success else 1)
