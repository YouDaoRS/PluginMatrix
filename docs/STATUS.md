# PluginMatrix Development Status

更新日期：2026-09-12

## 当前阶段

当前处于 **v0.3.1 Hosted CI Validation and Open-Source Reference Audit** 阶段：

> 在不改变 Runtime Verifier 和 Matrix 核心逻辑的前提下，完成 GitHub-hosted 验证准备、workflow 静态审计和有限的开源参考审计。

当前实现是一个 Python CLI，要求 Python 3.10+，不依赖第三方运行时库。

## 已完成

### CLI 与打包

- `python -m pluginmatrix test` 命令；
- 可通过 `pip install -e .` 安装；
- 安装后提供 `pluginmatrix` 命令；
- `--version`、`--help` 和基本参数校验。

### 插件预检

- 检查 JAR 是否存在、是否为有效 ZIP；
- 检查 `plugin.yml`；
- 读取插件名称、版本、主类和 `api-version`；
- 检查主类 `.class` 是否存在；
- 读取主类 bytecode major version；
- 读取 `depend`、`softdepend`、`loadbefore`；
- 计算插件 JAR SHA-256。

### Paper 环境

- 使用 Paper 官方 `fill.papermc.io/v3` API 查询 build；
- 默认选择最新稳定 build；
- 支持 `--paper-build` 固定 build；
- 下载 Paper server JAR；
- 校验 Paper JAR SHA-256；
- 使用隔离运行目录；
- 自动写入 `eula.txt`；
- 支持用户明确提供的本地依赖插件 JAR。

### Runtime Verifier

- 验证 Java 可执行文件和实际 major version；
- 启动真实 Paper 进程；
- 使用非阻塞日志读取，避免无输出时卡死；
- 等待 Paper ready；
- 观察插件发现、加载、enable、disable 和稳定窗口；
- 运行过程中采集结构化 lifecycle evidence，并记录事件时间戳、来源和原始日志行；
- 每次运行临时注入轻量 runtime probe，在真实 Paper 进程内通过 `PluginManager#getPlugin`、`Plugin#getDescription` 和 `Plugin#isEnabled` 读取目标插件状态；
- probe 结果通过原子快照文件回传主进程，成功判断不再只依赖日志中的 `Loading`/`Enabling` 文本；
- Paper bootstrap 成功后缓存 `cache/`、`libraries/` 和 `versions/`，后续隔离运行可复用已下载的运行时文件；
- 将环境失败、服务器失败、插件加载失败、插件 enable 失败、插件 disable 和启动超时分开归类；
- 保存原始 `server.log`；
- 输出 JSON 报告；
- 根据阶段返回结构化状态和 CLI 退出码。

### Matrix Readiness

- 每次验证使用 `run-<timestamp>-<uuid>` 唯一目录，运行中的 server、plugins、probe、日志和报告互不共享；
- 每次运行写入独立的 `server.properties`，通过本机临时 TCP 端口和 `127.0.0.1` 绑定，避免默认依赖 25565；
- Paper 进程在 PASS、失败、超时和异常路径都经过统一清理；Windows 下超时会使用进程树终止，避免留下子进程；
- 运行产物默认保留，便于复查日志、probe 快照和 JSON 报告；
- 连续运行多个任务后完成隔离验证，未发现上一 run 污染下一 run 的问题。

### Compatibility Matrix v0.2

- 新增 `pluginmatrix matrix <config>` 命令；
- 使用标准库 JSON 配置，支持插件路径、多个 Paper/Java 环境、可选固定 Paper build 和超时/稳定窗口/缓存/报告路径；
- 配置在执行前整体校验，非法配置不会启动任何环境；
- 环境按配置顺序串行执行，单个环境失败不会阻止后续环境；
- 每个环境复用 `runtime.verify()`，保留独立 run directory、server.log、runtime report 和 evidence；
- 生成统一 Matrix JSON Report，记录请求/解析后的环境、verdict、失败摘要、artifact 引用和统计；
- 定义 Matrix exit code：`0` 全部通过、`1` 至少一个环境失败、`2` 配置错误、`3` 未预期内部错误；
- README 提供可直接运行的 `matrix.json` 示例。

### GitHub Actions v0.3

