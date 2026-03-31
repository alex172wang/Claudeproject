"""
回测引擎使用示例

演示如何使用回测引擎进行策略回测
"""

import sys
sys.path.insert(0, 'f:\\Claudeproject\\quant-system')

from datetime import datetime
import pandas as pd
import numpy as np

from core.backtest import (
    BacktestEngine,
    BacktestConfig,
    ETFRotationStrategy,
    PermanentPortfolioStrategy,
    ThematicStrategy
)


def create_mock_data(symbols: list, start_date: str, end_date: str) -> dict:
    """
    创建模拟价格数据（用于测试）

    实际使用时，应该调用真实的数据加载器
    """
    data = {}
    dates = pd.date_range(start_date, end_date, freq='B')  # 工作日

    np.random.seed(42)

    for symbol in symbols:
        # 为每个品种生成不同的收益率特征
        base_return = np.random.normal(0.0002, 0.015, len(dates))

        # 添加一些趋势
        trend = np.linspace(0, 0.1, len(dates))

        # 计算价格
        returns = base_return + trend * 0.001
        price = 100 * (1 + returns).cumprod()

        # 创建OHLCV数据
        df = pd.DataFrame({
            'open': price * (1 + np.random.normal(0, 0.001, len(dates))),
            'high': price * (1 + abs(np.random.normal(0, 0.01, len(dates)))),
            'low': price * (1 - abs(np.random.normal(0, 0.01, len(dates)))),
            'close': price,
            'volume': np.random.randint(1000000, 10000000, len(dates))
        }, index=dates)

        data[symbol] = df

    return data


def run_etf_rotation_backtest():
    """运行ETF轮动策略回测"""
    print("="*60)
    print("ETF轮动策略回测")
    print("="*60)

    # 回测配置
    config = BacktestConfig(
        start_date='2023-01-01',
        end_date='2023-12-31',
        initial_capital=1000000.0,
        commission_rate=0.001,
        slippage_rate=0.001
    )

    # 创建回测引擎
    engine = BacktestEngine(config)

    # 加载数据
    symbols = ['159920', '513500', '518880', '159949']  # 恒生、标普、黄金、创业板

    def data_loader(symbol, start, end):
        # 这里应该调用真实的数据加载器
        # 现在使用模拟数据
        all_data = create_mock_data(symbols, start, end)
        return all_data.get(symbol)

    engine.load_data(symbols, data_loader)

    # 创建策略
    strategy_config = {
        'etf_universe': symbols,
        'top_n': 2,
        'min_score': 50,
        'rebalance_freq': 'weekly',
        'weight_method': 'equal'
    }
    strategy = ETFRotationStrategy(strategy_config)

    # 运行回测
    result = engine.run(strategy)

    return result


def run_permanent_portfolio_backtest():
    """运行永久组合策略回测"""
    print("\n" + "="*60)
    print("永久组合策略回测")
    print("="*60)

    config = BacktestConfig(
        start_date='2023-01-01',
        end_date='2023-12-31',
        initial_capital=1000000.0
    )

    engine = BacktestEngine(config)

    symbols = ['510300', '511010', '518880', '511880']

    def data_loader(symbol, start, end):
        all_data = create_mock_data(symbols, start, end)
        return all_data.get(symbol)

    engine.load_data(symbols, data_loader)

    strategy = PermanentPortfolioStrategy()
    result = engine.run(strategy)

    return result


def compare_strategies():
    """对比不同策略的表现"""
    results = {}

    try:
        results['ETF轮动'] = run_etf_rotation_backtest()
    except Exception as e:
        print(f"ETF轮动策略回测失败: {e}")

    try:
        results['永久组合'] = run_permanent_portfolio_backtest()
    except Exception as e:
        print(f"永久组合策略回测失败: {e}")

    # 对比结果
    print("\n" + "="*60)
    print("策略对比")
    print("="*60)

    comparison_data = []
    for name, result in results.items():
        comparison_data.append({
            '策略': name,
            '总收益': f"{result.total_return*100:.2f}%",
            '年化收益': f"{result.annual_return*100:.2f}%",
            '最大回撤': f"{result.max_drawdown*100:.2f}%",
            '夏普比率': f"{result.sharpe_ratio:.2f}",
            '交易次数': len(result.trades)
        })

    comparison_df = pd.DataFrame(comparison_data)
    print(comparison_df.to_string(index=False))

    return results


if __name__ == '__main__':
    # 运行策略对比
    results = compare_strategies()

    # 保存结果示例
    if results:
        for name, result in results.items():
            # 保存为JSON
            safe_name = name.replace('/', '_')
            result.save(f'backtest_result_{safe_name}.json')
            print(f"\n{name} 结果已保存")
