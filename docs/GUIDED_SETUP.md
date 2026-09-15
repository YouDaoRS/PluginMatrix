# Guided Setup / 使用指南

Source candidate: **0.9.0rc1**. Public stable release: **0.8.0**.
This development branch is not a published release.

## 简体中文

从此分支安装后运行 `python -m pluginmatrix web`，或启动对应的候选独立程序。
默认只监听 `127.0.0.1`，所有插件、配置、结果都留在本机。

### 首次验证

1. 选择插件 JAR，点击“分析并继续”。缺失依赖、名称/别名冲突、循环依赖需要先处理。
   依赖只能选择你已有的本地 JAR，不会自动下载 Vault、WorldEdit 等插件。
2. 明确填写准备验证的 Minecraft 版本。查询官方环境建议，核对 Provider、固定 build、
   Java 来源和未决项，再选择“采用已确认的建议”。版本列表更新不会替换你的目标。
3. 确认页展示实际环境及可编辑的检查。确认信任 JAR、接受 Minecraft EULA 后开始验证。
   运行时、行为与最终结果分别显示，原始 `server.log` 和报告保留。

`api-version` 是最低 API 声明，不是支持版本范围；静态分析和环境建议都不是 PASS。
未知 Java 基线保持未决，可以在高级模式明确选择 JDK 并验证，不能把“Java 更新”视为兼容性证明。

### 验证方案

| 方案（revision 1） | 默认启动 / 稳定时间 | 约束 |
| --- | --- | --- |
| quick | 120 / 5 秒 | 单环境，不自动建议检查 |
| standard | 180 / 10 秒 | 单环境，建议命令和权限注册检查 |
| matrix | 180 / 10 秒 | 2–256 个明确环境，并发 1–8 |
| strict | 240 / 30 秒 | 固定官方 build、完整的受支持静态分析、至少 30 秒稳定窗口 |

方案不是“兼容性等级”。建议只生成 `command_registered`、`permission_registered`，
不会根据命令名称执行控制台操作。动态注册、服务和玩家行为不能静态推断。
通配权限等不能表示的声明会列出为未生成项。
编辑、导入、保存和再次运行不会重新生成你已确认的 Behavior 检查。
高级模式仍可明确配置 v0.8 支持的五类检查。

### 项目、配置与历史

- 保存项目后，浏览器选择的 JAR 副本持久保存在 Web state 的 `inputs` 下。
  直接填写的本地路径不会被修改或删除。只生成 JSON、不保存或运行时，上传副本仍属临时文件。
- 项目保存规范化 schema 2、profile revision、托管 JDK ID/目录、明确的检查和 SHA-256。
  可以修改项目名称后再次保存；JSON 文本修改使用“校验并应用 JSON”。
- 按本地路径导入可正确解析相对路径。通过浏览器选择 JSON 时，浏览器不提供原始目录；
  配置应使用绝对路径，或先填写真实的配置路径作为相对路径基准。
- Web 运行的报告、工作目录和服务端缓存由本地进程分配，避免覆盖历史证据。
  导入/导出的原始输出选项仍完整保存。托管 JDK 目录不会被替换。
- 运行历史保留最近 64 项可见记录；旧证据不自动删除。重启后恢复已完成结果和 artifact
  身份，不重新读取日志计算 verdict。中断的任务标记为中断，没有补造 PASS。
- “恢复失败环境”依据核心 `verification_passed=false` 选择环境。若只剩一个环境，
  移除不适用的 matrix profile，但保留 schema 2、原有超时和全部明确检查；确认后再运行。
- artifact 被替换、编辑或变成链接时，访问会被拒绝，而不是展示成原始证据。

### JDK 与缓存

“下载与缓存”中先预览官方 Temurin GA full JDK，核对 release、平台、大小、官方 SHA-256
及来源，再点击下载。使用的是可移动归档，不执行 MSI 或系统安装器，不修改系统 Java。
`not_checked` 只表示列出了 receipt；“校验完整性”会验证整个已解压树，运行前也会校验。
运行中的托管 JDK 有跨进程租约，删除会被拒绝。
Linux/macOS TAR 中指向同一 JDK 目录内普通归档文件的符号链接会转换为独立副本，
计入解压限额及完整性清单。越界、目录链接、链接链/循环、硬链接和特殊文件仍拒绝，
安装目录不创建文件系统链接。

缓存目录可以在高级模式中明确指定。导入配置的 `java.managed` 和 `options.jdk_dir`
是一组引用，不能只把它替换为 executable 路径。
失败下载不会发布为安装成功；中断暂存目录与正式安装条目分开，不支持通用递归清理。

