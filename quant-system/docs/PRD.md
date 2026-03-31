# 量化交易门户 — 产品需求文档 (PRD)

> 版本：v1.0
> 最后更新：2026-03-29
> 关联文档：`docs/多维量化指标体系_v1.0.md`

---

## 一、产品概述

### 1.1 定位

个人使用的量化交易门户系统，集品种管理、策略回测、实盘监控于一体。核心目标是将 `多维量化指标体系_v1.0.md` 中定义的四层信号体系（L1趋势/L2结构/L3共振/L4缺口）落地为可运行的软件系统。

### 1.2 技术栈

| 组件 | 选型 | 说明 |
|------|------|------|
| 后端框架 | Django 5.x | ORM管理数据模型，Admin管理后台作为快速管理入口 |
| 数据库 | SQLite | 单机使用，轻量够用 |
| 任务调度 | Celery + Redis（或 APScheduler） | 实盘监控的定时任务 |
| 行情数据 | mootdx / AKShare | A股/港股/跨境ETF行情 |
| 宏观数据 | fredapi | FRED宏观指标 |
| 期权数据 | AKShare | 50ETF/300ETF期权 |
| 计算引擎 | pandas / numpy / scipy | 指标计算与回测 |
| 前端 | Django模板 + TailwindCSS + ECharts | 可视化Dashboard |
| 消息推送 | 飞书Webhook（预留接口） | 信号通知，后续开发 |

### 1.3 数据约定

- **回测引擎：** 使用后复权价格（历史稳定，收益率准确）
- **实盘信号：** 使用前复权价格（最新价=真实盘面价格）
- **L4缺口层：** 额外使用不复权价格（跳空/流动性分析）

---

## 二、系统架构

```
┌─────────────────────────────────────────────────────────┐
│                    Django Web 应用                       │
├─────────┬──────────────┬──────────────┬─────────────────┤
│ 品种管理 │   策略回测    │  实盘监控     │   Dashboard    │
│ Module  │   Module     │  Module      │   (前端)       │
├─────────┴──────────────┴──────────────┴─────────────────┤
│                    信号合成引擎                           │
│              (L1-L4 多维评分 + 加权合成)                  │
├──────────────┬──────────────┬──────────────┬────────────┤
│  indicators/ │  indicators/ │  indicators/ │ indicators/│
│  L1 趋势     │  L2 结构     │  L3 共振      │ L4 缺口    │
├──────────────┴──────────────┴──────────────┴────────────┤
│                    数据获取层                             │
│           mootdx / AKShare / FRED / 期权                │
├─────────────────────────────────────────────────────────┤
│                    SQLite 数据库                          │
│     品种表 / 行情缓存 / 回测结果 / 信号日志 / 偏差日志     │
└─────────────────────────────────────────────────────────┘
          │                              │
          ▼                              ▼
    Celery/APScheduler               飞书Webhook
    (定时信号计算)                   (预留，后续开发)
```

---

## 三、项目目录结构

