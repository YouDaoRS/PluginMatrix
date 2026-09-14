# PluginMatrix v0.7 Development Status

更新日期：2026-09-14。当前源码版本为 **0.7.0.dev1**，开发分支为 `codex/v0.7-local-web-ui`；公开稳定版本仍是 **v0.6.0**。没有创建 v0.7 tag、GitHub Release 或 PyPI 发布。

v0.7 已实现 loopback-only Web UI、同一 application API/Provider/Runtime Verifier 的单环境与 Matrix 运行、实时进度、取消、配置导入/生成及 artifact 白名单访问。已加入 PyInstaller `onedir` 原生打包和 Windows x86-64、Linux x86-64、macOS x86-64/arm64 workflow。实现与首轮跨平台修复位于 `c393e029fd3007dbd86ad0da7c600d551af276e8`、`4d9e7e1cc5ed4d84db27c8018ec2ce543e1b0a0e`；当前适合进入独立关键审查，但不是发布候选结论。

## v0.7 Implementation Gate

- 本机 Windows Python 3.11：175 项通过，5 项 POSIX/权限型跳过；`compileall`、sdist/wheel 内容检查、PyInstaller onedir/zip 构建、冻结 CLI/Provider/Java/Web smoke、浏览器页面与 JSON 配置生成均通过，包内 JAR 数为 0。
- [GitHub-hosted CI run 34825807094](https://github.com/YouDaoRS/PluginMatrix/actions/runs/34825807094) 成功。
- [Standalone Distribution run 34825807071](https://github.com/YouDaoRS/PluginMatrix/actions/runs/34825807071) 成功：Windows x86-64、Linux x86-64、macOS x86-64、macOS arm64 均从各自原生 runner 构建压缩包，并从冻结 CLI 和 Web UI 各执行真实 Paper 1.20.1/build 196/JDK 17 路径，确认 PASS、runtime probe、JSON/HTML 报告和原始 `server.log`；合并 checksum 任务成功。
- 首轮 [run 34824860650](https://github.com/YouDaoRS/PluginMatrix/actions/runs/34824860650) 暴露 `setup-python` 的 Unix 工具缓存未提供可发现许可证文件；现改为优先复制构建解释器许可证，并以仓库中的官方 CPython 许可证副本作为离线回退。该问题已由上述四平台最终 run 覆盖。
- 当前 CI 产物只用于开发验证；没有创建 tag、GitHub Release、PyPI 上传、签名、安装器、notarization 或自动更新。

## v0.6.0 Release Status

更新日期：2026-09-14。

当前公开稳定版本为 **v0.6.0**，正式长期开发与发布分支是 `main`。`main` 已从原发布分支安全 fast-forward 到 v0.6.0，随后加入发布基础设施和文档；未修改 v0.6.0 tag、GitHub Release、v0.5.0/v0.5.1 或历史。

结论：以 `30cbe2548c06e30dd8a12e93acaa7b20206f67b5` 为代码候选基线的 v0.6 Final Release Gate 已完成。关键路径复核、Windows/Linux × Python 3.10/3.11 离线测试、真实官方 Provider/local/串并行 Matrix、旧 Paper Gate、报告、打包、公开资产和干净安装均通过；最终版本提交只包含版本与发布文档调整，因此没有重复真实服务器 Gate。

## PyPI / pipx 分发

- 正式项目：[PyPI `pluginmatrix` 0.6.0](https://pypi.org/project/pluginmatrix/0.6.0/)
- 预发布验证：[TestPyPI `pluginmatrix` 0.6.0](https://test.pypi.org/project/pluginmatrix/0.6.0/)
- TestPyPI workflow：[run 34811137930](https://github.com/YouDaoRS/PluginMatrix/actions/runs/34811137930)；正式 PyPI workflow：[run 34817178850](https://github.com/YouDaoRS/PluginMatrix/actions/runs/34817178850)。
- 两次发布均使用 `.github/workflows/publish-pypi.yml`、GitHub OIDC 和 Trusted Publishing；没有长期 API token。Trusted Publisher 绑定 `YouDaoRS/PluginMatrix`、`publish-pypi.yml`，Environment 分别为 `testpypi` 与 `pypi`。正式 `pypi` Environment 只允许 `main`，并要求 `YouDaoRS` 审批且禁止管理员绕过。
- workflow 只下载现有 GitHub Release 的 wheel/sdist，核对 Release/tag commit、固定文件名、包名、版本和 GitHub asset digest 后上传，不重新构建。PyPA publish Action 固定到 commit `dc37677b2e1c63e2034f94d8a5b11f265b73ba33`；`skip-existing: false`，不可覆盖版本会明确失败。
- wheel `pluginmatrix-0.6.0-py3-none-any.whl`：`3605c7241f575ef3d1b55bc31d70bb4a92eaac2e156fe63b78e698d381d3c016`；sdist `pluginmatrix-0.6.0.tar.gz`：`1d5736e67bc9f04c1a72296edb8f7bb969216052f2c63fdf0774368e938d08b2`。GitHub Release、TestPyPI 和 PyPI 三处 SHA-256 一致。
- Windows Python 3.11.9 的全新临时 pipx home 从 TestPyPI 和正式 PyPI 分别安装 `pluginmatrix==0.6.0`；`--version`、`--help`、`providers --json` 均通过，Paper/Purpur/Folia/local 全部存在，`pipx upgrade pluginmatrix` 正确报告已是 0.6.0。

推荐 CLI 安装方式为 `pipx install pluginmatrix`，升级使用 `pipx upgrade pluginmatrix`。GitHub Release 继续作为源码、原始资产和校验值渠道；后续独立 Windows/Linux/macOS 程序包只作为清晰命名的 GitHub Release 资产，不混入 PyPI wheel/sdist。完整规则见 [PUBLISHING.md](PUBLISHING.md)。

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
| GitHub-hosted CI | 候选基线和最终版本提交的 Ubuntu/Windows × Python 3.10/3.11 全绿；Linux 实际执行 FIFO、symlink、hardlink、路径别名和 parent/child/grandchild POSIX process-group 测试；Windows 实际执行 junction、hardlink、Job Object 和取消清理 |
| 本机 JDK 21 Provider Gate | 14/14 预期结论：Paper/Purpur/Folia success 与 enable-failure、Folia unsupported、local、`max_parallel=1/3` 混合 Matrix；官方 success 都确认 `.paper-remapped` CodeSource |
| Hosted Release Gate | Paper 1.20.1/196/JDK17、Paper 1.21.4/232/JDK21，以及 Ubuntu/Windows Provider Gate；真实 Paper/Purpur/Folia success/enable-failure、local 和串并行混合 Matrix |
| Artifacts | 单环境 JSON/HTML/server.log；Matrix JSON/HTML/Summary；每环境 result.json/server.log；progress 事件和引用存在且可解析 |
| 构建与公开资产 | 从最终提交的干净源码构建 sdist/wheel，审计归档/metadata/版本/许可证/排除项与 SHA-256；GitHub Release、TestPyPI、PyPI 三处资产 hash 一致；全新 venv 与隔离 pipx 安装、CLI/providers/upgrade 通过 |

Hosted 结果见分支的 [CI history](https://github.com/YouDaoRS/PluginMatrix/actions/workflows/ci.yml?query=branch%3Acodex%2Fmulti-server-core) 和 [Release Gate history](https://github.com/YouDaoRS/PluginMatrix/actions/workflows/release-gate.yml?query=branch%3Acodex%2Fmulti-server-core)。本机完整 Provider 证据位于 `C:\Users\11580\AppData\Local\Temp\pluginmatrix-06-gate-jhssxmgr`；最终 Folia 复验位于 `C:\Users\11580\AppData\Local\Temp\pluginmatrix-folia-recheck-486b52508dc446f9bb1eb6d95a32628f`。这些路径是本机证据，不属于源码包。

## 保留限制

- Folia 1.21.4 build 6 的上游渠道为 ALPHA。Folia PASS 只证明该版本/构建中被接受、enable 并在观察窗口保持 enabled。
- local 是显式 `paperclip`/`bukkit`/`folia` 运行合同，不承诺所有未知 fork；Purpur 上游 MD5 与本地 SHA-256 在报告中分开表达。
- 取消是协作式且有界：进行中的 HTTP 最多等待其 30 秒 timeout，javac 最多 60 秒；PluginMatrix 不是 hostile-code sandbox。
- v0.6.0 的发布信心仅适用于 Gate 中记录的具体 Provider/build、Java 和平台组合；PyPI/pipx 分发不扩大 PASS 的含义。
- 为满足“使用 GitHub Release 中同一批已验证资产”的约束，PyPI 0.6.0 的内嵌 long description 仍是发布时的 README，包含当时“未发布到 PyPI”的历史句子。PyPI 不允许替换已上传版本的文件；主分支 README 和本状态页是当前分发状态，不为修正文案重发 0.6.0。