- 新增 `CI` workflow，在 `push` 和 `pull_request` 上运行 `pip install -e .`、`compileall` 和离线测试；
- 新增独立的手动 `Compatibility Matrix` workflow，仅响应 `workflow_dispatch`；
- 手动 workflow 接受仓库内 Matrix JSON 配置和插件 JAR 路径，固定使用 GitHub-hosted Java 17；
- workflow 调用现有 `python -m pluginmatrix matrix`，不复制 Matrix Runner 或 verdict 逻辑；
- 配置/JAR/Java 前置条件失败会在启动 Matrix 前明确报错；
- 无论 Matrix 成功或失败，均尝试上传 `pluginmatrix-matrix-report` 和 `pluginmatrix-runtime-artifacts`；
- Job Summary 从 Matrix JSON Report 读取插件、环境 verdict、统计和 artifact 名称；
- 未添加 secrets、`pull_request_target`、发布凭据或自动 Release/Issue/Comment。

### v0.3.1 Hosted CI 验证准备

- 已确认手动 workflow 需要仓库内的 Matrix JSON 配置和已存在于 checkout 的插件 JAR；
- 已确认 workflow 固定使用 GitHub-hosted `ubuntu-latest`、Temurin Java 17，并要求 runner 能访问 Paper API、Paper 下载源及 Paper bootstrap 所需网络；
- 已修复生成于 `.ci/matrix.json` 的临时配置路径，使插件、cache、run directory 和 Matrix report 正确解析到预期位置；
- 已增加插件 JAR 复制失败的明确 setup error；
- 已修复 Job Summary 对损坏、非 JSON 或非对象报告的容错，报告不可用时会提示检查上传的 runtime artifacts 和 setup errors；
- `Upload Matrix report` 与 `Upload runtime artifacts` 仍使用 `if: always()`，Matrix 在已启动环境中失败时仍会尝试保留报告和原始日志；
- 已新增 `docs/THIRD_PARTY_REVIEW.md`，记录三个指定项目的 revision、许可证、维护状态、设计差异和复用决定；
- 本次没有复制或引入任何外部代码、第三方 JAR 或许可证文件。

### 测试

- 预检模块有单元测试；
- Runtime evidence 有离线 fake-server 测试；
- 已覆盖正常启动、插件未发现、依赖缺失、load 失败、`onEnable` 异常、插件被 disable、Paper 启动失败、启动超时和网络/环境失败；
- 当前测试套件共 31 项，全部通过；
- 已验证 `compileall`；
- 已验证 editable install 和命令入口；
- 已使用真实 Paper 服务器完成多插件 E2E。

## 当前验证结果

以下三个插件均在 Paper 1.20.1 / Paper build 196 / Java 17 上得到真实 `PASS`：

- EnhancedFly 2.2.0；
- BetterRTP 3.6.13；
- EssentialsX 2.22.0。

跨版本 smoke 结果：

- EnhancedFly 2.2.0 在 Paper 1.19.4 / build 550 / Java 17：`PASS`；
- EnhancedFly 2.2.0 在 Paper 1.20.4 / build 499 / Java 17：`PASS`。

两次 smoke 均成功完成 server ready、runtime probe、稳定窗口和进程清理。

三次运行都记录了：

- server process started；
- Paper server ready；
- target plugin discovered；
- plugin enable started；
- plugin enabled（由 runtime probe 直接读取 `Plugin#isEnabled() == true`）；
- stability window 通过。

另外，使用真实 Paper 1.20.1/build 196 运行了一个带缺失 `DefinitelyMissing` 依赖的 fixture 插件，结果正确归类为 `PLUGIN_LOAD_FAILED`，而不是环境失败或启动超时。

此前网络受限的运行也被保留为失败样本：Paper 在下载 `mojang_1.20.1.jar` 时出现 `java.net.SocketException: Connection reset`。该运行不会再被简单归为模糊的插件启动失败，而会保留环境失败证据和原始日志。

## 当前 verdict 规则

verifier 先在运行过程中生成 evidence，再由 evidence 归纳最终 verdict，优先级如下：

1. 环境/基础设施失败；
2. 插件 load 失败；
3. 插件 enable 失败；
4. 插件被 disable；
5. Paper 服务器失败或退出；
6. Paper 未 ready 时的启动超时；
7. Paper ready 但目标插件没有发现证据；
8. Paper ready 但没有 enable 证据；
9. 服务器 ready、runtime probe 直接确认目标插件存在且 enabled，并在稳定窗口内仍运行：`PASS`。