```
quant_portal/
├── manage.py
├── config/
│   ├── settings.py                # Django配置
│   ├── celery.py                  # 任务调度配置
│   └── params/
│       ├── indicators.yaml        # 指标默认参数（L1-01到L4-07的所有参数）
│       ├── strategies.yaml        # 策略权重与阈值
│       ├── data_sources.yaml      # 数据源配置（mootdx/AKShare/FRED的连接参数）
│       └── monitor.yaml           # 实盘监控调度配置
│
├── apps/
│   ├── portfolio/                 # 模块一：品种管理
│   │   ├── models.py              # ETF品种、品种池、品种池成员
│   │   ├── admin.py               # Django Admin快速管理
│   │   ├── views.py               # Dashboard视图
│   │   ├── urls.py
│   │   └── templates/
│   │
│   ├── backtest/                  # 模块二：策略回测
│   │   ├── models.py              # 回测任务、回测结果
│   │   ├── engine.py              # 回测引擎核心逻辑
│   │   ├── optimizer.py           # 参数遍历与最优推荐
│   │   ├── views.py
│   │   ├── urls.py
│   │   └── templates/
│   │
│   ├── monitor/                   # 模块三：实盘监控
│   │   ├── models.py              # 监控策略、信号日志
│   │   ├── tasks.py               # Celery定时任务
│   │   ├── notifier.py            # 飞书Webhook推送（预留）
│   │   ├── views.py
│   │   ├── urls.py
│   │   └── templates/
│   │
│   └── journal/                   # L5执行偏差日志
│       ├── models.py              # 偏差记录
│       ├── views.py
│       └── templates/
│
├── core/
│   ├── data/                      # 数据获取层
│   │   ├── base.py                # DataFetcher抽象基类
│   │   ├── mootdx_fetcher.py      # mootdx数据源
│   │   ├── akshare_fetcher.py     # AKShare数据源
│   │   ├── fred_fetcher.py        # FRED宏观数据
│   │   ├── option_fetcher.py      # 期权数据
│   │   └── cache.py               # 行情数据本地缓存（写入SQLite）
│   │
│   ├── indicators/                # 四层指标计算
│   │   ├── base.py                # Indicator抽象基类
│   │   ├── l1_trend.py            # L1-01到L1-05
│   │   ├── l2_structure.py        # L2-01到L2-06
│   │   ├── l3_resonance.py        # L3-01到L3-06
│   │   ├── l4_gap.py              # L4-01到L4-07
│   │   └── registry.py            # 指标注册表（按编号查找指标）
│   │
│   └── signals/                   # 信号合成
│       ├── scorer.py              # 单品种四维评分
│       ├── composer.py            # 综合得分加权合成
│       └── trigger.py             # 策略触发规则
│
├── templates/                     # 全局模板
│   ├── base.html                  # 基础布局（侧边栏+顶栏）
│   └── dashboard.html             # 首页Dashboard
│
├── static/                        # 静态资源
│   ├── css/
│   └── js/
│
├── docs/
│   ├── 多维量化指标体系_v1.0.md
│   └── PRD.md                     # 本文档
│
├── tests/
│   ├── test_indicators/           # 每个指标的单元测试
│   ├── test_backtest/
│   └── test_data/
│
└── CLAUDE.md                      # 项目规范
```

---

## 四、模块一：品种管理

### 4.1 数据模型

```python
class ETF(Model):
    """ETF品种"""
    code = CharField(max_length=10, unique=True)       # 证券代码，如 "159920"
    name = CharField(max_length=50)                     # 名称，如 "恒生ETF"
    market = CharField(choices=["SH","SZ"])              # 交易所
    category = CharField(choices=[                       # 品种类别
        "industry",     # 行业ETF
        "broad_base",   # 宽基ETF
        "cross_border", # 跨境ETF
        "commodity",    # 商品ETF
        "bond",         # 债券ETF
        "money",        # 货币基金
    ])
    data_source = CharField(default="akshare")           # 首选数据源
    underlying_currency = CharField(default="CNY")       # 底层资产币种（跨境ETF用）
    has_options = BooleanField(default=False)             # 是否有对应期权
    is_active = BooleanField(default=True)                # 是否启用
    notes = TextField(blank=True)                         # 备注
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)

class Pool(Model):
    """品种池"""
    name = CharField(max_length=50)                      # 池名称
    pool_type = CharField(choices=[
        "rotation",     # ETF轮动池
        "permanent",    # 永久组合池
        "thematic",     # 主题仓位池
    ])
    description = TextField(blank=True)
    is_active = BooleanField(default=True)
    created_at = DateTimeField(auto_now_add=True)

class PoolMember(Model):
    """品种池成员"""
    pool = ForeignKey(Pool)
    etf = ForeignKey(ETF)
    target_weight = FloatField(null=True)                # 目标权重（永久组合用）
    rebalance_band = FloatField(null=True)               # 再平衡带宽（永久组合用）
    role = CharField(blank=True)                          # 在池中的角色描述
    order = IntegerField(default=0)                       # 排序
```

### 4.2 功能需求

| 功能 | 说明 | 入口 |
|------|------|------|
| 品种CRUD | 增删改查ETF品种 | Dashboard + Django Admin |
| 品种池管理 | 创建/编辑品种池，添加/移除成员 | Dashboard |
| 品种池模板 | 预置轮动池/永久组合池/主题池的初始配置 | 首次启动时初始化 |
| 数据状态 | 显示每个品种的最新数据日期、数据完整性 | Dashboard品种列表 |

