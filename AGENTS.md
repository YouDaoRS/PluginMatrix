# PluginMatrix Agent Development Rules

本文件是 PluginMatrix 面向 Codex、AI Agent 和贡献者的长期开发规则。它描述项目当前的边界和判断标准，优先级高于“顺手增加功能”的冲动。

## 项目定位

PluginMatrix 是一个面向 Minecraft Paper 插件开发者的发布前运行时兼容性验证工具。

当前核心流程是：

```text
插件 JAR
  -> 预检
  -> 准备隔离的 Paper/Java 环境
  -> 启动真实 Paper 服务器
  -> 观察插件发现、加载、enable 和稳定性
  -> 输出结构化结论与原始日志
```

Matrix v0.2 已提供同一个 Verifier 的多个环境串行编排。v0.3 已提供离线 CI 和手动 Matrix workflow；并行执行仍属于后续阶段。

## 当前技术边界

- 当前实现语言是 Python，要求 Python 3.10+。
- 当前 CLI 入口是 `python -m pluginmatrix`，安装后也支持 `pluginmatrix`。
- 当前只支持 Paper，不要擅自扩展到 Spigot、Folia、Fabric、Forge、Velocity 或其他服务端。
- Runtime Verifier 单次只验证一个插件、一个 Paper/Java 环境；Matrix 在本地按顺序重复调用它。
- 依赖插件只接受用户明确提供的本地 JAR。
- Paper 下载使用官方 API，并记录实际 Paper build 和 SHA-256。
- 每次运行必须使用隔离目录，并保留原始 `server.log`。
- 结果必须有稳定的机器可读状态和 JSON 报告。

## 状态语义

支持的顶层结果状态：

`ENVIRONMENT_INVALID`、`SERVER_START_FAILED`、`SERVER_START_TIMEOUT`、`PLUGIN_NOT_DISCOVERED`、`PLUGIN_LOAD_FAILED`、`PLUGIN_ENABLE_FAILED`、`PLUGIN_DISABLED`、`PASS`、`UNKNOWN_FAILURE`

必须尽量区分环境问题与插件问题：

- Java 不存在、Java 版本不匹配、Paper build 不可用、Paper bootstrap 无法下载自身依赖，属于环境或服务器问题。
- `plugin.yml` 缺失、主类缺失、插件加载异常、enable 异常，属于插件相关问题。
- `PASS` 只表示服务器成功启动，runtime probe 通过 `PluginManager` 找到目标插件并确认其 `isEnabled()`，且在稳定观察窗口内没有被 disable。
- 不得把 `PASS` 描述为“插件所有功能都兼容”。

## 开发原则

1. **证据优先**：状态结论必须能回溯到日志、预检结果或环境元数据。
2. **可复现优先**：记录 Minecraft/Paper 版本、Paper build、Java 版本、插件版本、JAR hash、命令和运行目录。
3. **失败可定位**：优先输出失败阶段和关键异常，不要只返回进程退出码。
4. **小步实现**：优先保持 Runtime Verifier 可靠，再在其公开能力之上扩展 Matrix。
5. **兼容现有结构**：优先使用标准库和当前模块边界，不为未来功能提前引入复杂框架。
6. **真实测试优先**：Mock 或模拟测试只能补充，不能替代真实 Paper 启动验证。
7. **保留原始证据**：任何日志摘要都不能替代原始 `server.log`。

## 不要擅自实现

除非用户明确改变范围，否则不要加入：

- 云端执行或 Web Dashboard；
- Bot、GUI 自动化、完整 E2E 测试 DSL；
- AI 日志分析、自动修复或兼容性评分；
- 自动下载 Vault、WorldEdit 等第三方依赖；
- Spigot/Folia/Fabric/Forge/Velocity 支持；
- 性能基准测试、分布式服务器拓扑或自动生成测试用例；
- 与 EnhancedFly 绑定的专用逻辑。
- 并行 Matrix、复杂 Matrix DSL 或跨环境共享状态。

## 代码与验证要求

- 搜索代码优先使用 `rg` / `rg --files`。
- 手工编辑文件使用 `apply_patch`。
- 修改后至少运行相关单元测试和 `python -m compileall`。
- 涉及运行状态判断的修改，应补充覆盖成功、超时、启动失败、插件加载失败或 disable 的测试。
- 不要因为测试方便而删除用户已有文件、缓存或未相关的工作区改动。
- 不要把本地 `.pluginmatrix/cache`、`.pluginmatrix/runs`、构建产物或 `__pycache__` 提交进源码。

## 产品判断标准

一个改动只有在能让普通 Paper 插件开发者更容易得到可信、可定位、可复现的运行时结论时，才属于当前核心价值。

如果一个功能主要增加展示层、平台数量或“看起来很大”的能力，却没有降低兼容性验证成本，应推迟。
