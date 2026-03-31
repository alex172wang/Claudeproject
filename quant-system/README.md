# Quant System - 多维量化交易系统

基于**多维量化指标体系**的 A 股量化交易平台，从**趋势(L1)、结构(L2)、共振(L3)、缺口(L4)** 四个维度构建市场认知框架。

---

## 核心特性

- **四维指标体系**：突破单一技术指标局限，多维度验证市场状态
- **三层策略架构**：ETF轮动 / 永久组合 / 主题仓位，差异化配置
- **动态信号合成**：L1-L4加权评分，策略自适应权重调整
- **完整回测系统**：基于 backtrader 的回测与绩效分析
- **执行偏差日志**：L5元层记录，持续优化决策质量

---

## 快速开始

### 安装依赖

```bash
# 克隆项目
git clone <repo-url>
cd quant-system

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 运行回测

```bash
# ETF轮动策略回测
python main.py --strategy etf_rotation --start 2020-01-01 --end 2024-12-31

# 永久组合策略回测
python main.py --strategy permanent_portfolio --start 2020-01-01

# 主题仓位策略回测
python main.py --strategy thematic_position --start 2023-01-01
```

### 查看帮助

```bash
python main.py --help
```

---

## 项目结构

```
quant-system/
├── CLAUDE.md                      # 项目规范与配置
├── README.md                      # 本文件
├── requirements.txt               # Python依赖
├── main.py                        # 主入口
├── config/                        # 配置文件
│   ├── __init__.py
│   ├── settings.py                # 全局设置
│   ├── weights.yaml               # 策略权重
│   ├── thresholds.yaml            # 阈值配置
│   └── pools.yaml                 # 候选池配置
├── docs/                          # 文档
│   └── 多维量化指标体系_v1.0.md    # 指标体系完整定义
├── src/                           # 源代码
│   ├── __init__.py
│   ├── data/                      # 数据获取层
│   │   ├── __init__.py
│   │   ├── loaders.py             # 数据加载器基类
│   │   ├── mootdx_loader.py     # 通达信数据接口
│   │   ├── akshare_loader.py    # AKShare数据接口
│   │   └── fred_loader.py       # FRED宏观数据接口
│   ├── indicators/               # 指标计算层
│   │   ├── __init__.py
│   │   ├── base.py               # 指标基类与工具
│   │   ├── l1_trend.py          # L1 趋势层指标
│   │   ├── l2_structure.py      # L2 结构层指标
│   │   ├── l3_resonance.py       # L3 共振层指标
│   │   └── l4_gap.py            # L4 缺口层指标
│   ├── signals/                  # 信号合成层
│   │   ├── __init__.py
│   │   ├── synthesizer.py        # 四维评分合成器
│   │   ├── rules.py              # 策略触发规则
│   │   └── weights.py            # 动态权重管理
│   ├── strategies/               # 策略执行层
│   │   ├── __init__.py
│   │   ├── base.py               # 策略基类
│   │   ├── etf_rotation.py       # ETF轮动策略
│   │   ├── permanent_portfolio.py # 永久组合策略
│   │   └── thematic_position.py  # 主题仓位策略
│   └── backtest/                 # 回测引擎
│       ├── __init__.py
│       ├── engine.py             # 回测引擎主类
│       ├── analyzer.py           # 绩效分析器
│       └── reporter.py           # 报告生成器
├── logs/                         # 执行日志
├── tests/                        # 测试代码
│   ├── __init__.py
│   ├── test_indicators.py
│   ├── test_signals.py
│   └── test_strategies.py
└── data/                         # 数据目录（gitignore）
    ├── raw/                      # 原始数据
    └── processed/                # 处理后数据
```

---

## 核心概念

### 四维指标体系

| 层级 | 名称 | 哲学隐喻 | 核心功能 |
|------|------|---------|---------|
| **L1** | 趋势层 | "概率最高的路径" | 方向判断 |
| **L2** | 结构层 | "投影的纹理" | 品质验证 |
| **L3** | 共振层 | "多投影间的交汇" | 关联分析 |
| **L4** | 缺口层 | "信息损失的度量" | 风险预警 |

### 三层策略架构

- **ETF轮动**：基于 L1 趋势动量排序，L2-L4 作为过滤器和风控
- **永久组合**：资产配置再平衡，L3 驱动配比调整，L4 触发防御
- **主题仓位**：事件驱动择时，四维综合评分决定进出场

---

## 开发文档

详见 [CLAUDE.md](CLAUDE.md) 了解：
- 代码规范与注释要求
- 开发工作流
- 模块接口定义
- 版本迭代路线图

---

## 许可证

[待定]

---

## 联系方式

[待定]
