# PluginMatrix Product Spec

## 1. 项目定义

PluginMatrix 是一个面向 Minecraft Paper 插件开发者的发布前运行时兼容性验证工具。

它接收插件 JAR，在真实 Paper 服务器中运行，并尽可能准确地区分：

- 测试环境无效；
- Paper 服务器启动失败或超时；
- 插件未被发现；
- 插件加载失败；
- 插件 enable 失败；
- 插件启动后被 disable；
- 插件进入稳定可运行状态。

PluginMatrix 的核心不是“支持多少版本”，而是把真实服务器启动过程转换为结构化、可定位、可复现的兼容性结论。

## 2. 目标用户

- 维护多个 Minecraft/Paper 版本的插件作者；
- 发布公共插件的个人开发者和小团队；
- 想在发布前验证插件 JAR 的作者；
- 不想为每个服务器版本手写启动、日志解析和失败报告脚本的项目。

## 3. 要解决的问题

编译通过和单元测试通过，不能证明插件能在真实 Paper 服务器中成功启动。

常见风险包括：

- `plugin.yml` 错误；
- 主类或 bytecode target 不匹配；
- Paper/Java 组合无效；
- 插件未被服务器发现；
- 依赖缺失；
- `onLoad`/`onEnable` 阶段异常；
- 插件 enable 后立即被 disable；
- Paper 自身启动或下载运行时依赖失败。

开发者通常需要手工维护服务器目录、启动脚本、超时逻辑和日志判断。这些脚本很容易只告诉用户“进程失败”，却不能回答失败发生在哪个阶段。

## 4. 核心价值

给定一个插件 JAR、一个 Paper 版本和一个 Java 环境，PluginMatrix 应该快速回答：

> 这个插件是否在这个真实 Paper 环境中完成了预检、被发现、被加载、成功 enable，并在观察窗口内保持运行？

结果应该比退出码或整段 `server.log` 更明确，同时保留足够原始证据供复查。

## 5. v0.1 范围

### 输入

- 一个插件 JAR；
- 一个 Paper/Minecraft 版本；
- 一个 Java major version 或 Java 可执行文件；
- 可选的、由用户明确提供的本地依赖插件 JAR；
- 可选超时、稳定观察窗口、报告路径和固定 Paper build。

### 预检

- JAR/ZIP 有效性；
- `plugin.yml` 是否存在且可读取；
- `name`、`version`、`main`；
- `main class` 是否存在；
- `api-version` 基本格式；
- 主类 JVM bytecode target；
- `depend`、`softdepend`、`loadbefore`；
- 插件 JAR SHA-256。

预检是快速发现明显错误的轻量检查，不是完整静态分析，也不替代真实运行。

### 运行验证

- 获取并校验指定 Paper build；
- 创建隔离临时目录；
- 接受 EULA；
- 放入目标插件和明确提供的依赖插件；
- 使用指定 Java 启动 Paper；
- 等待服务器 ready；
- 注入一个由 PluginMatrix 临时构建的轻量 runtime probe，通过 Bukkit/Paper `PluginManager` 和 `Plugin#isEnabled()` 读取目标插件状态；
- 观察插件发现、加载、enable、disable 和稳定性；
- 保存原始 `server.log`；
- 输出 CLI 结果和 JSON 报告。

### 状态

`ENVIRONMENT_INVALID`、`SERVER_START_FAILED`、`SERVER_START_TIMEOUT`、`PLUGIN_NOT_DISCOVERED`、`PLUGIN_LOAD_FAILED`、`PLUGIN_ENABLE_FAILED`、`PLUGIN_DISABLED`、`PASS`、`UNKNOWN_FAILURE`

## 6. 核心边界

`PASS` 的含义是：

1. 测试环境有效；
2. Paper 服务器达到 ready；
3. runtime probe 在服务器内部通过 `PluginManager` 找到目标插件；
4. runtime probe 读取到目标插件的名称/版本，并确认 `Plugin#isEnabled() == true`；
5. 观察窗口内插件没有被 disable；
6. 服务器没有在稳定窗口内异常退出。

Paper 日志仍用于确认 ready、发现/加载/enable 过程和提取失败原因；但成功结论不再只依赖 `Loading`/`Enabling` 文本，而要求 probe 的直接运行时证据。probe 无法产生有效状态时不会回退为 `PASS`。

`PASS` 不表示：

- 所有命令都可用；
- 所有事件和 GUI 都正常；
- 所有依赖服务都正确工作；
- 性能满足预期；
- 插件在其他 Paper、Java 或服务端实现上兼容；
- 完整游戏行为兼容。

## 7. v0.2 Compatibility Matrix

v0.2 adds a sequential matrix command without changing the single-environment verifier:

```text
pluginmatrix matrix matrix.json
```

The JSON configuration contains one plugin path, a non-empty `environments` array with `paper`, `java`, and optional `paper_build`, plus simple timeout, stability, artifact, and report options. Configuration is validated completely before any server starts. Each environment receives its own Runtime Verifier run, report, log, port, and artifact directory. A Matrix Report references those per-environment artifacts rather than copying full server logs.

Matrix exit codes are stable: `0` means all environments passed, `1` means the matrix completed with at least one failed environment, `2` means invalid configuration and no execution, and `3` means an unexpected PluginMatrix internal error.

`PASS` retains the v0.1 meaning: the existing runtime probe directly confirmed the target plugin through `PluginManager` and `Plugin#isEnabled()` during a stable real Paper run. It is not a claim of complete gameplay compatibility.

