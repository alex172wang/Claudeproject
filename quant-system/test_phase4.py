"""
Phase 4 实盘监控系统验证脚本
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from datetime import datetime

print("="*60)
print("Phase 4 实盘监控系统验证")
print("="*60)
print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

all_passed = True
results = {}

# 测试1: 实时数据流模块
print("-"*60)
print("测试1: 实时数据流模块")
print("-"*60)

try:
    from core.live.data.stream import RealtimeDataStream, DataSource, TickData
    from core.live.data.adapters import MootdxRealtimeAdapter, AKShareRealtimeAdapter

    # 创建模拟数据流
    stream = RealtimeDataStream(data_source=DataSource.MOCK, cache_size=100)

    # 测试TickData创建
    tick = TickData(
        symbol="510300",
        timestamp=datetime.now(),
        price=4.0,
        open=3.95,
        high=4.05,
        low=3.90,
        prev_close=3.95,
        volume=100000,
        amount=400000,
    )

    results['data_stream'] = True
    print(f"  [OK] RealtimeDataStream created, DataSource.MOCK")
    print(f"  [OK] TickData created for {tick.symbol} @ {tick.price}")
except Exception as e:
    results['data_stream'] = False
    all_passed = False
    print(f"  [FAIL] {e}")

# 测试2: 信号监控模块
print()
print("-"*60)
print("测试2: 信号监控模块")
print("-"*60)

try:
    from core.live.signals.monitor import (
        SignalMonitor, SignalAlert, AlertLevel, AlertType
    )

    # 创建监控器
    monitor = SignalMonitor(max_history=1000)

    # 触发测试告警
    alert = monitor.alert(
        level=AlertLevel.WARNING,
        alert_type=AlertType.THRESHOLD_BREACH,
        source="L101",
        title="Momentum Threshold Breach",
        message="L101 composite slope momentum exceeded threshold",
        symbol="510300",
        value=75.5,
        threshold=70.0,
    )

    # 检查告警历史
    history = monitor.get_alert_history(limit=10)

    results['signal_monitor'] = len(history) > 0
    print(f"  [OK] SignalMonitor created")
    print(f"  [OK] Test alert triggered: {alert.alert_id}")
    print(f"  [OK] Alert history: {len(history)} alerts")
except Exception as e:
    results['signal_monitor'] = False
    all_passed = False
    print(f"  [FAIL] {e}")

# 测试3: 交易执行模块
print()
print("-"*60)
print("测试3: 交易执行模块")
print("-"*60)

try:
    from core.live.execution.trader import (
        LiveTrader, OrderManager, Order, OrderStatus, OrderType, OrderSide
    )

    # 创建订单管理器
    order_manager = OrderManager()

    # 创建测试订单
    order = order_manager.create_order(
        symbol="510300",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        quantity=1000,
        price=4.0,
    )

    # 提交订单
    order_manager.submit_order(order.order_id)

    # 模拟成交
    fill = order_manager.handle_fill(
        order_id=order.order_id,
        fill_price=4.0,
        fill_quantity=1000,
    )

    # 创建LiveTrader
    trader = LiveTrader(order_manager)
    trader.start()

    # 测试买入
    buy_order = trader.buy_limit("510500", 500, 6.5)

    results['trader'] = buy_order is not None
    print(f"  [OK] OrderManager created")
    print(f"  [OK] Order created: {order.order_id}")
    print(f"  [OK] Fill handled: {fill.fill_id if fill else 'None'}")
    print(f"  [OK] LiveTrader started")
    print(f"  [OK] Buy order: {buy_order.order_id if buy_order else 'None'}")

    trader.stop()
except Exception as e:
    results['trader'] = False
    all_passed = False
    print(f"  [FAIL] {e}")
    import traceback
    traceback.print_exc()

# 测试4: 风险控制模块
print()
print("-"*60)
print("测试4: 风险控制模块")
print("-"*60)

try:
    from core.live.risk.controller import (
        RiskController, RiskRule, RiskLevel, RiskType,
        PositionSizeRule, DailyLossRule
    )

    # 创建风控控制器
    controller = RiskController()

    # 添加仓位大小规则
    position_rule = PositionSizeRule(
        max_position_value=1000000,
        max_single_position_pct=0.2,
    )
    controller.add_rule(position_rule)

    # 添加日损失规则
    loss_rule = DailyLossRule(max_daily_loss_pct=0.05)
    controller.add_rule(loss_rule)

    # 创建测试上下文
    context = {
        'positions': [
            {'symbol': '510300', 'market_value': 200000},
            {'symbol': '510500', 'market_value': 150000},
        ],
        'portfolio_value': 1000000,
        'daily_pnl': -20000,
    }

    # 执行检查
    results_list = controller.check_all(context)

    # 检查是否可交易
    can_trade = controller.can_trade(context)

    results['risk'] = len(results_list) > 0
    print(f"  [OK] RiskController created")
    print(f"  [OK] Rules added: {len(controller._rules)}")
    print(f"  [OK] Check results: {len(results_list)}")
    print(f"  [OK] Can trade: {can_trade}")

    # 统计信息
    stats = controller.get_statistics()
    print(f"  [OK] Stats: {stats['total_checks']} checks, {stats['passed']} passed")

except Exception as e:
    results['risk'] = False
    all_passed = False
    print(f"  [FAIL] {e}")
    import traceback
    traceback.print_exc()

# 汇总
print()
print("="*60)
passed = sum(results.values())
total = len(results)
print(f"测试结果: {passed}/{total} 通过")

for name, result in results.items():
    status = "[OK]" if result else "[FAIL]"
    print(f"  {status} {name}")

print()
if all_passed:
    print("Phase 4 验证通过！")
    sys.exit(0)
else:
    print("Phase 4 验证未完全通过")
    sys.exit(1)
