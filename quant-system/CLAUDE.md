# Quant System - Claude 配置文档

> **本文件的定位：** Claude 在本项目中编写代码、做设计决策时必须遵守的规则和约定。
> 指标体系定义见 `docs/多维量化指标体系_v1.0.md`，项目说明见 `README.md`，贡献规范见 `docs/CONTRIBUTING.md`。

---

## 项目定位

基于**多维量化指标体系**的 A 股量化交易系统。

**核心理念：** 从 **趋势(L1)、结构(L2)、共振(L3)、缺口(L4)** 四个维度构建市场评分，覆盖 ETF轮动 / 永久组合 / 主题仓位 三个策略层。

**当前版本：** v1.0（框架搭建完成，L1 指标定义完成待测试，L2-L4 待开发）

---

## 技术栈

| 组件 | 用途 |
|------|------|
| Python 3.8+ | 主要开发语言 |
| backtrader | 回测框架 |
| mootdx | 通达信 A 股数据接口 |
| AKShare | 财经数据接口 |
| pandas / numpy | 数据处理与数值计算 |
| matplotlib | 可视化绘图 |

---

## 目录结构

```
quant-system/
├── CLAUDE.md                      # 本文件：Claude 开发规则
├── README.md                      # 项目说明
├── docs/
│   ├── 多维量化指标体系_v1.0.md    # 指标体系完整定义
│   └── CONTRIBUTING.md            # 贡献规范（Git/审查/发布流程）
├── core/
│   ├── data/                      # 数据获取层（mootdx/AKShare/FRED）
│   ├── indicators/                # L1-L4 各层指标计算
│   │   ├── base.py                # 指标基类与工具方法
│   │   └── l1_trend.py            # L1 趋势层指标
│   ├── signals/                   # 信号合成层
│   ├── strategies/                # 三个策略的执行逻辑
│   └── backtest/                  # 回测引擎
├── config/
│   ├── settings.py                # 全局设置
│   ├── weights.yaml               # 各策略权重配置
│   └── thresholds.yaml            # 阈值配置
├── logs/                          # L5 执行偏差日志
├── tests/                         # 测试代码
├── data/                          # 数据目录（gitignore）
└── results/                       # 回测结果输出（gitignore）
```

---

## 代码规范

### 注释语言

所有代码注释、文档字符串使用**中文**。函数/方法必须包含参数说明和返回值描述。

```python
"""
均线交叉策略模块

实现简单的双均线交叉交易策略，包括金叉买入和死叉卖出信号。
"""

class MACrossStrategy(bt.Strategy):
    """
    双均线交叉策略

    参数:
        fast_period (int): 短期均线周期，默认 5
        slow_period (int): 长期均线周期，默认 20
    """
```

### 命名约定

| 类型 | 约定 | 示例 |
|------|------|------|
| 类名 | PascalCase | `CompositeSlopeMomentum` |
| 函数/方法 | snake_case | `calculate_returns` |
| 常量 | UPPER_CASE | `INITIAL_CAPITAL` |
| 私有成员 | 单下划线前缀 | `_internal_calc` |
| 指标文件 | `l{N}_{name}.py` | `l1_trend.py`, `l2_structure.py` |
| 数据加载器 | `{source}_loader.py` | `mootdx_loader.py`, `fred_loader.py` |
| 策略文件 | `{name}_strategy.py` | `etf_rotation.py` |
| 配置文件 | `{name}.yaml` | `weights.yaml` |

---

## 关键开发约束

### 数据层

- **mootdx**: 单次请求最多 800 条，超出需分页；首次连接使用 `bestip=True`；**程序结束务必调用 `close_client()`**
- **AKShare**: ETF 列表、行业分类等财经数据；注意接口更新频繁，调用前确认函数签名
- **FRED**: 宏观数据（美债收益率、VIX 等），用于 L1-05 FRED趋势共振和 L4 缺口层；需联网访问
- 回测使用前复权数据（mootdx 默认已处理）

### 回测纪律

- 参数优化**必须**做样本外测试，警惕过拟合
- 佣金默认 0.1%，必须考虑滑点
- 考虑幸存者偏差（已退市标的）
- A 股数据可能存在缺失或异常，注意数据清洗

### 指标开发

- 所有指标继承 `core/indicators/base.py` 中的 `BaseIndicator`
- 指标输出统一归一化到 `[0, 100]` 评分
- 指标按 L1-L4 层级组织，文件命名 `l{N}_{name}.py`
- 新指标必须在 `docs/多维量化指标体系_v1.0.md` 中有对应定义

## 数据约定

- **回测引擎**：使用后复权价格（历史稳定，收益率准确）
- **实盘信号**：使用前复权价格（最新价=真实盘面价格）
- **L4缺口层**：额外使用不复权价格（跳空/流动性分析）

---

## 开发工作流速查

```python
# 1. 数据获取
from src.data import MootdxLoader, AKShareLoader, FREDLoader

mootdx = MootdxLoader()
df = mootdx.get_stock_history('000001', start='20230101', end='20231231')

ak = AKShareLoader()
etf_list = ak.get_etf_list()

fred = FREDLoader()
us10y = fred.get_series('GS10')  # 美国10年期国债收益率

# 2. 指标计算
from src.indicators import CompositeSlopeMomentum
momentum = CompositeSlopeMomentum(data).calculate()

# 3. 信号合成
from src.signals import SignalSynthesizer
scores = synthesizer.calculate_scores(data)

# 4. 回测
from src.backtest import BacktestEngine
engine = BacktestEngine(start_date='20200101', end_date='20231231')
results = engine.run()
```

---

## 常用命令

```bash
pip install -r requirements.txt   # 安装依赖
python main.py                     # 运行回测
python -m pytest tests/            # 运行测试
pytest tests/smoke_test.py -v     # 运行启动冒烟测试（每次改代码后必跑）
black core/ config/ tests/          # 代码格式化
mypy core/                          # 类型检查
```

## 测试规范

### 启动冒烟测试（smoke_test.py）

每次修改代码版本后，**必须**运行启动冒烟测试，确保系统能正常启动：

```bash
pytest tests/smoke_test.py -v
```

该测试验证以下内容：
- Django 核心模块导入链完整（捕获 ImportError、字段名错误等）
- Django runserver 能正常启动并响应 HTTP 请求
- Dashboard 能正常启动（环境无关问题时 skip）
- Django + Dashboard 同时启动正常运行

如测试失败，说明代码改动引入了启动级错误，必须修复后才能继续。

---

*本文档随项目迭代更新。最后更新：2026-03-29*