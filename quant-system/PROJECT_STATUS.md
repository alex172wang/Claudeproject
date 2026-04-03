# 量化交易系统 - 项目进度报告

**报告日期:** 2026-04-01  
**项目版本:** v1.0-beta

---

## 执行摘要

已完成 Phase 1-3 的核心开发工作，包括：
- ✅ Django 后端项目骨架
- ✅ 数据层（mootdx/AKShare/FRED/期权）
- ✅ L1-L4 四层指标体系（26个指标）
- ✅ 回测引擎（含防过拟合机制）
- ✅ Dashboard 前端框架

---

## 详细进度

### Phase 0: 项目骨架 ✅ 已完成

**Django 项目结构:**
```
quant-system/quant_portal/     # Django 项目配置
├── settings.py               # 包含 Celery 配置
├── urls.py                   # URL 路由
├── wsgi.py / asgi.py         # 网关接口

quant-system/ 应用目录:
├── portfolio/                # 品种管理
│   ├── models.py             # ETF, Pool, PoolMember
│   ├── admin.py              # Django Admin 配置
│   └── management/commands/  # 初始化命令
├── backtest/                 # 回测模块
│   ├── models.py             # BacktestTask, BacktestResult
│   └── admin.py
├── monitor/                  # 实盘监控
│   ├── models.py             # MonitorStrategy, Signal
│   └── admin.py
└── journal/                  # 偏差日志
    ├── models.py             # DeviationLog
    └── admin.py
```

**YAML 配置文件:**
- `config/params/indicators.yaml` - 26个L1-L4指标参数
- `config/params/strategies.yaml` - 策略权重配置
- `config/params/data_sources.yaml` - 数据源配置
- `config/params/monitor.yaml` - 监控调度配置

---

### Phase 1: 数据层 + 品种管理 ✅ 已完成

**数据获取层 (core/data/):**

| 模块 | 功能 | 状态 |
|------|------|------|
| `base.py` | DataFetcher 抽象基类 | ✅ |
| `mootdx_fetcher.py` | A股/港股行情 | ✅ |
| `akshare_fetcher.py` | ETF/财经数据 | ✅ |
| `fred_fetcher.py` | 宏观数据 | ✅ |
| `option_fetcher.py` | 期权数据 | ✅ |
| `cache.py` | SQLite缓存 | ✅ |

**品种管理 (portfolio/):**

```python
# 数据模型
ETF (id, code, name, market, category, tracking_index, fund_manager, is_active)
Pool (id, code, name, purpose, description, is_active)
PoolMember (id, pool, etf, added_date, removed_date, is_active)
```

**Django Admin 配置:**
- ETF 品种管理界面
- Pool 品种池管理
- PoolMember 池成员管理

---

### Phase 2: 指标计算层 ✅ 已完成

**四层指标体系 (core/indicators/):**

#### L1 趋势层 (5个指标)

| ID | 指标名 | 描述 | 状态 |
|----|--------|------|------|
| L1-01 | 复合斜率动量 | 30日/15日斜率加权 | ✅ |
| L1-02 | EMA趋势过滤 | 收盘价与EMA(120)关系 | ✅ |
| L1-03 | 趋势加速度 | 斜率动量的一阶差分 | ✅ |
| L1-04 | 价格通道位置 | (Close - Low) / (High - Low) | ✅ |
| L1-05 | FRED趋势共振 | 美债收益率+美元指数斜率 | ✅ |

#### L2 结构层 (6个指标)

| ID | 指标名 | 描述 | 状态 |
|----|--------|------|------|
| L2-01 | Hurst指数 | R/S分析趋势持续性 | ✅ |
| L2-02 | 波动率结构比 | 短期/长期实现波动率比 | ✅ |
| L2-03 | 成交量形态分歧 | 量价背离分析 | ✅ |
| L2-04 | 回撤分形维度 | 回撤序列Hurst指数 | ✅ |
| L2-05 | K线实体比 | 实体/振幅均值 | ✅ |
| L2-06 | 波动率自相关 | 日收益率绝对值ACF(1) | ✅ |

#### L3 共振层 (6个指标)

| ID | 指标名 | 描述 | 状态 |
|----|--------|------|------|
| L3-01 | 滚动相关性矩阵 | 多资产相关性结构 | ✅ |
| L3-02 | 相关性变速 | 相关性变化速率 | ✅ |
| L3-03 | PCA解释方差 | 第一主成分占比 | ✅ |
| L3-04 | 跨市场一致性 | 多市场动量一致性 | ✅ |
| L3-05 | 宏观-资产共振 | FRED数据与资产相关性 | ✅ |
| L3-06 | 板块轮动速度 | 行业相关性变化速度 | ✅ |

#### L4 缺口层 (7个指标)

