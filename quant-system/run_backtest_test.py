"""
Phase 3 回测引擎验证脚本 - Windows兼容版
"""

import sys
import os

# 添加src到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import pandas as pd
import numpy as np
from datetime import datetime

print("="*60)
print("Phase 3 回测引擎验证")
print("="*60)
print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

all_passed = True
results = {}

# 测试1: 指标模块
print("-"*60)
print("测试1: 指标计算模块")
print("-"*60)

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

# L101
try:
    from core.indicators import L101CompositeSlopeMomentum
    l101 = L101CompositeSlopeMomentum(data=test_data)
    result = l101.calculate()
    print(f"  [OK] L101: {len(result)} values")
    results['L101'] = True
except Exception as e:
    print(f"  [FAIL] L101: {e}")
    results['L101'] = False
    all_passed = False

# L201
try:
    from core.indicators import L201HurstExponent
    l201 = L201HurstExponent(data=test_data)
    result = l201.calculate()
    print(f"  [OK] L201: {len(result)} values")
    results['L201'] = True
except Exception as e:
    print(f"  [FAIL] L201: {e}")
    results['L201'] = False
    all_passed = False

# L301
try:
    from core.indicators import L301RollingCorrelationMatrix, L302CorrelationVelocity
    print(f"  [OK] L301-L302: import success")
    results['L3_import'] = True
except Exception as e:
    print(f"  [FAIL] L3 import: {e}")
    results['L3_import'] = False
    all_passed = False

# L4
try:
    from core.indicators import L404LiquidityGap
    l404 = L404LiquidityGap(data=test_data)
    result = l404.calculate()
    print(f"  [OK] L404: {len(result)} values")
    results['L404'] = True
except Exception as e:
    print(f"  [FAIL] L404: {e}")
    results['L404'] = False
    all_passed = False

passed_indicators = sum(results.values())
total_indicators = len(results)
print(f"\n指标模块: {passed_indicators}/{total_indicators} 通过")
print()

# 测试2: 回测组件
print("-"*60)
print("测试2: 回测组件")
print("-"*60)

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
    print(f"  [OK] Broker: {len(positions)} positions, cash={cash:.0f}")
except Exception as e:
    print(f"  [FAIL] Broker: {e}")
    backtest_results['broker'] = False
    all_passed = False

# Strategy Base
try:
    from core.backtest import StrategyBase
    class TestStrategy(StrategyBase):
        def generate_signals(self, current_date, broker, price_data):
            return []
    test_strategy = TestStrategy({'name': 'test'})
    backtest_results['strategy'] = True
    print(f"  [OK] StrategyBase: instantiated")
except Exception as e:
    print(f"  [FAIL] StrategyBase: {e}")
    backtest_results['strategy'] = False
    all_passed = False

# Performance Analyzer
try:
    from core.backtest import PerformanceAnalyzer
    dates = pd.date_range('2023-01-01', periods=100, freq='D')
    equity_curve = pd.Series(1000000 * (1 + np.random.randn(100).cumsum() * 0.01), index=dates)
    trades = [{'symbol': '510300', 'pnl': 200}]
    analyzer = PerformanceAnalyzer()
    metrics = analyzer.calculate_all(equity_curve, trades)
    backtest_results['metrics'] = 'returns' in metrics
    print(f"  [OK] PerformanceAnalyzer: calculated")
except Exception as e:
    print(f"  [FAIL] PerformanceAnalyzer: {e}")
    backtest_results['metrics'] = False
    all_passed = False

passed_backtest = sum(backtest_results.values())
total_backtest = len(backtest_results)
print(f"\n回测组件: {passed_backtest}/{total_backtest} 通过")

# 汇总
print()
print("="*60)
all_passed_count = passed_indicators + passed_backtest
all_total = total_indicators + total_backtest
print(f"总结果: {all_passed_count}/{all_total} 通过")

if all_passed:
    print("Phase 3 验证通过！")
    sys.exit(0)
else:
    print("Phase 3 验证未完全通过")
    sys.exit(1)
