# 贡献规范

## Git 提交规范

### 提交信息格式

```
[类型] 简短描述（不超过50字）

详细描述（可选，解释为什么做这个修改）

- 修改点1
- 修改点2
```

### 提交类型

| 类型 | 说明 | 示例 |
|------|------|------|
| `feat` | 新功能 | `[feat] 实现L1-01复合斜率动量指标` |
| `fix` | Bug修复 | `[fix] 修复EMA过滤器的边界条件` |
| `docs` | 文档更新 | `[docs] 更新L2指标说明文档` |
| `style` | 代码格式（不影响功能） | `[style] 统一代码缩进格式` |
| `refactor` | 重构（不新增功能） | `[refactor] 重构指标基类结构` |
| `test` | 测试相关 | `[test] 添加L1指标单元测试` |
| `chore` | 构建/工具/依赖 | `[chore] 更新requirements.txt` |
| `config` | 配置文件 | `[config] 调整ETF轮动权重` |

### 分支策略

```
main          # 主分支，稳定版本
  ↓
develop       # 开发分支，日常开发
  ↓
feature/l1-indicators   # 功能分支
feature/l2-structure
bugfix/ema-filter
```

---

## 代码审查清单

- [ ] 代码是否符合命名规范（见 CLAUDE.md）
- [ ] 注释是否完整且使用中文
- [ ] 文档字符串是否包含参数说明
- [ ] 是否有适当的类型注解
- [ ] 是否有单元测试覆盖
- [ ] 是否通过 `black` 格式化检查
- [ ] 是否有性能影响较大的计算

---

## 版本发布流程

1. 更新版本号（`setup.py`、`__init__.py`）
2. 更新 `CHANGELOG.md`
3. 运行完整测试套件：`python -m pytest tests/`
4. 更新文档
5. 创建 Git 标签：`git tag -a v1.0.0 -m "版本 1.0.0"`
6. 推送到远程：`git push origin v1.0.0`

---

## 版本迭代路线图

| 阶段 | 目标 | 关键里程碑 | 状态 |
|------|------|-----------|------|
| **v1.0** | 指标定义 + 框架搭建 | 目录结构、配置系统、指标基类、L1定义 | ✅ 已完成 |
| **v1.1** | L1 + L2 指标代码实现 | 接入 mootdx，单品种信号生成 | 📅 待开发 |
| **v1.2** | L3 共振层实现 | 相关性矩阵 + PCA，多品种联动 | 📅 待开发 |
| **v1.3** | L4 缺口层实现 | 期权数据接入 + FRED 宏观数据 | 📅 待开发 |
| **v2.0** | 信号合成 + 回测验证 | 综合评分系统 + 历史回测对比 | 📅 待开发 |
| **v2.1** | 执行偏差分析 | L5 日志系统 + 直觉胜率统计 | 📅 待开发 |
| **v3.0** | 参数自适应 | 各层权重根据市场状态动态调整 | 📅 待开发 |

---

## 开发工具推荐

### VS Code 推荐插件

- Python（微软官方）
- Pylance（类型检查）
- Black Formatter（代码格式化）
- autoDocstring（文档字符串生成）
- YAML（配置文件支持）

### PyCharm 配置

- 启用类型检查器
- 配置 Black 作为默认格式化工具
- 设置 docstring 格式为 Google 风格

### VS Code 调试配置

`.vscode/launch.json`：

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: main.py",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/main.py",
            "console": "integratedTerminal",
            "args": ["--strategy", "etf_rotation", "--verbose"]
        },
        {
            "name": "Python: 当前文件",
            "type": "python",
            "request": "launch",
            "program": "${file}",
            "console": "integratedTerminal"
        }
    ]
}
```