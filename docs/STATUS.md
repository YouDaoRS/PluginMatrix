# PluginMatrix v0.6 Release Candidate Status

更新日期：2026-09-14。

当前候选版本为 **0.6.0rc1**；公开稳定版本仍为 **v0.5.1**。候选分支是 `codex/multi-server-core`。本轮不创建 Tag 或 GitHub Release，不发布 PyPI，不修改 v0.5.0/v0.5.1 或历史。

结论：v0.6 Release Candidate Gate 已覆盖关键路径复核、普通代码审查、Windows/Linux × Python 3.10/3.11 离线测试、真实官方 Provider/local/串并行 Matrix、旧 Paper Gate、报告与归档审计。候选保持未发布，可进入独立的 v0.6 最终 Release Gate。

## Folia 并行故障闭环

失败不是时钟回拨、共享文件锁、run/probe 隔离、启动参数或 probe 写文件错误。GitHub Ubuntu 证据显示 Folia 在双核 runner 上只分配了一个 region tick thread；`Done` 后仍在同一 region scheduler 上初始化三个世界，watchdog 记录主 region 连续约 5.5 秒未响应。原实现允许一个过早 callback 成为首样本，之后会因超过两秒未更新而严格失败；第一轮修复隐藏早期样本后，又暴露出通用的 `ready + 10s` 首样本截止会在世界刚初始化完成时过早停止服务器。

最终修复：

- Folia probe 先要求 global region scheduler 连续产生完整两秒的新鲜 callback，再发布首个样本；孤立的启动 callback 不再成为 PASS 证据。
- host 端两秒新鲜度、身份/CodeSource、递增序列/时间和窗口末端新样本规则均未放宽；完整稳定窗口只从首个有效样本开始。
- Folia 的冷世界初始化和未发布握手使用原始 `--timeout` 启动截止；普通 Bukkit scheduler 仍使用最多十秒的 post-ready probe grace。
- probe 已直接确认目标不存在或 disabled 且日志已追平时立即形成负向 verdict，不再等待不可能出现的 enabled 样本；这不影响任何 PASS 路径。
- 空世界使用固定 seed，使并行 Folia 回归可复现。三个并发真实子进程的回归先模拟超过两秒无样本，再要求各自完成严格窗口。

失败证据保留在 [superseded hosted run 34768288891](https://github.com/YouDaoRS/PluginMatrix/actions/runs/34768288891)。Folia 的 support declaration 与 scheduler 合同依据 Paper 官方 [Folia support](https://docs.papermc.io/paper/dev/folia-support/) 和 [Folia overview](https://docs.papermc.io/folia/reference/overview/)；PASS 仍不声称线程安全或跨 region 安全。

## 普通审查完成项

- Provider：旧 Paper JSON/CLI/report/cache 字段继续兼容；新旧字段混用和未知字段明确拒绝。Paper、Purpur、Folia、local/custom 共享同一 Runtime Verifier。Windows 短路径/规范化别名不再误拒绝同一个 local JAR，复制前后 hash 和输入保护不变。
- CLI/application：`init`、`validate`、`doctor`、`providers` 的离线/JSON/退出码已覆盖；application API、取消和有界 progress observer 异常不改变 verdict。
- 报告：损坏的嵌套 runtime/Matrix JSON fail closed，不留下部分 HTML；JSON、HTML、Summary、result.json、server.log、progress JSONL 和 artifact 引用均由 Gate 校验。
- 并发与清理：缓存和输出使用跨进程锁与原子发布；环境失败不取消 siblings，内部异常会取消 owned work；Ctrl+C 后 drain workers，并通过 Windows Job Object 或 POSIX process group 清理进程树。
- 运行语义：服务器在稳定窗口内自行退出优先判定为 server failure，不再被后续 disable 日志误分类。删除了旧 Paper-only marker、未使用缓存路径函数和重复异常分支，未进行大规模重构。

## Gate 记录

| Gate | 结果 |
| --- | --- |
| Windows Python 3.10.21 / 3.11.9 | 各 162 项全部通过（本机 3 项为 POSIX/权限型跳过）；`compileall` 通过 |
| GitHub-hosted CI | Ubuntu/Windows × Python 3.10/3.11 全绿；Linux 实际执行 FIFO、symlink、hardlink、路径别名和 parent/child/grandchild POSIX process-group 测试；Windows 实际执行 junction、hardlink、Job Object 和取消清理 |
| 本机 JDK 21 Provider Gate | 14/14 预期结论：Paper/Purpur/Folia success 与 enable-failure、Folia unsupported、local、`max_parallel=1/3` 混合 Matrix；官方 success 都确认 `.paper-remapped` CodeSource |
| Hosted Release Gate | Paper 1.20.1/196/JDK17、Paper 1.21.4/232/JDK21，以及 Ubuntu/Windows Provider Gate；真实 Paper/Purpur/Folia success/enable-failure、local 和串并行混合 Matrix |
| Artifacts | 单环境 JSON/HTML/server.log；Matrix JSON/HTML/Summary；每环境 result.json/server.log；progress 事件和引用存在且可解析 |
| 构建 | 从最终提交在全新 checkout 构建 sdist/wheel，审计归档/metadata/版本/排除项，并在全新 venv 运行两个 CLI 入口及 providers/doctor smoke |

Hosted 结果见分支的 [CI history](https://github.com/YouDaoRS/PluginMatrix/actions/workflows/ci.yml?query=branch%3Acodex%2Fmulti-server-core) 和 [Release Gate history](https://github.com/YouDaoRS/PluginMatrix/actions/workflows/release-gate.yml?query=branch%3Acodex%2Fmulti-server-core)。本机完整 Provider 证据位于 `C:\Users\11580\AppData\Local\Temp\pluginmatrix-06-gate-jhssxmgr`；最终 Folia 复验位于 `C:\Users\11580\AppData\Local\Temp\pluginmatrix-folia-recheck-486b52508dc446f9bb1eb6d95a32628f`。这些路径是本机证据，不属于源码包。

## 保留限制

- Folia 1.21.4 build 6 的上游渠道为 ALPHA。Folia PASS 只证明该版本/构建中被接受、enable 并在观察窗口保持 enabled。
- local 是显式 `paperclip`/`bukkit`/`folia` 运行合同，不承诺所有未知 fork；Purpur 上游 MD5 与本地 SHA-256 在报告中分开表达。
- 取消是协作式且有界：进行中的 HTTP 最多等待其 30 秒 timeout，javac 最多 60 秒；PluginMatrix 不是 hostile-code sandbox。
- v0.6 尚未发布。最终 Release Gate 需要独立复核 RC 证据和 owner 的单独发布授权；本状态不授权 tag、Release 或 PyPI。