### 4.3 Dashboard页面

**品种管理页：**
- 左侧：品种池列表（树形，按类型分组）
- 右侧：选中池的成员列表，支持拖拽排序
- 每个品种显示：代码、名称、类别、最新价、最新数据日期
- 操作：添加品种（搜索或手动输入代码）、移除、编辑权重

---

## 五、模块二：策略回测

### 5.1 数据模型

```python
class BacktestTask(Model):
    """回测任务"""
    name = CharField(max_length=100)
    pool = ForeignKey(Pool)                              # 使用哪个品种池
    strategy_type = CharField(choices=[
        "rotation",     # ETF轮动
        "permanent",    # 永久组合
        "thematic",     # 主题仓位
    ])
    start_date = DateField()
    end_date = DateField()
    indicator_config = JSONField()                       # 选用的指标及参数范围
    # 示例：{
    #   "L1": {"L1-01": {"long_window": [20,30,40], "short_window": [10,15,20]}},
    #   "L2": {"L2-01": {"window": [40,60,80]}},
    #   "weights": {"W1": [0.3,0.4,0.5], "W2": [0.15,0.2,0.25]}
    # }
    status = CharField(choices=["pending","running","completed","failed"])
    created_at = DateTimeField(auto_now_add=True)

class BacktestResult(Model):
    """回测结果（每个参数组合一条记录）"""
    task = ForeignKey(BacktestTask)
    param_hash = CharField(max_length=32)                # 参数组合的哈希（去重用）
    params = JSONField()                                  # 具体参数值
    # 样本内指标
    in_sample_return = FloatField()                       # 样本内年化收益
    in_sample_sharpe = FloatField()                       # 样本内夏普
    in_sample_max_drawdown = FloatField()                 # 样本内最大回撤
    in_sample_win_rate = FloatField()                     # 样本内胜率
    in_sample_turnover = FloatField()                     # 样本内年化换手率
    # 样本外指标
    out_sample_return = FloatField(null=True)
    out_sample_sharpe = FloatField(null=True)
    out_sample_max_drawdown = FloatField(null=True)
    out_sample_win_rate = FloatField(null=True)
    # 过拟合检测
    param_count = IntegerField()                          # 该任务总参数组合数
    in_out_sharpe_ratio = FloatField(null=True)           # 样本内夏普/样本外夏普
    # 净值曲线（JSON存储，用于前端画图）
    equity_curve = JSONField(null=True)                   # [{"date":"2023-01-03","value":1.05}, ...]
    created_at = DateTimeField(auto_now_add=True)
```

### 5.2 回测引擎逻辑

```
输入：品种池 + 指标组合 + 参数范围 + 时间段

1. 数据准备
   - 拉取品种池内所有品种的后复权日线数据
   - 拉取FRED/期权数据（如果选用了L3-05/L4指标）
   - 按时间段切分：前70%为样本内，后30%为样本外

2. 参数遍历
   - 生成所有参数组合（笛卡尔积）
   - 每个组合执行一次完整回测：
     a. 按选用的指标计算各层得分
     b. 加权合成综合得分
     c. 按策略触发规则生成交易信号
     d. 模拟交易，计算净值曲线
     e. 计算绩效指标

3. 防过拟合机制
   - 记录参数组合总数 param_count
   - 分别计算样本内和样本外绩效
   - 计算 in_out_sharpe_ratio（>2.0 标记为高度疑似过拟合）
   - 推荐排序：优先样本外夏普，而非样本内最优

4. 输出
   - 所有参数组合的绩效写入 BacktestResult
   - 标记推荐组合（样本外夏普最高 + in_out_sharpe_ratio < 1.5）
```

### 5.3 回测约束与成本模拟

| 项目 | 默认值 | 可配置 |
|------|--------|--------|
| 交易成本（单边） | 0.1%（含佣金+冲击成本） | ✓ |
| 最小持有期 | 轮动策略5个交易日，永久组合20个交易日 | ✓ |
| 滑点模型 | 固定滑点0.05% | ✓ |
| 样本内/样本外比例 | 70% / 30% | ✓ |
| 再平衡频率 | 轮动=周度，永久组合=月度 | ✓ |

