"""
数据适配器测试脚本
测试 mootdx 连接和数据获取功能
"""

import sys
sys.path.insert(0, 'f:/Claudeproject/quant-system')

from dashboard.data_adapter_v2 import DashboardDataAdapterV2
import pandas as pd

def test_data_adapter():
    """测试数据适配器各项功能"""

    print("=" * 60)
    print("数据适配器 v2 测试")
    print("=" * 60)

    # 1. 初始化适配器
    print("\n【1】初始化数据适配器...")
    adapter = DashboardDataAdapterV2()

    if adapter._connected:
        print("[OK] mootdx 连接成功")
    else:
        print("[FAIL] mootdx 连接失败，将使用模拟数据")

    # 2. 测试获取ETF价格数据
    print("\n【2】测试获取ETF价格数据...")
    test_etfs = ['510300', '510500', '159915', '518880']

    for code in test_etfs:
        print(f"\n  获取 {code} 数据...")
        df = adapter.get_etf_price_real(code, days=30)

        if df is not None and not df.empty:
            print(f"  [OK] 成功获取 {len(df)} 条数据")
            print(f"    日期范围: {df['date'].min()} ~ {df['date'].max()}")
            print(f"    最新收盘价: {df['close'].iloc[-1]:.2f}")
        else:
            print(f"  [FAIL] 获取失败或数据为空")

    # 3. 测试获取ETF列表
    print("\n【3】测试获取ETF列表...")
    etf_list = adapter.get_etf_list_real()

    if etf_list is not None and not etf_list.empty:
        print(f"[OK] 成功获取 {len(etf_list)} 个ETF")
        print(f"\n前10个ETF:")
        print(etf_list.head(10).to_string())
    else:
        print("[FAIL] 获取ETF列表失败，返回本地列表")

    # 4. 测试获取实时行情
    print("\n【4】测试获取实时行情...")
    quotes = adapter.get_realtime_quotes_real(test_etfs[:3])

    if quotes is not None and not quotes.empty:
        print(f"[OK] 成功获取 {len(quotes)} 条实时行情")
        print(f"\n行情数据:")
        print(quotes.to_string())
    else:
        print("[FAIL] 获取实时行情失败")

    # 5. 测试获取指数数据
    print("\n【5】测试获取指数数据...")
    index_codes = ['000001', '000300', '000905']

    for code in index_codes:
        print(f"\n  获取指数 {code} 数据...")
        df = adapter.get_index_data(code, days=20)

        if df is not None and not df.empty:
            print(f"  [OK] 成功获取 {len(df)} 条数据")
        else:
            print(f"  [FAIL] 获取失败")

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)

if __name__ == "__main__":
    test_data_adapter()
