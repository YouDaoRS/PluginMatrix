# Third-Party Reference Review

审计日期：2026-09-12  
审计范围：仅限真实 Paper 启动/插件生命周期、GitHub Actions 组织方式、fixture/隔离/确定性测试，以及与 PluginMatrix 当前架构直接相关的设计取舍。

本次审计没有复制任何外部代码、workflow YAML、注释、测试实现或文件结构。

## v0.5 仓库来源审计

公开源码准备阶段按仓库内容重新分类如下：

- **项目原创代码与文档**：`pluginmatrix/`、`tests/`、仓库 workflow、示例和项目治理文档均从当前 Git 历史表现为本项目内容；没有发现复制第三方实现的声明或证据。这里的“原创”是仓库来源分类，不伪造个人、实体或版权归属。
- **仓库内 fixture**：`PluginMatrixSmoke.jar` 与 `PluginMatrixEnableFailure.jar` 只包含相邻 Java 源码编译出的 class 和 `plugin.yml`，没有 shaded dependency；源码、用途、构建脚本和 SHA-256 清单均保留在 `ci-fixtures/`。Paper libraries 只作为 compile-time classpath，不进入 fixture JAR。这些是可核验的仓库证据，不等同于独立法律权属结论；项目所有者已确认两个 fixture 源码树和 JAR 的 Apache-2.0 发布权。
- **第三方 JAR**：v0.4 使用的 `EnhancedFly-2.2.0.jar` 曾提交在 `ci-fixtures/`。JAR 内 `plugin.yml` 声明 `author: YouDaoRS` 与项目 URL，但 PluginMatrix 仓库及审计时可见的 EnhancedFly 源码 checkout 均没有根许可证或明确再分发授权；JAR 内的 `LICENSE` 是 shaded MySQL Connector/J 的许可证信息，不能作为 EnhancedFly 自身的授权。v0.5 因此移除该 JAR，并将公开示例切换到仓库内可审计的 smoke fixture。历史 hosted 结果只作为事实记录保留。
- **只参考、未复制的第三方项目**：下列 MockBukkit、paper-integration-tester 和 minecraft-plugin-runtime-test 仅用于高层设计比较；没有复制代码、workflow、测试、注释或文件结构。

Python wheel/sdist 不包含 Paper、Mojang runtime、JDK、第三方插件 JAR或任何 fixture JAR。运行时下载边界及仓库 fixture 说明见 `THIRD_PARTY_NOTICES.md`。

## 许可证边界

- MIT、Apache-2.0、BSD 等宽松许可证项目：本次只识别候选实现和高层思路，不复制代码。未来若复用实质性代码，必须保留版权声明和完整许可证文本，并记录 URL、原始 revision、文件范围、修改内容和修改理由。
- GPL-3.0 项目：只借鉴高层设计、用户体验和测试策略；不复制、改写式复制或逐行参考源代码、workflow、注释、测试实现或文件结构。
- 许可证或来源不明确时，不复用代码。

## 1. MockBukkit/MockBukkit

- URL：<https://github.com/MockBukkit/MockBukkit>
- 审计 revision：`ae642f964954082562a4afdf5d67b19c07058b3d`
- 审计时分支：`minecraft/v26.2`
- 许可证：MIT（以该 revision 的许可证文件为准）
- 可用性与维护状态：项目仍有持续维护迹象，当前分支和文档面向较新的 Minecraft/Paper API；适合作为可运行的 Bukkit/Paper mock 测试框架。

### 值得借鉴

- 用明确的 `mock`、`load`、`unmock` 生命周期建立可重复 fixture；
- 允许测试插件发现、加载、enable/disable 以及依赖关系；
- 把测试服务器状态封装成测试 fixture，减少每个测试自行清理的机会。

### 与 PluginMatrix 的差异

MockBukkit 主要在测试进程内模拟 Bukkit/Paper API，不启动真实 Paper JVM，不执行 Paper bootstrap，也不能证明真实服务器对插件 JAR 的发现、类加载和运行时兼容性。因此它适合补充离线测试，不替代 PluginMatrix 的真实 Paper Verifier。

### 复用决定