当前 `PASS` 的真实含义是：目标插件在指定 Paper/Java 环境中被服务器的 `PluginManager` 发现，`Plugin#isEnabled()` 在 probe 快照中为 `true`，服务器达到 ready，且在稳定观察窗口内没有观察到插件被 disable 或服务器退出。probe 缺失或写入失败时不会把日志中的 enable 文本升级为 `PASS`。

## 当前验证边界

- 本地结构验证、离线测试和编译检查已完成；
- GitHub-hosted runner 的真实手动 workflow 尚未执行；
- 该真实执行是本 milestone 唯一仍需用户完成的外部操作，不能由本地检查替代；
- 本工作区没有可用的 `.git` 元数据，因此无法可靠报告当前 branch、commit、remote 或 git diff；没有据此猜测远程仓库信息；
- 人工步骤和输入示例见 README 的 `Manual hosted validation`。

## 下一阶段

- 唯一推荐的下一完整 milestone 是 **v0.4 Hosted Matrix Configuration and Evidence Usability**：
  - 用户价值：降低准备测试仓库、理解前置失败和定位 hosted 运行证据的成本；
  - 现在做的原因：v0.3.1 已完成本地与静态验证，下一项最大不确定性是 hosted 使用反馈和证据可读性，而不是更多 Matrix 环境；
  - 范围：更明确的配置/JAR 前置诊断、更稳定的 report/artifact 引用、失败证据展示和测试仓库准备体验，继续复用现有 Runtime Verifier 与串行 Matrix；
  - 不做：并行 Matrix、Marketplace、新服务端实现、Web UI、Bot、行为测试 DSL、第三方依赖自动下载；
  - 完成标准：用户可按文档准备一个测试仓库，在 hosted runner 上得到稳定的成功/失败状态，且每种结果都有可下载的 report、`result.json` 和 `server.log` 或明确说明为何没有运行产物；
  - 风险与许可证：主要风险是 GitHub/Paper 网络、runner 环境和输入路径差异；不需要引入外部代码，许可证风险低。

## 尚未开始

- Web Dashboard；
- Bot 或 GUI 行为测试；
- 完整 E2E 测试 DSL；
- AI 日志分析；
- 自动修复；
- 第三方依赖自动下载；
- Spigot/Folia/Fabric/Forge/Velocity；
- 云端测试平台；
- 性能和压力测试。

## 已知限制

- server ready 仍主要依据 Paper 的 `Done` 日志 marker；
- 失败阶段和关键异常仍主要通过日志 marker/异常文本归类；
- probe 只能观察 `PluginManager` 注册状态和 `isEnabled()`，不验证命令、事件、GUI、外部服务或完整业务行为；
- probe 需要可用 JDK 的 `javac`，并依赖目标 Paper artifact 中可提取的编译库；
- 直接状态是稳定观察窗口中的采样，不是对插件整个生命周期的形式化证明；
- 轻量 `plugin.yml` 解析器不是完整 YAML 实现；
- 当前只检查主类 bytecode，不扫描插件全部 class；
- `--java 17` 会验证当前可用 Java，不会自动安装或管理 JDK；
- Paper bootstrap 可能在首次启动时继续下载 Mojang 运行时文件；
- 当前没有自动注入或验证第三方插件依赖；
- 当前 `PASS` 只代表服务器启动和插件运行时初始化兼容性，不代表完整功能兼容。
- Matrix 当前只串行执行，不提供并行调度；
- Matrix 配置格式当前为 JSON，不是通用 YAML/DSL；
- Matrix 仍继承 Runtime Verifier 对 Paper ready 和失败原因的日志启发式依赖；
- Matrix 真实环境仍可能受 Paper bootstrap 网络和本机 Java 可用性影响。
- GitHub-hosted runner 无法替用户构建任意插件；手动 workflow 要求输入的插件 JAR 已存在于 checkout 中；
- 当前手动 workflow 只支持 Java 17 配置，其他 Java 组合会在执行前失败；
- 本地 workflow 静态检查已完成，但本环境未直接执行 GitHub-hosted runner。

## 当前阶段结论

**v0.3 GitHub Actions Integration 已实现，v0.3.1 的本地准备、workflow 修复和参考审计已完成。**

EnhancedFly 已在 Paper 1.19.4/build 550、1.20.1/build 196、1.20.4/build 499 与 Java 17 上完成真实 Matrix PASS。当前工作区已具备离线常规 CI 和手动真实 Matrix workflow；workflow 本身尚未在 GitHub-hosted runner 上执行，等待用户在实际插件测试仓库中手动触发验证。
