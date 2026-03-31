"""
Phase 3 回测引擎验证脚本（简化版）
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

print("=" * 60)
print("Phase 3 回测引擎验证")
print("=" * 60)
print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# 测试1: 指标计算模块
print("-" * 60)
print("测试1: 指标计算模块")
print("-" * 60)

results = {}

# 生成测试数据
np.random.seed(42)
dates = pd.date_range('2023-01-01', periods=100, freq='D')
test_data = pd.DataFrame({
    'open': 100 + np.cumsum(np.random.randn(100) * 0.5),
    'high': 100 + np.cumsum(np.random.randn(100) * 0.5) + 1,
    'low': 100 + np.cumsum(np.random.randn(100) * 0.5) - 1,
    'close': 100 + np.cumsum(np.random.randn(100) * 0.5),
    'volume': np.random.randint(100000, 1000000, 100)
}, index=dates)
test_data['high'] = test_data[['open', 'close', 'high']].max(axis=1) + 0.5
test_data['low'] = test_data[['open', 'close', 'low']].min(axis=1) - 0.5

# L1
try:
    from core.indicators import L101CompositeSlopeMomentum
    l101 = L101CompositeSlopeMomentum(data=test_data)
    l101_result = l101.calculate()
    results['L101'] = len(l101_result) > 0
    print(f"  [OK] L101 复合斜率动量: {len(l101_result)} 个值")
except Exception as e:
    results['L101'] = False
    print(f"  [FAIL] L101: {e}")

# L2
try:
    from core.indicators import L201HurstExponent
    l201 = L201HurstExponent(data=test_data)
    l201_result = l201.calculate()
    results['L201'] = len(l201_result) > 0
    print(f"  [OK] L201 Hurst指数: {len(l201_result)} 个值")
except Exception as e:
    results['L201'] = False
    print(f"  [FAIL] L201: {e}")

# L3
try:
    from core.indicators import L301RollingCorrelationMatrix, L305MacroAssetResonance
    print(f"  [OK] L3指标导入成功")
    results['L3_import'] = True
except Exception as e:
    results['L3_import'] = False
    print(f"  [FAIL] L3导入: {e}")

# L4
try:
    from core.indicators import L404LiquidityGap
    l404 = L404LiquidityGap(data=test_data)
    l404_result = l404.calculate()
    results['L404'] = len(l404_result) > 0
    print(f"  [OK] L404 流动性缺口: {len(l404_result)} 个值")
except Exception as e:
    results['L404'] = False
    print(f"  [FAIL] L404: {e}")

passed = sum(results.values())
total = len(results)
print(f"\n指标模块: {passed}/{total} 通过")
print()

# 测试2: 回测组件
print("-" * 60)
print("测试2: 回测组件")
print("-" * 60)

backtest_results = {}

# Broker
try:
    from core.backtest import SimulatedBroker, Order
    broker = SimulatedBroker(initial_cash=1000000.0, commission_rate=0.001)
    order = Order(symbol='510300', side='buy', quantity=1000, order_type='market')
    broker.submit_order(order)
    broker.process_market_data(datetime.now(), {'510300': {'open': 4.0, 'high': 4.1, 'low': 3.9, 'close': 4.0}})
    positions = broker.get_positions()
    cash = broker.get_cash()
    backtest_results['broker'] = True
    print(f"  [OK] Broker: 持仓{len(positions)}个, 现金{cash:.0f}")
except Exception as e:
    backtest_results['broker'] = False
    print(f"  [FAIL] Broker: {e}")

# Strategy Base
try:
    from core.backtest import StrategyBase
    class TestStrategy(StrategyBase):
        def generate_signals(self, current_date, broker, price_data):
            return []
    test_strategy = TestStrategy({'name': 'test'})
    backtest_results['strategy'] = True
    print(f"  [OK] StrategyBase: 实例化成功")
except Exception as e:
    backtest_results['strategy'] = False
    print(f"  [FAIL] StrategyBase: {e}")

# Performance Analyzer
try:
    from core.backtest import PerformanceAnalyzer
    dates = pd.date_range('2023-01-01', periods=100, freq='D')
    equity_curve = pd.Series(1000000 * (1 + np.random.randn(100).cumsum() * 0.01), index=dates)
    trades = [{'symbol': '510300', 'pnl': 200}]
    analyzer = PerformanceAnalyzer()
    metrics = analyzer.calculate_all(equity_curve, trades)
    backtest_results['metrics'] = 'returns' in metrics
    print(f"  [OK] PerformanceAnalyzer: 计算完成")
except Exception as e:
    backtest_results['metrics'] = False
    print(f"  [FAIL] PerformanceAnalyzer: {e}")

passed = sum(backtest_results.values())
total = len(backtest_results)
print(f"\n回测组件: {passed}/{total} 通过")

# 汇总
print()
print("=" * 60)
all_passed = sum(results.values()) + sum(backtest_results.values())
all_total = len(results) + len(backtest_results)
print(f"总结果: {all_passed}/{all_total} 通过")

if all_passed == all_total:
    print("Phase 3 验证通过！")
    sys.exit(0)
else:
    print("Phase 3 验证未完全通过")
    sys.exit(1)
