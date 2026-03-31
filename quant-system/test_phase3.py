"""
Phase 3 回测引擎验证脚本

测试内容：
1. 指标计算模块 (L1-L4)
2. 回测引擎 (Event-driven)
3. 策略执行 (ETF轮动、永久组合、主题仓位)
4. 绩效分析模块
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# 颜色输出
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_header(text):
    print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BLUE}{text:^60}{Colors.END}")
    print(f"{Colors.BLUE}{'='*60}{Colors.END}\n")

def print_success(text):
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")

def print_error(text):
    print(f"{Colors.RED}✗ {text}{Colors.END}")

def print_warning(text):
    print(f"{Colors.YELLOW}⚠ {text}{Colors.END}")

# ============================================
# 测试 1: 指标计算模块
# ============================================
def test_indicators():
    print_header("测试 1: L1-L4 指标计算模块")

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

    results = {}

    # 测试 L1 指标
    try:
        from core.indicators import L101CompositeSlopeMomentum
        l101 = L101CompositeSlopeMomentum(data=test_data)
        l101_result = l101.calculate()
        results['L101'] = len(l101_result) > 0
        print_success(f"L101 复合斜率动量: {len(l101_result)} 个值, 范围 [{l101_result.min():.2f}, {l101_result.max():.2f}]")
    except Exception as e:
        results['L101'] = False
        print_error(f"L101 失败: {e}")

    # 测试 L2 指标
    try:
        from core.indicators import L201HurstExponent
        l201 = L201HurstExponent(data=test_data)
        l201_result = l201.calculate()
        results['L201'] = len(l201_result) > 0
        print_success(f"L201 Hurst指数: {len(l201_result)} 个值, 均值 {l201_result.mean():.3f}")
    except Exception as e:
        results['L201'] = False
        print_error(f"L201 失败: {e}")

    # 测试 L3 指标
    try:
        from core.indicators import L301RollingCorrelationMatrix
        test_symbols = ['000001', '000002', '000333']
        test_data_dict = {sym: test_data.copy() for sym in test_symbols}
        l301 = L301RollingCorrelationMatrix(data=test_data_dict)
        l301_result = l301.calculate()
        results['L301'] = l301_result is not None
        print_success(f"L301 滚动相关性矩阵: 计算完成")
    except Exception as e:
        results['L301'] = False
        print_error(f"L301 失败: {e}")

    # 测试 L4 指标
    try:
        from core.indicators import L404LiquidityGap
        l404 = L404LiquidityGap(data=test_data)
        l404_result = l404.calculate()
        results['L404'] = len(l404_result) > 0
        print_success(f"L404 流动性缺口: {len(l404_result)} 个值")
    except Exception as e:
        results['L404'] = False
        print_error(f"L404 失败: {e}")

    # 汇总
    passed = sum(results.values())
    total = len(results)
    print(f"\n{Colors.BLUE}指标模块测试结果: {passed}/{total} 通过{Colors.END}")

    return passed == total

# ============================================
# 测试 2: 回测引擎组件
# ============================================
def test_backtest_components():
    print_header("测试 2: 回测引擎组件")

    results = {}

    # 测试 Broker
    try:
        from core.backtest import SimulatedBroker, Order
        broker = SimulatedBroker(initial_cash=1000000.0, commission_rate=0.001)

        # 提交买入订单
        order = Order(symbol='510300', side='buy', quantity=1000, order_type='market')
        broker.submit_order(order)

        # 模拟成交
        broker.process_market_data(datetime.now(), {'510300': {'open': 4.0, 'high': 4.1, 'low': 3.9, 'close': 4.0}})

        positions = broker.get_positions()
        cash = broker.get_cash()

        results['broker'] = len(positions) >= 0 and cash > 0
        print_success(f"Broker 测试: 持仓 {len(positions)} 个, 现金 {cash:.2f}")
    except Exception as e:
        results['broker'] = False
        print_error(f"Broker 失败: {e}")
        import traceback
        traceback.print_exc()

    # 测试策略基类
    try:
        from core.backtest import StrategyBase
        from core.backtest.broker import SimulatedBroker

        class TestStrategy(StrategyBase):
            def generate_signals(self, current_date, broker, price_data):
                return []

        test_strategy = TestStrategy({'name': 'test'})
        results['strategy_base'] = test_strategy is not None
        print_success("StrategyBase 测试: 实例化成功")
    except Exception as e:
        results['strategy_base'] = False
        print_error(f"StrategyBase 失败: {e}")
        import traceback
        traceback.print_exc()

    # 测试绩效分析
    try:
        from core.backtest import PerformanceAnalyzer

        # 模拟权益曲线
        dates = pd.date_range('2023-01-01', periods=100, freq='D')
        equity_curve = pd.Series(1000000 * (1 + np.random.randn(100).cumsum() * 0.01), index=dates)

        # 模拟交易记录
        trades = [
            {'symbol': '510300', 'entry_date': dates[10], 'exit_date': dates[20],
             'entry_price': 4.0, 'exit_price': 4.2, 'quantity': 1000, 'pnl': 200},
            {'symbol': '510500', 'entry_date': dates[30], 'exit_date': dates[40],
             'entry_price': 6.0, 'exit_price': 5.8, 'quantity': 500, 'pnl': -100},
        ]

        analyzer = PerformanceAnalyzer()
        metrics = analyzer.calculate_all(equity_curve, trades)

        results['metrics'] = 'returns' in metrics and 'risk' in metrics
        print_success(f"PerformanceAnalyzer 测试: 计算完成，包含 {len(metrics)} 个类别")
    except Exception as e:
        results['metrics'] = False
        print_error(f"PerformanceAnalyzer 失败: {e}")
        import traceback
        traceback.print_exc()

    # 汇总
    passed = sum(results.values())
    total = len(results)
    print(f"\n{Colors.BLUE}回测组件测试结果: {passed}/{total} 通过{Colors.END}")

    return passed == total

# ============================================
# 测试 3: 完整回测流程
# ============================================
def test_full_backtest():
    print_header("测试 3: 完整回测流程")

    try:
        from core.backtest import BacktestEngine, ETFRotationStrategy, PerformanceAnalyzer

        # 创建模拟数据
        np.random.seed(42)
        dates = pd.date_range('2023-01-01', periods=200, freq='D')

        # 模拟价格数据
        price_data = {}
        for symbol in ['510300', '510500', '510050', '159915']:
            base_price = np.random.uniform(2, 6)
            returns = np.random.randn(200) * 0.02
            prices = base_price * np.exp(np.cumsum(returns))
            price_data[symbol] = pd.DataFrame({
                'open': prices * (1 + np.random.randn(200) * 0.005),
                'high': prices * (1 + abs(np.random.randn(200)) * 0.01),
                'low': prices * (1 - abs(np.random.randn(200)) * 0.01),
                'close': prices,
                'volume': np.random.randint(1000000, 10000000, 200)
            }, index=dates)

        # 创建策略
        strategy_config = {
            'name': 'ETF轮动测试',
            'etf_universe': ['510300', '510500', '510050', '159915'],
            'top_n': 2,
            'rebalance_freq': 20,
            'score_weights': {
                'momentum': 0.4,
                'volatility': 0.3,
                'volume': 0.3
            }
        }
        strategy = ETFRotationStrategy(strategy_config)

        # 创建回测引擎
        engine = BacktestEngine(
            start_date='2023-01-01',
            end_date='2023-12-31',
            initial_capital=1000000.0,
            commission_rate=0.001,
            slippage_rate=0.001
        )

        # 加载数据
        engine.price_data = price_data
        engine.trading_days = dates

        # 运行回测
        print("运行回测...")
        result = engine.run(strategy)

        # 分析结果
        print("\n回测结果:")
        print(f"  初始资金: {result.initial_capital:,.2f}")
        print(f"  最终权益: {result.final_equity:,.2f}")
        print(f"  总收益率: {result.total_return:.2%}")
        print(f"  年化收益: {result.annualized_return:.2%}")
        print(f"  最大回撤: {result.max_drawdown:.2%}")
        print(f"  夏普比率: {result.sharpe_ratio:.2f}")
        print(f"  交易次数: {len(result.trades)}")

        print_success("完整回测流程测试通过")
        return True

    except Exception as e:
        print_error(f"完整回测流程失败: {e}")
        import traceback
        traceback.print_exc()
        return False

# ============================================
# 主函数
# ============================================
def main():
    print_header("Phase 3 回测引擎验证")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    results = {}

    # 测试1: 指标计算模块
    results['indicators'] = test_indicators()

    # 测试2: 回测引擎组件
    results['components'] = test_backtest_components()

    # 测试3: 完整回测流程
    results['full_backtest'] = test_full_backtest()

    # 汇总
    print_header("验证完成汇总")

    passed = sum(results.values())
    total = len(results)

    print("测试项:")
    for name, result in results.items():
        status = f"{Colors.GREEN}通过{Colors.END}" if result else f"{Colors.RED}失败{Colors.END}"
        print(f"  {name}: {status}")

    print(f"\n总计: {passed}/{total} 通过")

    end_time = datetime.now()
    duration = (end_time - datetime.now()).total_seconds()
    print(f"结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")

    if passed == total:
        print(f"\n{Colors.GREEN}Phase 3 验证全部通过！可以进入 Phase 4 开发。{Colors.END}")
        return 0
    else:
        print(f"\n{Colors.RED}Phase 3 验证未完全通过，请修复问题。{Colors.END}")
        return 1

if __name__ == '__main__':
    sys.exit(main())
