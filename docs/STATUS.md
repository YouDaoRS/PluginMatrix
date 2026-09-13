# PluginMatrix Development Status

更新日期：2026-09-13。

当前开发版本 **0.6.0.dev0**；公开稳定版本仍为 **v0.5.1**。本次工作在 `codex/multi-server-core` 本地开发分支上，不创建 Tag、GitHub Release，不发布 PyPI，不修改已发布版本或历史。

独立关键路径审查已修复来源绕过、输出覆盖/锁、异常取消、清理中断及特殊缓存文件问题，见 [CRITICAL_PATH_REVIEW.md](CRITICAL_PATH_REVIEW.md)。最新离线回归为 155 项（152 通过、3 项平台/权限跳过）。本轮真实并行 Matrix 两次出现 Folia probe 超过 2 秒未更新，严格返回 UNKNOWN_FAILURE；下文较早的全通过记录不能替代本轮失败证据，Release Gate 仍未通过。

## 已实现

- 单一 Runtime Verifier + Server Provider 层：配置、能力描述、官方 version/build、完整性、cache identity、启动参数、ready/startup/shutdown 解释、CodeSource 规则和报告 metadata。
- Paper 保留旧配置/CLI/报告字段和下载 cache 布局；新旧字段混用明确拒绝。新增语义使用 `server` 对象；未知字段不再静默忽略。
- Purpur 官方 API、固定/latest build、独立 cache namespace；校验官方 MD5，另外记录与固定本地 SHA-256。
- Folia 官方构建与渠道、regionized 标记、global region scheduler probe、`PLUGIN_UNSUPPORTED` 声明 verdict。PASS 不证明线程安全、跨 region 安全或完整功能。
- local/custom JAR：明确名称/version/runtime/metadata、只读输入、复制后 hash 校验、`official=false`，未知运行契约 fail closed。
- CLI：`init`、`validate [--network] [--json]`、`doctor [--offline] [--json]`、`providers [--json]`、`report --html`；不自动安装 Java。
- 静态单文件 HTML：JSON 为权威，动态内容转义、相对 artifact 路径、元数据/证据展开、Folia 限制、无外部脚本和原始日志内嵌。
- Matrix 默认 1、上限 8 个 worker；环境独立、结果保持配置顺序，失败继续；跨线程/进程缓存锁与原子发布，取消后完整等待所有 worker/进程树清理。
- `pluginmatrix.application` 服务接口、`RunControl` 取消与结构化 progress events；CLI 复用服务，不实现 GUI。
- 项目自有 Folia success/unsupported/enable-failure 源码 fixture；新二进制只构建到本地忽略目录，原有两个已提交 fixture/hash 未改动。
- 新手动 `Provider Gate` workflow 支持 Linux/Windows。公网/真实 JVM 测试继续与普通离线 CI 分离。

架构与接口见 [ARCHITECTURE.md](ARCHITECTURE.md)、[APPLICATION_API.md](APPLICATION_API.md)。

## 验证记录

本次独立运行的开发 Gate（不是沿用 v0.5.1 的测试结论）：

| Gate | 结果 |
| --- | --- |
| Windows Python 3.11.9 离线回归 | 139 项：137 通过，2 项 symlink 权限跳过；31.597 秒 |
| Windows Python 3.10.21 离线回归 | 139 项：137 通过，2 项 symlink 权限跳过；31.851 秒 |
| compileall / sdist / wheel | Python 3.10/3.11 compileall 通过；离线回归内的 sdist/wheel 构建及内容审计通过 |
| 新 Provider/application/parallel 测试 | API 损坏、URL/文件名/hash、缓存冲突与并发、descriptor/Folia、local 原始 JAR/alias 保护、旧配置、CLI JSON、HTML 注入、顺序/失败继续/取消、真实 Windows 子孙进程清理 |
| 真实 Paper 1.21.4 build 232 | success PASS；预期 PLUGIN_ENABLE_FAILED |
| 真实 Purpur 1.21.4 build 2416 | success PASS；预期 PLUGIN_ENABLE_FAILED；latest 解析为 2416 |
| 真实 Folia 1.21.4 build 6 / ALPHA | supported PASS；预期 PLUGIN_ENABLE_FAILED；unsupported 返回 PLUGIN_UNSUPPORTED，预检阻止下载/启动 |
| 混合 Paper/Purpur/Folia Matrix | max_parallel=1 和 3 都为 3/3 PASS，顺序、独立 port/run/probe/artifacts 保持 |
| local 用户提供 Paperclip JAR | PASS，输入 SHA-256 未改变，报告 official=false |
| 较新服务端 CodeSource | Paper/Purpur/Folia 都为预期的隔离 .paper-remapped 目标路径 |
| 旧 Paper 1.20.1/196 / JDK 17 | 4/4：PASS、PLUGIN_ENABLE_FAILED、noise/invalid UTF-8 PASS、PLUGIN_DISABLED；原始字节与完整窗口通过 |
| 报告 | JSON、HTML、runtime metadata、Summary、原始 server.log、progress JSONL 均保留 |