**采用高层测试思想，暂缓代码复用。** 当前不需要引入 mock framework；PluginMatrix 的核心证据仍必须来自真实 Paper、runtime probe、server.log 和结构化报告。

## 2. MockBukkit/paper-integration-tester

- URL：<https://github.com/MockBukkit/paper-integration-tester>
- 审计 revision：`f256873e92145dffed2f4a0718b25689a1d811f4`
- 许可证：MIT（以该 revision 的许可证文件为准）
- 可用性与维护状态：README 在该 revision 明确标记项目为 WIP，并说明当前不能编译；因此不能视为当前可直接依赖的成熟组件。

### 值得借鉴

- 通过 Testcontainers 隔离真实 Paper 运行环境；
- 将测试 client 与 Paper server 通过 socket 通信，减少对宿主进程细节的依赖；
- 为 Paper API 建立可供测试编译使用的 mirror，说明真实集成测试需要明确 server/API 版本边界。

### 与 PluginMatrix 的差异

该项目的重点是容器化的交互式集成测试和测试客户端；PluginMatrix 当前只验证单个插件的启动、生命周期和稳定窗口，使用本地隔离目录、临时端口和 runtime probe，不引入容器或游戏行为客户端。容器编排、client/server 协议和 API mirror 会显著扩大当前产品复杂度。

### 复用决定

**暂缓。** 当前只保留“真实 Paper 必须隔离运行”的设计认识，不引入其代码、容器结构或测试协议。若未来重新评估，应先确认项目可编译、维护状态和许可证文本仍与审计 revision 一致。

## 3. FN-FAL113/minecraft-plugin-runtime-test

- URL：<https://github.com/FN-FAL113/minecraft-plugin-runtime-test>
- 审计 revision：`e9b0107e8aab78f404b14f1fca30478864b4f93f`
- 许可证：GPL-3.0；`package.json` 在该 revision 标注 `GPL-3.0-or-later`
- 可用性与维护状态：早期 composite GitHub Action；可作为流程原型阅读，但不具备 PluginMatrix 所需的稳定证据和失败分类能力。

### 值得借鉴

- 在 GitHub Actions 中准备 Java/Node 环境；
- 获取待测试插件 artifact，下载 Paper，写入 EULA 并启动服务器；
- 将真实服务器启动纳入 CI，而不是只做编译或静态检查。

### 与 PluginMatrix 的差异

该项目的实现包含下载最新 Paper、硬编码第三方依赖、启动 Java 进程等早期流程，但没有可靠的 ready 判定、超时控制、进程清理、结构化 Matrix Report 或按环境保留 artifacts。PluginMatrix 已将这些职责放入 Python Runtime Verifier 和串行 Matrix，并要求依赖插件由用户明确提供、Paper build 和 JAR 证据可追溯。

### 复用决定

**明确不采用代码。** 由于 GPL-3.0 许可边界，本项目只记录高层 CI 流程经验，不复制或改写其源代码、workflow YAML、注释、测试实现或文件结构。当前 workflow 也不依赖其实现。

## 综合结论

1. 没有任何外部代码在本次审计中达到“应直接引入”的标准。
2. MockBukkit 的 fixture/lifecycle 思路可作为未来离线测试补充，但不改变真实 Paper 证据边界。
3. paper-integration-tester 的隔离和真实服务器方向有参考价值，但当前 WIP 状态和额外容器协议使其暂缓。
4. GPL 项目只保留高层经验，明确排除代码和 workflow 复用。
5. 当前源码树和发行包已排除 EnhancedFly 二进制；旧公开提交的 raw JAR 仍可访问（2026-09-13 HEAD：200，17,868,623 字节）。不得将删除当前树文件描述成历史对象已撤除。授权核实或历史对象处理由所有者决定，见 `V0.5.1_PREPARATION.md`。公开成功示例使用仓库内可审计且已由所有者确认发布权的 fixture。

如未来决定复用 MIT 项目的实质性代码，必须在项目中记录：项目 URL、原始 revision、版权声明、完整许可证文本、复用文件、修改内容及理由。当前没有复制第三方代码，因此无需把被参考项目的许可证并入项目根许可证；运行时下载项和非复制参考项仍需保留来源记录。
