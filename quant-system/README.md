# Quant System - 量化交易系统

基于**四维量化指标体系**的 A 股量化交易平台，从**趋势(L1)、结构(L2)、共振(L3)、缺口(L4)** 四个维度构建市场认知框架。

---

## 核心特性

- **四维指标体系**：突破单一技术指标局限，多维度验证市场状态
- **三层策略架构**：ETF轮动 / 永久组合 / 主题仓位，差异化配置
- **动态信号合成**：L1-L4加权评分，策略自适应权重调整
- **实时数据同步**：基于 mootdx 的实时行情和 K 线数据
- **Dashboard 可视化**：实时监控、K线图、ETF数据展示

---

## 快速开始

### 安装依赖

```bash
cd quant-system
pip install -r requirements.txt
```

### 启动系统

**Windows 用户（推荐）：**
```batch
# 双击启动
启动系统.bat
```

**命令行启动：**
```bash
# 完整启动（初始化 + 数据同步 + Dashboard）
python scripts/start_quant_system.py

# 仅启动 Dashboard
python run_dashboard.py
```

启动后访问：http://localhost:8050

---

## 项目结构

```
quant-system/
├── CLAUDE.md                      # 项目规范与配置
├── README.md                      # 本文件
├── requirements.txt               # Python依赖
├── manage.py                      # Django管理
├── run_dashboard.py              # Dashboard启动脚本
├── 启动系统.bat                   # Windows一键启动
├── 启动Dashboard.bat               # Windows Dashboard启动
├── 启动说明.md                     # 详细启动说明
│
├── quant_system/                  # Django项目配置
│   ├── settings.py                # 全局配置（含ETF池）
│   ├── urls.py                    # URL路由
│   └── wsgi.py
│
├── core/                           # 核心计算层
│   ├── data/                      # 数据获取层
│   │   ├── base.py                # DataFetcher抽象基类
│   │   ├── mootdx_fetcher.py      # A股/港股行情
│   │   ├── akshare_fetcher.py     # ETF/财经数据
│   │   ├── fred_fetcher.py        # 宏观数据
│   │   └── cache.py               # 数据缓存
│   ├── indicators/                # 指标计算层
│   │   ├── base.py                # 指标基类
│   │   ├── l1_trend.py           # L1趋势层（5个指标）
│   │   ├── l2_structure.py       # L2结构层（6个指标）
│   │   ├── l3_resonance.py       # L3共振层（6个指标）
│   │   └── l4_gap.py             # L4缺口层（7个指标）
│   ├── signals/                   # 信号合成层
│   │   ├── scorer.py             # 四维评分器
│   │   ├── composer.py           # 信号合成器
│   │   └── trigger.py            # 策略触发器
│   ├── backtest/                  # 回测引擎
│   │   ├── engine.py              # 回测引擎
│   │   └── ...
│   └── live/                       # 实盘风控
│       └── risk/                  # 风控规则
│
├── data_sync/                      # 数据同步服务
│   ├── adapters.py                # 数据适配器
│   ├── tasks.py                   # 同步任务
│   ├── scheduler.py               # 调度器
│   ├── sync_service.py            # 同步服务
│   ├── cache_manager.py           # 缓存管理
│   └── apps.py                    # Django App配置
│
├── api/                            # REST API
│   ├── views.py                   # API视图
│   ├── serializers.py             # 序列化器
│   └── urls.py                    # API路由
│
├── dashboard/                      # Dash仪表板
│   ├── main.py                    # 完整版Dashboard（多标签页）
│   ├── simple_dashboard.py        # 简化版Dashboard（单页版）
│   ├── data_adapter_direct.py     # 直接数据适配器
│   ├── api_client.py              # API客户端
│   ├── components/                # 组件库
│   │   ├── charts.py              # 图表组件
│   │   └── widgets.py             # UI组件
│   └── pages/                     # 页面模块
│
├── portfolio/                      # 品种管理
│   ├── models.py                  # ETF/Pool模型
│   ├── admin.py                   # Django Admin
│   └── management/commands/       # 管理命令
│
├── backtest/                       # 回测模块
│   ├── models.py                  # 回测任务/结果模型
│   └── admin.py
│
├── monitor/                        # 监控模块
│   ├── models.py                  # 监控/信号模型
│   └── admin.py
│
├── journal/                        # 交易日志
│   ├── models.py                  # 决策/偏差日志模型
│   └── admin.py
│
├── scripts/                        # 脚本工具
│   └── start_quant_system.py      # 系统启动脚本
│
├── config/                         # 配置文件
│   └── params/                    # 参数配置
│
├── docs/                           # 文档
│   ├── PRD.md                     # 产品需求文档
│   └── 多维量化指标体系_v1.0.md  # 指标体系定义
│
└── logs/                           # 日志目录
```

---

## 四维指标体系

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

## 配置说明

### ETF 池配置

编辑 `quant_system/settings.py` 中的 `QUANT_SYSTEM` 配置：

```python
QUANT_SYSTEM = {
    'etf_pool': [
        {'code': '510300', 'name': '沪深300ETF', 'category': 'broad', 'market': 'sh'},
        {'code': '159915', 'name': '创业板ETF', 'category': 'broad', 'market': 'sz'},
        # 添加更多 ETF...
    ],
    'data_sync': {
        'realtime_interval': 5,    # 实时行情同步间隔（秒）
        'kline_ttl': 3600,         # K线缓存时间（秒）
    }
}
```

---

## 开发文档

详见 [CLAUDE.md](CLAUDE.md) 了解：
- 代码规范与注释要求
- 开发工作流
- 模块接口定义

---

## 技术栈

| 组件 | 用途 | 版本 |
|------|------|------|
| Django | 后端框架 | 5.x |
| Dash + Plotly | 前端 Dashboard | 2.x |
| Django REST Framework | API框架 | 3.x |
| pandas/numpy | 数据处理 | 2.x |
| mootdx | A股数据接口 | - |

---

## 许可证

[待定]
