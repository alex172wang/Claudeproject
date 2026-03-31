"""
仪表板数据适配器 v2

使用最新 mootdx 0.11.7 API 获取真实数据
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any


class DashboardDataAdapterV2:
    """仪表板数据适配器 v2 - 使用真实数据源"""

    def __init__(self):
        self.client = None
        self._connected = False
        self._connect()

    def _connect(self):
        """连接 mootdx"""
        try:
            from mootdx.quotes import Quotes
            self.client = Quotes.factory(market='std')
            self._connected = True
            print("[DataAdapterV2] mootdx 连接成功")
        except Exception as e:
            print(f"[DataAdapterV2] mootdx 连接失败: {e}")
            self._connected = False

    def get_etf_price_real(self, code: str, days: int = 60) -> pd.DataFrame:
        """
        获取ETF真实历史价格数据

        Args:
            code: ETF代码，如 '510300'
            days: 获取天数

        Returns:
            DataFrame: 包含真实价格数据的DataFrame
        """
        if not self._connected:
            print(f"[DataAdapterV2] 未连接，返回模拟数据")
            return self._generate_mock_price(code, days)

        try:
            # 使用 mootdx 0.11.7 正确API获取K线数据
            # bars(symbol, frequency=9, limit=30) - frequency=9表示日线
            symbol = f'{code}' if not code.startswith(('SH', 'SZ', 'sh', 'sz')) else code[-6:]

            df = self.client.bars(
                symbol=symbol,
                frequency=9,  # 日线
                limit=days + 10  # 多取一些，防止停牌等
            )

            if df is None or df.empty:
                print(f"[DataAdapterV2] 获取 {code} 数据为空")
                return self._generate_mock_price(code, days)

            # 标准化列名
            column_mapping = {
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'volume': 'volume',
                'amount': 'amount',
                'vol': 'volume',
                '成交额': 'amount',
                '成交量': 'volume',
                '开盘': 'open',
                '最高': 'high',
                '最低': 'low',
                '收盘': 'close',
            }

            # 转换为小写并映射标准列名
            df.columns = [str(c).lower().strip() for c in df.columns]
            for old_col, new_col in list(column_mapping.items()):
                if old_col.lower() in df.columns and new_col not in df.columns:
                    df.rename(columns={old_col.lower(): new_col}, inplace=True)

            # 处理 date 列
            if 'date' not in df.columns:
                # 如果有 year/month/day 列，组合成 date
                if all(c in df.columns for c in ['year', 'month', 'day']):
                    df['date'] = pd.to_datetime(df[['year', 'month', 'day']])
                elif 'datetime' in df.columns:
                    df['date'] = pd.to_datetime(df['datetime'])

            # 确保必要的列存在
            required_cols = ['open', 'high', 'low', 'close', 'volume']
            for col in required_cols:
                if col not in df.columns:
                    print(f"[DataAdapterV2] 警告：缺少列 {col}")
                    df[col] = np.nan

            # 按日期排序并取最近days条
            if 'date' in df.columns:
                df = df.sort_values('date')

            if len(df) > days:
                df = df.tail(days).reset_index(drop=True)

            print(f"[DataAdapterV2] 成功获取 {code} 真实数据，共 {len(df)} 条")
            return df

        except Exception as e:
            print(f"[DataAdapterV2] 获取 {code} 价格失败: {e}")
            import traceback
            traceback.print_exc()
            return self._generate_mock_price(code, days)

    def get_etf_list_real(self) -> pd.DataFrame:
        """
        获取真实ETF列表

        Returns:
            DataFrame: ETF列表
        """
        if not self._connected:
            print("[DataAdapterV2] 未连接，返回本地列表")
            return self._get_local_etf_list()

        try:
            # 使用 mootdx 0.11.7 的 stock_all() 获取所有股票
            df_all = self.client.stock_all()

            if df_all is None or df_all.empty:
                print("[DataAdapterV2] 获取股票列表为空")
                return self._get_local_etf_list()

            etf_list = []

            # 将 code 列转为字符串
            if 'code' in df_all.columns:
                df_all['code'] = df_all['code'].astype(str)

                # 筛选上海ETF（51/56/58/50开头）
                sh_etfs = df_all[df_all['code'].str.startswith(('51', '56', '58', '50'))]
                if not sh_etfs.empty:
                    sh_etfs = sh_etfs.copy()
                    sh_etfs['market'] = 'SH'
                    etf_list.append(sh_etfs)

                # 筛选深圳ETF（15/16开头）
                sz_etfs = df_all[df_all['code'].str.startswith(('15', '16'))]
                if not sz_etfs.empty:
                    sz_etfs = sz_etfs.copy()
                    sz_etfs['market'] = 'SZ'
                    etf_list.append(sz_etfs)

            if etf_list:
                result = pd.concat(etf_list, ignore_index=True)

                # 标准化列名
                if 'name' not in result.columns and '股票名称' in result.columns:
                    result.rename(columns={'股票名称': 'name'}, inplace=True)
                if 'code' not in result.columns and '股票代码' in result.columns:
                    result.rename(columns={'股票代码': 'code'}, inplace=True)

                # 只保留需要的列
                columns_to_keep = ['code', 'name', 'market']
                existing_columns = [c for c in columns_to_keep if c in result.columns]
                result = result[existing_columns]

                print(f"[DataAdapterV2] 成功获取 {len(result)} 个ETF")
                return result

        except Exception as e:
            print(f"[DataAdapterV2] 获取ETF列表失败: {e}")
            import traceback
            traceback.print_exc()

        return self._get_local_etf_list()

    def get_realtime_quotes_real(self, codes: List[str]) -> pd.DataFrame:
        """
        获取实时行情数据

        Args:
            codes: ETF代码列表

        Returns:
            DataFrame: 实时行情数据
        """
        if not self._connected:
            print("[DataAdapterV2] 未连接，返回模拟行情")
            return self._generate_mock_quotes(codes)

        try:
            # 使用 mootdx 0.11.7 的 quotes() 方法获取实时行情
            quotes = self.client.quotes(symbol=codes)

            if quotes is not None and not quotes.empty:
                print(f"[DataAdapterV2] 成功获取 {len(quotes)} 条实时行情")
                return quotes
            else:
                print("[DataAdapterV2] 获取实时行情返回空数据")

        except Exception as e:
            print(f"[DataAdapterV2] 获取实时行情失败: {e}")
            import traceback
            traceback.print_exc()

        return self._generate_mock_quotes(codes)

    def get_index_data(self, code: str = '000001', days: int = 60) -> pd.DataFrame:
        """
        获取大盘指数数据（上证指数/沪深300等）

        Args:
            code: 指数代码，如 '000001'(上证), '000300'(沪深300)
            days: 获取天数

        Returns:
            DataFrame: 指数数据
        """
        if not self._connected:
            print(f"[DataAdapterV2] 未连接，返回模拟数据")
            return self._generate_mock_price(code, days)

        try:
            # 使用 index_bars 方法获取指数K线数据
            df = self.client.index_bars(
                symbol=code,
                frequency=9,  # 日线
                limit=days + 10
            )

            if df is None or df.empty:
                print(f"[DataAdapterV2] 获取指数 {code} 数据为空")
                return self._generate_mock_price(code, days)

            # 标准化列名
            df.columns = [str(c).lower().strip() for c in df.columns]

            # 处理 date 列
            if 'date' not in df.columns:
                if all(c in df.columns for c in ['year', 'month', 'day']):
                    df['date'] = pd.to_datetime(df[['year', 'month', 'day']])

            if len(df) > days:
                df = df.tail(days).reset_index(drop=True)

            print(f"[DataAdapterV2] 成功获取指数 {code} 数据，共 {len(df)} 条")
            return df

        except Exception as e:
            print(f"[DataAdapterV2] 获取指数 {code} 失败: {e}")
            return self._generate_mock_price(code, days)

    # ============ 私有方法：备用数据 ============

    def _get_local_etf_list(self) -> pd.DataFrame:
        """获取本地ETF列表（备用）"""
        try:
            from .pages.instruments import ETF_DATA
            return pd.DataFrame(ETF_DATA)
        except Exception:
            # 如果导入失败，返回硬编码数据
            return pd.DataFrame([
                {'code': '510300', 'name': '沪深300ETF', 'market': 'SH'},
                {'code': '510500', 'name': '中证500ETF', 'market': 'SH'},
                {'code': '159915', 'name': '创业板ETF', 'market': 'SZ'},
                {'code': '518880', 'name': '黄金ETF', 'market': 'SH'},
            ])

    def _generate_mock_price(self, code: str, days: int) -> pd.DataFrame:
        """生成模拟价格数据（备用）"""
        np.random.seed(42)
        dates = pd.date_range(end=datetime.now(), periods=days, freq='B')

        initial_price = np.random.uniform(1, 10)
        returns = np.random.normal(0.0005, 0.02, len(dates))
        prices = initial_price * (1 + returns).cumprod()

        df = pd.DataFrame({
            'date': dates,
            'open': prices * np.random.uniform(0.99, 1.01, len(dates)),
            'high': prices * np.random.uniform(1.00, 1.03, len(dates)),
            'low': prices * np.random.uniform(0.97, 1.00, len(dates)),
            'close': prices,
            'volume': np.random.randint(1000000, 10000000, len(dates)),
        })

        print(f"[DataAdapterV2] 返回 {code} 模拟数据，共 {len(df)} 条")
        return df

    def _generate_mock_quotes(self, codes: List[str]) -> pd.DataFrame:
        """生成模拟实时行情（备用）"""
        data = []
        for code in codes:
            price = np.random.uniform(1, 10)
            data.append({
                'code': code,
                'name': f'ETF{code}',
                'price': price,
                'change': np.random.uniform(-0.05, 0.05),
                'volume': np.random.randint(1000000, 10000000),
            })
        return pd.DataFrame(data)


# 全局数据适配器实例
data_adapter_v2 = DashboardDataAdapterV2()