## 8. v0.3 GitHub Actions Integration

v0.3 adds repository-local CI integration around the existing CLI and Matrix runner:

- the normal `CI` workflow runs on `push` and `pull_request` and performs only offline tests, compilation, and syntax checks;
- the manual `Compatibility Matrix` workflow runs only on `workflow_dispatch`, uses GitHub-hosted Java 17, accepts a repository-relative Matrix config and plugin JAR, and invokes `python -m pluginmatrix matrix`;
- Matrix reports and per-environment runtime artifacts are uploaded on both success and failure;
- the Job Summary reads the generated Matrix JSON report instead of reimplementing verdict logic.

GitHub Actions does not change the product boundary: PluginMatrix does not manage arbitrary JDKs, build user plugins, download third-party dependencies, run Matrix environments in parallel, or publish releases. A hosted runner must already have a usable Java 17 path and a plugin JAR/configuration supplied by the workflow inputs.

## 9. v0.4 Configuration and Evidence Usability

v0.4 keeps the Runtime Verifier, sequential Matrix runner, and manual workflow architecture unchanged while making their prerequisites and evidence easier to act on:

- Matrix validates the plugin JAR, Java runtime version, JDK `javac`, and writable work/cache/report locations before any Paper server starts;
- configuration errors identify the field, current value, expected shape or prerequisite, and a concrete correction;
- Paper version and optional fixed-build failures retain the requested values and explain whether to correct or unpin the build;
- Matrix CLI failures name the environment, verdict, failure stage, reason, runtime report, `server.log`, run directory, and primary evidence before ending with the Matrix Report path;
- the Matrix Report keeps existing fields and adds the config source, preflight metadata, top-level artifact roots, and per-environment `primary_evidence`/artifact-availability references;
- GitHub Job Summary is rendered from the Matrix Report by tested package code and tolerates missing, corrupt, non-JSON, and non-object reports.

The manual workflow still supports Java 17 only and still uploads the Matrix report and runtime artifacts with `if: always()`. These usability changes do not add automatic JDK management, Paper variants, Matrix parallelism, or gameplay testing.

## 10. v0.5 Open-Source Release Readiness

v0.5 只完善公开源码所需的项目边界，不增加运行时验证能力：

- 提供根许可证、贡献、安全、行为准则、Issue/PR 模板、Changelog、版本策略和发布检查清单；
- 从单一代码属性生成打包版本，并验证 sdist、wheel、全新环境安装和 CLI 入口；
- 公开示例只使用仓库内带可审计源码、构建方法、用途和 hash 的 fixture；项目所有者已确认这些 fixture 的 Apache-2.0 发布权；
- 记录运行时下载、二进制 fixture 和只参考未复制项目的来源边界；
- 保留 v0.4 hosted 成功/失败验证事实，但来源或再分发授权不清楚的第三方 JAR 不进入公开仓库。

v0.5 不增加自动发布 workflow。`v0.5.0` 的正式发布由项目所有者在完成发布检查清单后手动授权；发布渠道仅为 GitHub Tag 与 GitHub Release，不发布 PyPI。

## 11. 非目标

v0.5.1 是 v0.5.0 可信度和安全修复，不扩展产品架构。成功证据必须来自本次 probe 协议，名称、版本、主类和实际加载路径匹配隔离目标，序列与采样时间持续增加；从 ready 后首个有效 enabled 样本开始完成整个稳定窗口，并取得窗口末端的新样本。两次有效更新的间隔不得超过 2 秒；identity mismatch 不被后续样本清除。配置只接受正数稳定窗口，`stability_window=0` 明确拒绝。

输入冲突包括文件名、插件名与 `provides` 别名；输出不得覆盖输入或通过符号链接、junction、硬链接写坏其他文件。单环境 report 写入失败继续后续 Matrix 环境，并以内部错误退出码反映保存失败。原始 `server.log` 保留字节，日志读取或进程清理失败不能支撑 PASS。

隔离目录与 probe 不是恶意代码沙箱。插件与 probe 在同一 JVM/操作系统用户权限下执行，故不能证明主动篡改文件、伪造日志/probe、自行脱离 POSIX 进程组的恶意插件安全。此类插件需要外部受限执行环境，本补丁不新增沙箱或容器平台。

当前不做：

- Web UI 或云端测试平台；
- Bot、GUI 自动化和完整 E2E 测试；
- AI 日志分析或自动修复；
- 自动下载第三方依赖插件；
- Spigot、Folia、Fabric、Forge、Velocity；
- 性能测试、压力测试和分布式服务器测试；
- 自动判断完整业务功能是否正确。

## 12. 成功标准

第一阶段成立的证据不是功能数量，而是：

- 开发者能用一条命令运行一次真实验证；
- 每个结果都有明确状态、失败阶段和原始日志；
- 固定 Paper build 后可以复现同一测试环境；
- 能区分至少一类环境失败与一类插件失败；
- EnhancedFly 之外，至少有其他类型插件可以被验证；
- 用户认为它比手写 Paper 启动和日志脚本更省事。

## 13. 未来扩展原则

未来的 CI 和行为测试都应建立在同一个可靠 Verifier 之上；Matrix v0.2 已是该 Verifier 的本地串行编排层。

扩展不应改变 v0.1 的基本语义：每个环境都必须有独立元数据、独立日志、独立状态和可复查证据。
