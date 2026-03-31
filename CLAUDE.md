# 量化交易策略开发项目 - Claude 配置文件

## 项目概述

A 股量化交易策略研发项目，核心系统位于 `quant-system/` 子目录。

## 项目结构

```
Claudeproject/
├── CLAUDE.md              # 本文件：全局导航
├── quant-system/          # 量化系统（主代码库）
│   ├── CLAUDE.md          # 详细开发规范与工作流
│   ├── docs/
│   │   ├── 多维量化指标体系_v1.0.md  # L1-L4 指标定义
│   │   └── CONTRIBUTING.md          # Git/审查/发布流程
│   ├── src/               # 源代码（indicators / signals / strategies / backtest）
│   ├── config/            # 参数与权重配置（YAML）
│   └── ...
├── hello.py               # 测试脚本
├── requirements.txt       # 全局依赖
└── README.md              # 项目说明
```

## 全局约定

- **语言**: 所有代码注释、文档使用中文，专业术语保留英文
- **代码风格**: PascalCase 类名 / snake_case 函数 / UPPER_CASE 常量
- **回测纪律**: 参数优化必须做样本外测试，务必计入佣金（0.1%）和滑点

## 详细文档指引

| 需要了解 | 去哪看 |
|---------|--------|
| 开发规范、目录结构、工作流 | `quant-system/CLAUDE.md` |
| 指标体系定义（L1-L4） | `quant-system/docs/多维量化指标体系_v1.0.md` |
| Git 提交规范、版本发布、代码审查 | `quant-system/docs/CONTRIBUTING.md` |
| 权重与阈值配置 | `quant-system/config/` |