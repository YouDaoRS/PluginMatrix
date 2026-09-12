# PluginMatrix Development Status

更新日期：2026-09-12

## 当前阶段

**v0.5 Open-Source Release Readiness 已完成本地实现与离线闭环。**

> 在不改变 Runtime Verifier、串行 Matrix 和手动 workflow 总体架构的前提下，使仓库具备公开源码、干净安装、外部贡献和可重复发布前检查的基础。

当前实现是一个 Python CLI，要求 Python 3.10+，不依赖第三方运行时库。

## 已完成

### CLI 与打包

- `python -m pluginmatrix test` 命令；
- 可通过 `pip install -e .` 安装；
- 安装后提供 `pluginmatrix` 命令；
- `--version`、`--help` 和基本参数校验。
- v0.5 版本为 `0.5.0`，唯一字面版本维护在 `pluginmatrix.__version__`，打包元数据动态读取该属性；
- `pyproject.toml` 已补齐 README、Apache-2.0 SPDX、Python 要求、描述、URL、classifiers、keywords 和 release-only 构建工具 extra；没有伪造 authors/maintainers 身份；
- 已从隔离 checkout 构建 sdist/wheel、审计内容、在全新 venv 安装 wheel，并验证所有要求的 CLI 入口。

### v0.5 开源治理与来源边界

- 根许可证采用 Apache-2.0 官方原文，不填写未经确认的个人、邮箱、法律实体或版权声明；
- 新增 `CONTRIBUTING.md`、`SECURITY.md`、`CODE_OF_CONDUCT.md`、`THIRD_PARTY_NOTICES.md`、Issue forms 和 Pull Request 模板；
- 新增 `CHANGELOG.md`、`docs/VERSIONING.md` 与 `docs/RELEASE_CHECKLIST.md`；
- 完成代码、文档、workflow、fixture、二进制与只参考项目的来源分类；继续明确排除 GPL-3.0 代码、workflow、测试、注释和文件结构复用；
- `EnhancedFly-2.2.0.jar` 的 plugin metadata 虽指向同一 GitHub 账号，但仓库及可见源码 checkout 均没有 EnhancedFly 自身的明确许可证或再分发授权；v0.5 已将该 JAR 从公开仓库内容移除，历史 v0.4 hosted 结果仍保留为事实记录；
- 新增项目原创 `PluginMatrixSmoke` 成功 fixture，与原 enable-failure fixture 一并保留源码、descriptor、统一构建脚本、用途和 SHA-256；两个 JAR 均不含 shaded dependency；
- README 和所有可复制示例改用原创 fixture，说明 PASS 边界、系统/网络要求、相对路径、artifact 位置、常见故障、隐私风险和手动 workflow 成功/预期失败的区别。

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

### v0.4 GitHub Actions 维护

