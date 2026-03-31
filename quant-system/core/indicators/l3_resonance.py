"""
L3 共振层指标实现

包含：
- L3-01: 滚动相关性矩阵
- L3-02: 相关性变速
- L3-03: PCA第一主成分解释率
- L3-04: 跨市场动量一致性
- L3-05: 宏观-资产共振度
- L3-06: 板块轮动速度
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List

from .base import (
    BaseIndicator, IndicatorRegistry, IndicatorResult, IndicatorValue,
    normalize_score, hurst_exponent
)


@IndicatorRegistry.register
class L301RollingCorrelationMatrix(BaseIndicator):
    """
    L3-01: 滚动相关性矩阵

    计算多个资产间的滚动相关性，用于识别市场内部相关性结构变化
    """

    INDICATOR_ID = 'L3-01'
    INDICATOR_NAME = '滚动相关性矩阵'
    LAYER = 'L3'

    DEFAULT_PARAMS = {
        'window': 60,
    }

    def calculate(self, data: Dict[str, pd.DataFrame]) -> 'IndicatorResult':
        """
        计算滚动相关性矩阵

        Args:
            data: 多资产数据字典 {symbol: DataFrame}
        """
        params = self.params

        # 构建收益率矩阵
        returns_df = pd.DataFrame()
        for symbol, df in data.items():
            returns_df[symbol] = df['close'].pct_change()

        returns_df = returns_df.dropna()

        if len(returns_df) < params['window']:
            current_value = self._create_error_value('数据不足')
            return IndicatorResult(
                indicator_id=self.INDICATOR_ID,
                indicator_name=self.INDICATOR_NAME,
                layer=self.LAYER,
                current=current_value,
                params=params,
            )

        # 计算滚动相关性矩阵
        recent_returns = returns_df.iloc[-params['window']:]
        corr_matrix = recent_returns.corr()

        # 计算平均相关性（排除对角线）
        avg_corr = 0
        count = 0
        for i in range(len(corr_matrix.columns)):
            for j in range(i+1, len(corr_matrix.columns)):
                avg_corr += corr_matrix.iloc[i, j]
                count += 1

        avg_corr = avg_corr / count if count > 0 else 0

        # 归一化得分（相关性0-1映射到0-100，中等相关性最好）
        # 太高或太低都不好，中等(0.3-0.5)最好
        if avg_corr < 0.3:
            normalized_score = normalize_score(avg_corr, 0, 0.3, reverse=False)
        elif avg_corr > 0.5:
            normalized_score = normalize_score(avg_corr, 0.5, 0.8, reverse=True)
        else:
            normalized_score = 100

        # 信号方向
        if avg_corr > 0.7:
            signal = -1  # 高度相关，系统性风险
        elif avg_corr < 0.1:
            signal = -1  # 极度分散，可能无效
        else:
            signal = 1

        current_value = IndicatorValue(
            value=avg_corr,
            raw_score=avg_corr,
            normalized_score=normalized_score,
            signal=signal,
            metadata={
                'avg_correlation': avg_corr,
                'corr_matrix_shape': corr_matrix.shape,
            }
        )

        return IndicatorResult(
            indicator_id=self.INDICATOR_ID,
            indicator_name=self.INDICATOR_NAME,
            layer=self.LAYER,
            current=current_value,
            params=params,
        )

    def _create_error_value(self, error_msg: str) -> 'IndicatorValue':
        return IndicatorValue(
            value=0.0,
            raw_score=0.0,
            normalized_score=50.0,
            signal=0,
            metadata={'error': error_msg}
        )


@IndicatorRegistry.register
class L302CorrelationVelocity(BaseIndicator):
    """
    L3-02: 相关性变速

    相关性随时间的变化速率，识别相关性结构的快速变化
    """

    INDICATOR_ID = 'L3-02'
    INDICATOR_NAME = '相关性变速'
    LAYER = 'L3'

    DEFAULT_PARAMS = {
        'window': 60,
        'velocity_window': 20,
    }

    def calculate(self, data: Dict[str, pd.DataFrame]) -> 'IndicatorResult':
        params = self.params

        # 构建收益率矩阵
        returns_df = pd.DataFrame()
        for symbol, df in data.items():
            returns_df[symbol] = df['close'].pct_change()

        returns_df = returns_df.dropna()

        if len(returns_df) < params['window'] + params['velocity_window']:
            current_value = self._create_error_value('数据不足')
            return IndicatorResult(
                indicator_id=self.INDICATOR_ID,
                indicator_name=self.INDICATOR_NAME,
                layer=self.LAYER,
                current=current_value,
                params=params,
            )

        # 计算滚动相关性序列
        corr_series = []
        for i in range(params['window'], len(returns_df)):
            window_returns = returns_df.iloc[i-params['window']:i]
            corr_matrix = window_returns.corr()
            # 取平均非对角线相关性
            avg_corr = 0
            count = 0
            for j in range(len(corr_matrix.columns)):
                for k in range(j+1, len(corr_matrix.columns)):
                    avg_corr += corr_matrix.iloc[j, k]
                    count += 1
            corr_series.append(avg_corr / count if count > 0 else 0)

        corr_series = pd.Series(corr_series)

        # 计算相关性变速
        velocity = corr_series.diff().rolling(window=params['velocity_window']).std().iloc[-1]

        # 归一化
        normalized_score = normalize_score(velocity, 0, 0.5, reverse=True)

        signal = -1 if velocity > 0.3 else (1 if velocity < 0.1 else 0)

        current_value = IndicatorValue(
            value=velocity,
            raw_score=velocity,
            normalized_score=normalized_score,
            signal=signal,
            metadata={'velocity': velocity, 'avg_correlation_history': corr_series.tolist()[-20:]}
        )

        return IndicatorResult(
            indicator_id=self.INDICATOR_ID,
            indicator_name=self.INDICATOR_NAME,
            layer=self.LAYER,
            current=current_value,
            params=params,
        )

    def _create_error_value(self, error_msg: str) -> 'IndicatorValue':
        return IndicatorValue(
            value=0.0,
            raw_score=0.0,
            normalized_score=50.0,
            signal=0,
            metadata={'error': error_msg}
        )


@IndicatorRegistry.register
class L303PCAExplainedVariance(BaseIndicator):
    """
    L3-03: PCA第一主成分解释率

    使用主成分分析识别市场的主导驱动因子
    """

    INDICATOR_ID = 'L3-03'
    INDICATOR_NAME = 'PCA解释方差率'
    LAYER = 'L3'

    DEFAULT_PARAMS = {
        'window': 60,
    }

    def calculate(self, data: Dict[str, pd.DataFrame]) -> 'IndicatorResult':
        try:
            from sklearn.decomposition import PCA
        except ImportError:
            current_value = IndicatorValue(
                value=0.5,
                raw_score=0.5,
                normalized_score=50.0,
                signal=0,
                metadata={'note': 'sklearn未安装，使用默认值'}
            )
            return IndicatorResult(
                indicator_id=self.INDICATOR_ID,
                indicator_name=self.INDICATOR_NAME,
                layer=self.LAYER,
                current=current_value,
                params=self.params,
            )

        params = self.params

        # 构建收益率矩阵
        returns_df = pd.DataFrame()
        for symbol, df in data.items():
            returns_df[symbol] = df['close'].pct_change()

        returns_df = returns_df.dropna()

        if len(returns_df) < params['window']:
            current_value = IndicatorValue(
                value=0.5,
                raw_score=0.5,
                normalized_score=50.0,
                signal=0,
                metadata={'error': '数据不足'}
            )
            return IndicatorResult(
                indicator_id=self.INDICATOR_ID,
                indicator_name=self.INDICATOR_NAME,
                layer=self.LAYER,
                current=current_value,
                params=params,
            )

        # 使用最近window数据
        recent_returns = returns_df.iloc[-params['window']:]

        # 标准化
        standardized = (recent_returns - recent_returns.mean()) / recent_returns.std()
        standardized = standardized.fillna(0)

        # PCA
        pca = PCA(n_components=min(5, len(standardized.columns)))
        pca.fit(standardized)

        # 第一主成分解释率
        explained_variance_ratio = pca.explained_variance_ratio_[0]

        # 归一化（解释率0.3-0.8为最佳）
        if explained_variance_ratio < 0.3:
            normalized_score = normalize_score(explained_variance_ratio, 0, 0.3, reverse=False)
        elif explained_variance_ratio > 0.8:
            normalized_score = normalize_score(explained_variance_ratio, 0.8, 0.95, reverse=True)
        else:
            normalized_score = 100

        signal = 1 if 0.3 < explained_variance_ratio < 0.7 else (-1 if explained_variance_ratio > 0.8 else 0)

        current_value = IndicatorValue(
            value=explained_variance_ratio,
            raw_score=explained_variance_ratio,
            normalized_score=normalized_score,
            signal=signal,
            metadata={
                'explained_variance': explained_variance_ratio,
                'components': len(pca.components_),
            }
        )

        return IndicatorResult(
            indicator_id=self.INDICATOR_ID,
            indicator_name=self.INDICATOR_NAME,
            layer=self.LAYER,
            current=current_value,
            params=params,
        )


@IndicatorRegistry.register
class L304CrossMarketConsistency(BaseIndicator):
    """
    L3-04: 跨市场动量一致性

    股票、债券、商品、外汇等市场的动量方向一致性
    """

    INDICATOR_ID = 'L3-04'
    INDICATOR_NAME = '跨市场动量一致性'
    LAYER = 'L3'

    DEFAULT_PARAMS = {
        'window': 20,
        'momentum_lookback': 20,
    }

    def calculate(self, data: Dict[str, pd.DataFrame]) -> 'IndicatorResult':
        params = self.params

        # 计算各资产的动量
        momentums = {}
        for symbol, df in data.items():
            if len(df) < params['momentum_lookback']:
                continue
            recent_return = (df['close'].iloc[-1] / df['close'].iloc[-params['momentum_lookback']] - 1)
            momentums[symbol] = recent_return

        if len(momentums) < 2:
            current_value = IndicatorValue(
                value=0.5,
                raw_score=0.5,
                normalized_score=50.0,
                signal=0,
                metadata={'error': '资产数据不足'}
            )
            return IndicatorResult(
                indicator_id=self.INDICATOR_ID,
                indicator_name=self.INDICATOR_NAME,
                layer=self.LAYER,
                current=current_value,
                params=params,
            )

        # 计算动量的一致性（同方向的比例）
        momentum_values = list(momentums.values())
        positive_count = sum(1 for m in momentum_values if m > 0)
        total = len(momentum_values)

        # 一致性 = max(正比例, 负比例)
        consistency = max(positive_count / total, (total - positive_count) / total)

        # 归一化（0.5-1.0映射到0-100，但中等一致性最好）
        if consistency > 0.8:
            normalized_score = normalize_score(consistency, 1.0, 0.8, reverse=True)
        elif consistency < 0.5:
            normalized_score = normalize_score(consistency, 0.5, 0.3, reverse=False)
        else:
            normalized_score = 100

        signal = 1 if 0.5 < consistency < 0.8 else (-1 if consistency > 0.9 else 0)

        current_value = IndicatorValue(
            value=consistency,
            raw_score=consistency,
            normalized_score=normalized_score,
            signal=signal,
            metadata={
                'consistency': consistency,
                'positive_momentum': positive_count,
                'total_assets': total,
                'momentums': momentums,
            }
        )

        return IndicatorResult(
            indicator_id=self.INDICATOR_ID,
            indicator_name=self.INDICATOR_NAME,
            layer=self.LAYER,
            current=current_value,
            params=params,
        )


@IndicatorRegistry.register
class L305MacroAssetResonance(BaseIndicator):
    """
    L3-05: 宏观-资产共振度

    FRED指标（10Y利率、CPI、PMI）与资产收益的滚动相关
    用于识别宏观因子对资产的影响程度
    """

    INDICATOR_ID = 'L3-05'
    INDICATOR_NAME = '宏观-资产共振度'
    LAYER = 'L3'

    DEFAULT_PARAMS = {
        'window': 90,
        'macro_indicators': ['GS10', 'CPIAUCSL', 'PMI'],
    }

    def calculate(self, data: pd.DataFrame, macro_data: Optional[pd.DataFrame] = None) -> IndicatorResult:
        """
        计算宏观-资产共振度

        Args:
            data: 资产价格数据
            macro_data: 宏观数据DataFrame（列为宏观指标）
        """
        params = self.params
        close = data['close']

        # 计算资产收益率
        asset_returns = close.pct_change().dropna()

        # 如果没有提供宏观数据，使用代理数据
        if macro_data is None:
            # 使用价格数据的移动平均作为代理
            normalized_price = (close - close.rolling(window=params['window']).mean()) / close.rolling(window=params['window']).std()
            macro_proxy = normalized_price.pct_change().dropna()

            # 计算简单的相关性
            if len(asset_returns) >= params['window'] and len(macro_proxy) >= params['window']:
                corr = asset_returns.iloc[-params['window']:].corr(macro_proxy.iloc[-params['window']:])
                avg_resonance = abs(corr) if not pd.isna(corr) else 0.0
            else:
                avg_resonance = 0.0

            status = 'partial'
            error_msg = '宏观数据未提供，使用价格代理'
        else:
            # 计算与各宏观指标的相关性
            correlations = []
            for col in macro_data.columns:
                if col in params['macro_indicators']:
                    macro_returns = macro_data[col].pct_change().dropna()

                    # 对齐时间序列
                    common_idx = asset_returns.index.intersection(macro_returns.index)
                    if len(common_idx) >= params['window']:
                        asset_aligned = asset_returns.loc[common_idx]
                        macro_aligned = macro_returns.loc[common_idx]

                        # 计算滚动相关性
                        corr = asset_aligned.iloc[-params['window']:].corr(macro_aligned.iloc[-params['window']:])
                        correlations.append(abs(corr) if not pd.isna(corr) else 0.0)

            avg_resonance = np.mean(correlations) if correlations else 0.0
            status = 'success'
            error_msg = ''

        # 归一化得分（共振度0-0.8映射到0-100）
        # 共振度太高表示资产被宏观因子主导（系统性风险），得低分
        normalized_score = normalize_score(avg_resonance, 0.0, 0.8, reverse=True)

        # 信号方向
        if avg_resonance > 0.6:
            signal = -1  # 高度共振，系统性风险
        elif avg_resonance < 0.2:
            signal = 1  # 低共振，独立性强
        else:
            signal = 0

        current_value = IndicatorValue(
            value=avg_resonance,
            raw_score=avg_resonance,
            normalized_score=normalized_score,
            signal=signal,
            metadata={
                'avg_resonance': avg_resonance,
                'correlations_count': len(correlations) if 'correlations' in locals() else 0,
                'note': error_msg if error_msg else '宏观-资产共振度',
            }
        )

        result = IndicatorResult(
            indicator_id=self.INDICATOR_ID,
            indicator_name=self.INDICATOR_NAME,
            layer=self.LAYER,
            current=current_value,
            params=params,
        )
        result.status = status
        result.error_message = error_msg

        return result


@IndicatorRegistry.register
class L306RotationSpeed(BaseIndicator):
    """
    L3-06: 板块轮动速度

    候选池内排名变化的标准差（排名越稳定，轮动越慢）
    用于识别市场风格轮动速度
    """

    INDICATOR_ID = 'L3-06'
    INDICATOR_NAME = '板块轮动速度'
    LAYER = 'L3'

    DEFAULT_PARAMS = {
        'rolling_weeks': 4,
        'rank_period': 20,
    }

    def calculate(self, data: pd.DataFrame) -> IndicatorResult:
        """
        计算板块轮动速度

        Args:
            data: DataFrame，列为不同资产，行为时间序列
        """
        params = self.params

        # 计算收益率
        returns = data.pct_change().dropna()

        if len(returns) < params['rank_period'] * params['rolling_weeks']:
            # 数据不足
            current_value = IndicatorValue(
                value=0.0,
                raw_score=0.0,
                normalized_score=50.0,
                signal=0,
                metadata={'error': '数据不足'}
            )
            return IndicatorResult(
                indicator_id=self.INDICATOR_ID,
                indicator_name=self.INDICATOR_NAME,
                layer=self.LAYER,
                current=current_value,
                params=params,
            )

        # 计算滚动排名
        rank_std = []
        for i in range(len(returns) - params['rank_period'] + 1):
            period_returns = returns.iloc[i:i+params['rank_period']]
            # 累计收益率排名
            cumulative_returns = (1 + period_returns).prod() - 1
            ranks = cumulative_returns.rank()
            rank_std.append(ranks.std())

        rank_std_series = pd.Series(rank_std)

        # 计算最近rolling_weeks的排名变化标准差
        if len(rank_std_series) >= params['rolling_weeks']:
            recent_rank_std = rank_std_series.iloc[-params['rolling_weeks']:].mean()
        else:
            recent_rank_std = rank_std_series.mean()

        # 归一化得分（轮动速度0-2映射到0-100）
        # 轮动太快（高分）或太慢（低分）都不好，中间最好
        # 这里我们映射：快速轮动（2.0）= 0分，稳定（0.5）= 100分，极慢（0）= 50分
        if recent_rank_std >= 1.0:
            normalized_score = normalize_score(recent_rank_std, 2.0, 1.0, reverse=True)
        else:
            normalized_score = 50 + (recent_rank_std / 1.0) * 50

        normalized_score = max(0, min(100, normalized_score))

        # 信号方向
        if recent_rank_std > 1.5:
            signal = -1  # 轮动太快，风格混乱
        elif recent_rank_std < 0.3:
            signal = -1  # 轮动太慢，风格僵化
        else:
            signal = 1  # 轮动适中，风格清晰

        current_value = IndicatorValue(
            value=recent_rank_std,
            raw_score=recent_rank_std,
            normalized_score=normalized_score,
            signal=signal,
            metadata={
                'rotation_speed': recent_rank_std,
                'rank_std_series': rank_std_series.tolist()[-10:] if len(rank_std_series) > 10 else rank_std_series.tolist(),
            }
        )

        return IndicatorResult(
            indicator_id=self.INDICATOR_ID,
            indicator_name=self.INDICATOR_NAME,
            layer=self.LAYER,
            current=current_value,
            params=params,
        )
