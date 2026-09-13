# PluginMatrix Agent Development Rules

本文件是 PluginMatrix 面向 Codex、AI Agent 和贡献者的长期开发规则。它描述项目当前的边界和判断标准，优先级高于“顺手增加功能”的冲动。

## 项目定位

PluginMatrix 是一个面向 Minecraft 插件开发者的发布前运行时兼容性验证工具。

当前核心流程是：

```text
插件 JAR
  -> 预检
  -> 准备隔离的 Paper/Java 环境
  -> 启动真实 Paper 服务器
  -> 观察插件发现、加载、enable 和稳定性
  -> 输出结构化结论与原始日志
```

v0.6 开发沿用同一个 Runtime Verifier，通过 Provider 支持 Paper、Purpur、Folia 和明确运行契约的 local JAR。Matrix 默认串行，可选 1–8 个并发环境。

## 当前技术边界

- 当前实现语言是 Python，要求 Python 3.10+。
- 当前 CLI 入口是 `python -m pluginmatrix`，安装后也支持 `pluginmatrix`。
- 官方 Provider 为 Paper、Purpur、Folia；local/custom 必须明确指定受支持运行契约。不要新增其他官方 Provider。
- Runtime Verifier 单次只验证一个插件、一个服务端/Java 环境；所有 Provider 复用它，禁止复制 verifier。
- 依赖插件只接受用户明确提供的本地 JAR。
- 内置 Provider 使用官方 API，记录实际 build、来源、官方校验算法与本地 SHA-256。local 不下载服务端，不修改输入。
- 每次运行必须使用隔离目录，并保留原始 `server.log`。
- 结果必须有稳定的机器可读状态和 JSON 报告。

## 状态语义

支持的顶层结果状态：

`ENVIRONMENT_INVALID`、`SERVER_START_FAILED`、`SERVER_START_TIMEOUT`、`PLUGIN_NOT_DISCOVERED`、`PLUGIN_LOAD_FAILED`、`PLUGIN_ENABLE_FAILED`、`PLUGIN_DISABLED`、`PLUGIN_UNSUPPORTED`、`CANCELLED`、`PASS`、`UNKNOWN_FAILURE`

必须尽量区分环境问题与插件问题：

- Java 不存在、Java 版本不匹配、Paper build 不可用、Paper bootstrap 无法下载自身依赖，属于环境或服务器问题。
- `plugin.yml` 缺失、主类缺失、插件加载异常、enable 异常，属于插件相关问题。
- `PASS` 只表示服务器成功启动，runtime probe 通过 `PluginManager` 找到目标插件并确认其 `isEnabled()`，且在稳定观察窗口内没有被 disable。
- 不得把 `PASS` 描述为“插件所有功能都兼容”。
- Folia 未声明支持返回 `PLUGIN_UNSUPPORTED`；Folia PASS 不证明线程安全或跨 region 安全。

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
- 新增 Spigot/Fabric/Forge/Velocity 官方 Provider 或自动 BuildTools；
- 性能基准测试、分布式服务器拓扑或自动生成测试用例；
- 与 EnhancedFly 绑定的专用逻辑。
- 复杂 Matrix DSL 或跨环境共享运行状态。

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