真实 Provider Gate 使用临时 JDK 21.0.12.1（官方 Temurin ZIP 校验 SHA-256，未修改系统 Java/PATH）。共 14 项结论全部匹配预期；成功的三种官方服务端均保留完整稳定窗口证据。最初一轮发现 Windows 交互控制台无换行提示符使日志无法完全消费，严格返回 UNKNOWN_FAILURE；修复为 Provider 关闭 JLine/ANSI、进程 stdin=DEVNULL 后重新完整运行通过，未放宽任何 probe/日志/稳定要求。

本机证据（未提交生成物）：

- Provider 最终 Gate：`C:\Users\11580\AppData\Local\Temp\pluginmatrix-06-gate-d2ueo5vp\gate-summary.json`。
- 同目录含单环境 JSON/HTML、`matrix-1.json/html`、`matrix-3.json/html`、两份 Summary、`progress.jsonl` 和原始 run/log。
- 首轮失败证据保留于 `C:\Users\11580\AppData\Local\Temp\pluginmatrix-06-gate-0nqch4pf`。
- 本地最终测试日志：`.pluginmatrix/final-py311.log`、`.pluginmatrix/final-py310.log`；旧 Paper Gate：`.pluginmatrix/legacy-paper-gate.log`。
- 旧 Paper Gate 原始证据：`C:\Users\11580\AppData\Local\Temp\pluginmatrix-051-gate-1z00vz8h\summary.json`。相对于 106 项 v0.5.1 基线新增 33 项高价值测试；旧安全回归未删减。

## 真实限制与未完成 Gate

- 本次未执行 Linux/远程 hosted 验证。本机仅有 Docker Desktop WSL，Docker Linux daemon 未运行；当前任务未获得明确的本分支 push/远程执行授权。保留本地提交，不能把既有 v0.5.1 hosted 结果当作本次通过证据。
- Windows symlink 创建权限不足，2 项跳过；junction、hardlink、Job Object 及取消子孙进程清理实际执行。Linux symlink/POSIX 验证仍是下一次独立审查/Release Gate 的必需项。
- local 是受支持运行契约，不承诺所有 Spigot/未知 fork 布局均能运行。不支持自动 BuildTools；复杂 Paper bootstrapper/loader/dependencies descriptor 明确拒绝。
- Folia 构建渠道保留 ALPHA，Folia PASS 无线程/跨 region 安全含义。Purpur 上游仅提供 MD5，本地 SHA-256 不伪称为上游加密签名。
- 取消是协作式：正在执行的 HTTP 操作最多等其 30 秒超时，javac 最多 60 秒；进程清理有独立有界等待。外部进程仍可抢占刚分配的端口，这会产生显式启动失败。
- PluginMatrix 不是 hostile-code sandbox，不证明恶意插件安全；不增加遥测，不上传插件/日志。
- 本次未发布；适合提交下一次独立审查，正式 Release Gate 仍需新候选 revision 的完整 hosted 验证与单独发布授权。

历史 v0.5.1 发布结果完整保留于 [V0.5.1_PREPARATION.md](V0.5.1_PREPARATION.md) 和 [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md) 的历史段落。