### 5.4 Dashboard页面

**回测配置页：**
- 步骤一：选择品种池（从模块一的池中选）
- 步骤二：选择策略类型（轮动/永久组合/主题）
- 步骤三：选择指标组合（勾选L1-L4中要使用的指标）
- 步骤四：设定参数范围（每个指标的参数滑块或输入框）
- 步骤五：设定时间段和回测约束
- 提交按钮 → 创建BacktestTask

**回测结果页：**
- 顶部：任务概要（品种池、时间段、参数组合数、耗时）
- 过拟合警告横幅：当最优参数的 in_out_sharpe_ratio > 2.0 时显示红色警告
- 左侧：参数组合排行榜（表格，可按各指标排序）
  - 默认按样本外夏普降序
  - 颜色标记：绿色=推荐，黄色=可接受，红色=疑似过拟合
- 右侧：选中组合的详情
  - 净值曲线图（ECharts，样本内/样本外用不同底色区分）
  - 回撤曲线
  - 月度收益热力图
  - 各层指标的时序图（L1-L4得分随时间变化）

---

## 六、模块三：实盘监控

### 6.1 数据模型

```python
class MonitorStrategy(Model):
    """监控策略"""
    name = CharField(max_length=100)
    pool = ForeignKey(Pool)
    strategy_type = CharField(choices=["rotation","permanent","thematic"])
    indicator_config = JSONField()                        # 使用的指标及参数（固定值，非范围）
    weight_config = JSONField()                           # L1-L4权重
    frequency = CharField(choices=[
        "intraday_10min",   # 盘中10分钟一次（日度轮换）
        "daily_1445",       # 每日14:45一次（周度轮换）
        "weekly",           # 每周执行一次
        "monthly",          # 每月执行一次
    ])
    is_active = BooleanField(default=True)
    created_at = DateTimeField(auto_now_add=True)

class Signal(Model):
    """信号日志"""
    strategy = ForeignKey(MonitorStrategy)
    timestamp = DateTimeField()                           # 信号生成时间
    signal_type = CharField(choices=[
        "buy", "sell", "hold",
        "rebalance",                                      # 永久组合再平衡
        "risk_alert",                                     # L4风险预警
    ])
    etf = ForeignKey(ETF)
    score = FloatField()                                  # 综合得分
    score_detail = JSONField()                            # 各层得分明细
    current_price = FloatField()                          # 当前前复权价格
    action_description = TextField()                      # 人类可读的操作建议
    is_notified = BooleanField(default=False)             # 是否已推送飞书
    created_at = DateTimeField(auto_now_add=True)
```

### 6.2 调度逻辑

```
定时任务调度（Celery Beat 或 APScheduler）：

任务：calculate_signals(strategy_id)

执行流程：
1. 检查当前是否为交易日、是否在交易时间内
2. 拉取品种池内所有品种的最新前复权行情
3. 计算L1-L4各层指标得分
4. 加权合成综合得分
5. 与上一次信号对比，判断是否产生新交易信号
6. 写入Signal表
7. 调用notifier.py发送飞书通知（预留，当前仅记录）

调度频率映射：
- intraday_10min：交易日 9:30-15:00，每10分钟执行
- daily_1445：交易日 14:45 执行一次
- weekly：每周五 14:45 执行
- monthly：每月最后一个交易日 14:45 执行

交易日判断：
- 使用AKShare的 tool_trade_date_hist_sina() 获取交易日历
- 缓存到本地，每月更新一次
```

### 6.3 飞书Webhook接口（预留）

```python
# core/notifier.py

class FeishuNotifier:
    """飞书通知推送（预留接口）"""

    def __init__(self, webhook_url: str = None):
        self.webhook_url = webhook_url  # 从config/monitor.yaml读取

    def send_signal(self, signal: Signal) -> bool:
        """
        推送信号到飞书

        消息格式：
        ┌──────────────────────────┐
        │ 📊 ETF轮动信号            │
        │ 时间：2025-03-28 14:45   │
        │ 策略：周度轮动            │
        │ 操作：买入 黄金ETF(518880)│
        │ 综合得分：78.5            │
        │ L1=85 L2=72 L3=80 L4=65 │
        │ 当前价：5.234             │
        └──────────────────────────┘

        返回：是否发送成功
        """
        if not self.webhook_url:
            return False
        # TODO: 实现飞书webhook调用
        pass
```

