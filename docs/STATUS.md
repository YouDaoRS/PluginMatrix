# PluginMatrix Release Status

## v0.9.0 Final Release Gate（2026-09-15）

最终源码版本为 `0.9.0`，分支为 `codex/v0.9-guided-core`，基于核心提交 `776adc4`。
已验收代码候选为 `0c1c97c72c20c2050254429bc6012d26a3d82146`（产品集成为 `57f49ae`）；
候选记录提交 `f9f8cd0` 仅修改文档，没有后续代码变化或未关闭的发布阻断项。
最终发布已获授权：复用下列完整 RC 证据，从最终 release commit 构建、验证并公开同一批资产，
经 TestPyPI 验证后再原样发布至 PyPI。v0.8.0 及更早的 Tag、Release 和资产保持不变。

- 已接入 Web 三步向导、明确目标与官方建议确认、简单/高级模式、深色/系统外观、双语与响应式布局。
- schema 2、profile revision、托管 JDK ID/目录、明确 Behavior 检查和输出选项完整导入/编辑/导出；
  Web 执行仍调用 application API，不重新计算 verdict。
- 新增本地项目与最近 64 项运行记录恢复、输入/配置 hash、失败环境恢复和原 artifact 身份保护。
  保存/运行会保留浏览器选择的本地 JAR 副本，不进行远程上传。
- 增加 JDK 预览、下载、完整性校验、租约保护删除，以及固定官方服务端 JAR 缓存管理。
  未识别文件、暂存条目、系统 Java、bootstrap runtime 与持久锁不进行递归删除。
- CLI 提供人类可读输出与 `jdk verify`；补充 init 的本地依赖/JDK/Behavior 参数、
  [双语使用指南](GUIDED_SETUP.md) 和四种 profile 示例。
- 本机真实 Web Paper 1.20.1/196 已得到 Runtime PASS、两项自动建议注册检查 PASS、最终 PASS。
  该运行使用仓库自有 Behavior fixture，记录位于
  `C:\Users\11580\AppData\Local\Temp\pluginmatrix-v09-sol-rc1\web`。
- 定稿浏览器验收通过：1280px English 浅色、390px 中文深色、真实结果查看、项目保存、
  历史恢复、JSON 检查编辑、托管 ID 无静默替换和缓存页；无页面异常或横向溢出。
  证据为同级目录 `ui-qa.json` 及截图，浏览器为 Playwright/Edge。
- 一次完整本机 RC 离线验证共 267 项：258 passed / 9 平台型 skips；包含实际 sdist/wheel
  构建与归档排除检查。`compileall`、JavaScript syntax 和 `git diff --check` 通过。
  首次并发编译遇到 Windows pyc 临时锁，测试结束后单独编译通过，没有重复完整测试。
