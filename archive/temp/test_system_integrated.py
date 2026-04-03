"""
系统集成测试
验证 Phase 1-3 的所有核心功能
"""

import pandas as pd
import numpy as np
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_data_layer():
    """测试数据层 (Phase 1)"""
    print("\n" + "="*80)
    print("测试 Phase 1: 数据层")
    print("="*80)

    try:
        from core.data.mootdx_fetcher import MootdxFetcher
        from core.data.cache import DataCache

        print("  ✓ 数据获取模块导入成功")

        # 测试缓存功能
        cache = DataCache()
        print(f"  ✓ 数据缓存初始化成功")

        return True

    except Exception as e:
        print(f"  ✗ 数据层测试失败: {e}")
        return False


def test_indicators():
    """测试指标层 (Phase 2)"""
    print("\n" + "="*80)
    print("测试 Phase 2: 指标层 (L1-L4)")
    print("="*80)

    try:
        from core.indicators import list_indicators, get_indicator

        # 列出所有指标
        indicators = list_indicators()
        print(f"  ✓ 指标系统加载成功")
        print(f"    - L1 (趋势层): {len(indicators['L1'])} 个指标")
        print(f"    - L2 (结构层): {len(indicators['L2'])} 个指标")
        print(f"    - L3 (共振层): {len(indicators['L3'])} 个指标")
        print(f"    - L4 (缺口层): {len(indicators['L4'])} 个指标")

        # 测试单个指标计算
        print("\n  测试指标计算...")

        # 生成测试数据
        np.random.seed(42)
        n_days = 100
        dates = pd.date_range(start='2023-01-01', periods=n_days, freq='D')

        prices = 100 * (1 + np.random.normal(0.0005, 0.02, n_days)).cumprod()

        test_data = pd.DataFrame({
            'open': prices * (1 + np.random.normal(0, 0.001, n_days)),
            'high': prices * (1 + abs(np.random.normal(0, 0.01, n_days))),
            'low': prices * (1 - abs(np.random.normal(0, 0.01, n_days))),
            'close': prices,
            'volume': np.random.randint(100000, 1000000, n_days),
        }, index=dates)

        # 测试 L1-01 复合斜率动量
        indicator = get_indicator('L1-01')
        result = indicator.calculate(test_data)

        print(f"    ✓ L1-01 计算成功")
        print(f"      标准化得分: {result.current.normalized_score:.2f}")
        print(f"      信号: {result.current.signal}")

        # 测试 L2-01 Hurst指数
        indicator = get_indicator('L2-01')
        result = indicator.calculate(test_data)

        print(f"    ✓ L2-01 计算成功")
        print(f"      Hurst值: {result.current.value:.3f}")

        return True

    except Exception as e:
        import traceback
        print(f"  ✗ 指标层测试失败: {e}")
        traceback.print_exc()
        return False


def test_backtest():
    """测试回测引擎 (Phase 3)"""
    print("\n" + "="*80)
    print("测试 Phase 3: 回测引擎（含防过拟合）")
    print("="*80)

    try:
        from core.backtest.optimizer import ParameterOptimizer, optimize_strategy
        from core.backtest.strategy import StrategyBase

        print("  ✓ 回测模块导入成功")

        # 创建测试策略
        class TestMAStrategy(StrategyBase):
            """测试用双均线策略"""

            def __init__(self, fast: int = 5, slow: int = 20):
                super().__init__()
                self.fast = fast
                self.slow = slow
                self.lookback = slow + 5

            def generate_signal(self, data: pd.DataFrame) -> int:
                if len(data) < self.slow:
                    return 0

                close = data['close']
                fast_ma = close.rolling(window=self.fast).mean().iloc[-1]
                slow_ma = close.rolling(window=self.slow).mean().iloc[-1]

                if fast_ma > slow_ma:
                    return 1
                elif fast_ma < slow_ma:
                    return -1
                else:
                    return 0

        # 生成测试数据
        print("\n  生成测试数据...")
        np.random.seed(42)
        n_days = 300
        dates = pd.date_range(start='2020-01-01', periods=n_days, freq='D')

        returns = np.random.normal(0.0005, 0.015, n_days)
        prices = 100 * (1 + returns).cumprod()

        test_data = pd.DataFrame({
            'open': prices * (1 + np.random.normal(0, 0.001, n_days)),
            'high': prices * (1 + abs(np.random.normal(0, 0.008, n_days))),
            'low': prices * (1 - abs(np.random.normal(0, 0.008, n_days))),
            'close': prices,
            'volume': np.random.randint(100000, 1000000, n_days),
        }, index=dates)

        print(f"    ✓ 数据生成完成: {len(test_data)} 条")

        # 执行参数优化
        print("\n  执行参数优化（含防过拟合机制）...")

        param_grid = {
            'fast': [3, 5, 10],
            'slow': [15, 20, 30],
        }

        results, summary_df = optimize_strategy(
            strategy_class=TestMAStrategy,
            data=test_data,
            param_grid=param_grid,
            split_ratio=0.7,
            commission=0.001,
            slippage=0.001,
        )

        print("\n  优化结果:")
        print(f"    ✓ 成功优化: {len(results)} 组参数")
        print(f"    ✓ 过拟合警告: {sum(1 for r in results if r.is_overfit)} 组")
        print(f"    ✓ 自由度警告: {sum(1 for r in results if r.degrees_of_freedom_warning)} 组")

        if results:
            best = results[0]
            print(f"\n    最优参数:")
            print(f"      参数: {best.params}")
            print(f"      样本内夏普: {best.in_sample_sharpe:.3f}")
            print(f"      样本外夏普: {best.out_sample_sharpe:.3f}")
            print(f"      夏普比率: {best.in_out_sharpe_ratio:.2f}")
            print(f"      综合评分: {best.composite_score:.3f}")

        return True

    except Exception as e:
        import traceback
        print(f"  ✗ 回测引擎测试失败: {e}")
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("\n" + "="*80)
    print("量化交易系统 - 集成测试")
    print("="*80)

    results = {}

    # 测试数据层
    results['data_layer'] = test_data_layer()

    # 测试指标层
    results['indicators'] = test_indicators()

    # 测试回测引擎
    results['backtest'] = test_backtest()

    # 汇总结果
    print("\n" + "="*80)
    print("测试结果汇总")
    print("="*80)

    for name, passed in results.items():
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"  {name:20s}: {status}")

    total = len(results)
    passed = sum(results.values())

    print(f"\n总计: {passed}/{total} 项测试通过 ({passed/total*100:.1f}%)")

    if passed == total:
        print("\n🎉 所有测试通过！系统运行正常。")
    else:
        print("\n⚠️ 部分测试失败，请检查日志。")

    print("="*80)

    return results


if __name__ == '__main__':
    main()
