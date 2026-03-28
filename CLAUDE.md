# 量化交易策略开发项目 - Claude 配置文件

## 项目概述

A 股量化交易策略研发平台，基于 backtrader 回测框架 + mootdx 通达信数据接口。

**核心目标：** 策略开发 → 回测验证 → 参数优化 → 风险分析

## 技术栈

| 组件 | 用途 |
|------|------|
| **Python 3.8+** | 主要开发语言 |
| **backtrader** | 回测框架 |
| **mootdx** | 通达信 A 股数据接口 |
| **pandas / numpy** | 数据处理与数值计算 |
| **matplotlib** | 可视化绘图 |

## 目录结构

```
Claudeproject/
├── data/                   # 数据目录（raw/ 原始 + processed/ 处理后）
├── strategies/            # 策略目录（继承 bt.Strategy）
│   ├── base.py            # 策略基类
│   └── ma_cross.py        # 均线交叉策略示例
├── utils/                 # 工具模块
│   ├── data_loader.py     # 数据加载（mootdx 封装）
│   ├── analyzer.py        # 绩效分析
│   └── plotter.py         # 绘图工具
├── config/settings.py     # 全局配置
├── results/               # 回测结果输出
├── tests/                 # 测试代码
├── main.py                # 主入口
└── requirements.txt       # 依赖包
```

## 代码规范

### 注释规范

- **所有代码注释使用中文**
- 模块级文档字符串：描述用途和主要功能
- 函数/方法文档字符串：包含参数说明、返回值
- 复杂逻辑处添加行内注释

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

- **类名**: PascalCase → `MACrossStrategy`
- **函数/方法**: snake_case → `calculate_returns`
- **常量**: UPPER_CASE → `INITIAL_CAPITAL`
- **私有成员**: 单下划线前缀 → `_internal_calc`

## 开发工作流

### 数据获取

通过 `utils/data_loader.py` 封装 mootdx 接口，提供以下核心方法：

- `get_stock_history(symbol, start_date, end_date)` — 历史 K 线
- `get_realtime_quotes(symbols)` — 实时行情
- `get_stock_list(market)` — 股票列表
- `close_client()` — 关闭连接（程序结束时必须调用）

### 策略开发

在 `strategies/` 目录下创建策略文件，继承 `bt.Strategy` 或 `base.py` 中的基类。

### 回测执行

```bash
python main.py
```

回测流程：初始化 Cerebro → 加载数据 → 添加策略 → 设置佣金/资金 → 添加分析器 → 运行 → 输出结果

### 常用分析器

- `bt.analyzers.SharpeRatio` — 夏普比率
- `bt.analyzers.DrawDown` — 最大回撤
- `bt.analyzers.Returns` — 收益率
- `bt.analyzers.TradeAnalyzer` — 交易统计

## 注意事项

1. **数据质量**: A 股数据可能存在缺失或异常，注意数据清洗
2. **复权处理**: 回测使用前复权数据（mootdx 默认已处理）
3. **幸存者偏差**: 回测时考虑已退市股票
4. **过拟合风险**: 参数优化时必须做样本外测试
5. **交易成本**: 务必考虑佣金（默认 0.1%）、滑点
6. **通达信连接**: 需网络通畅，首次使用 `bestip=True` 自动选服务器，程序结束务必 `close_client()`
7. **数据频率限制**: 单次请求最多 800 条，更多数据需分页获取

## 常用命令

```bash
pip install -r requirements.txt   # 安装依赖
python main.py                     # 运行回测
jupyter notebook                   # 启动 Notebook
```

## .gitignore

```
data/
results/
*.pyc
__pycache__/
*.ipynb_checkpoints
.vscode/
.idea/
*.log
```