- 首轮候选 `57f49ae` 的 hosted CI 在 Ubuntu 通过，Windows 暴露 8.3 路径别名；
  native 冻结 Gate 在 Windows x64 通过，Linux 暴露官方 TAR 内部许可证链接，
  macOS 暴露测试临时目录 `/var` 别名。已针对这三项修复并补充回归：
  32 项局部测试中 31 passed / 1 本机权限 skip；没有重复完整本机 RC 或浏览器测试。
  修复后候选的 [CI 34953514364](https://github.com/YouDaoRS/PluginMatrix/actions/runs/34953514364)
  四组 Ubuntu/Windows × Python 3.10/3.11 全部通过。
- TAR 仅将同一顶层 JDK 目录中指向原始普通成员的内部符号链接物化为普通副本；
  链接链/循环、目录链接、逃逸、硬链接和特殊文件仍拒绝，安装树继续完全无链接。
  Gate artifact 上传显式包含白名单中的隐藏 `.pluginmatrix` 证据，不上传 JDK 安装树。
- [Standalone 34953514365](https://github.com/YouDaoRS/PluginMatrix/actions/runs/34953514365)
  的 Windows x64、Linux x64/arm64、macOS x64/arm64 五组原生验收及合并校验和全部通过：
  JDK 文件系统回归、冻结包构建/smoke、官方 Temurin 下载/校验、真实 Paper CLI/Web、
  schema 2 配置恢复、报告/artifact 访问及托管 JDK 删除均完成。
  五份平台归档及校验和/运行证据保存在该 workflow artifacts（保留 14 天），没有发布为 Release。

本轮沿用 Astra 已验证的 Runtime、Behavior、分析和 profile 合同，不重复完整 Provider Gate。
新增跨平台冻结 Gate 直接验证官方托管 JDK 的下载/解压/Java/Javac/manifest、
schema-2 CLI/Web 运行和删除，覆盖 Windows x64、Linux x64/arm64、macOS x64/arm64。
最终版本/文档整理没有改变已验收代码，因此仅运行必要的最终 CI、包审计和 smoke。
托管 JDK 仅在用户明确确认后从 Eclipse Adoptium API 和匹配 Temurin release 下载，
保留上游包内 `legal` 说明；JDK 不进入 wheel、sdist、standalone 或 GitHub Release 资产。
独立包仍未签名、未 notarize；
PASS 仍仅证明对应环境中已观察到的 Runtime/Behavior 合同，不证明所有插件功能兼容。

## v0.9 Guided Setup core development history（2026-09-15）

以下记录描述核心交接时公开稳定版本仍为 `0.8.0` 的历史状态。开发分支 `codex/v0.9-guided-core` 已实现共享静态分析、
本地依赖图、四种版本化 profile、安全 Behavior 建议、可解释环境推荐、schema 2 兼容层、
显式托管 JDK 下载/校验/选择/删除和稳定 application 服务。Runtime/Behavior PASS 语义未改变。

- 225 项相关回归通过（219 passed / 6 skips）；最终托管引用和前置失败状态加固后的 89 项局部复验通过
  （87 passed / 2 skips），含新增回归。`compileall` 和 `git diff --check` 通过。
- 新 CLI smoke 通过；修复参数完整的 `init` 仍进入交互提示的问题，追加回归与 application
  子集共 15 项通过。
- 真实 Windows x64 Temurin 17.0.20.1+1 下载、SHA-256、Java/Javac、缓存完整性与使用租约通过；
  使用中删除被拒绝，Gate 完成后删除成功，系统 Java 配置未改动。
- Paper 1.20.1/196 的 quick、standard、strict，以及 1.20.1/196 + 1.20.4/499 的双环境
  并行 Matrix 共五个真实结果全部符合预期。快速方案为 Runtime PASS / Behavior NOT_RUN，
  其余为 Runtime PASS / Behavior PASS。日志、配置、来源和报告已保留。
- 首轮安装暴露并修复了 Windows JDK `release` 文件 CRLF 解析问题；未发布无效缓存。
- GPT-5.6 Sol 接续 Web 向导、界面/深色模式、历史、缓存页面、翻译、用户文档、跨平台
  native/standalone 验收和发布准备。旧 Web 编辑器暂时拒绝 schema 2 导入，避免静默丢字段。

完整合同、证据路径/hash、限制和交接清单见 [GUIDED_SETUP_CORE.md](GUIDED_SETUP_CORE.md)。
此阶段不创建 Tag、Release，不发布 TestPyPI/PyPI，也不修改公开版本号。

## v0.8.0 Final Release（2026-09-15）

PluginMatrix `0.8.0` 已正式发布。Release commit `72843cf205658df16c8728936b8104af2d0c0083` 已从 `codex/v0.8-behavior-core` fast-forward 到 `main`；annotated `v0.8.0`、GitHub Release、TestPyPI 和 PyPI 发布均已完成。

- 最终 [CI run 34933468358](https://github.com/YouDaoRS/PluginMatrix/actions/runs/34933468358) 与 [Standalone Distribution run 34933468354](https://github.com/YouDaoRS/PluginMatrix/actions/runs/34933468354) 成功。四平台归档均记录 `0.8.0`、release commit、clean source，并完成冻结 CLI/Web 的真实 Paper runtime + behavior PASS。
- 公开 [GitHub Release](https://github.com/YouDaoRS/PluginMatrix/releases/tag/v0.8.0) 包含 11 个已验证资产。wheel SHA-256 为 `2d488600b7727ef3d59b1d8965f7382294e199de1c5c49619f368b5191c711e8`；sdist 为 `c5ccbddbc02c763be812b4d4f9ac3cd0163090ae3620b7ce522e4d79ed37404f`。
- Standalone SHA-256：Linux x86-64 `ace91f922f9aa537370b3af01bab9c2c0b12b4c5f505e746e09db36ad6fbf2f6`；macOS arm64 `da1e086366aad604199206bda487461490876535428c8b1e9a5271db2b7e99c2`；macOS x86-64 `0a73b4130240e80a93a2b81cf4dbb40222ed33ad3e568b4070abedba739c75f2`；Windows x86-64 `63f478e3622a433163101f72b45cfdac03c9bdc7d619111a5fcb4bdb62725768`；`SHA256SUMS.txt` 为 `efcec124a070adfb729c12bc097a97dbc4598361b6245fa51cbdbbaf42c9d81b`。
- [TestPyPI run 34934372164](https://github.com/YouDaoRS/PluginMatrix/actions/runs/34934372164) 与 [PyPI run 34934563716](https://github.com/YouDaoRS/PluginMatrix/actions/runs/34934563716) 均通过 Trusted Publishing。两个索引和 GitHub Release 的 wheel/sdist byte-identical；正式 PyPI 未重新构建。
- 已从公开 GitHub Release、TestPyPI 和 PyPI 重新下载资产并核对 SHA-256。全新 pipx 安装、`--version`、Provider JSON、loopback Web `/health`、behavior 配置解析和 behavior HTML 报告均通过；公开 Windows standalone 的版本与 Web health 也通过。
- v0.5.0、v0.5.1、v0.6.0、v0.7.0、v0.7.1 的 Tag、Release 和资产元数据与发布前基线一致。

- Web UI 已支持五类 behavior check 的配置、严格核心校验、Matrix JSON 导入/导出和再次运行。English / 简体中文界面分别展示 runtime verdict、behavior verdict、最终结果，以及每项检查的状态、原因、耗时、结构化 evidence 和 post-check health。
- CLI、application API、单环境 JSON、Matrix JSON、静态 HTML、progress event、GitHub Job Summary 和 Web summary 使用同一语义：`result`/`verdict` 是 runtime verdict，`behavior.verdict` 独立保存，`verification_passed` 才是最终结果。
- Web artifact 白名单与 hosted workflow 已扩展到 behavior runtime probe/response，继续执行打开后文件身份、link、size、mtime/ctime 校验；原始 `server.log` 不被摘要替代。
- 旧 v0.7 legacy Paper 配置与不含 behavior 的配置继续 round-trip；没有 behavior 时为 `NOT_RUN`，runtime PASS 仍产生最终成功。含 behavior 时，最终 PASS 要求 runtime PASS 和 behavior PASS。
- 本机浏览器验收已覆盖 behavior 编辑、wait 类型切换、规范化 JSON 生成、English / 简体中文切换和桌面布局。本机 217 项测试通过、8 项按平台能力跳过；`compileall`、JavaScript syntax、`git diff --check` 和实际 sdist/wheel 构建审计通过。
- local Provider 单次重试已成功：Paper 1.20.1 local `paperclip` 合同的 success/false/exception/disable/hang/cancel/missing 与 local+Paper Matrix 共 9 个结果全部匹配预期，退出码 0。`gate-summary.json` SHA-256 为 `4c30f55b1eb7b410665569d63995ba58d8cd451fbade38c1a58a4ced871fa93b`；首次失败因此确认是 Mojang bootstrap 下载外部故障，不是实现问题。证据位于 `C:\Users\11580\AppData\Local\Temp\pluginmatrix-08-local-retry-rc1`，不属于源码或发布资产。
- RC code candidate `388ade8` 的 [CI run 34929167890](https://github.com/YouDaoRS/PluginMatrix/actions/runs/34929167890) 首次运行全绿，覆盖 Ubuntu/Windows x Python 3.10/3.11。[Standalone Distribution run 34929167986](https://github.com/YouDaoRS/PluginMatrix/actions/runs/34929167986) 也在首次运行全绿，Windows x86-64、Linux x86-64、macOS x86-64 与 macOS arm64 均完成冻结 CLI/Web 的真实 Paper runtime + `wait` behavior PASS，并成功上传 JSON、HTML、原始日志、probe evidence、平台归档及 combined checksums。

最终版本与文档修改未改变 Runtime Verifier 或 behavior 实现，因此没有重复完整 Runtime/Behavior Provider Gate；最终 CI、包审计、四平台 standalone smoke、公开资产复核与安装验证已全部通过。

发布边界：Behavior PASS 只证明配置声明的 typed observation 与每项检查后的新鲜健康样本；console command 的返回值不证明业务或玩家效果，不捕获文本输出。Folia PASS 不证明线程或跨 region 安全，Folia console command 仍为 `UNSUPPORTED`。PluginMatrix 不是 hostile-code sandbox。

## v0.8 核心开发交接（2026-09-15）

`codex/v0.8-behavior-core` 已实现有限、结构化的 Behavioral Verification，代码提交 `543076f`。
配置、双 verdict、probe 协议、安全边界和 Sol 接续事项见 [BEHAVIOR_CORE.md](BEHAVIOR_CORE.md)。
核心交接后的产品集成曾以 `0.8.0rc1` 完成候选验证，现已作为上述 `0.8.0` 正式发布；下方 v0.7.1 历史、Tag、Release 和 PyPI 均保持不变。
真实核心 Gate 已验证 Paper、Purpur、Folia 和双环境并行/取消；local 首轮因 Mojang bootstrap 下载超时而正确跳过行为检查，尚无本轮 local 行为成功结论。详细证据见上述交接页。

以下为 2026-09-14 的 **v0.7.1 历史发布记录**：当时源码与公开稳定版本均为 v0.7.1。Release commit `49543d122fa3ec241f937e70b6d2cf1440705803` 已从 `codex/v0.7.1-usability` fast-forward 到 `main`；annotated tag、GitHub Release、TestPyPI 和 PyPI 发布均已完成。

## v0.7.1 Final Release

- Release commit/tag：`49543d122fa3ec241f937e70b6d2cf1440705803` / annotated `v0.7.1`；公开 [GitHub Release](https://github.com/YouDaoRS/PluginMatrix/releases/tag/v0.7.1) 与 [PyPI 0.7.1](https://pypi.org/project/pluginmatrix/0.7.1/) 均已发布。
- 最终 [CI run 34854638499](https://github.com/YouDaoRS/PluginMatrix/actions/runs/34854638499) 与 [Standalone Distribution run 34854638550](https://github.com/YouDaoRS/PluginMatrix/actions/runs/34854638550) 成功。四平台 standalone、Windows 无参数 Web 启动、English / 简体中文切换、Provider 版本列表和 Java 自动发现 smoke 均通过。
- Python 包 SHA-256：wheel `bd13cc968e43fe72cc772a86cb309b37ecc0049ac328f7e1c7c33f5ddb73b9da`；sdist `25803469e36d2142d39a351abd94bf15f8ca1b147661f00c876f0cbf958fbea7`。
- Standalone SHA-256：Windows x86-64 `24d21a0c41f8ff23f4c31f38f191bd1b6104e0acc9b664a044414345657bc396`；Linux x86-64 `bb659c1b51b064e729d21b0e160e297a911b89bc517dca40acb11fc1dc7bacbb`；macOS x86-64 `7c9b98790e69e2ba248a028fb9be7b47f30e391c2ac5a0d74fb98e799d4e75b6`；macOS arm64 `446742045b6a566f84224593c9c5f64d80b61f6d0a5b166d5a9f5b3dc91d4e48`；`SHA256SUMS.txt` `8d2379b69be36c99464c5fdf4ab21ece3257da860c887dffedff4d089bad2727`。
- [TestPyPI workflow 34858876724](https://github.com/YouDaoRS/PluginMatrix/actions/runs/34858876724) 与正式 [PyPI workflow 34858963676](https://github.com/YouDaoRS/PluginMatrix/actions/runs/34858963676) 均通过 Trusted Publishing。GitHub Release、TestPyPI 和 PyPI 的 wheel/sdist 文件逐字节一致。
- 已从公开 GitHub Release 重新下载全部 11 个资产，并从正式 PyPI 重新下载 wheel/sdist。隔离 `pipx` 安装、`pluginmatrix --version`、`providers --json` 和 loopback Web `/health` 均通过；公开 Windows standalone 无参数启动也已验证。

## v0.7.1 Usability Preparation

- Windows standalone 无参数启动现在自动选择可用 loopback 端口并打开 Web UI，状态与缓存写入用户本地目录；启动失败通过可理解的原生对话框说明原因和 `pluginmatrix.exe web --port 0` 回退命令。显式 CLI 子命令保持不变。
- Web UI 通过现有 Provider 官方 API 枚举 Minecraft 版本与 build，元数据使用受限本地缓存；在线、缓存、过期缓存与完全不可用状态均明确展示，安全的损坏 JSON 可在线恢复，且始终保留手动输入。
- application 层发现本机 Java/JDK、版本、路径和匹配 `javac`，界面依据所选 Minecraft 版本提示文档基线，并保留手动 executable 高级入口。不会下载、安装或修改 Java。
- English / 简体中文静态与动态界面文本已覆盖，语言选择保存在浏览器本地。进度事件改为普通用户状态，内部事件和原始字段仅在“技术详情”中展开。
- PASS、失败、取消真实流程均已通过本机 Web 验收；完成和取消后不再显示可操作的 Cancel 按钮，Provider 与结果标题统一使用展示名称。Runtime Verifier 和 PASS 语义未修改。
- 本机 Windows Python 3.11 完整离线测试 192 项通过、7 项按平台能力跳过；`compileall`、JavaScript 语法/DOM 安全检查和 `git diff --check` 通过。真实浏览器验收覆盖 1280px/390px、语言持久化、在线与缓存 Provider metadata、JDK 路径/版本提示、Paper PASS、无效 Java 失败和运行中取消。
- Windows x86-64 standalone `0.7.1.dev1` 候选构建、归档审计、冻结 CLI/Provider/doctor/Web health、无参数双击入口与真实冻结 CLI/Web Paper PASS 均通过；最终本地开发归档 SHA-256 为 `d0cc0013fe39b421cd77dd9b95abe2a5e3baf76828260bc9d3153f8f356dedeb`，不属于发布资产。
- GitHub-hosted [CI run 34846010581](https://github.com/YouDaoRS/PluginMatrix/actions/runs/34846010581) 已在 Ubuntu/Windows、Python 3.10/3.11 全绿；[Standalone Distribution run 34845461889](https://github.com/YouDaoRS/PluginMatrix/actions/runs/34845461889) attempt 2 已在 Windows x86-64、Linux x86-64、macOS x86-64/arm64 全绿，四个平台均完成冻结 CLI/Web 的真实 Paper 验证。首次 macOS x86-64 attempt 仅因 Paper API DNS 解析失败，单独重跑后通过。
- v0.7.1 已从最终 Release commit 构建并完成公开分发；开发候选归档未被用作发布资产。

v0.7.0 发布记录（2026-09-14）：最终发布提交 `2421a4213ca7cbbd8669926dc7fb365f8512913b` 已从 `codex/v0.7-local-web-ui` fast-forward 到 `main`，annotated tag、GitHub Release、TestPyPI 和 PyPI 发布均已完成。

v0.7 已实现 loopback-only Web UI、同一 application API/Provider/Runtime Verifier 的单环境与 Matrix 运行、实时进度、取消、配置导入/生成及 artifact 白名单访问。已加入 PyInstaller `onedir` 原生打包和 Windows x86-64、Linux x86-64、macOS x86-64/arm64 workflow。Astra 关键安全审查、修复后完整离线测试、最终跨平台 standalone 构建与归档审计已经完成；RC 代码候选为 `d3aeecc1b20d26b22ab9a9d75ff744d7a57a9b42`，`caeefd6` 仅记录 RC 结果，最终版本修改不涉及运行时代码，因此没有重复真实 Provider Gate。

## v0.7.0 Final Release

- Release commit/tag：`2421a4213ca7cbbd8669926dc7fb365f8512913b` / annotated `v0.7.0`；公开 [GitHub Release](https://github.com/YouDaoRS/PluginMatrix/releases/tag/v0.7.0) 与 [PyPI 0.7.0](https://pypi.org/project/pluginmatrix/0.7.0/) 均指向该版本。
- 最终 [CI run 34833821162](https://github.com/YouDaoRS/PluginMatrix/actions/runs/34833821162) 与 [Standalone Distribution run 34833820926](https://github.com/YouDaoRS/PluginMatrix/actions/runs/34833820926) 成功。四个平台均记录冻结 CLI 和 Web UI 的真实 Paper PASS；本机再次验证 Windows 冻结 CLI、Provider registry 和 Web `/health`。
- Python 包从最终提交的干净 `git archive` 构建一次并原样发布。wheel `326d00669090f4f1bde2565d9d3b09333c7124953e5b28ca0c39f60394c831b5`；sdist `c84cb05271c2a35bf6aaf0c7da8f4612f783d396b10fc9f9413e5d347410b942`。
- Standalone SHA-256：Windows x86-64 `e0933f67011d51613bda0db82bce826c16505a3e814e3c6746e3c0b1f4bdfd81`；Linux x86-64 `11211e97ba9073e3134b3bd1b5cd97b7af0f662f858b7d82c85c7c48efcd63ef`；macOS x86-64 `2eb339a1adb30986ec148c89c28f457c2f06d6d0da7b2a38fb71746c1af62b0f`；macOS arm64 `5bbcbb235585571303a8bef8a7f273f8daa79fd260a0518154d632686a9433dd`。
- [TestPyPI workflow 34835141840](https://github.com/YouDaoRS/PluginMatrix/actions/runs/34835141840) 与正式 [PyPI workflow 34835387582](https://github.com/YouDaoRS/PluginMatrix/actions/runs/34835387582) 均通过 Trusted Publishing，从 GitHub Release 下载并验证同一 wheel/sdist 后发布。GitHub Release、TestPyPI、PyPI 的两个 Python 包 hash 一致。
- 已从公开 GitHub Release 重新下载全部 11 个资产，并从 PyPI CDN 重新下载 wheel/sdist；大小、GitHub digest、SHA-256 和原始发布文件均一致。全新 venv、普通 `pip`、隔离 `pipx`、CLI `--version`、`providers --json` 和 loopback Web health smoke 通过。
- `v0.5.0`、`v0.5.1`、`v0.6.0` 的 Tag target、Release 元数据和全部资产 ID、大小、时间戳及 digest 与发布前基线一致。

剩余限制：standalone 是普通压缩包，不是系统签名安装包；Windows/macOS 可执行文件未 code-sign，macOS 包未 notarize。冻结 Windows 的 `run_external` 在外部进程等待期间仍持有全局 DLL 环境覆盖锁，可能串行化并发 Java/Javac 启动，但 Gate 中未观察到 verdict、清理或稳定性错误。native notices 只覆盖本次四平台归档中实际携带的库，构建工具链变化后必须重新审计。

## v0.7 Release Candidate Gate

- 安全修复提交：`a3969e9` 限制 HTTP 连接、解析、上传和配置读取并加固 artifact TOCTOU；`73b4a16` 在归档前拒绝 runtime/private/special/escaping assets；`d3aeecc` 为实际打包出的 OpenSSL、bzip2、libffi、liblzma、libuuid 和 zlib 补齐 native notices 与 build metadata。
- 本机 Windows Python 3.11 最终完整离线测试：186 项通过，7 项 POSIX/symlink 权限型跳过；`python -m compileall -q pluginmatrix tests standalone ci-fixtures/build_fixtures.py`、`git diff --check` 和工作树/未跟踪源码检查通过。
- 从 `d3aeecc` 的干净 `git archive` 构建 sdist/wheel，metadata、Web assets、许可证和敏感/二进制排除通过。开发候选 SHA-256：wheel `96480512b0bb573bcc249d48016265b8d0fe6135ed2669a880ad7b76efe34b13`；sdist `a3d76a6b0179ae8ed583343633447c9312ec6afd2a89305266497e6383018cba`。
- 最终 [GitHub-hosted CI run 34831078163](https://github.com/YouDaoRS/PluginMatrix/actions/runs/34831078163) 成功。Ubuntu/Windows × Python 3.10/3.11 每项均运行 186 个测试；Ubuntu 各跳过 2 个 Windows-only 测试，Windows 各跳过 3 个 POSIX-only 测试，互补覆盖实际执行。
- 最终 [Standalone Distribution run 34831078226](https://github.com/YouDaoRS/PluginMatrix/actions/runs/34831078226) 成功：Windows x86-64、Linux x86-64、macOS x86-64、macOS arm64 均从原生 runner 构建，并从冻结 CLI 和 Web UI 各执行真实 Paper 1.20.1/build 196/JDK 17 路径，确认 PASS、runtime probe、JSON/HTML 报告和原始 `server.log`；合并 checksum 任务成功。
- 最终 standalone SHA-256：Windows x86-64 `0b1e16d0d2d873ebe65efcf9eb213ac7894a5f1a01dabea478a669059ca73fb4`；Linux x86-64 `2cd63b7d5e659abd951d49e114d7469f9e531c5e88dca57dfe12462ea7a50787`；macOS x86-64 `b1393dc962608f376256ea8b782844c5e297ea890815aa130ccd9066512b62f3`；macOS arm64 `7a23d76036a83442dfed72c3803797a495543aa123daf96aec11188fc7fe0dba`。
- 归档审计确认每包只有预期的应用/CPython/PyInstaller runtime、Web assets、README、build provenance 和四份许可证/notice；没有 JAR、日志、缓存、密钥、环境文件、构建机路径或可读凭据。macOS 各 4 个内部 native-library symlink 均留在 bundle 内；所有 notice 上游链接返回 HTTP 200。
- 安全修复后的首轮 [CI run 34830003867](https://github.com/YouDaoRS/PluginMatrix/actions/runs/34830003867) 与 [standalone run 34830003909](https://github.com/YouDaoRS/PluginMatrix/actions/runs/34830003909) 功能全绿，但人工归档审计发现 Unix 包只携带 CPython 核心 fallback、未覆盖复制的 native libraries；该 RC 阻塞已由 `d3aeecc` 和上述最终 run 关闭。
- Provider/Runtime Verifier 代码未在本轮改变，因此没有重复已经完成的真实 Provider Gate；最终 standalone 仍在四平台各自执行了一次真实 Paper CLI/Web runtime probe。
- 最终 Release 已从版本提交重新构建并审计全部资产，没有复用开发 CI 归档；standalone 作为普通压缩包发布，不提供签名、安装器、notarization 或自动更新。

剩余风险：冻结 Windows 的 `run_external` 仍在外部进程等待期间持有全局 DLL 环境覆盖锁，可能串行化并发 Java/Javac 启动，但未观察到 verdict、清理或稳定性错误；native notice 覆盖当前四平台归档中实际观察到的库，后续 Python/PyInstaller/runner 依赖变化仍需重新审计。正式 standalone 资产仍未签名、未 notarize，不得描述为系统签名安装包。

## v0.6.0 Release Status

更新日期：2026-09-14。

**v0.6.0** 是上一公开稳定版本，正式长期开发与发布分支是 `main`。`main` 当时从原发布分支安全 fast-forward 到 v0.6.0，随后加入发布基础设施和文档；v0.7.0 发布没有修改 v0.6.0 tag、GitHub Release、v0.5.0/v0.5.1 或历史。

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