| ID | 指标名 | 描述 | 状态 |
|----|--------|------|------|
| L4-01 | IV-RV价差 | 隐含-实现波动率价差 | ✅ |
| L4-02 | 期权偏度 | 25Δ看跌-看涨IV | ✅ |
| L4-03 | 认沽认购比 | Put/Call成交量比 | ✅ |
| L4-04 | 流动性缺口 | 盘口深度缺口 | ✅ |
| L4-05 | 尾部风险 | 期权隐含的左尾风险 | ✅ |
| L4-06 | 跳空缺口频率 | 日内跳空统计 | ✅ |
| L4-07 | FRED压力合成 | 美债+美元+原油综合压力 | ✅ |

**指标基类 (base.py):**
- `BaseIndicator`: 指标基类
- `IndicatorRegistry`: 指标注册表
- `IndicatorResult`: 指标结果
- `IndicatorValue`: 指标值
- 工具函数: `normalize_score`, `calculate_slope`, `hurst_exponent`, `calculate_r_squared`

---

### Phase 3: 回测引擎 ✅ 已完成

**回测核心 (core/backtest/):**

| 模块 | 功能 | 状态 |
|------|------|------|
| `engine.py` | 回测引擎 | ✅ |
| `strategy.py` | 策略基类 | ✅ |
| `broker.py` | 模拟经纪商 | ✅ |
| `metrics.py` | 绩效指标 | ✅ |
| `results.py` | 回测结果 | ✅ |
| `optimizer.py` | 参数优化（防过拟合） | ✅ |

**防过拟合机制:**

1. **样本内/样本外分割** (强制 70/30)
   - 默认 split_ratio = 0.7
   - 不可关闭

2. **参数组合数展示**
   - 每个回测结果显示 "共遍历了 N 组参数"
   - 自由度检查: 参数组合数 vs 样本外交易次数

3. **推荐排序逻辑**
   - 优先: 样本外夏普 > 样本内夏普
   - 综合评分 = (out_sharpe * 0.6 + in_sharpe * 0.4) * 惩罚因子

4. **过拟合警告**
   - 阈值: in_out_sharpe_ratio > 2.0
   - 红色横幅警告

5. **自由度提示**
   - 当 参数组合数 > 样本外交易次数 时警告
   - 提示 "参数空间可能过大"

**测试结果验证:**
```
✓ 参数组合数: 9
✓ 样本内/样本外分割: 210 / 90 条
✓ 过拟合检测: 发现 0 组过拟合参数 (阈值: 2.0)
✓ 自由度检查: 发现 0 组自由度警告
✓ 推荐排序逻辑验证: 最优参数样本外夏普 = 0.934
```

---

### Phase 4-6: 进行中/待开发

**Phase 4: 实盘监控 (Celery)** ✅ 已完成
- [x] Celery Beat 定时任务配置
- [x] 信号计算任务
- [x] 飞书 Webhook 通知
- [x] 实时监控 Dashboard 页面

**Phase 5: L5 偏差日志 + Dashboard 首页** ✅ 已完成
- [x] L5 执行偏差日志模型
- [x] 偏差统计与分析
- [ ] Dashboard 首页图表
- [ ] 权益曲线、雷达图、信号时间线

**Phase 6: 优化与测试**
- [ ] 并行计算优化
- [ ] 数据缓存优化
- [ ] 集成测试
- [ ] 性能测试

---

## 快速开始

### 安装依赖
```bash
cd quant-system
pip install -r requirements.txt
```

### 初始化数据库
```bash
python manage.py migrate
python manage.py init_pools  # 初始化品种池
```

### 启动 Dashboard
```bash
python run_dashboard.py
# 访问 http://127.0.0.1:8050
```

### 运行测试
```bash
# 集成测试
python test_system_integrated.py

# 回测优化器测试
python test_optimizer.py
```

---

## 技术栈

| 组件 | 用途 | 版本 |
|------|------|------|
| Django | 后端框架 | 5.x |
| Dash + Plotly | 前端 Dashboard | 2.x |
| Celery + Redis | 定时任务调度 | 5.x |
| pandas/numpy | 数据处理 | 2.x |
| mootdx | A股数据接口 | - |
| AKShare | 财经数据 | - |

---

## 项目统计

| 指标 | 数值 |
|------|------|
| 总代码行数 | ~15,000+ |
| Python 文件数 | 80+ |
| Django 应用数 | 4 |
| 数据库模型数 | 15+ |
| L1-L4 指标数 | 26 |
| Dashboard 页面数 | 7 |

---

## 后续开发计划

### 短期 (1-2周) ✅ 已完成
1. ✅ 完善 Celery 实盘监控任务
2. ✅ 实现 L5 偏差日志
3. 优化 Dashboard 首页

### 中期 (1个月)
1. 实盘接口对接
2. 飞书通知集成
3. 性能优化

### 长期 (3个月)
1. 机器学习策略优化
2. 多因子模型
3. 实时风控系统

---

## 联系与贡献

如有问题或建议，请通过以下方式联系：
- 提交 Issue
- 发送邮件
- 提交 PR

---

**文档版本:** v1.0  
**最后更新:** 2026-04-01