### 6.4 Dashboard页面

**实盘监控页：**
- 顶部：当前活跃监控策略列表（卡片形式）
  - 每张卡片：策略名称、品种池、频率、上次执行时间、状态
  - 开关按钮：启用/停用
- 中部：最新信号时间线（按时间倒序）
  - 每条信号：时间、品种、操作、得分、得分明细柱状图
  - 点击展开：各层指标详情
- 底部：信号统计
  - 最近7天/30天信号频率
  - 各品种信号分布饼图

**监控策略配置页：**
- 选择品种池
- 选择策略类型
- 选择指标组合和参数（可从回测推荐结果直接导入）
- 设定监控频率
- 保存并启动

---

## 七、Dashboard首页

### 7.1 布局

```
┌──────┬──────────────────────────────────────────────┐
│      │  Dashboard首页                                │
│      ├──────────────────────────────────────────────┤
│      │ ┌─────────────┐ ┌─────────────┐ ┌─────────┐ │
│ 侧   │ │ 活跃品种池数 │ │ 运行中监控数 │ │今日信号数│ │
│ 边   │ └─────────────┘ └─────────────┘ └─────────┘ │
│ 栏   ├──────────────────────────────────────────────┤
│      │ ┌────────────────────┐ ┌──────────────────┐  │
│ 品   │ │                    │ │                  │  │
│ 种   │ │  候选池品种走势图   │ │  最新L1-L4雷达图  │  │
│ 管   │ │  (ECharts多线图)   │ │  (每个品种一个)    │  │
│ 理   │ │                    │ │                  │  │
│      │ └────────────────────┘ └──────────────────┘  │
│ 策   ├──────────────────────────────────────────────┤
│ 略   │ ┌────────────────────┐ ┌──────────────────┐  │
│ 回   │ │                    │ │                  │  │
│ 测   │ │  最新信号时间线     │ │  L4风险状态仪表盘 │  │
│      │ │                    │ │  (平静/隐忧/恐慌) │  │
│ 实   │ │                    │ │                  │  │
│ 盘   │ └────────────────────┘ └──────────────────┘  │
│ 监   ├──────────────────────────────────────────────┤
│ 控   │ ┌────────────────────────────────────────┐   │
│      │ │  回测任务状态（最近5条）                  │   │
│ 偏   │ │  名称 | 品种池 | 进度 | 最优样本外夏普    │   │
│ 差   │ └────────────────────────────────────────┘   │
│ 日   │                                              │
│ 志   │                                              │
└──────┴──────────────────────────────────────────────┘
```

### 7.2 关键可视化组件

| 组件 | 类型 | 数据来源 |
|------|------|---------|
| 品种走势图 | ECharts多线图 | 数据获取层，后复权日线 |
| L1-L4雷达图 | ECharts雷达图 | indicators计算结果 |
| 信号时间线 | 自定义HTML列表 | Signal表 |
| 风险仪表盘 | ECharts仪表盘 | L4缺口层实时计算 |
| 净值曲线 | ECharts折线图 | BacktestResult |
| 月度收益热力图 | ECharts热力图 | BacktestResult |
| 回撤曲线 | ECharts面积图 | BacktestResult |

---

## 八、模块四：L5 执行偏差日志

### 8.1 数据模型

```python
class DeviationLog(Model):
    """执行偏差日志"""
    signal = ForeignKey(Signal, null=True)                 # 关联的原始信号
    timestamp = DateTimeField()
    planned_action = TextField()                           # 策略要求的操作
    actual_action = TextField()                            # 实际执行的操作
    deviation_type = CharField(choices=[
        "early",        # 提前执行
        "delayed",      # 延迟执行
        "partial",      # 部分执行
        "reversed",     # 反向操作
        "skipped",      # 跳过不执行
    ])
    subjective_reason = TextField()                        # 主观原因/直觉
    verification_result = CharField(                       # 事后验证（7天后填写）
        choices=["correct","wrong","neutral"],
        blank=True
    )
    review_note = TextField(blank=True)                    # 复盘标注
    created_at = DateTimeField(auto_now_add=True)
```

