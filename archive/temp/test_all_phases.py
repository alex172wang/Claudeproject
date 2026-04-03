"""
Phase 3 + Phase 4 综合验证脚本
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

print("="*70)
print("量化交易系统 - Phase 3 & 4 综合验证")
print("="*70)

results = {}

# ============ Phase 3: 回测引擎 ============
print("\n[Phase 3] 回测引擎验证")
print("-"*70)

# 指标模块
try:
    from core.indicators import L101CompositeSlopeMomentum, L201HurstExponent
    from core.indicators import L301RollingCorrelationMatrix, L404LiquidityGap
    results['p3_indicators'] = True
    print("  [OK] 指标模块 (L1-L4)")
except Exception as e:
    results['p3_indicators'] = False
    print(f"  [FAIL] 指标模块: {e}")

# 回测组件
try:
    from core.backtest import SimulatedBroker, BacktestEngine
    from core.backtest import ETFRotationStrategy, PerformanceAnalyzer
    results['p3_backtest'] = True
    print("  [OK] 回测引擎组件")
except Exception as e:
    results['p3_backtest'] = False
    print(f"  [FAIL] 回测引擎: {e}")

# ============ Phase 4: 实盘监控 ============
print("\n[Phase 4] 实盘监控系统验证")
print("-"*70)

# 实时数据流
try:
    from core.live.data.stream import RealtimeDataStream, DataSource, TickData
    results['p4_data'] = True
    print("  [OK] 实时数据流模块")
except Exception as e:
    results['p4_data'] = False
    print(f"  [FAIL] 实时数据流: {e}")

# 信号监控
try:
    from core.live.signals.monitor import SignalMonitor, SignalAlert, AlertLevel
    results['p4_signals'] = True
    print("  [OK] 信号监控模块")
except Exception as e:
    results['p4_signals'] = False
    print(f"  [FAIL] 信号监控: {e}")

# 交易执行
try:
    from core.live.execution.trader import LiveTrader, OrderManager, OrderStatus
    results['p4_execution'] = True
    print("  [OK] 交易执行模块")
except Exception as e:
    results['p4_execution'] = False
    print(f"  [FAIL] 交易执行: {e}")

# 风险控制
try:
    from core.live.risk.controller import RiskController, RiskRule, RiskLevel
    results['p4_risk'] = True
    print("  [OK] 风险控制模块")
except Exception as e:
    results['p4_risk'] = False
    print(f"  [FAIL] 风险控制: {e}")

# ============ 汇总 ============
print("\n" + "="*70)
print("验证结果汇总")
print("="*70)

p3_passed = sum([results.get('p3_indicators', False), results.get('p3_backtest', False)])
p4_passed = sum([
    results.get('p4_data', False),
    results.get('p4_signals', False),
    results.get('p4_execution', False),
    results.get('p4_risk', False),
])

print(f"\nPhase 3 (回测引擎): {p3_passed}/2 模块通过")
print(f"Phase 4 (实盘监控): {p4_passed}/4 模块通过")

total_passed = p3_passed + p4_passed
total_modules = 6

print(f"\n总计: {total_passed}/{total_modules} 模块通过")

if all(results.values()):
    print("\n所有验证通过！系统运行正常。")
    sys.exit(0)
else:
    print("\n部分验证未通过，请检查错误信息。")
    sys.exit(1)
