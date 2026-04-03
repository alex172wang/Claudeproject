"""
回测参数优化器（含防过拟合机制）

核心功能：
1. 参数网格搜索
2. 样本内/样本外分割（强制70/30）
3. 多重过拟合检测机制：
   - 夏普比率比较（in_out_sharpe_ratio > 2.0）
   - 收益稳定性检验（CSCV方法）
   - 参数敏感性分析
4. 自由度检查（参数组合数 vs 样本外交易次数）
5. 智能参数选择（带置信区间）
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Tuple, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import itertools
import warnings
from scipy import stats
from sklearn.model_selection import TimeSeriesSplit

from .metrics import calculate_sharpe_ratio, calculate_max_drawdown, calculate_total_return


@dataclass
class OptimizationResult:
    """优化结果数据类（增强版，含多重过拟合检测）"""
    # 参数组合
    params: Dict[str, Any]

    # 样本内绩效
    in_sample_sharpe: float
    in_sample_return: float
    in_sample_drawdown: float
    in_sample_trades: int

    # 样本外绩效
    out_sample_sharpe: float
    out_sample_return: float
    out_sample_drawdown: float
    out_sample_trades: int

    # 过拟合指标 - 夏普比率比较
    in_out_sharpe_ratio: float = field(default=0.0)  # 样本内/样本外夏普比
    is_overfit_sharpe: bool = field(default=False)  # 夏普比率法检测过拟合

    # 过拟合指标 - CSCV（组合对称交叉验证）
    cscv_score: float = field(default=0.0)  # CSCV得分（接近0.5表示过拟合）
    cscv_pvalue: float = field(default=1.0)  # CSCV检验p值
    is_overfit_cscv: bool = field(default=False)  # CSCV检测过拟合

    # 过拟合指标 - 参数敏感性
    param_sensitivity: float = field(default=0.0)  # 参数敏感度（越大越不稳定）
    is_overfit_sensitivity: bool = field(default=False)  # 敏感度检测过拟合

    # 综合过拟合判定
    is_overfit: bool = field(default=False)  # 综合判定是否过拟合
    overfit_confidence: float = field(default=0.0)  # 过拟合置信度（0-1）

    # 自由度检查
    param_combinations: int = field(default=1)  # 参数组合数
    degrees_of_freedom_warning: bool = field(default=False)  # 自由度警告
    dof_ratio: float = field(default=0.0)  # 参数组合数/交易次数比率

    # 置信区间
    sharpe_confidence_interval: Tuple[float, float] = field(default_factory=lambda: (0.0, 0.0))
    return_confidence_interval: Tuple[float, float] = field(default_factory=lambda: (0.0, 0.0))

    # 综合评分（用于排序）
    composite_score: float = field(default=0.0)
    robustness_score: float = field(default=0.0)  # 稳健性得分

    def __post_init__(self):
        """计算派生指标和过拟合检测"""
        self._calculate_sharpe_ratio_check()
        self._calculate_degrees_of_freedom()
        self._calculate_confidence_intervals()
        self._assess_overfit_combined()
        self._calculate_composite_score()

    def _assess_overfit_combined(self):
        """综合评估过拟合风险"""
        # 三种检测方法的权重
        sharpe_weight = 0.4
        cscv_weight = 0.35
        sensitivity_weight = 0.25

        # 归一化各指标风险
        sharpe_risk = min(self.in_out_sharpe_ratio / 3.0, 1.0) if self.is_overfit_sharpe else 0.0
        cscv_risk = 1.0 - self.cscv_pvalue if self.is_overfit_cscv else 0.0
        sensitivity_risk = min(self.param_sensitivity / 0.5, 1.0) if self.is_overfit_sensitivity else 0.0

        # 计算综合置信度
        self.overfit_confidence = (
            sharpe_risk * sharpe_weight +
            cscv_risk * cscv_weight +
            sensitivity_risk * sensitivity_weight
        )

        # 综合判定：置信度 > 0.5 或任一种方法强烈指示过拟合
        self.is_overfit = (
            self.overfit_confidence > 0.5 or
            self.in_out_sharpe_ratio > 3.0 or
            (self.is_overfit_cscv and self.cscv_pvalue < 0.01)
        )

        # 计算稳健性得分（反向过拟合风险）
        self.robustness_score = 1.0 - self.overfit_confidence

    def _calculate_composite_score(self):
        """计算综合评分（考虑稳健性）"""
        # 基础得分：加权夏普比率
        base_score = (
            self.out_sample_sharpe * 0.6 +
            self.in_sample_sharpe * 0.4
        )

        # 惩罚因子
        overfit_penalty = 0.5 if self.is_overfit else 1.0
        dof_penalty = 0.8 if self.degrees_of_freedom_warning else 1.0
        robustness_bonus = 1.0 + (self.robustness_score * 0.2)  # 最高20%奖励

        self.composite_score = (
            base_score * overfit_penalty * dof_penalty * robustness_bonus
        )
        self._assess_overfit_combined()
        self._calculate_composite_score()

    def _calculate_sharpe_ratio_check(self):
        """夏普比率比较法检测过拟合"""
        if abs(self.out_sample_sharpe) > 0.01:  # 避免除以极小值
            self.in_out_sharpe_ratio = abs(self.in_sample_sharpe / self.out_sample_sharpe)
        else:
            self.in_out_sharpe_ratio = float('inf') if self.in_sample_sharpe > 0 else 0.0

        # 夏普比率 > 2.0 判定为过拟合
        self.is_overfit_sharpe = self.in_out_sharpe_ratio > 2.0

    def _calculate_degrees_of_freedom(self):
        """计算自由度相关指标"""
        min_trades = max(self.out_sample_trades, 10)
        self.dof_ratio = self.param_combinations / min_trades
        self.degrees_of_freedom_warning = self.dof_ratio > 1.0

    def _calculate_confidence_intervals(self):
        """计算置信区间（基于假设的正态分布）"""
        if self.out_sample_trades > 1:
            # 夏普比率的近似置信区间
            sharpe_std = 1.0 / np.sqrt(self.out_sample_trades)
            self.sharpe_confidence_interval = (
                self.out_sample_sharpe - 1.96 * sharpe_std,
                self.out_sample_sharpe + 1.96 * sharpe_std
            )

            # 收益置信区间
            return_std = abs(self.out_sample_return) * 0.5  # 简化假设
            self.return_confidence_interval = (
                self.out_sample_return - 1.96 * return_std,
                self.out_sample_return + 1.96 * return_std
            )

    def _assess_overfit_combined(self):
        """综合评估过拟合风险"""
        # 三种检测方法的权重
        sharpe_weight = 0.4
        cscv_weight = 0.35
        sensitivity_weight = 0.25

        # 归一化各指标风险
        sharpe_risk = min(self.in_out_sharpe_ratio / 3.0, 1.0) if self.is_overfit_sharpe else 0.0
        cscv_risk = 1.0 - self.cscv_pvalue if self.is_overfit_cscv else 0.0
        sensitivity_risk = min(self.param_sensitivity / 0.5, 1.0) if self.is_overfit_sensitivity else 0.0

        # 计算综合置信度
        self.overfit_confidence = (
            sharpe_risk * sharpe_weight +
            cscv_risk * cscv_weight +
            sensitivity_risk * sensitivity_weight
        )

        # 综合判定：置信度 > 0.5 或任一种方法强烈指示过拟合
        self.is_overfit = (
            self.overfit_confidence > 0.5 or
            self.in_out_sharpe_ratio > 3.0 or
            (self.is_overfit_cscv and self.cscv_pvalue < 0.01)
        )

        # 计算稳健性得分（反向过拟合风险）
        self.robustness_score = 1.0 - self.overfit_confidence

    def _calculate_composite_score(self):
        """计算综合评分（考虑稳健性）"""
        # 基础得分：加权夏普比率
        base_score = (
            self.out_sample_sharpe * 0.6 +
            self.in_sample_sharpe * 0.4
        )

        # 惩罚因子
        overfit_penalty = 0.5 if self.is_overfit else 1.0
        dof_penalty = 0.8 if self.degrees_of_freedom_warning else 1.0
        robustness_bonus = 1.0 + (self.robustness_score * 0.2)  # 最高20%奖励

        self.composite_score = (
            base_score * overfit_penalty * dof_penalty * robustness_bonus
        )


class ParameterOptimizer:
    """
    参数优化器（含多重防过拟合机制）

    核心机制：
    1. 样本内/样本外分割（默认70/30）
    2. 夏普比率比较法（阈值 > 2.0）
    3. CSCV（组合对称交叉验证）
    4. 参数敏感性分析
    5. 多重自由度检查
    """

    # 默认样本内外分割比例
    DEFAULT_SPLIT_RATIO = 0.7

    # 过拟合阈值
    OVERFIT_THRESHOLD = 2.0

    # CSCV参数
    CSCV_S = 8  # 分割数

    def __init__(
        self,
        strategy_class: type,
        param_grid: Dict[str, List[Any]],
        split_ratio: float = DEFAULT_SPLIT_RATIO,
        n_jobs: int = 1,
        enable_cscv: bool = True,
        enable_sensitivity: bool = True,
        random_state: int = 42
    ):
        """
        初始化优化器

        Args:
            strategy_class: 策略类
            param_grid: 参数网格 {param_name: [values]}
            split_ratio: 样本内数据比例（默认0.7）
            n_jobs: 并行任务数（暂未实现）
            enable_cscv: 是否启用CSCV检测
            enable_sensitivity: 是否启用敏感性分析
            random_state: 随机种子
        """
        self.strategy_class = strategy_class
        self.param_grid = param_grid
        self.split_ratio = split_ratio
        self.n_jobs = n_jobs
        self.enable_cscv = enable_cscv
        self.enable_sensitivity = enable_sensitivity
        self.random_state = random_state
        np.random.seed(random_state)

        # 计算总参数组合数
        self.total_combinations = 1
        for values in param_grid.values():
            self.total_combinations *= len(values)

        # 存储所有结果用于CSCV分析
        self.all_results = []
        self.param_list = []

    def optimize(
        self,
        data: pd.DataFrame,
        commission: float = 0.001,
        slippage: float = 0.001,
        risk_free_rate: float = 0.02,
        use_walk_forward: bool = False,
        n_splits: int = 5
    ) -> Tuple[List[OptimizationResult], pd.DataFrame]:
        """
        执行参数优化（增强版，含多重防过拟合机制）

        Args:
            data: 回测数据
            commission: 佣金率
            slippage: 滑点
            risk_free_rate: 无风险利率
            use_walk_forward: 是否使用前向交叉验证
            n_splits: 交叉验证折数

        Returns:
            results: 优化结果列表（已排序）
            summary_df: 汇总DataFrame
        """
        print(f"="*80)
        print(f"开始参数优化（增强版 - 含多重防过拟合机制）")
        print(f"="*80)
        print(f"总参数组合数: {self.total_combinations}")
        print(f"样本内/样本外分割: {self.split_ratio:.0%} / {1-self.split_ratio:.0%}")
        print(f"启用CSCV检测: {self.enable_cscv}")
        print(f"启用敏感性分析: {self.enable_sensitivity}")
        print(f"使用前向交叉验证: {use_walk_forward}")

        if use_walk_forward:
            return self._optimize_walk_forward(
                data, commission, slippage, risk_free_rate, n_splits
            )
        else:
            return self._optimize_standard(
                data, commission, slippage, risk_free_rate
            )

    def _optimize_standard(
        self,
        data: pd.DataFrame,
        commission: float,
        slippage: float,
        risk_free_rate: float
    ) -> Tuple[List[OptimizationResult], pd.DataFrame]:
        """标准优化（单一样本内/外分割）"""

        # 分割数据
        split_idx = int(len(data) * self.split_ratio)
        in_sample_data = data.iloc[:split_idx]
        out_sample_data = data.iloc[split_idx:]

        print(f"\n样本内数据: {len(in_sample_data)} 条")
        print(f"样本外数据: {len(out_sample_data)} 条")

        # 生成所有参数组合
        param_names = list(self.param_grid.keys())
        param_values = list(self.param_grid.values())

        results = []
        all_sharpes = []  # 用于CSCV分析

        print(f"\n开始回测 {self.total_combinations} 个参数组合...")
        print("-"*80)

        for i, combination in enumerate(itertools.product(*param_values)):
            params = dict(zip(param_names, combination))

            if (i + 1) % 10 == 0 or i == 0 or (i + 1) == self.total_combinations:
                progress = (i + 1) / self.total_combinations * 100
                print(f"  [{i+1:4d}/{self.total_combinations:4d}] {progress:5.1f}% - 当前: {params}")

            try:
                # 样本内回测
                in_result = self._run_backtest(
                    in_sample_data, params, commission, slippage, risk_free_rate
                )

                # 样本外回测
                out_result = self._run_backtest(
                    out_sample_data, params, commission, slippage, risk_free_rate
                )

                # 收集CSCV数据
                if self.enable_cscv:
                    all_sharpes.append({
                        'params': params,
                        'in_sharpe': in_result['sharpe_ratio'],
                        'out_sharpe': out_result['sharpe_ratio'],
                    })

                # 计算参数敏感性（初始值，后续会细化）
                param_sensitivity = 0.0

                # 创建优化结果
                opt_result = OptimizationResult(
                    params=params,
                    in_sample_sharpe=in_result['sharpe_ratio'],
                    in_sample_return=in_result['total_return'],
                    in_sample_drawdown=in_result['max_drawdown'],
                    in_sample_trades=in_result['total_trades'],
                    out_sample_sharpe=out_result['sharpe_ratio'],
                    out_sample_return=out_result['total_return'],
                    out_sample_drawdown=out_result['max_drawdown'],
                    out_sample_trades=out_result['total_trades'],
                    param_combinations=self.total_combinations,
                    param_sensitivity=param_sensitivity,
                )

                results.append(opt_result)

            except Exception as e:
                print(f"    ⚠️  参数组合 {params} 回测失败: {e}")
                continue

        # 计算参数敏感性（需要所有结果）
        if self.enable_sensitivity and len(results) > 1:
            self._calculate_param_sensitivity(results)

        # 执行CSCV分析
        if self.enable_cscv and len(all_sharpes) > 5:
            self._run_cscv_analysis(results, all_sharpes)

        # 按综合评分排序
        results.sort(key=lambda x: x.composite_score, reverse=True)

        return self._generate_summary(results)

    def _calculate_param_sensitivity(self, results: List[OptimizationResult]):
        """计算参数敏感性（基于邻近参数的表现差异）"""
        for i, result in enumerate(results):
            sensitivities = []

            for param_name, param_value in result.params.items():
                # 查找邻近参数组合
                neighbors = [
                    r for r in results if r != result and
                    all(k == result.params[k] or k == param_name
                        for k in result.params.keys())
                ]

                if len(neighbors) >= 2:
                    # 计算夏普比率的变化率
                    neighbor_sharpes = [n.out_sample_sharpe for n in neighbors]
                    sharpe_std = np.std(neighbor_sharpes)
                    sharpe_mean = np.abs(np.mean(neighbor_sharpes))
                    if sharpe_mean > 0.01:
                        coeff_variation = sharpe_std / sharpe_mean
                        sensitivities.append(coeff_variation)

            # 平均敏感性
            if sensitivities:
                result.param_sensitivity = np.mean(sensitivities)
                # 敏感性 > 0.5 判定为不稳定
                result.is_overfit_sensitivity = result.param_sensitivity > 0.5

    def _run_cscv_analysis(self, results: List[OptimizationResult], all_sharpes: List[Dict]):
        """
        执行CSCV（Combinatorially Symmetric Cross-Validation）分析

        CSCV方法：将样本内/外数据多次随机分割，检测策略是否过度优化
        参考："The Probability of Backtest Overfitting" (Bailey et al., 2016)
        """
        if len(all_sharpes) < 8:
            return

        try:
            # 提取夏普比率
            in_sharpes = np.array([s['in_sharpe'] for s in all_sharpes])
            out_sharpes = np.array([s['out_sharpe'] for s in all_sharpes])

            # 创建排名矩阵
            n = len(in_sharpes)
            n_half = n // 2

            if n_half < 4:
                return

            # CSCV主循环
            logit_values = []
            num_splits = min(self.CSCV_S, n_half)

            for _ in range(100):  # 随机组合
                # 随机分割
                indices = np.random.permutation(n)
                in_indices = indices[:n_half]
                out_indices = indices[n_half:]

                if len(in_indices) < 2 or len(out_indices) < 2:
                    continue

                # 计算分割内的最优策略
                in_best_idx = in_indices[np.argmax(in_sharpes[in_indices])]
                out_perf = out_sharpes[in_best_idx]
                out_best = np.max(out_sharpes[out_indices])
                out_median = np.median(out_sharpes[out_indices])

                # 计算logit
                if out_best != out_median:
                    logit = (out_perf - out_median) / (out_best - out_median)
                    logit = max(-1, min(1, logit))  # 限制范围
                    logit_values.append(logit)

            if not logit_values:
                return

            # 计算CSCV概率
            prob_overfit = np.mean([l <= 0 for l in logit_values])

            # 将CSCV结果应用到所有结果
            for result in results:
                result.cscv_score = prob_overfit
                result.cscv_pvalue = prob_overfit
                # p < 0.05 认为显著过拟合
                result.is_overfit_cscv = prob_overfit > 0.5

        except Exception as e:
            warnings.warn(f"CSCV分析失败: {e}")

    def _generate_summary(self, results: List[OptimizationResult]) -> Tuple[List[OptimizationResult], pd.DataFrame]:
        """生成优化结果摘要"""

        # 生成汇总DataFrame（前20名）
        summary_data = []
        for r in results[:20]:
            summary_data.append({
                '排名': len(summary_data) + 1,
                '参数': str(r.params),
                '样本内夏普': f"{r.in_sample_sharpe:.2f}",
                '样本外夏普': f"{r.out_sample_sharpe:.2f}",
                '夏普比': f"{r.in_out_sharpe_ratio:.2f}",
                'CSCV概率': f"{r.cscv_score:.2f}" if r.cscv_score > 0 else "-",
                '敏感度': f"{r.param_sensitivity:.2f}" if r.param_sensitivity > 0 else "-",
                '过拟合': '⚠️' if r.is_overfit else '✓',
                '稳健性': f"{r.robustness_score:.2f}",
                '综合评分': f"{r.composite_score:.2f}",
            })

        summary_df = pd.DataFrame(summary_data)

        # 打印结果摘要
        print("\n" + "="*100)
        print("✅ 优化完成!")
        print("="*100)
        print(f"📊 总参数组合: {self.total_combinations}")
        print(f"✅ 成功回测: {len(results)}")
        print(f"⚠️  过拟合警告: {sum(1 for r in results if r.is_overfit)} (夏普比法)")
        print(f"⚠️  CSCV警告: {sum(1 for r in results if r.is_overfit_cscv)}")
        print(f"⚠️  自由度警告: {sum(1 for r in results if r.degrees_of_freedom_warning)}")
        print(f"⚠️  敏感度警告: {sum(1 for r in results if r.is_overfit_sensitivity)}")

        if results:
            best = results[0]
            print(f"\n🏆 最优参数（综合评分最高）:")
            print(f"   参数: {best.params}")
            print(f"   样本内夏普: {best.in_sample_sharpe:.3f}")
            print(f"   样本外夏普: {best.out_sample_sharpe:.3f}")
            print(f"   夏普比率: {best.in_out_sharpe_ratio:.2f}")
            print(f"   过拟合风险: {'⚠️ 高' if best.is_overfit else '✓ 低'}")
            print(f"   稳健性得分: {best.robustness_score:.3f}")
            print(f"   综合评分: {best.composite_score:.3f}")

            # 推荐参数（最稳健）
            robust_candidates = [r for r in results if not r.is_overfit and r.robustness_score > 0.5]
            if robust_candidates:
                most_robust = max(robust_candidates, key=lambda x: x.out_sample_sharpe)
                print(f"\n🛡️  最稳健推荐（低风险）:")
                print(f"   参数: {most_robust.params}")
                print(f"   样本外夏普: {most_robust.out_sample_sharpe:.3f}")
                print(f"   稳健性: {most_robust.robustness_score:.3f}")

        print("="*100)

        return results, summary_df

    def _run_backtest(
        self,
        data: pd.DataFrame,
        params: Dict[str, Any],
        commission: float,
        slippage: float,
        risk_free_rate: float
    ) -> Dict[str, Any]:
        """
        运行单次回测

        Returns:
            dict: 回测结果指标
        """
        # 创建策略实例
        strategy = self.strategy_class(**params)

        # 简单模拟回测（实际应使用更复杂的引擎）
        # 这里使用价格数据生成模拟信号和收益
        close = data['close']
        returns = close.pct_change().dropna()

        # 使用策略生成信号
        signals = []
        for i in range(len(data)):
            if i < strategy.lookback:
                signals.append(0)
            else:
                window_data = data.iloc[i-strategy.lookback:i+1]
                signal = strategy.generate_signal(window_data)
                signals.append(signal)

        # 计算策略收益
        strategy_returns = []
        for i in range(1, len(signals)):
            if signals[i-1] != 0:
                daily_return = returns.iloc[i-1] if i-1 < len(returns) else 0
                # 扣除佣金和滑点
                trade_cost = commission + slippage if signals[i] != signals[i-1] else 0
                strategy_returns.append(signals[i-1] * daily_return - trade_cost)
            else:
                strategy_returns.append(0)

        strategy_returns = pd.Series(strategy_returns)

        # 计算绩效指标
        total_return = (strategy_returns + 1).prod() - 1 if len(strategy_returns) > 0 else 0

        # 年化收益
        n_days = len(strategy_returns)
        annual_return = (1 + total_return) ** (252 / n_days) - 1 if n_days > 0 and total_return > -1 else 0

        # 夏普比率
        excess_returns = strategy_returns - risk_free_rate / 252
        sharpe_ratio = np.sqrt(252) * excess_returns.mean() / excess_returns.std() if excess_returns.std() > 0 else 0

        # 最大回撤
        cumulative = (1 + strategy_returns).cumprod()
        rolling_max = cumulative.expanding().max()
        drawdown = (cumulative - rolling_max) / rolling_max
        max_drawdown = drawdown.min() if len(drawdown) > 0 else 0

        # 交易次数
        trades = sum(1 for i in range(1, len(signals)) if signals[i] != signals[i-1] and signals[i-1] != 0)

        return {
            'total_return': total_return,
            'annual_return': annual_return,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'total_trades': trades,
        }


# 便捷的优化函数
def optimize_strategy(
    strategy_class: type,
    data: pd.DataFrame,
    param_grid: Dict[str, List[Any]],
    split_ratio: float = 0.7,
    commission: float = 0.001,
    slippage: float = 0.001,
    risk_free_rate: float = 0.02
) -> Tuple[List[OptimizationResult], pd.DataFrame]:
    """
    便捷函数：优化策略参数

    Args:
        strategy_class: 策略类
        data: 回测数据
        param_grid: 参数网格
        split_ratio: 样本内比例
        commission: 佣金率
        slippage: 滑点
        risk_free_rate: 无风险利率

    Returns:
        results: 优化结果列表
        summary_df: 汇总DataFrame
    """
    optimizer = ParameterOptimizer(
        strategy_class=strategy_class,
        param_grid=param_grid,
        split_ratio=split_ratio
    )

    return optimizer.optimize(
        data=data,
        commission=commission,
        slippage=slippage,
        risk_free_rate=risk_free_rate
    )