- 已通过 GitHub REST API 读取 [`Compatibility Matrix #2`](https://github.com/YouDaoRS/PluginMatrix/actions/runs/34685958473) 的真实 check annotations；两条黄色警告分别来自：
  - `actions/checkout@v4`、`actions/setup-python@v5`、`actions/setup-java@v4`、`actions/upload-artifact@v4` 仍以已弃用的 Node.js 20 为目标并被 runner 强制使用 Node.js 24；
  - `actions/setup-java@v4` 自身已弃用。
- 按 2026-09-12 官方稳定版本将受影响 Actions 更新为 [`checkout@v7`](https://github.com/actions/checkout/releases/tag/v7.0.1)、[`setup-python@v7`](https://github.com/actions/setup-python/releases/tag/v7.0.0)、[`setup-java@v6`](https://github.com/actions/setup-java/releases/tag/v6.0.1)、[`upload-artifact@v7`](https://github.com/actions/upload-artifact/releases/tag/v7.0.1)；四个 tag 的 `action.yml` 均声明 `using: node24`，未增加第三方 Action。
- checkout、Python 3.11、Temurin Java 17、两个 artifact 名称和路径、`if: always()` 上传、Job Summary 及最终 exit-code 保留逻辑不变。
- 新增静态测试，拒绝四个旧版本，固定当前版本、上传条件、`result.json`/`server.log` 路径和 embedded Python 语法。
- 版本升级后的真实 GitHub-hosted 成功与失败路径均已执行；两次运行的 warning annotations 均为 `0`，Node.js 20 与 `setup-java@v4` 弃用警告已消失。

### v0.4 Matrix 前置检查与配置诊断

- Matrix 在任何 Paper 进程启动或 artifact 下载前检查插件 JAR 预检、请求的 Java 版本/可执行文件、同一 JDK 的 `javac`，以及 work/cache/report 父目录的可创建与可写性；
- work 与 cache 使用同一路径、report 指向目录或与输出目录冲突会在执行前拒绝；
- 空 environment、重复/规范化后冲突 environment、非法 Paper 版本、非正整数 `paper_build`、timeout 和稳定窗口均报告精确字段与当前值；
- 配置/JAR 相对路径错误会同时显示原始值、解析后路径、配置文件相对路径规则，以及 hosted workflow 必须使用所选 branch 中已提交文件的修复提示；
- Paper API、版本、固定 build、下载和 checksum 失败信息保留版本/build/cache 当前值，并提供更直接的修复方向；
- 不下载 JDK、不自动修改配置，也不增加配置 DSL。

### v0.4 Report、Artifact 与失败证据

- Matrix CLI 在失败时输出 environment、verdict、failure stage、reason、primary evidence、runtime report、`server.log` 和 run directory；最后明确输出 Matrix Report 路径；
- 单环境 CLI 保持原命令和 exit code，并统一显示 Report、Server log 与 Run directory；自定义 report 的父目录现在会按需创建；
- Matrix JSON 保留既有字段，向后兼容地新增 `config_source`、`preflight`、顶层 `artifacts` 和每环境 `primary_evidence`/`artifact_availability`；启动前失败会明确标记 `server.log` 未生成，且仍不复制完整日志；
- Job Summary 渲染移入可离线测试的 `pluginmatrix.github_summary`，只消费 Matrix Report 的 verdict/stage/evidence，不重新实现 verifier 状态判断；
- Job Summary 对报告缺失、损坏 JSON、非 UTF-8、非对象顶层和部分字段异常保持容错，并指向 setup log 或 runtime artifact。
- 新增项目自有源码的 `PluginMatrixEnableFailure` fixture；它通过 JAR 预检并在 `onEnable()` 抛出固定异常。本地真实 Paper 1.20.1/build 196/Java 17 已确认得到 `PLUGIN_ENABLE_FAILED`、`plugin_enable` 和可用的 runtime report/`server.log`，可用于 hosted 失败回归。
- 使用 v0.4 当前代码在本地重新运行 EnhancedFly 2.2.0 / Paper 1.20.1/build 196/Java 17，得到 `PASS` 和 `1 passed, 0 failed`；成功与失败两条本地真实路径均已通过。

### 测试

- 预检模块有单元测试；
- Runtime evidence 有离线 fake-server 测试；
- 已覆盖正常启动、插件未发现、依赖缺失、load 失败、`onEnable` 异常、插件被 disable、Paper 启动失败、启动超时和网络/环境失败；
- 新增配置字段/路径诊断、无效插件、Java/JDK、输出目录冲突、Paper 固定 build、artifact 引用、CLI 失败摘要、单环境 CLI、Job Summary 成功/失败/损坏报告和 Action 版本回归测试；
- 当前测试套件共 58 项，全部通过；
- 已验证 `compileall`；
- 已验证 editable install、隔离 sdist/wheel 构建、全新 wheel 安装和命令入口；
- 已使用真实 Paper 服务器完成多插件 E2E。

## 当前验证结果

GitHub-hosted v0.3.1 基线：

- Workflow：`Compatibility Matrix #2`；
- Commit：`7ffe94b`；
- Paper `1.20.1` / build `196` / Java `17`；
- EnhancedFly `2.2.0`：`PASS`；
- Job Summary：`1 passed, 0 failed`；
- Artifacts：`pluginmatrix-matrix-report`、`pluginmatrix-runtime-artifacts`。

GitHub-hosted v0.4 闭环验证（commit `c5fe4ef`）：

- [`Compatibility Matrix #3`](https://github.com/YouDaoRS/PluginMatrix/actions/runs/34687494718)：EnhancedFly 2.2.0 / Paper 1.20.1/build 196 / Java 17，结果 `PASS`，Summary 为 `1 passed, 0 failed`；warning annotations 为 `0`；`pluginmatrix-matrix-report` 与 `pluginmatrix-runtime-artifacts` 均存在、未过期且有非空内容。
- [`Compatibility Matrix #4`](https://github.com/YouDaoRS/PluginMatrix/actions/runs/34687590131)：项目自有 `PluginMatrixEnableFailure` fixture 在真实 Paper `onEnable()` 阶段失败；Matrix 正确报告 `PLUGIN_ENABLE_FAILED`、`plugin_enable`、指向 `server.log` 的 `primary_evidence` 和 `0 passed, 1 failed`；workflow 按预期以 exit code `1` 失败；warning annotations 为 `0`；两个 artifacts 均在失败后保留、未过期且有非空内容。

这两次运行确认了 Action 升级、成功 Summary、失败 Summary、失败 evidence 和 `if: always()` artifact 上传，v0.4 hosted 验证已闭环。

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

- v0.5 本地结构、来源、打包、干净安装、离线测试和编译检查已完成；
- v0.4 已在 GitHub-hosted runner 上完成一次真实成功路径和一次真实 plugin enable 失败路径；
- 两次 hosted 运行均确认弃用警告消失、Summary 正确和两个 artifacts 可用；
- v0.5 没有触发远程 workflow；真正发布前仍应使用新的原创 success fixture 与现有 failure fixture 各做一次 hosted smoke；
- 人工步骤和输入示例见 README 与 `docs/RELEASE_CHECKLIST.md`。

## v0.5 本地验证结果

- 完整离线测试：58/58 通过；
- `python -m compileall pluginmatrix tests ci-fixtures/build_fixtures.py`：通过；
- 隔离 checkout 构建：`pluginmatrix-0.5.0.tar.gz` 与 `pluginmatrix-0.5.0-py3-none-any.whl` 均成功；
- archive 审计：sdist 67 entries、wheel 16 entries；无 `.pluginmatrix`、cache/runs、`__pycache__`、`.pyc`、build/dist、虚拟环境、EnhancedFly 或 fixture JAR；
- wheel metadata：名称、0.5.0、Python >=3.10、Apache-2.0、LICENSE 和项目 URL 均正确；
- 全新 venv 从 wheel 安装后，`pluginmatrix --version`、`pluginmatrix --help`、`python -m pluginmatrix --version`、`test --help` 与 `matrix --help` 均通过；
- 打包期间没有 setuptools license 弃用警告；临时验证目录位于系统临时目录，不进入工作树；
- 本阶段没有下载/启动 Paper，没有触发远程 workflow，没有发布 PyPI、Release 或 Tag，也没有 commit/push。

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
- preflight 会验证 Paper 版本格式和 `paper_build` 类型；某个 build 是否真实存在仍由该环境执行前的官方 Paper API 查询确认；
- 输出目录可写性是在 preflight 时探测，之后仍可能因权限或磁盘状态变化而失败；
- v0.4 workflow 已完成静态检查及 GitHub-hosted 成功/失败路径验证。

## 当前阶段结论

**v0.5 Open-Source Release Readiness 已达到可以公开源码的本地仓库状态，但尚未正式发布。**

Runtime Verifier、串行 Matrix 和手动 workflow 架构未重做。公开前项目所有者仍应启用 GitHub private vulnerability reporting 并检查仓库首页的 Apache-2.0 检测结果；真正发布前还要执行原创 success/failure hosted smoke，并由所有者单独授权 Tag、GitHub Release 或 PyPI 发布。完成这些发布动作不属于 v0.5，也没有进入 v0.6。