### 8.2 Dashboard页面

- 偏差记录列表（时间倒序）
- 每条可展开编辑"事后验证"和"复盘标注"
- 统计面板：
  - 直觉胜率（按偏离类型分组）
  - 偏差频率趋势
  - 胜率 > 60% 的偏差模式高亮提示

---

## 九、开发顺序

### Phase 0：项目骨架（预计1天）
- Django项目初始化
- 目录结构搭建
- config/params/ 下各yaml文件创建（填入指标体系文档中的默认参数）
- 基础模板和TailwindCSS集成
- SQLite数据库初始化

### Phase 1：数据层 + 品种管理（预计2-3天）
- `core/data/` 数据获取层实现
  - mootdx_fetcher: 获取A股/港股行情（前复权+后复权+不复权）
  - akshare_fetcher: ETF日线数据
  - fred_fetcher: 宏观数据
  - option_fetcher: 期权数据
  - cache: 行情缓存到SQLite
- `apps/portfolio/` 品种管理模块
  - 数据模型 + migration
  - Django Admin配置
  - Dashboard品种管理页面
  - 初始品种池数据导入（指标体系文档第八节的候选池）

### Phase 2：指标计算层（预计3-4天）
- `core/indicators/` 四层指标实现
  - l1_trend.py: L1-01到L1-05
  - l2_structure.py: L2-01到L2-06
  - l3_resonance.py: L3-01到L3-06
  - l4_gap.py: L4-01到L4-07
  - registry.py: 指标注册表
  - 每个指标写单元测试
- `core/signals/` 信号合成
  - scorer.py + composer.py + trigger.py

### Phase 3：回测引擎（预计3-4天）
- `apps/backtest/` 回测模块
  - 回测引擎核心（engine.py）
  - 参数遍历器（optimizer.py）
  - 防过拟合机制（样本内外分割、in_out_sharpe_ratio）
  - 回测结果存储
  - Dashboard回测配置页 + 结果展示页

### Phase 4：实盘监控（预计2-3天）
- `apps/monitor/` 监控模块
  - 定时任务调度（Celery或APScheduler）
  - 信号计算与记录
  - 飞书Webhook预留接口
  - Dashboard监控页面

### Phase 5：偏差日志 + Dashboard首页（预计1-2天）
- `apps/journal/` 偏差日志模块
- Dashboard首页集成（走势图、雷达图、信号时间线、风险仪表盘）

### Phase 6：打磨与优化（持续）
- 回测性能优化（大参数空间时的并行计算）
- 数据缓存策略优化
- Dashboard交互细节
- 飞书套件对接

---

## 十、注意事项

### 10.1 防过拟合（重要）

回测模块的参数优化必须内置以下机制，不可省略：

1. **样本内/样本外强制分割：** 默认70/30，用户可调但不可关闭
2. **参数组合数量展示：** 每个回测结果页面必须显著展示"共遍历了N组参数"
3. **推荐排序逻辑：** 优先样本外夏普 > 样本内夏普
4. **过拟合警告：** 当 in_out_sharpe_ratio > 2.0 时，红色警告横幅
5. **自由度提示：** 当参数组合数 > 样本外交易次数时，提示"参数空间可能过大"

### 10.2 数据约定（重复强调）

- 回测 → 后复权
- 实盘信号 → 前复权
- L4跳空/流动性 → 不复权
- 三套数据在data层统一管理，上层模块通过参数指定

### 10.3 指标参数外置

所有指标的默认参数存储在 `config/params/indicators.yaml`，格式：

```yaml
L1:
  L1-01:
    name: "复合斜率动量"
    long_window: 30
    short_window: 15
    long_weight: 0.6
    short_weight: 0.4
  L1-02:
    name: "EMA趋势过滤"
    period: 120
  # ...

L2:
  L2-01:
    name: "Hurst指数"
    window: 60
  # ...
```

代码中不硬编码任何指标参数。

### 10.4 交易日历

- 使用AKShare获取A股交易日历
- 本地缓存，每月初更新
- 实盘监控的定时任务需检查交易日历，非交易日跳过

---

*本PRD随开发进展持续更新。*
