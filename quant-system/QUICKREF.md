# 量化交易系统 - 快速参考

## 常用命令

### 启动系统
```bash
# 启动 Dashboard
python run_dashboard.py
# 访问 http://127.0.0.1:8050

# 启动 Django 开发服务器
python manage.py runserver

# 启动 Celery  worker
 celery -A quant_portal worker -l info

# 启动 Celery beat (定时任务)
 celery -A quant_portal beat -l info
```

### 数据库操作
```bash
# 迁移数据库
python manage.py migrate

# 创建超级用户
python manage.py createsuperuser

# 初始化品种池
python manage.py init_pools

# 导出数据
python manage.py dumpdata portfolio > portfolio.json

# 导入数据
python manage.py loaddata portfolio.json
```

### 测试
```bash
# 运行集成测试
python test_system_integrated.py

# 测试回测优化器
python test_optimizer.py

# 运行 Django 测试
python manage.py test

# 测试数据适配器
python -c "from core.data.mootdx_fetcher import MootdxFetcher; f = MootdxFetcher(); print('OK')"
```

---

## 核心 API 使用

### 指标计算
```python
from core.indicators import get_indicator, list_indicators

# 列出所有指标
indicators = list_indicators()
print(f"L1: {len(indicators['L1'])}, L2: {len(indicators['L2'])}, ...")

# 获取指标实例
indicator = get_indicator('L1-01')  # 复合斜率动量

# 计算指标
import pandas as pd
data = pd.DataFrame({
    'open': [...], 'high': [...], 'low': [...], 
    'close': [...], 'volume': [...]
})
result = indicator.calculate(data)

# 获取结果
print(f"得分: {result.current.normalized_score}")
print(f"信号: {result.current.signal}")
print(f"元数据: {result.current.metadata}")
```

### 回测引擎
```python
from core.backtest.optimizer import optimize_strategy
from core.backtest.strategy import StrategyBase
import pandas as pd

# 定义策略
class MyStrategy(StrategyBase):
    def __init__(self, fast=5, slow=20):
        super().__init__()
        self.fast = fast
        self.slow = slow
        self.lookback = slow + 5
    
    def generate_signal(self, data):
        close = data['close']
        fast_ma = close.rolling(self.fast).mean().iloc[-1]
        slow_ma = close.rolling(self.slow).mean().iloc[-1]
        return 1 if fast_ma > slow_ma else (-1 if fast_ma < slow_ma else 0)

# 准备数据
data = pd.read_csv('your_data.csv', index_col=0, parse_dates=True)

# 参数优化（含防过拟合）
results, summary = optimize_strategy(
    strategy_class=MyStrategy,
    data=data,
    param_grid={
        'fast': [3, 5, 10],
        'slow': [15, 20, 30],
    },
    split_ratio=0.7,  # 70/30 分割
    commission=0.001,
    slippage=0.001,
)

# 查看最优参数
best = results[0]
print(f"最优参数: {best.params}")
print(f"样本外夏普: {best.out_sample_sharpe:.3f}")
print(f"是否过拟合: {best.is_overfit}")
```

### 数据获取
```python
from core.data.mootdx_fetcher import MootdxFetcher
from core.data.cache import DataCache

# 创建获取器
fetcher = MootdxFetcher()

# 获取ETF列表
etf_list = fetcher.get_etf_list()
print(f"ETF数量: {len(etf_list)}")

# 获取历史数据
data = fetcher.get_kline('510300', start='20240101', end='20241231')
print(f"数据条数: {len(data)}")

# 使用缓存
cache = DataCache()
cache.set('510300_daily', data)
cached_data = cache.get('510300_daily')
```

---

## 项目结构速查

```
quant-system/
├── core/                       # 核心计算层
│   ├── backtest/              # 回测引擎
│   │   ├── engine.py
│   │   ├── optimizer.py       # 防过拟合优化器
│   │   └── strategy.py
│   ├── data/                  # 数据获取层
│   │   ├── mootdx_fetcher.py
│   │   ├── akshare_fetcher.py
│   │   └── cache.py
│   ├── indicators/            # 指标计算层
│   │   ├── l1_trend.py        # 5个趋势指标
│   │   ├── l2_structure.py    # 6个结构指标
│   │   ├── l3_resonance.py    # 6个共振指标
│   │   ├── l4_gap.py          # 7个缺口指标
│   │   └── base.py            # 指标基类
│   └── live/                  # 实盘监控
├── dashboard/                 # Dash前端
│   ├── main.py                # 主应用
│   ├── pages/                 # 各页面
│   │   ├── backtest.py
│   │   ├── config.py
│   │   ├── instruments.py
│   │   ├── realtime.py
│   │   ├── risk.py
│   │   └── signals.py
│   └── config.py              # 主题配置
├── quant_portal/              # Django项目
│   ├── settings.py            # 包含Celery配置
│   └── urls.py
├── portfolio/                 # 品种管理App
├── backtest/                  # 回测App
├── monitor/                   # 监控App
└── journal/                   # 日志App
```

---

## 常见问题

### Q: 如何添加新的指标？
```python
# 1. 在相应的 L1-L4 文件中创建类
from .base import BaseIndicator, IndicatorRegistry, IndicatorResult

@IndicatorRegistry.register
class L1XXMyIndicator(BaseIndicator):
    INDICATOR_ID = 'L1-XX'
    INDICATOR_NAME = '我的指标'
    LAYER = 'L1'
    
    DEFAULT_PARAMS = {'period': 20}
    
    def calculate(self, data):
        # 实现计算逻辑
        value = data['close'].rolling(self.params['period']).mean()
        # ...
        return IndicatorResult(...)

# 2. 在 __init__.py 中导出
# 3. 在 indicators.yaml 中添加参数
```

### Q: 如何添加新的策略？
```python
from core.backtest.strategy import StrategyBase

class MyStrategy(StrategyBase):
    def __init__(self, param1=10, param2=20):
        super().__init__()
        self.param1 = param1
        self.param2 = param2
        self.lookback = max(param1, param2) + 5
    
    def generate_signal(self, data):
        # 实现信号逻辑
        # return 1 (买入), -1 (卖出), 0 (无信号)
        pass
```

### Q: Dashboard 不显示数据？
1. 检查数据适配器是否正确配置
2. 查看浏览器控制台是否有 JavaScript 错误
3. 确认后台没有报错
4. 尝试重启 Dashboard: `python run_dashboard.py`

### Q: 如何重置数据库？
```bash
# 删除数据库文件
rm db.sqlite3

# 重新迁移
python manage.py migrate

# 初始化数据
python manage.py init_pools
python manage.py createsuperuser
```

---

## 参考资料

- [Django 文档](https://docs.djangoproject.com/)
- [Dash 文档](https://dash.plotly.com/)
- [Celery 文档](https://docs.celeryproject.org/)
- [mootdx 文档](https://github.com/mootdx/mootdx)
- [AKShare 文档](https://www.akshare.xyz/)

---

**文档版本:** v1.0  
**最后更新:** 2026-04-01
