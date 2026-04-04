# 量化交易系统集成测试计划

## 1. 测试概述

### 1.1 测试目标
验证量化交易系统各模块的集成工作情况，确保数据流、控制流在各组件间正确传递。

### 1.2 测试范围
- Django后端API服务
- Dash实时Dashboard
- 数据适配器（mootdx）
- 交易日志模块（Journal）
- 信号监控模块（Monitor）

### 1.3 测试环境
- **操作系统**: Windows 10/11
- **Python版本**: 3.14.2
- **虚拟环境**: venv (项目根目录)
- **主要依赖**:
  - Django 6.0.3
  - Dash 4.1.0
  - mootdx 0.11.7

---

## 2. 测试用例

### TC-001: 虚拟环境激活测试
**目的**: 验证虚拟环境能正确激活
**前置条件**: 虚拟环境已创建
**测试步骤**:
1. 执行 `venv\Scripts\activate.bat`
2. 检查Python路径是否为虚拟环境路径
**预期结果**: Python解释器指向 `venv\Scripts\python.exe`
**通过标准**: `which python` 显示虚拟环境路径

---

### TC-002: 依赖包导入测试
**目的**: 验证所有关键依赖包能正常导入
**前置条件**: 虚拟环境已激活
**测试步骤**:
1. 导入各关键包
```python
import django
import dash
import dash_bootstrap_components as dbc
import plotly
import pandas
import numpy
import akshare
import backtrader
```
**预期结果**: 所有导入无报错
**通过标准**: 无 ImportError

---

### TC-003: Django 服务启动测试
**目的**: 验证Django后端能正常启动
**前置条件**: 依赖已安装，数据库已初始化
**测试步骤**:
1. 进入 `quant-system` 目录
2. 执行 `python manage.py runserver 0.0.0.0:8000`
**预期结果**: 服务启动，显示 `Starting development server at http://0.0.0.0:8000/`
**验证方法**: 访问 http://localhost:8000/api/ 返回JSON

---

### TC-004: Dashboard 启动测试
**目的**: 验证Dash仪表板能正常启动
**前置条件**: Django服务已启动
**测试步骤**:
1. 在 `quant-system` 目录
2. 执行 `python run_dashboard.py --port 8050`
**预期结果**: Dashboard启动，显示 `Dash is running on http://127.0.0.1:8050/`
**验证方法**: 访问 http://localhost:8050 显示仪表板

---

### TC-005: 数据适配器连接测试
**目的**: 验证mootdx数据连接正常
**前置条件**: 网络连接正常
**测试步骤**:
```python
from dashboard.data_adapter_v2 import overview_data_adapter
adapter = overview_data_adapter
print(adapter)
```
**预期结果**: 显示 `DataAdapterV2` 实例，mootdx连接成功
**通过标准**: 无连接错误

---

### TC-006: 信号模块初始化测试
**目的**: 验证信号模块能正确初始化
**前置条件**: 数据适配器已连接
**测试步骤**:
```python
from core.signals import SignalScorer, SignalComposer
scorer = SignalScorer()
print(scorer)
```
**预期结果**: `SignalScorer` 实例创建成功
**通过标准**: 无初始化错误

---

### TC-007: 交易日志模块测试
**目的**: 验证交易日志模型工作正常
**前置条件**: Django已配置
**测试步骤**:
```python
from journal.models import DecisionLog
print(DecisionLog.objects.count())
```
**预期结果**: 返回数字（记录数），无查询错误
**通过标准**: 数据库查询正常

---

### TC-008: 端到端启动测试
**目的**: 验证完整启动流程
**前置条件**: 所有前置条件满足
**测试步骤**:
1. 执行 `scripts/start_quant_system.bat`
2. 等待所有服务启动
3. 检查浏览器是否自动打开
**预期结果**:
- Django运行在 http://localhost:8000
- Dashboard运行在 http://localhost:8050
- 浏览器自动打开 http://localhost:8050
**通过标准**: 所有服务启动，无报错

---

## 3. 测试执行计划

### 阶段1: 环境验证（10分钟）
- TC-001: 虚拟环境激活
- TC-002: 依赖包导入

### 阶段2: 单模块测试（20分钟）
- TC-003: Django服务
- TC-004: Dashboard服务
- TC-005: 数据适配器

### 阶段3: 集成测试（20分钟）
- TC-006: 信号模块
- TC-007: 交易日志
- TC-008: 端到端启动

### 总计预计时间: 50分钟

---

## 4. 测试通过标准

### 通过率要求
- 关键测试（TC-003, TC-004, TC-008）: 100%通过
- 普通测试: 80%以上通过

### 失败处理
1. 记录失败原因
2. 修复问题
3. 重新执行失败的测试
4. 验证修复效果

---

## 5. 测试报告模板

```
============================================================
量化交易系统集成测试报告
测试时间: 2026-XX-XX XX:XX:XX
============================================================

测试环境:
- 操作系统: Windows 10
- Python版本: 3.14.2
- Django版本: 6.0.3
- Dash版本: 4.1.0

测试结果汇总:
- 总测试数: 8
- 通过: X
- 失败: X
- 通过率: XX%

详细结果:
TC-001 [通过/失败] 虚拟环境激活测试
TC-002 [通过/失败] 依赖包导入测试
TC-003 [通过/失败] Django服务启动测试
TC-004 [通过/失败] Dashboard启动测试
TC-005 [通过/失败] 数据适配器连接测试
TC-006 [通过/失败] 信号模块初始化测试
TC-007 [通过/失败] 交易日志模块测试
TC-008 [通过/失败] 端到端启动测试

问题记录:
1. ...
2. ...

改进建议:
1. ...
2. ...

============================================================
```

---

**文档版本**: 1.0  
**创建日期**: 2026-04-04  
**最后更新**: 2026-04-04  
**作者**: Claude Code