服务端下载要求明确的官方 Provider、Minecraft 版本和固定 build。
缓存校验检查已有 SHA-256 receipt；重新下载/使用时由 Provider 校验官方算法。
安全删除只移除已识别的 JAR 与对应 receipt，不删除系统文件、锁文件、bootstrap runtime
目录、第三方插件、用户输入或报告。未识别文件只显示诊断，不提供强制删除。

### 结果与排错

| 结果 | 处理方向 |
| --- | --- |
| ENVIRONMENT_INVALID | 核对报告里的具体前置条件、完整 JDK/javac、依赖与目录权限 |
| SERVER_START_FAILED / TIMEOUT | 先看 server.log 的首个启动/bootstrap 错误和网络下载进度 |
| PLUGIN_LOAD_FAILED / ENABLE_FAILED | 核对描述符、字节码、明确本地依赖及 onLoad/onEnable 异常 |
| PLUGIN_DISABLED | 查看禁用原因与最后的新鲜探针证据 |
| Runtime PASS + Behavior 失败 | 检查明确断言、typed observation 和 post-check health，不能改写 Runtime PASS |

建议是基于已知状态的确定性处理方向，不是 AI 日志分析或自动修复。
PASS 只证明本次固定环境和观察窗口；Folia PASS 不证明线程/跨 region 安全。
PluginMatrix 不是恶意代码沙箱，只运行可信 JAR。

## English

Run `python -m pluginmatrix web` from this candidate checkout. Select a local plugin,
resolve local dependency diagnostics, choose an explicit Minecraft target, review the
official build/JDK recommendation, then confirm the profile and editable checks.
Guided mode keeps advanced fields out of the main flow; Advanced shows the complete editor.

Profiles are immutable versioned policies, not compatibility scores. Strict requires
fixed official builds, supported complete static analysis and at least 30 seconds of
stability. Generated checks observe command/permission registration only, never console
execution. Import/edit/export/rerun preserves explicit checks rather than regenerating them.

Save a project to retain browser-selected JARs after the Web process exits. A local
config-path import resolves relative paths beside that file. Browser JSON selection
cannot reveal its original directory: use absolute paths or supply the real config source
path. JSON editing rejects duplicate/unknown fields through the shared parser.
Web runs use fresh owned output locations, while saved/exported options are preserved.

Projects preserve schema/profile revision, managed IDs/store, checks and configuration/input
hashes. History restores the latest 64 records and original artifact identities. Changed
inputs are reported; changed evidence is not served. Failed-environment restore uses the
application's combined result. A one-environment retry removes only an inapplicable
`matrix` profile, retaining concrete options and checks.

Temurin installation is an explicit preview/download action using official metadata,
size/SHA-256 verification, bounded extraction, atomic publication and per-process leases.
No system Java settings change. A listing is not a fresh integrity verification.
Direct internal TAR symlinks become independent, bounded, manifest-checked regular
copies. Escapes, directory links, link chains/cycles, hardlinks and special files
are rejected; installed trees contain no filesystem links.
Server cache deletion is limited to recognized JAR/receipt pairs; persistent locks,
bootstrap caches and unrelated files remain. There is no recursive cleanup button.

## CLI Examples

```console
python -m pluginmatrix analyze --plugin ci-fixtures/PluginMatrixSmoke.jar
python -m pluginmatrix profiles
python -m pluginmatrix recommend --plugin ci-fixtures/PluginMatrixSmoke.jar --minecraft 1.20.1 --build 196 --network
python -m pluginmatrix init matrix.json --plugin ci-fixtures/PluginMatrixSmoke.jar --minecraft 1.20.1 --build 196 --java 17 --profile standard
python -m pluginmatrix matrix matrix.json
```

`--json` preserves machine-readable output. `init` also accepts repeated `--dependency`,
`--jdk-dir`, `--behavior`, and `--no-suggestions`. The examples under `examples/guided-*.json`
use only repository-owned fixtures.

```console
python -m pluginmatrix jdk preview --major 17
python -m pluginmatrix jdk install --major 17 --id <reviewed-id>
python -m pluginmatrix jdk list
python -m pluginmatrix jdk verify --id <installed-id>
python -m pluginmatrix test --plugin ci-fixtures/PluginMatrixSmoke.jar --paper 1.20.1 --paper-build 196 --java managed:<installed-id> --profile quick
python -m pluginmatrix jdk remove --id <installed-id>
```

Replace placeholders with the exact opaque IDs returned by preview/install.
Use the same `--directory` for JDK operations and `--jdk-dir` for verification when
choosing a nondefault store. Config load, validation and execution never download a JDK.
Native acceptance results and remaining platform limits are recorded in [STATUS.md](STATUS.md).
