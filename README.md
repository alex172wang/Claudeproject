# 量化交易系统

A股量化交易策略研发平台，支持多维度指标体系、信号合成、回测引擎和手动交易记录。

**注意**: 主代码库位于 `quant-system/` 目录。本目录为项目根目录，包含项目级配置和文档。

## 快速开始

### 1. 环境要求
- Python 3.8+
- Windows / Linux / macOS

### 2. 启动系统

```bash
cd quant-system
python scripts/start_quant_system.py
```

Windows 用户也可使用:
```bash
quant-system\scripts\start_quant_system.bat
```

### 3. 访问系统

- **Dashboard**: http://localhost:8050
- **Django Admin**: http://localhost:8000/admin/ (admin/admin123)

## 项目结构

```
Claudeproject/                 # 项目根目录
├── README.md                  # 本文件
├── CLAUDE.md                  # Claude配置
├── quant-system/              # 主代码库（核心系统）
│   ├── README.md              # 系统详细文档
│   ├── core/                  # 核心模块（指标、信号、回测）
│   ├── dashboard/             # Dash可视化界面
│   ├── journal/               # 交易记录、L5偏差日志
│   ├── monitor/               # 信号监控
│   ├── portfolio/             # 品种管理
│   ├── docs/                  # 项目文档
│   └── scripts/               # 启动脚本
├── config/                    # 全局配置（根目录级）
└── archive/                 # 归档文件（temp/等）
```

## 文档索引

**系统级文档** (位于 `quant-system/docs/`):
- [PRD.md](quant-system/docs/PRD.md) - 产品需求文档
- [多维量化指标体系](quant-system/docs/多维量化指标体系_v1.0.md) - L1-L4指标定义
- [手动交易指南](quant-system/docs/user_guide/manual_trading.md)
- [L5偏差日志指南](quant-system/docs/user_guide/l5_journal.md)

**项目级文档**:
- [CLAUDE.md](CLAUDE.md) - 全局配置
- [quant-system/CLAUDE.md](quant-system/CLAUDE.md) - 开发规范
- [quant-system/CONTRIBUTING.md](quant-system/CONTRIBUTING.md) - Git/审查/发布流程

## 开发状态

当前完成度: **65%**

| 阶段 | 状态 | 完成度 |
|------|------|-------|
| Phase 0: 数据层 | 基础结构 | 60% |
| Phase 1: 品种管理 | Model定义 | 50% |
| Phase 2: 指标计算层 | 开发中 | 30% |
| Phase 3: 信号/回测 | 基础结构 | 40% |
| Phase 4: 实盘监控 | 部分实现 | 30% |
| Phase 5: Dashboard | 基础结构 | 35% |
| **L5偏差日志** | 重点完善 | 60% |

详见: [quant-system/PROJECT_STATUS.md](quant-system/PROJECT_STATUS.md)

## 许可证

MIT License
