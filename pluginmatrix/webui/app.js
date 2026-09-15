"use strict";

const token = document.querySelector('meta[name="pluginmatrix-token"]').content;
const byId = (id) => document.getElementById(id);
const messages = {
  en: {
    eyebrow: "LOCAL RUNTIME VERIFIER", language: "Language", localOnly: "Local only.",
    scopeNotice: "Files selected here are copied only to this local process and are never uploaded to a remote service. PASS has the same narrow meaning as the CLI: ready, matching identity and CodeSource, enabled, and stable probe evidence. Folia PASS does not prove thread or cross-region safety.",
    inputs: "Inputs", single: "Single", matrix: "Matrix", pluginPath: "Plugin JAR path",
    selectPlugin: "Or select plugin JAR", dependencyPaths: "Dependency JAR paths", onePerLine: "one path per line",
    selectDependencies: "Or select dependency JARs", environments: "Environments", addEnvironment: "Add environment",
    behaviorChecks: "Behavior checks", enableBehavior: "Enable behavior verification", behaviorTimeout: "Behavior phase timeout (seconds)",
    addBehaviorCheck: "Add check", behaviorScope: "Checks run only after runtime stability passes. Final PASS requires both runtime PASS and behavior PASS.",
    check: "Check", checkId: "Check ID", checkType: "Check type", checkTimeout: "Check timeout (seconds)",
    checkName: "Registered name or service class", expectedResult: "Expected result", expectedTrue: "true", expectedFalse: "false",
    commandArgs: "Command arguments (JSON array)", waitSeconds: "Wait duration (seconds)", typeCommandRegistered: "Command registered",
    typePermissionRegistered: "Permission registered", typeServiceRegistered: "Service registered", typeConsoleCommand: "Console command", typeWait: "Wait",
    runOptions: "Run options", startupTimeout: "Startup timeout (seconds)", stabilityWindow: "Stability window (seconds)",
    concurrentEnvironments: "Concurrent environments", runVerification: "Run verification", generateConfig: "Generate JSON config",
    importConfigPath: "Import existing JSON config by local path", import: "Import", configuration: "Generated / imported configuration",
    downloadJson: "Download JSON", progressResults: "Progress & results", cancelTask: "Cancel task", cancelling: "Cancelling...",
    noTask: "No task running.", runAgain: "Run again", environment: "Environment", remove: "Remove", provider: "Provider", localServer: "Local server",
    minecraftVersion: "Minecraft version", build: "Build", latestOrNumber: "latest or number", heap: "Heap MiB",
    catalogLoading: "Loading available versions...", javaRuntime: "Java runtime", manualJava: "Specify executable manually",
    useDetectedJava: "Use a detected runtime", javaExecutable: "Java version, command, or executable path",
    javaLoading: "Discovering installed Java runtimes...", localJarPath: "Local server JAR path", selectLocalJar: "Or select local server JAR",
    serverName: "Declared server name", runtimeContract: "Runtime contract", importing: "Importing {name} locally...",
    selectJar: "Select or enter the {kind} JAR", plugin: "plugin", dependency: "dependency", server: "server",
    fileImportFailed: "File import failed", catalogOnline: "{count} {item} loaded from the official Provider API.",
    catalogCached: "{count} {item} loaded from the local metadata cache.", catalogStale: "Network refresh failed. Showing {count} cached {item}.",
    catalogUnavailable: "Could not load the Provider list. You can still enter a value manually.", versions: "versions", builds: "builds",
    localCatalog: "Local servers use the version declared by you.", noBuilds: "No builds were returned for this version. Check the version or enter a build manually.",
    buildNotFound: "The selected build is not in the published list.", noJava: "No working Java runtime was detected. Use the manual executable field.",
    javaDetected: "Detected {count} Java runtime(s). Select a full JDK.", javaLocal: "Compatibility depends on the selected local server contract. A full JDK with javac is required.",
    javaManualHint: "Manual Java selection is enabled. PluginMatrix will verify the executable before starting the server.",
    javaNeedJdk: "This runtime has no usable javac. Select a full JDK.", javaCompatible: "Java {major} matches the documented requirement for Minecraft {version}.",
    javaTooOld: "Java {actual} is older than the documented Java {required} requirement for Minecraft {version}.",
    javaNewer: "Java {actual} is newer than the documented Java {required} baseline. Java {required} is the reproducible choice.",
    javaRequired: "Minecraft {version} uses the documented Java {required} baseline. Select a full JDK.",
    taskStatus: "{status} - task {id}", queued: "Queued", running: "Verification running", cancellingStatus: "Cancellation requested",
    completedPass: "Verification completed", completedIssues: "Verification completed with issues", cancelled: "Verification cancelled", failed: "Task failed",
    cancellationRequested: "cancellation requested", technicalDetails: "Technical details", eventEnvironment: "Environment {number}",
    event_matrix_started: "Started a matrix of {total} environments with up to {max_parallel} running at once.",
    event_environment_started: "Preparing {provider}.", event_download_started: "Downloading the selected server build.",
    event_download_cached: "Checking the cached server build.", event_download_completed: "Server build is ready.",
    event_server_started: "The server process started.", event_plugin_enabled: "The target plugin is enabled.",
    event_stability_progress: "Observing stability: {elapsed} of {duration} seconds.", event_environment_completed: "Finished with: {verdict}.",
    event_behavior_started: "Behavior verification started with {checks} checks.",
    event_behavior_check_started: "Started behavior check {check_id} ({check_type}).",
    event_behavior_check_completed: "Behavior check {check_id} finished with {verdict}.",
    event_behavior_completed: "Behavior verification finished with {verdict}.",
    event_matrix_completed: "Finished {completed} of {total} environments.", event_unknown: "Verification progress updated.",
    verdict_PASS: "Passed", verdict_ENVIRONMENT_INVALID: "Environment invalid", verdict_SERVER_START_FAILED: "Server start failed",
    verdict_SERVER_START_TIMEOUT: "Server start timed out", verdict_PLUGIN_NOT_DISCOVERED: "Plugin not discovered",
    verdict_PLUGIN_LOAD_FAILED: "Plugin load failed", verdict_PLUGIN_ENABLE_FAILED: "Plugin enable failed",
    verdict_PLUGIN_DISABLED: "Plugin was disabled", verdict_PLUGIN_UNSUPPORTED: "Plugin unsupported",
    verdict_CANCELLED: "Cancelled", verdict_UNKNOWN_FAILURE: "Unknown failure", verdict_FAIL: "Failed", verdict_ERROR: "Error",
    verdict_TIMEOUT: "Timed out", verdict_UNSUPPORTED: "Unsupported", verdict_SKIPPED: "Skipped", verdict_NOT_RUN: "Not run",
    runtimeVerdict: "Runtime verdict", behaviorVerdict: "Behavior verdict", finalResult: "Final result", finalPass: "Passed", finalFail: "Failed",
    behaviorReason: "Behavior reason", duration: "Duration", structuredEvidence: "Structured evidence", behaviorPostHealth: "Post-check health",
    reason_PASS: "The server became ready and the plugin remained enabled during the recorded stability window.",
    reason_ENVIRONMENT_INVALID: "The selected local Java/server environment could not be validated.",
    reason_SERVER_START_FAILED: "The server exited or reported a startup failure.", reason_SERVER_START_TIMEOUT: "The server did not become ready before the configured timeout.",
    reason_PLUGIN_NOT_DISCOVERED: "The runtime probe could not find the target plugin.", reason_PLUGIN_LOAD_FAILED: "The server could not load the target plugin.",
    reason_PLUGIN_ENABLE_FAILED: "The target plugin failed while enabling.", reason_PLUGIN_DISABLED: "The target plugin was disabled during observation.",
    reason_PLUGIN_UNSUPPORTED: "The plugin does not declare support required by this environment.", reason_CANCELLED: "The task was cancelled and owned processes were cleaned up.",
    reason_UNKNOWN_FAILURE: "PluginMatrix could not classify the failure. Review the report and server log.",
    configGenerated: "Configuration generated. Browser-selected files use session-temporary paths; enter durable local paths before saving a reusable config.",
    configImported: "Imported {source}", generateFirst: "Generate or import a configuration first.", invalidJson: "Configuration is not valid JSON: {error}",
    errorPrefix: "Error: {message}", artifactJson: "JSON report", artifactHtml: "HTML report", artifactLog: "server.log",
    artifactMatrixJson: "Matrix JSON report", artifactMatrixHtml: "Matrix HTML report", artifactEnvironmentJson: "Environment {number} JSON report",
    artifactEnvironmentLog: "Environment {number} server.log"
  },
  "zh-CN": {
    eyebrow: "本地运行时兼容性验证", language: "语言", localOnly: "仅在本机运行。",
    scopeNotice: "此处选择的文件只会复制到当前本地进程，不会上传到远程服务。PASS 与命令行含义相同且范围有限：服务器已就绪、目标身份与 CodeSource 匹配、插件已启用，并在稳定性窗口内持续通过探针。Folia PASS 不证明线程安全或跨 region 安全。",
    inputs: "输入", single: "单环境", matrix: "兼容性矩阵", pluginPath: "插件 JAR 路径", selectPlugin: "或选择插件 JAR",
    dependencyPaths: "依赖插件 JAR 路径", onePerLine: "每行一个路径", selectDependencies: "或选择依赖插件 JAR",
    environments: "运行环境", addEnvironment: "添加环境", behaviorChecks: "行为检查", enableBehavior: "启用行为验证",
    behaviorTimeout: "行为阶段超时（秒）", addBehaviorCheck: "添加检查",
    behaviorScope: "行为检查仅在运行时稳定性通过后执行；最终 PASS 要求 runtime 和 behavior 均通过。",
    check: "检查", checkId: "检查 ID", checkType: "检查类型", checkTimeout: "检查超时（秒）",
    checkName: "注册名称或服务类", expectedResult: "预期结果", expectedTrue: "true", expectedFalse: "false",
    commandArgs: "命令参数（JSON 数组）", waitSeconds: "等待时长（秒）", typeCommandRegistered: "命令已注册",
    typePermissionRegistered: "权限已注册", typeServiceRegistered: "服务已注册", typeConsoleCommand: "控制台命令", typeWait: "等待",
    runOptions: "运行选项", startupTimeout: "启动超时（秒）",
    stabilityWindow: "稳定观察窗口（秒）", concurrentEnvironments: "并发环境数", runVerification: "开始验证",
    generateConfig: "生成 JSON 配置", importConfigPath: "按本地路径导入现有 JSON 配置", import: "导入",
    configuration: "生成或导入的配置", downloadJson: "下载 JSON", progressResults: "进度与结果", cancelTask: "取消任务",
    cancelling: "正在取消...", noTask: "当前没有运行中的任务。", runAgain: "再次运行", environment: "环境", remove: "移除", provider: "服务端 Provider",
    localServer: "本地服务端", minecraftVersion: "Minecraft 版本", build: "构建版本", latestOrNumber: "latest 或构建号",
    heap: "堆内存 MiB", catalogLoading: "正在加载可用版本...", javaRuntime: "Java 运行时", manualJava: "手动指定 executable",
    useDetectedJava: "使用已发现的 Java", javaExecutable: "Java 主版本、命令或 executable 路径",
    javaLoading: "正在发现本机 Java...", localJarPath: "本地服务端 JAR 路径", selectLocalJar: "或选择本地服务端 JAR",
    serverName: "声明的服务端名称", runtimeContract: "运行时合同", importing: "正在本地导入 {name}...",
    selectJar: "请选择或输入{kind} JAR", plugin: "插件", dependency: "依赖插件", server: "服务端", fileImportFailed: "文件导入失败",
    catalogOnline: "已从官方 Provider API 加载 {count} 个{item}。", catalogCached: "已从本地元数据缓存加载 {count} 个{item}。",
    catalogStale: "网络刷新失败，当前显示 {count} 个缓存{item}。", catalogUnavailable: "无法加载 Provider 列表，仍可手动输入。",
    versions: "版本", builds: "构建", localCatalog: "本地服务端使用你声明的版本。", noBuilds: "该版本没有返回可用构建，请检查版本或手动输入构建号。",
    buildNotFound: "所选构建不在已发布列表中。", noJava: "未发现可用的 Java，请使用手动 executable 输入。",
    javaDetected: "发现 {count} 个 Java 运行时，请选择完整 JDK。", javaLocal: "兼容性取决于本地服务端合同；PluginMatrix 需要包含 javac 的完整 JDK。",
    javaManualHint: "已启用手动 Java 选择。PluginMatrix 会在启动服务端前验证该 executable。", javaNeedJdk: "此运行时没有可用的 javac，请选择完整 JDK。",
    javaCompatible: "Java {major} 符合 Minecraft {version} 的文档要求。", javaTooOld: "Java {actual} 低于 Minecraft {version} 的文档要求 Java {required}。",
    javaNewer: "Java {actual} 高于文档基线 Java {required}；为便于复现，建议使用 Java {required}。",
    javaRequired: "Minecraft {version} 的文档基线是 Java {required}，请选择完整 JDK。", taskStatus: "{status} - 任务 {id}",
    queued: "等待运行", running: "正在验证", cancellingStatus: "已请求取消", completedPass: "验证完成",
    completedIssues: "验证完成，但存在问题", cancelled: "验证已取消", failed: "任务失败", cancellationRequested: "已请求取消",
    technicalDetails: "技术详情", eventEnvironment: "环境 {number}",
    event_matrix_started: "开始验证 {total} 个环境，最多并发运行 {max_parallel} 个。", event_environment_started: "正在准备 {provider}。",
    event_download_started: "正在下载所选服务端构建。", event_download_cached: "正在检查缓存的服务端构建。", event_download_completed: "服务端构建已准备完成。",
    event_server_started: "服务端进程已启动。", event_plugin_enabled: "目标插件已启用。",
    event_stability_progress: "正在观察稳定性：{elapsed} / {duration} 秒。", event_environment_completed: "环境完成：{verdict}。",
    event_behavior_started: "行为验证已开始，共 {checks} 项检查。", event_behavior_check_started: "开始行为检查 {check_id}（{check_type}）。",
    event_behavior_check_completed: "行为检查 {check_id} 完成：{verdict}。", event_behavior_completed: "行为验证完成：{verdict}。",
    event_matrix_completed: "已完成 {completed} / {total} 个环境。", event_unknown: "验证进度已更新。",
    verdict_PASS: "通过", verdict_ENVIRONMENT_INVALID: "环境无效", verdict_SERVER_START_FAILED: "服务端启动失败",
    verdict_SERVER_START_TIMEOUT: "服务端启动超时", verdict_PLUGIN_NOT_DISCOVERED: "未发现插件", verdict_PLUGIN_LOAD_FAILED: "插件加载失败",
    verdict_PLUGIN_ENABLE_FAILED: "插件启用失败", verdict_PLUGIN_DISABLED: "插件被禁用", verdict_PLUGIN_UNSUPPORTED: "插件不受支持",
    verdict_CANCELLED: "已取消", verdict_UNKNOWN_FAILURE: "未知失败", verdict_FAIL: "失败", verdict_ERROR: "错误",
    verdict_TIMEOUT: "超时", verdict_UNSUPPORTED: "不支持", verdict_SKIPPED: "已跳过", verdict_NOT_RUN: "未运行",
    runtimeVerdict: "运行时结论", behaviorVerdict: "行为结论", finalResult: "最终结果", finalPass: "通过", finalFail: "失败",
    behaviorReason: "行为原因", duration: "耗时", structuredEvidence: "结构化证据", behaviorPostHealth: "检查后健康状态",
    reason_PASS: "服务端已就绪，插件在记录的稳定观察窗口内持续保持启用。", reason_ENVIRONMENT_INVALID: "所选本地 Java 或服务端环境未通过验证。",
    reason_SERVER_START_FAILED: "服务端退出或报告了启动失败。", reason_SERVER_START_TIMEOUT: "服务端未在配置的超时时间内就绪。",
    reason_PLUGIN_NOT_DISCOVERED: "运行时探针未找到目标插件。", reason_PLUGIN_LOAD_FAILED: "服务端无法加载目标插件。",
    reason_PLUGIN_ENABLE_FAILED: "目标插件在启用阶段失败。", reason_PLUGIN_DISABLED: "目标插件在观察期间被禁用。",
    reason_PLUGIN_UNSUPPORTED: "插件未声明此环境要求的支持能力。", reason_CANCELLED: "任务已取消，并已清理所属进程。",
    reason_UNKNOWN_FAILURE: "PluginMatrix 无法对失败分类，请查看报告和 server.log。",
    configGenerated: "配置已生成。浏览器选择的文件使用会话临时路径；保存可复用配置前，请改为持久的本地路径。",
    configImported: "已导入 {source}", generateFirst: "请先生成或导入配置。", invalidJson: "配置不是有效 JSON：{error}",
    errorPrefix: "错误：{message}", artifactJson: "JSON 报告", artifactHtml: "HTML 报告", artifactLog: "server.log",
    artifactMatrixJson: "矩阵 JSON 报告", artifactMatrixHtml: "矩阵 HTML 报告", artifactEnvironmentJson: "环境 {number} JSON 报告",
    artifactEnvironmentLog: "环境 {number} server.log"
  }
};

Object.assign(messages.en, {
  localScope: "Local execution & verification scope", choosePlugin: "Choose plugin JAR", noPluginSelected: "No plugin selected",
  useLocalPath: "Use an existing local path", localDependencies: "Local dependency JARs", analyzeNext: "Analyze & continue",
  selectedEnvironment: "Selected environment", runSummary: "Startup {timeout} s · Stability {stability} s · Concurrency {parallel}",
  incompleteDownloads: "Incomplete or active staging (not installed)", diag_MISSING_DEPENDENCY: "Provide the local JAR for {name}, required by {plugin}.",
  diag_DEPENDENCY_CASE_MISMATCH: "Correct the declared dependency name and capitalization: {plugin} / {name}.",
  diag_OPTIONAL_DEPENDENCY_ABSENT: "Optional local dependency not supplied: {name} ({plugin}).",
  diag_DEPENDENCY_CYCLE: "Resolve the required-dependency cycle before running.", diag_IDENTITY_CONFLICT: "Resolve duplicate plugin names, file names or provides aliases.",
  diag_STATIC_ANALYSIS_FAILED: "Correct the JAR or descriptor error shown in the recorded evidence.",
  appearance: "Appearance", systemTheme: "System", lightTheme: "Light", darkTheme: "Dark",
  verifyTab: "Verify", projectsTab: "Projects & history", cacheTab: "Downloads & cache",
  simpleMode: "Guided", advancedMode: "Advanced", profile: "Verification profile", customProfile: "Custom / legacy",
  wizardInput: "1. Plugin", wizardEnvironment: "2. Environment", wizardReview: "3. Review & run",
  analyzeContinue: "Analyze plugin", continueEnvironment: "Choose environment", recommendEnvironment: "Check official recommendation",
  applyRecommendation: "Use reviewed recommendation", prepareReview: "Prepare review", manageJdks: "Manage JDKs",
  jdkDirectory: "Managed JDK directory", configurationEditor: "Configuration import / export", selectConfig: "Select JSON configuration",
  applyJson: "Validate & apply JSON", projectName: "Project name", saveProject: "Save project", refresh: "Refresh",
  searchHistory: "Filter by name, version or result", savedProjects: "Saved projects", runHistory: "Run history",
  managedJdks: "Managed Temurin JDKs", jdkMajor: "JDK major version", previewOfficial: "Preview official package",
  downloadReviewed: "Download reviewed JDK", serverCache: "Server download cache", downloadServer: "Download fixed official build",
  retryFailed: "Restore failed environments", trustInputs: "I trust these local JARs and accept the Minecraft EULA.",
  trustRequired: "Confirm that you trust the JARs and accept the Minecraft EULA before running.",
  profile_quick: "One environment. Startup 120 s; stability 5 s. No automatic Behavior checks.",
  profile_standard: "One environment. Startup 180 s; stability 10 s. Review command and permission registration checks.",
  profile_matrix: "2-256 explicit environments. Startup 180 s; stability 10 s. Concurrency 1-8.",
  profile_strict: "Fixed builds, complete supported static analysis and at least 30 s stability. Not a full compatibility guarantee.",
  profile_custom: "Explicit configuration; no profile defaults or automatic checks.",
  analysisReady: "Static prerequisites satisfied", analysisBlocked: "Static prerequisites need attention",
  staticScope: "Static analysis is not a runtime PASS or a safety guarantee.",
  dependenciesTitle: "Local dependency diagnostics", suggestionsTitle: "Suggested registration checks",
  omissions: "Omitted declarations", recommendationReady: "Recommendation ready for review", recommendationBlocked: "Unresolved prerequisites",
  recommendationScope: "Recommendation only. No compatibility verdict has been assigned.",
  emptyProjects: "No saved projects.", emptyHistory: "No verification runs yet.", emptyCache: "No recognized cached packages.",
  openProject: "Open project", viewResult: "View result", restoreRun: "Restore configuration",
  projectSaved: "Project saved locally.", changedInputs: "Inputs have changed or are missing: {paths}. Re-analyze before running.",
  managedIntegrity: "Integrity: {state}", verifyIntegrity: "Verify integrity", deleteCache: "Delete",
  confirmDelete: "Delete only this managed cache entry? {name}", source: "Source", pendingOperation: "Cache operation in progress...",
  operationComplete: "Cache operation completed.", noRecommendation: "Review a current, resolved recommendation first.",
  staleRecommendation: "Inputs changed. Request a fresh recommendation.", reviewRequired: "Configuration prepared. Review the profile, environment and checks.",
  checksReviewed: "Registration checks only; no console commands are generated.",
  scopeNotice: "Local execution, no remote uploads. Saving or running keeps selected JAR copies and evidence in the local project store. JARs execute with your OS permissions. PASS covers only the recorded runtime and declared Behavior checks; not all functionality or Folia thread safety.",
  configGenerated: "Configuration normalized. Save a project to retain browser-selected JARs across sessions.",
  jdkStorageScope: "Only managed entries can be deleted. System Java, persistent locks and server bootstrap caches are retained.",
  originalReason: "Recorded reason", nextSteps: "Next steps", sourceHash: "Configuration SHA-256",
  javaUnknown: "No reviewed Java baseline for this target. Select and validate a full JDK explicitly.",
  managedSelection: "Managed JDK (verified before use)", configEdited: "JSON has unapplied edits.",
  event_jdk_download_started: "Downloading the reviewed Temurin JDK.", event_jdk_download_completed: "JDK archive checksum verified.",
  event_jdk_installed: "Managed JDK installed and verified.", nativePlatform: "Platform",
  fix_ENVIRONMENT_INVALID: "Check the recorded prerequisite. Select a matching full JDK with javac; provide missing dependencies as local JARs.",
  fix_SERVER_START_FAILED: "Open server.log and check the first server/bootstrap error. Confirm the fixed build and required upstream downloads.",
  fix_SERVER_START_TIMEOUT: "Inspect server.log for download or startup progress before changing the timeout.",
  fix_PLUGIN_NOT_DISCOVERED: "Check plugin.yml, the declared name and the target JAR identity against the report.",
  fix_PLUGIN_LOAD_FAILED: "Inspect the load exception and supply declared local dependencies; correct the plugin descriptor or bytecode target.",
  fix_PLUGIN_ENABLE_FAILED: "Inspect the onEnable exception and the plugin's local configuration and dependencies.",
  fix_PLUGIN_DISABLED: "Inspect the disable reason and the last fresh probe sample; fix the reported plugin prerequisite.",
  fix_PLUGIN_UNSUPPORTED: "Use a supported server target. Only declare Folia support after implementing and validating its threading contract.",
  fix_UNKNOWN_FAILURE: "Inspect the original report, server.log and probe evidence. Do not infer success from missing evidence.",
  fix_CANCELLED: "Restore the configuration and start a new isolated run when ready.",
  fix_BEHAVIOR: "Review the failed check's typed observation and post-check health. Correct the plugin or the explicit assertion; runtime PASS remains separate."
});
Object.assign(messages["zh-CN"], {
  localScope: "本地执行与验证范围", choosePlugin: "选择插件 JAR", noPluginSelected: "尚未选择插件",
  useLocalPath: "使用已有的本地路径", localDependencies: "本地依赖插件 JAR", analyzeNext: "分析并继续",
  selectedEnvironment: "本次验证环境", runSummary: "启动超时 {timeout} 秒 · 稳定观察 {stability} 秒 · 并发 {parallel}",
  incompleteDownloads: "未完成或正在下载的暂存条目（尚未安装）", diag_MISSING_DEPENDENCY: "{plugin} 缺少依赖 {name}，请提供对应的本地 JAR。",
  diag_DEPENDENCY_CASE_MISMATCH: "请修正依赖声明名称及大小写：{plugin} / {name}。",
  diag_OPTIONAL_DEPENDENCY_ABSENT: "尚未提供可选本地依赖：{name}（{plugin}）。",
  diag_DEPENDENCY_CYCLE: "必需依赖存在循环，请修正后再运行。", diag_IDENTITY_CONFLICT: "请修正重复的插件名称、文件名或 provides 别名。",
  diag_STATIC_ANALYSIS_FAILED: "请根据原始证据修正 JAR 或描述符错误。",
  appearance: "外观", systemTheme: "跟随系统", lightTheme: "浅色", darkTheme: "深色",
  verifyTab: "验证", projectsTab: "项目与历史", cacheTab: "下载与缓存",
  simpleMode: "简单向导", advancedMode: "高级模式", profile: "验证方案", customProfile: "自定义 / 旧版",
  wizardInput: "1. 插件", wizardEnvironment: "2. 环境", wizardReview: "3. 确认并运行",
  analyzeContinue: "分析插件", continueEnvironment: "选择运行环境", recommendEnvironment: "查询官方环境建议",
  applyRecommendation: "采用已确认的建议", prepareReview: "生成待确认配置", manageJdks: "管理 JDK",
  jdkDirectory: "托管 JDK 目录", configurationEditor: "导入 / 导出配置", selectConfig: "选择 JSON 配置文件",
  applyJson: "校验并应用 JSON", projectName: "项目名称", saveProject: "保存项目", refresh: "刷新",
  searchHistory: "按名称、版本或结果筛选", savedProjects: "已保存项目", runHistory: "运行历史",
  managedJdks: "托管 Temurin JDK", jdkMajor: "JDK 主版本", previewOfficial: "预览官方安装包",
  downloadReviewed: "下载已确认的 JDK", serverCache: "服务端下载缓存", downloadServer: "下载指定官方构建",
  retryFailed: "恢复失败环境", trustInputs: "我信任这些本地 JAR，并接受 Minecraft EULA。",
  trustRequired: "运行前请确认信任 JAR 并接受 Minecraft EULA。",
  profile_quick: "单环境。启动超时 120 秒，稳定观察 5 秒。不自动添加行为检查。",
  profile_standard: "单环境。启动超时 180 秒，稳定观察 10 秒。确认命令与权限注册检查后运行。",
  profile_matrix: "2–256 个明确环境。启动超时 180 秒，稳定观察 10 秒。支持 1–8 并发。",
  profile_strict: "固定构建、完整的受支持静态分析、至少 30 秒稳定观察。不保证完整业务兼容。",
  profile_custom: "使用明确配置，不应用方案默认值或自动检查。",
  analysisReady: "静态前置条件已满足", analysisBlocked: "静态前置条件需要处理",
  staticScope: "静态分析不代表运行时通过，也不保证插件安全。",
  dependenciesTitle: "本地依赖诊断", suggestionsTitle: "建议的注册检查", omissions: "未生成的声明",
  recommendationReady: "建议已就绪，等待确认", recommendationBlocked: "尚有未解决的前置条件",
  recommendationScope: "仅为环境建议，尚未形成兼容性结论。",
  emptyProjects: "暂无已保存项目。", emptyHistory: "暂无验证历史。", emptyCache: "暂无可识别的缓存包。",
  openProject: "打开项目", viewResult: "查看结果", restoreRun: "恢复配置",
  projectSaved: "项目已保存到本机。", changedInputs: "输入已变化或缺失：{paths}。运行前请重新分析。",
  managedIntegrity: "完整性：{state}", verifyIntegrity: "校验完整性", deleteCache: "删除",
  confirmDelete: "仅删除此托管缓存条目？{name}", source: "来源", pendingOperation: "正在处理缓存操作...",
  operationComplete: "缓存操作完成。", noRecommendation: "请先获取并确认没有未决项的建议。",
  staleRecommendation: "输入已变化，请重新查询建议。", reviewRequired: "配置已生成，请确认方案、环境与检查项。",
  checksReviewed: "仅生成注册检查，不会自动执行控制台命令。",
  scopeNotice: "仅在本机执行，不远程上传。保存项目或运行时，会在本地保留所选 JAR 副本与证据。JAR 使用当前系统账户权限执行。PASS 仅涵盖记录的运行窗口和声明的行为检查，不代表全部功能兼容或 Folia 线程安全。",
  configGenerated: "配置已规范化。保存项目可在会话结束后继续使用浏览器选择的 JAR。",
  jdkStorageScope: "仅能删除托管条目。系统 Java、持久锁文件和服务端 bootstrap 缓存会保留。",
  originalReason: "原始原因", nextSteps: "处理建议", sourceHash: "配置 SHA-256",
  javaUnknown: "此目标尚无经审查的 Java 基线，请明确选择并验证完整 JDK。",
  managedSelection: "托管 JDK（使用前校验）", configEdited: "JSON 有尚未应用的编辑。",
  event_jdk_download_started: "正在下载已确认的 Temurin JDK。", event_jdk_download_completed: "JDK 归档校验通过。",
  event_jdk_installed: "托管 JDK 已安装并校验。", nativePlatform: "平台",
  fix_ENVIRONMENT_INVALID: "先查看报告中的前置错误。选择含 javac 的匹配 JDK；缺失依赖需手动提供本地 JAR。",
  fix_SERVER_START_FAILED: "打开 server.log，检查最早的启动或 bootstrap 错误，确认固定构建及上游依赖下载。",
  fix_SERVER_START_TIMEOUT: "先检查 server.log 的下载与启动进度，再决定是否调整超时。",
  fix_PLUGIN_NOT_DISCOVERED: "核对 plugin.yml、声明名称，以及报告中的目标 JAR 身份。",
  fix_PLUGIN_LOAD_FAILED: "查看加载异常，提供声明的本地依赖，并修正插件描述符或字节码目标。",
  fix_PLUGIN_ENABLE_FAILED: "查看 onEnable 异常，检查插件本地配置及依赖。",
  fix_PLUGIN_DISABLED: "查看禁用原因和最后的新鲜探针样本，修复报告指出的插件前置问题。",
  fix_PLUGIN_UNSUPPORTED: "改用支持的服务端目标。只有实现并验证 Folia 线程合同后才能声明支持。",
  fix_UNKNOWN_FAILURE: "检查原始报告、server.log 与探针证据。不能从缺少证据推断成功。",
  fix_CANCELLED: "准备好后恢复配置，启动新的隔离验证。",
  fix_BEHAVIOR: "检查失败项的结构化 observation 与检查后健康样本，修正插件或明确断言；运行时 PASS 保持独立。"
});

let language = null;
try { language = localStorage.getItem("pluginmatrix-language"); } catch (_) { /* Browser storage is optional. */ }
if (!messages[language]) language = navigator.language.toLowerCase().startsWith("zh") ? "zh-CN" : "en";
let activeJob = null, eventCursor = 0, pollTimer = null, lastJob = null, eventHistory = [];
let javaCatalog = { runtimes: [], recommended: null }, providerNames = { paper: "Paper", purpur: "Purpur", folia: "Folia", local: "Local server" };
const catalogRequests = new Map();
let cardSequence = 0;
let configurationBase = { schema: 2, profile: { id: "standard", revision: 1 } };
let profileCatalog = [], wizardStep = 0, currentView = "verify", projectId = null;
let analysisResult = null, recommendationResult = null, recommendationFingerprint = null;
let behaviorReviewed = false, configDirty = false, currentSource = null, jdkPreview = null, cacheJob = null;
let historyData = [], projectsData = [], runSubmitting = false;
const uploadedFiles = new WeakMap();

function t(key, values = {}) {
  let text = (messages[language] && messages[language][key]) || messages.en[key] || key;
  for (const [name, value] of Object.entries(values)) text = text.replaceAll(`{${name}}`, String(value));
  return text;
}
function applyLanguage(root = document) {
  document.documentElement.lang = language;
  root.querySelectorAll("[data-i18n]").forEach((element) => { element.textContent = t(element.dataset.i18n); });
  byId("language").value = language;
}
function api(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  if (options.body !== undefined && !(options.body instanceof Blob)) {
    headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(options.body);
  }
  if (options.method && options.method !== "GET") headers["X-PluginMatrix-Token"] = token;
  return fetch(path, { credentials: "same-origin", ...options, headers }).then(async (response) => {
    const data = await response.json().catch(() => ({ error: `HTTP ${response.status}` }));
    if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
    return data;
  });
}
function setStatus(text, error = false) {
  byId("status").textContent = text;
  byId("status").classList.toggle("error", error);
}
function element(tag, text, className) {
  const node = document.createElement(tag); if (text !== undefined) node.textContent = text;
  if (className) node.className = className; return node;
}
function detailsFor(title, data) {
  const details = element("details"); details.append(element("summary", title), element("pre", JSON.stringify(data, null, 2))); return details;
}
function actionButton(text, action, className = "secondary") {
  const button = element("button", text, className); button.type = "button";
  button.addEventListener("click", () => busy(button, action)); return button;
}
async function busy(button, action) {
  if (button.disabled) return;
  button.disabled = true;
  try { return await action(); } catch (error) { setStatus(t("errorPrefix", { message: error.message }), true); }
  finally { button.disabled = false; }
}
function setView(view) {
  currentView = view;
  document.querySelectorAll(".workspace-view").forEach((node) => node.classList.toggle("hidden", node.id !== `${view}-view`));
  document.querySelectorAll("[data-view]").forEach((node) => { if (node.dataset.view === view) node.setAttribute("aria-current", "page"); else node.removeAttribute("aria-current"); });
  if (view === "projects") loadHistory();
  if (view === "cache") refreshCache();
}
function setStep(step) {
  wizardStep = step;
  const advanced = document.querySelector('input[name="experience"]:checked').value === "advanced";
  document.body.classList.toggle("advanced", advanced);
  document.querySelectorAll(".wizard-page").forEach((node) => node.classList.toggle("hidden", !advanced && Number(node.dataset.wizard) !== step));
  byId("wizard-nav").classList.toggle("hidden", advanced);
  document.querySelectorAll("[data-step]").forEach((node) => node.setAttribute("aria-current", Number(node.dataset.step) === step ? "step" : "false"));
  renderReview();
}
function renderReview() {
  const host = byId("review-summary"); host.replaceChildren();
  host.append(element("h3", t("selectedEnvironment")));
  for (const card of document.querySelectorAll(".environment")) {
    const provider = card.querySelector(".provider").value, version = card.querySelector(".minecraft").value;
    const java = card.dataset.manualJava === "true" ? card.querySelector(".java").value : card.querySelector(".java-select").value;
    const runtime = javaCatalog.runtimes.find(r => r.path === java);
    const title = [providerDisplay(provider), version, `${t("build")} ${card.querySelector(".build").value}`].join(" / ");
    const row = element("div", undefined, "review-environment");
    row.append(element("strong", title), element("span", runtime?.major ? `JDK ${runtime.major}` : (java.startsWith("managed:") ? t("managedSelection") : java)));
    row.title = java; host.append(row);
  }
  byId("run-summary").textContent = t("runSummary", { timeout: byId("timeout").value, stability: byId("stability").value, parallel: byId("parallel").value });
}
function refreshSourceName() {
  const name = byId("plugin-file").files[0]?.name || byId("plugin-path").value.split(/[\\/]/).pop();
  byId("plugin-file-name").textContent = name || t("noPluginSelected");
  byId("plugin-file-name").removeAttribute("data-i18n");
}
function updateProfile() { byId("profile-description").textContent = t(`profile_${byId("profile").value || "custom"}`); }
function setConfigurationText(document) { byId("configuration").value = JSON.stringify(document, null, 2); configDirty = false; }
function fingerprint() {
  return JSON.stringify([byId("plugin-path").value, [...byId("plugin-file").files].map(f => [f.name, f.size, f.lastModified]),
    byId("dependency-paths").value, [...byId("dependency-files").files].map(f => [f.name, f.size, f.lastModified]),
    [...document.querySelectorAll(".environment")].map(c => [c.querySelector(".provider").value, c.querySelector(".minecraft").value, c.querySelector(".build").value]),
    byId("jdk-directory").value]);
}
function setManualJava(card, manual) {
  if (!javaCatalog.runtimes.length) manual = true;
  card.dataset.manualJava = manual ? "true" : "false";
  card.querySelector(".java-advanced").classList.toggle("hidden", !manual);
  card.querySelector(".java-select").disabled = manual;
  const button = card.querySelector(".java-advanced-toggle");
  button.classList.toggle("hidden", !javaCatalog.runtimes.length);
  button.textContent = t(manual ? "useDetectedJava" : "manualJava");
  updateJavaHint(card);
}
function populateJava(card, requested = card.dataset.requestedJava || "") {
  const select = card.querySelector(".java-select");
  select.replaceChildren();
  for (const runtime of javaCatalog.runtimes) {
    const option = document.createElement("option");
    option.value = runtime.path;
    option.textContent = runtime.source === "managed" ? `JDK ${runtime.major} · ${t("managedSelection")} · ${runtime.id}` : `Java ${runtime.version}${runtime.jdk ? " JDK" : " JRE"} - ${runtime.path}`;
    select.appendChild(option);
  }
  const match = requested ? (javaCatalog.runtimes.find((runtime) => runtime.path === requested)
    || (/^\d+$/.test(requested) ? javaCatalog.runtimes.find((runtime) => runtime.jdk && runtime.major === Number(requested)) : null))
    : javaCatalog.runtimes.find((runtime) => runtime.path === javaCatalog.recommended);
  if (match) select.value = match.path;
  card.querySelector(".java").value = requested || (match ? String(match.major) : "21");
  setManualJava(card, Boolean(requested && !match) || !match);
  card.querySelector(".java-hint").textContent = javaCatalog.runtimes.length
    ? t("javaDetected", { count: javaCatalog.runtimes.length }) : t("noJava");
  updateJavaHint(card);
}
function addEnvironment(value = {}) {
  const fragment = byId("environment-template").content.cloneNode(true);
  const card = fragment.querySelector(".environment");
  const server = value.server || {};
  card.dataset.requestedJava = value.java && typeof value.java === "object" ? `managed:${value.java.managed}` : String(value.java || "");
  card.originalServer = { ...server };
  card.originalEnvironment = { ...value };
  card.querySelector(".provider").value = server.type || "paper";
  card.querySelector(".minecraft").value = server.version || value.paper || "";
  card.dataset.recommendedJava = javaRequirement(card.querySelector(".minecraft").value) || "";
  card.querySelector(".build").value = server.build ?? value.paper_build ?? "latest";
  card.querySelector(".heap").value = server.heap_mb || 1024;
  card.querySelector(".server-path").value = server.jar || "";
  card.querySelector(".server-name").value = server.name || "";
  card.querySelector(".runtime").value = server.runtime || "paperclip";
  const suffix = ++cardSequence;
  const versions = card.querySelector(".version-options"), builds = card.querySelector(".build-options");
  versions.id = `versions-${suffix}`; builds.id = `builds-${suffix}`;
  card.querySelector(".minecraft").setAttribute("list", versions.id);
  card.querySelector(".build").setAttribute("list", builds.id);
  byId("environments").appendChild(fragment);
  applyLanguage(card);
  card.querySelector(".provider").addEventListener("change", () => { updateLocal(card); loadProviderVersions(card, true); });
  let versionTimer = null;
  card.querySelector(".minecraft").addEventListener("input", () => {
    clearTimeout(versionTimer);
    card.dataset.recommendedJava = javaRequirement(card.querySelector(".minecraft").value) || "";
    versionTimer = setTimeout(() => loadBuilds(card, false), 350);
    updateJavaHint(card);
  });
  card.querySelector(".java-select").addEventListener("change", () => updateJavaHint(card));
  card.querySelector(".java").addEventListener("input", () => updateJavaHint(card));
  card.querySelector(".java-advanced-toggle").addEventListener("click", () => setManualJava(card, card.dataset.manualJava !== "true"));
  card.querySelector(".remove").addEventListener("click", () => { card.remove(); renumber(); });
  updateLocal(card); populateJava(card); renumber(); loadProviderVersions(card, false);
}
function updateBehaviorCheck(card) {
  const type = card.querySelector(".behavior-type").value;
  const wait = type === "wait", command = type === "console_command";
  card.querySelector(".behavior-named-fields").classList.toggle("hidden", wait);
  card.querySelector(".behavior-wait-field").classList.toggle("hidden", !wait);
  card.querySelector(".behavior-args-field").classList.toggle("hidden", !command);
}
function renumberBehavior() {
  [...document.querySelectorAll(".behavior-check")].forEach((card, index) => {
    card.querySelector(".behavior-check-number").textContent = String(index + 1);
  });
}
function addBehaviorCheck(value = {}) {
  const fragment = byId("behavior-check-template").content.cloneNode(true);
  const card = fragment.querySelector(".behavior-check");
  const number = document.querySelectorAll(".behavior-check").length + 1;
  card.querySelector(".behavior-id").value = value.id || `check-${number}`;
  card.querySelector(".behavior-type").value = value.type || "command_registered";
  card.querySelector(".behavior-check-timeout").value = value.timeout ?? 5;
  card.querySelector(".behavior-name").value = value.name || "";
  card.querySelector(".behavior-expect").value = String(value.expect ?? true);
  card.querySelector(".behavior-args").value = JSON.stringify(value.args || []);
  card.querySelector(".behavior-seconds").value = value.seconds ?? 1;
  byId("behavior-checks").appendChild(fragment);
  applyLanguage(card);
  card.querySelector(".behavior-type").addEventListener("change", () => updateBehaviorCheck(card));
  card.querySelector(".remove-behavior").addEventListener("click", () => { card.remove(); renumberBehavior(); });
  updateBehaviorCheck(card); renumberBehavior();
}
function setBehaviorEnabled(enabled) {
  byId("behavior-enabled").checked = enabled;
  byId("behavior-editor").classList.toggle("hidden", !enabled);
  if (enabled && !document.querySelector(".behavior-check")) addBehaviorCheck();
}
function updateLocal(card) {
  const local = card.querySelector(".provider").value === "local";
  card.querySelector(".local-fields").classList.toggle("hidden", !local);
  card.querySelector(".build").disabled = local;
  card.querySelector(".minecraft").removeAttribute("readonly");
  if (local) card.querySelector(".catalog-status").textContent = t("localCatalog");
  updateJavaHint(card);
}
function renumber() {
  const cards = [...document.querySelectorAll(".environment")];
  cards.forEach((card, index) => { card.querySelector(".environment-number").textContent = String(index + 1); });
  const single = document.querySelector('input[name="mode"]:checked').value === "single";
  byId("add-environment").disabled = single;
  cards.forEach((card) => { card.querySelector(".remove").disabled = single || cards.length === 1; });
  if (single) cards.slice(1).forEach((card) => card.remove());
}
function catalog(path) {
  if (!catalogRequests.has(path)) catalogRequests.set(path, api(path).catch((error) => { catalogRequests.delete(path); throw error; }));
  return catalogRequests.get(path);
}
function catalogText(data, count, item) {
  if (!data.available) return t("catalogUnavailable");
  if (data.source === "stale_cache") return t("catalogStale", { count, item: t(item) });
  if (data.source === "cache") return t("catalogCached", { count, item: t(item) });
  return t("catalogOnline", { count, item: t(item) });
}
function javaRequirement(version) {
  // The application catalog supplies the reviewed baseline; the browser never extrapolates it.
  return null;
}
function providerDisplay(type, fallback = "") {
  if (type === "local") return t("localServer");
  return providerNames[type] || fallback || type || "Provider";
}
async function loadProviderVersions(card, providerChanged) {
  const provider = card.querySelector(".provider").value;
  if (provider === "local") { updateLocal(card); return; }
  const status = card.querySelector(".catalog-status");
  status.textContent = t("catalogLoading"); status.classList.remove("error");
  if (providerChanged) { card.querySelector(".version-options").replaceChildren(); card.querySelector(".build-options").replaceChildren(); }
  try {
    const data = await catalog(`/api/providers/${encodeURIComponent(provider)}/versions`);
    if (!card.isConnected || card.querySelector(".provider").value !== provider) return;
    const list = card.querySelector(".version-options"); list.replaceChildren();
    for (const version of data.versions || []) { const option = document.createElement("option"); option.value = version; list.appendChild(option); }
    const input = card.querySelector(".minecraft");
    status.textContent = catalogText(data, data.versions.length, "versions");
    status.classList.toggle("warning", data.source === "stale_cache" || !data.available);
    await loadBuilds(card, false);
  } catch (error) {
    status.textContent = `${t("catalogUnavailable")} ${error.message}`; status.classList.add("error");
  }
}
async function loadBuilds(card, resetBuild) {
  const provider = card.querySelector(".provider").value;
  const version = card.querySelector(".minecraft").value.trim();
  if (provider === "local" || !/^\d+\.\d+(?:\.\d+)?$/.test(version)) { updateJavaHint(card); return; }
  const input = card.querySelector(".build");
  if (!input.value.trim()) input.value = "latest";
  card.dataset.recommendedJava = javaRequirement(version) || "";
  updateJavaHint(card);
  const status = card.querySelector(".catalog-status");
  try {
    const data = await catalog(`/api/providers/${encodeURIComponent(provider)}/versions/${encodeURIComponent(version)}/builds`);
    if (!card.isConnected || card.querySelector(".provider").value !== provider || card.querySelector(".minecraft").value.trim() !== version) return;
    const list = card.querySelector(".build-options"); list.replaceChildren();
    const latest = document.createElement("option"); latest.value = "latest"; list.appendChild(latest);
    for (const build of data.builds || []) {
      const option = document.createElement("option"); option.value = String(build.id);
      option.label = build.channel ? `${build.id} (${build.channel})` : String(build.id); list.appendChild(option);
    }
    const fixed = /^\d+$/.test(input.value) ? Number(input.value) : null;
    const missing = fixed !== null && !(data.builds || []).some((build) => build.id === fixed);
    status.textContent = missing ? t("buildNotFound") : (data.builds.length ? catalogText(data, data.builds.length, "builds") : t("noBuilds"));
    status.classList.toggle("warning", missing || data.source === "stale_cache" || !data.available || !data.builds.length);
    card.dataset.recommendedJava = data.recommended_java || "";
    updateJavaHint(card);
  } catch (error) {
    status.textContent = `${t("catalogUnavailable")} ${error.message}`; status.classList.add("error");
  }
}
function updateJavaHint(card) {
  const hint = card.querySelector(".java-hint");
  hint.classList.remove("error", "warning", "success");
  if (card.querySelector(".provider").value === "local") { hint.textContent = t("javaLocal"); return; }
  const version = card.querySelector(".minecraft").value.trim();
  const required = Number(card.dataset.recommendedJava || 0);
  if (card.dataset.manualJava === "true") { hint.textContent = t("javaManualHint"); return; }
  const runtime = javaCatalog.runtimes.find((item) => item.path === card.querySelector(".java-select").value);
  if (!runtime) { hint.textContent = required ? t("javaRequired", { version, required }) : t("noJava"); hint.classList.add("warning"); return; }
  if (!runtime.jdk) { hint.textContent = t("javaNeedJdk"); hint.classList.add("error"); return; }
  if (!required) { hint.textContent = t("javaUnknown"); return; }
  if (runtime.major < required) { hint.textContent = t("javaTooOld", { actual: runtime.major, required, version }); hint.classList.add("error"); }
  else if (runtime.major > required) { hint.textContent = t("javaNewer", { actual: runtime.major, required, version }); hint.classList.add("warning"); }
  else { hint.textContent = t("javaCompatible", { major: runtime.major, version }); hint.classList.add("success"); }
}
async function loadJava() {
  try { javaCatalog = await api("/api/java"); } catch (_) { javaCatalog = { runtimes: [], recommended: null }; }
  document.querySelectorAll(".environment").forEach((card) => populateJava(card, card.querySelector(".java").value.trim()));
}
async function loadProviders() {
  try {
    const data = await api("/api/providers");
    for (const provider of data.providers || []) providerNames[provider.type] = provider.name;
  } catch (_) { /* Static names remain available. */ }
}
async function upload(file, kind) {
  if (uploadedFiles.has(file)) return uploadedFiles.get(file);
  const response = await fetch("/api/import", { method: "POST", credentials: "same-origin", headers: {
    "Content-Type": "application/octet-stream", "X-PluginMatrix-Token": token,
    "X-PluginMatrix-Filename": encodeURIComponent(file.name), "X-PluginMatrix-File-Kind": kind
  }, body: file });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || t("fileImportFailed"));
  const reference = { file_id: data.file_id }; uploadedFiles.set(file, reference); return reference;
}
async function fileReference(pathInput, fileInput, kind) {
  const path = pathInput.value.trim();
  if (path) return path;
  if (fileInput.files.length !== 1) throw new Error(t("selectJar", { kind: t(kind) }));
  setStatus(t("importing", { name: fileInput.files[0].name }));
  return upload(fileInput.files[0], kind);
}
async function collectInputs() {
  const plugin = await fileReference(byId("plugin-path"), byId("plugin-file"), "plugin");
  const dependencies = byId("dependency-paths").value.split(/\r?\n/).map((value) => value.trim()).filter(Boolean);
  for (const file of byId("dependency-files").files) { setStatus(t("importing", { name: file.name })); dependencies.push(await upload(file, "dependency")); }
  return { plugin, dependencies };
}
async function collect() {
  const { plugin, dependencies } = await collectInputs();
  const environments = [];
  for (const card of document.querySelectorAll(".environment")) {
    const type = card.querySelector(".provider").value, buildText = card.querySelector(".build").value.trim();
    const server = { ...(card.originalServer.type === type ? card.originalServer : {}), type, version: card.querySelector(".minecraft").value.trim(), heap_mb: Number(card.querySelector(".heap").value) };
    if (type === "local") {
      server.jar = await fileReference(card.querySelector(".server-path"), card.querySelector(".server-file"), "server");
      server.name = card.querySelector(".server-name").value.trim(); server.runtime = card.querySelector(".runtime").value;
    } else server.build = buildText === "" || buildText === "latest" ? "latest" : Number(buildText);
    const java = card.dataset.manualJava === "true" ? card.querySelector(".java").value.trim() : card.querySelector(".java-select").value;
    const environment = { server, java: java.startsWith("managed:") ? { managed: java.slice(8) } : java };
    environments.push(environment);
  }
  const payload = { ...configurationBase, plugin, dependencies, environments, options: { ...(configurationBase.options || {}),
    timeout: Number(byId("timeout").value), stability_window: Number(byId("stability").value), max_parallel: Number(byId("parallel").value)
  } };
  if (byId("profile").value) { payload.schema = 2; payload.profile = { id: byId("profile").value, revision: configurationBase.profile?.revision || 1 }; }
  else delete payload.profile;
  if (payload.schema === 2 && byId("jdk-directory").value.trim()) payload.options.jdk_dir = byId("jdk-directory").value.trim();
  else delete payload.options.jdk_dir;
  delete payload.behavior;
  if (byId("behavior-enabled").checked) {
    payload.behavior = {
      schema: 1,
      timeout: Number(byId("behavior-timeout").value),
      checks: [...document.querySelectorAll(".behavior-check")].map((card) => {
        const type = card.querySelector(".behavior-type").value;
        const check = { id: card.querySelector(".behavior-id").value.trim(), type, timeout: Number(card.querySelector(".behavior-check-timeout").value) };
        if (type === "wait") check.seconds = Number(card.querySelector(".behavior-seconds").value);
        else {
          check.name = card.querySelector(".behavior-name").value.trim();
          check.expect = card.querySelector(".behavior-expect").value === "true";
          if (type === "console_command") check.args = JSON.parse(card.querySelector(".behavior-args").value);
        }
        return check;
      })
    };
  }
  return { configuration: payload };
}
function applyConfiguration(config) {
  configurationBase = structuredClone(config); behaviorReviewed = true; configDirty = false;
  byId("profile").value = config.profile?.id || ""; updateProfile();
  byId("jdk-directory").value = config.options?.jdk_dir || "";
  byId("plugin-path").value = config.plugin || ""; byId("dependency-paths").value = (config.dependencies || []).join("\n");
  byId("plugin-file").value = ""; byId("dependency-files").value = "";
  const options = config.options || {}; byId("timeout").value = options.timeout || 120; byId("stability").value = options.stability_window || 5;
  byId("parallel").value = options.max_parallel || 1; document.querySelector(`input[name="mode"][value="${config.environments.length > 1 ? "matrix" : "single"}"]`).checked = true;
  byId("environments").replaceChildren(); (config.environments || []).forEach(addEnvironment); if (!(config.environments || []).length) addEnvironment(); renumber();
  byId("behavior-checks").replaceChildren();
  if (config.behavior) {
    byId("behavior-timeout").value = config.behavior.timeout ?? 60;
    (config.behavior.checks || []).forEach(addBehaviorCheck);
    setBehaviorEnabled(true);
  } else {
    byId("behavior-timeout").value = 60;
    setBehaviorEnabled(false);
  }
  setConfigurationText(config);
  refreshSourceName(); renderReview();
}
function verdictText(value) { return t(`verdict_${value || "UNKNOWN_FAILURE"}`); }
function checkTypeText(value) {
  const keys = { command_registered: "typeCommandRegistered", permission_registered: "typePermissionRegistered", service_registered: "typeServiceRegistered", console_command: "typeConsoleCommand", wait: "typeWait" };
  return keys[value] ? t(keys[value]) : value;
}
function jobStatus(job) {
  if (job.status === "queued") return t("queued");
  if (job.status === "running") return t("running");
  if (job.status === "cancelling") return t("cancellingStatus");
  if (job.status === "cancelled") return t("cancelled");
  if (job.status === "failed") return t("failed");
  return (job.summary && Number(job.summary.failed || 0) === 0) ? t("completedPass") : t("completedIssues");
}
function renderEvent(event) {
  const wrapper = document.createElement("div"); wrapper.className = "event";
  const text = document.createElement("span"), data = { ...(event.data || {}) };
  data.provider = providerDisplay(data.provider);
  data.verdict = verdictText(data.verdict);
  data.behavior_verdict = verdictText(data.behavior_verdict);
  data.check_type = checkTypeText(data.check_type);
  const key = event.kind === "download_started" && data.cached ? "event_download_cached" : `event_${event.kind}`;
  const prefix = event.environment_index === null || event.environment_index === undefined ? "" : `${t("eventEnvironment", { number: event.environment_index + 1 })}: `;
  text.textContent = prefix + t(messages.en[key] ? key : "event_unknown", data); wrapper.appendChild(text);
  const details = document.createElement("details"), summary = document.createElement("summary"), pre = document.createElement("pre");
  summary.textContent = t("technicalDetails"); pre.textContent = JSON.stringify(event, null, 2); details.append(summary, pre); wrapper.appendChild(details);
  byId("progress").appendChild(wrapper);
}
function artifactLabel(label) {
  const exact = { "JSON report": "artifactJson", "HTML report": "artifactHtml", "server.log": "artifactLog", "Matrix JSON report": "artifactMatrixJson", "Matrix HTML report": "artifactMatrixHtml", "behavior runtime probe": "structuredEvidence", "behavior response": "structuredEvidence" };
  if (exact[label]) return t(exact[label]);
  let match = /^Environment (\d+) JSON report$/.exec(label); if (match) return t("artifactEnvironmentJson", { number: match[1] });
  match = /^Environment (\d+) server\.log$/.exec(label); if (match) return t("artifactEnvironmentLog", { number: match[1] });
  match = /^Environment (\d+) behavior (runtime probe|response)$/.exec(label); if (match) return `${t("eventEnvironment", { number: match[1] })} ${t("structuredEvidence")} (${match[2]})`;
  return label;
}
function resultCell(label, value, state = null) {
  const cell = document.createElement("span"), caption = document.createElement("span"), strong = document.createElement("strong");
  caption.className = "verdict-label"; caption.textContent = label;
  strong.textContent = value; if (state) { strong.dataset.state = state; strong.title = state; }
  cell.append(caption, strong); return cell;
}
function renderResults(job) {
  if (job.error) { const p = document.createElement("p"); p.className = "error"; p.textContent = t("errorPrefix", { message: job.error }); byId("result").replaceChildren(p); return; }
  if (!job.summary) return;
  const container = document.createElement("div");
  for (const env of job.summary.environments || []) {
    const row = document.createElement("div"); row.className = "verdict";
    const head = document.createElement("div"); head.className = "verdict-head";
    const identity = document.createElement("span");
    const provider = providerDisplay(env.provider, env.provider_name) || t("environment");
    identity.textContent = [provider, env.minecraft_version, env.java ? `Java ${env.java}` : null].filter(Boolean).join(" / ");
    const runtime = env.runtime_verdict || env.verdict || "UNKNOWN_FAILURE";
    const behavior = env.behavior || { verdict: "NOT_RUN", checks: [] };
    const finalPass = Boolean(env.verification_passed);
    head.append(identity, resultCell(t("runtimeVerdict"), verdictText(runtime), runtime),
      resultCell(t("behaviorVerdict"), verdictText(behavior.verdict), behavior.verdict),
      resultCell(t("finalResult"), t(finalPass ? "finalPass" : "finalFail"), finalPass ? "PASS" : "FAIL"));
    const details = document.createElement("details"), summary = document.createElement("summary"), pre = document.createElement("pre");
    summary.textContent = t("technicalDetails"); pre.textContent = JSON.stringify({ id: env.id, runtime_verdict: runtime, behavior_verdict: behavior.verdict, verification_passed: finalPass, failure_stage: env.failure_stage, reason: env.reason, behavior_reason: behavior.reason }, null, 2);
    details.append(summary, pre); row.append(head, details);
    const reason = element("p", t(`reason_${runtime}`));
    const original = element("p", `${t("originalReason")}: ${env.reason || "-"}`, "recorded-reason");
    row.append(reason, original);
    if (!finalPass) {
      const fixKey = runtime === "PASS" ? "BEHAVIOR" : runtime;
      row.append(element("p", `${t("nextSteps")}: ${t(`fix_${fixKey}`)}`, "diagnostic"));
    }
    if ((behavior.checks || []).length) {
      const checks = document.createElement("div"); checks.className = "behavior-results";
      for (const check of behavior.checks) {
        const item = document.createElement("div"); item.className = "behavior-result";
        const evidence = check.evidence || {}, duration = evidence.duration_seconds;
        const evidenceDetails = document.createElement("details"), evidenceSummary = document.createElement("summary"), evidencePre = document.createElement("pre");
        evidenceSummary.textContent = t("structuredEvidence"); evidencePre.textContent = JSON.stringify(evidence, null, 2); evidenceDetails.append(evidenceSummary, evidencePre);
        item.append(resultCell(t("checkId"), check.id || ""), resultCell(t("checkType"), checkTypeText(check.type) || ""),
          resultCell(t("behaviorVerdict"), verdictText(check.status), check.status),
          resultCell(t("duration"), typeof duration === "number" ? `${duration.toFixed(3)} s` : "-"),
          resultCell(t("behaviorReason"), check.reason || "-"), evidenceDetails);
        checks.appendChild(item);
      }
      const health = document.createElement("details"), healthSummary = document.createElement("summary"), healthPre = document.createElement("pre");
      healthSummary.textContent = t("behaviorPostHealth"); healthPre.textContent = JSON.stringify(behavior.post_health || {}, null, 2); health.append(healthSummary, healthPre); checks.appendChild(health);
      row.appendChild(checks);
    }
    container.appendChild(row);
  }
  byId("result").replaceChildren(container);
}
function renderArtifacts(job) {
  if (!job.artifacts || !job.artifacts.length) { byId("artifacts").replaceChildren(); return; }
  const list = document.createElement("div"); list.className = "artifact-list";
  for (const artifact of job.artifacts) {
    const link = document.createElement("a"); link.href = artifact.url; link.target = "_blank"; link.rel = "noopener";
    link.textContent = `${artifactLabel(artifact.label)} (${Math.ceil(artifact.size / 1024)} KiB)`; list.appendChild(link);
  }
  byId("artifacts").replaceChildren(list);
}
function renderJob(job, rebuild = false) {
  lastJob = job;
  if (rebuild) { byId("progress").replaceChildren(); eventHistory.forEach(renderEvent); }
  else for (const event of job.events || []) { eventHistory.push(event); renderEvent(event); }
  setStatus(t("taskStatus", { status: jobStatus(job), id: job.id.slice(0, 8) }), job.status === "failed");
  const active = ["queued", "running", "cancelling"].includes(job.status);
  byId("run").disabled = active;
  const cancel = byId("cancel"); cancel.classList.toggle("hidden", !active); cancel.disabled = job.status === "cancelling";
  cancel.textContent = t(job.status === "cancelling" ? "cancelling" : "cancelTask");
  byId("rerun").classList.toggle("hidden", active || !job.summary);
  byId("retry-failed").classList.toggle("hidden", active || !job.summary?.environments?.some(e => e.verification_passed === false));
  renderResults(job); renderArtifacts(job);
}
async function poll() {
  if (!activeJob) return;
  try {
    const job = await api(`/api/jobs/${activeJob}?after=${eventCursor}`); eventCursor = job.next_event; renderJob(job);
    if (["queued", "running", "cancelling"].includes(job.status)) pollTimer = setTimeout(poll, 500); else { activeJob = null; loadHistory(); }
  } catch (error) { setStatus(t("errorPrefix", { message: error.message }), true); pollTimer = setTimeout(poll, 1500); }
}

byId("language").addEventListener("change", () => {
  language = byId("language").value;
  try { localStorage.setItem("pluginmatrix-language", language); } catch (_) { /* Keep the in-memory choice. */ }
  applyLanguage();
  updateProfile(); renderAnalysis(); renderRecommendation(); renderHistory(); renderReview(); refreshSourceName();
  document.querySelectorAll(".environment").forEach((card) => {
    setManualJava(card, card.dataset.manualJava === "true"); updateJavaHint(card); loadProviderVersions(card, false);
  });
  if (lastJob) renderJob(lastJob, true); else setStatus(t("noTask"));
});
byId("add-environment").addEventListener("click", () => addEnvironment());
byId("behavior-enabled").addEventListener("change", () => setBehaviorEnabled(byId("behavior-enabled").checked));
byId("add-behavior-check").addEventListener("click", () => addBehaviorCheck());
document.querySelectorAll('input[name="mode"]').forEach((input) => input.addEventListener("change", renumber));
async function startRun() {
  if (runSubmitting || activeJob) return;
  runSubmitting = true; byId("run").disabled = true;
  try {
    if (!byId("trust-inputs").checked) throw new Error(t("trustRequired"));
    if (configDirty) await applyJson();
    clearTimeout(pollTimer); const payload = await collect(); const job = await api("/api/jobs", { method: "POST", body: payload });
    applyConfiguration(job.configuration);
    activeJob = job.id; eventCursor = job.next_event; eventHistory = []; lastJob = null;
    byId("progress").replaceChildren(); byId("result").replaceChildren(); byId("artifacts").replaceChildren(); renderJob(job); poll();
  } catch (error) { setStatus(t("errorPrefix", { message: error.message }), true); }
  finally { runSubmitting = false; byId("run").disabled = Boolean(activeJob); }
}
byId("run").addEventListener("click", startRun);
byId("rerun").addEventListener("click", () => busy(byId("rerun"), async () => { await restoreRun(lastJob.id, false); }));
byId("retry-failed").addEventListener("click", () => busy(byId("retry-failed"), async () => { await restoreRun(lastJob.id, true); }));
byId("cancel").addEventListener("click", async () => {
  if (!activeJob) return;
  try {
    const job = await api(`/api/jobs/${activeJob}/cancel`, { method: "POST", body: {} });
    eventCursor = job.next_event; eventHistory = job.events || [];
    renderJob({ ...job, events: [] }, true);
  }
  catch (error) { setStatus(t("errorPrefix", { message: error.message }), true); }
});
byId("generate").addEventListener("click", async () => {
  try {
    const data = await api("/api/config/generate", { method: "POST", body: await collect() });
    setConfigurationText(data.configuration); byId("config-editor").open = true; setStatus(t("configGenerated"));
  } catch (error) { setStatus(t("errorPrefix", { message: error.message }), true); }
});
byId("import-config").addEventListener("click", async () => {
  try {
    const data = await api("/api/config/import", { method: "POST", body: { path: byId("config-path").value.trim() } });
    currentSource = data.source; applyConfiguration(data.configuration); setStatus(t("configImported", { source: data.source }));
  } catch (error) { setStatus(t("errorPrefix", { message: error.message }), true); }
});
byId("download-config").addEventListener("click", () => busy(byId("download-config"), async () => {
  if (configDirty) await applyJson();
  const data = await api("/api/config/normalize", { method: "POST", body: await collect() });
  setConfigurationText(data.configuration);
  const link = document.createElement("a"); link.href = URL.createObjectURL(new Blob([byId("configuration").value + "\n"], { type: "application/json" }));
  link.download = "pluginmatrix-matrix.json"; link.click(); setTimeout(() => URL.revokeObjectURL(link.href), 1000);
}));

function renderAnalysis() {
  const host = byId("analysis-result"); host.replaceChildren(); if (!analysisResult) return;
  const data = analysisResult;
  host.append(element("h3", t(data.valid ? "analysisReady" : "analysisBlocked"), data.valid ? "success" : "error"));
  if (data.plugin) {
    const metadata = data.plugin;
    host.append(element("p", `${metadata.plugin_name} ${metadata.plugin_version || metadata.version || ""}`));
    host.append(detailsFor(t("technicalDetails"), metadata));
  }
  const issues = [...(data.errors || []), ...(data.dependency_report?.errors || []), ...(data.dependency_report?.warnings || [])];
  for (const issue of issues) {
    const key = `diag_${issue.code}`;
    host.append(element("p", messages.en[key] ? t(key, issue) : (issue.reason || JSON.stringify(issue)), "diagnostic"));
    host.append(detailsFor(t("originalReason"), issue));
  }
  if (!data.valid) byId("dependency-editor").open = true;
  host.append(detailsFor(t("dependenciesTitle"), data.dependency_report));
  if (data.suggestions) {
    host.append(detailsFor(t("suggestionsTitle"), data.suggestions));
    if (data.suggestions.omitted?.length) host.append(detailsFor(t("omissions"), data.suggestions.omitted));
  }
  host.append(element("p", t("staticScope"), "hint"));
}
async function analyzeInputs() {
  analysisResult = await api("/api/guided/analyze", { method: "POST", body: await collectInputs() }); renderAnalysis();
  if (!analysisResult.valid) { setStep(0); throw new Error(t("analysisBlocked")); }
  if (!byId("project-name").value) byId("project-name").value = analysisResult.plugin?.plugin_name || "";
  setStatus(t("analysisReady")); return analysisResult;
}
function renderRecommendation() {
  const host = byId("recommendation-result"); host.replaceChildren(); if (!recommendationResult) return;
  const data = recommendationResult.recommendation;
  host.append(element("h3", t(data.ready ? "recommendationReady" : "recommendationBlocked"), data.ready ? "success" : "warning"));
  host.append(element("p", [data.selection.provider, data.selection.minecraft, data.selection.build, data.java_major ? `JDK ${data.java_major}` : null].filter(Boolean).join(" / ")));
  for (const issue of [...data.conflicts, ...data.unresolved]) host.append(element("p", issue, "diagnostic"));
  host.append(detailsFor(t("source"), data.reasons), element("p", t("recommendationScope"), "hint"));
  byId("apply-recommendation").disabled = !data.ready;
}
async function prepareReview() {
  await analyzeInputs();
  const payload = (await collect()).configuration;
  if (!payload.profile) {
    const normalized = await api("/api/config/normalize", { method: "POST", body: { configuration: payload } });
    applyConfiguration(normalized.configuration);
  } else {
    const data = await api("/api/guided/prepare", { method: "POST", body: {
      ...await collectInputs(), environments: payload.environments, profile: payload.profile,
      options: payload.options, ...(payload.behavior ? { behavior: payload.behavior } : {}),
      use_suggestions: !behaviorReviewed
    } });
    applyConfiguration(data.configuration);
  }
  setStep(2); setStatus(t("reviewRequired"));
}
async function applyJson() {
  const payload = { configuration: byId("configuration").value };
  if (currentSource) payload.source = currentSource;
  const data = await api("/api/config/normalize", { method: "POST", body: payload });
  applyConfiguration(data.configuration); setStatus(t("configGenerated")); return data;
}
async function restoreRun(id, failedOnly) {
  const data = await api(`/api/jobs/${id}/restore`, { method: "POST", body: { failed_only: failedOnly } });
  applyConfiguration(data.configuration); setView("verify"); setStep(2); byId("trust-inputs").checked = false;
  if (data.changed_sources.length) setStatus(t("changedInputs", { paths: data.changed_sources.join(", ") }), true);
  else setStatus(t("reviewRequired"));
}
function renderHistory() {
  const query = byId("history-filter").value.toLowerCase();
  const projects = byId("projects-list"), history = byId("history-list"); projects.replaceChildren(); history.replaceChildren();
  for (const project of projectsData.filter(p => JSON.stringify(p).toLowerCase().includes(query))) {
    const row = element("article", undefined, "history-row");
    row.append(element("strong", project.name), element("time", new Date(project.updated_at * 1000).toLocaleString(language)));
    row.append(actionButton(t("openProject"), async () => {
      projectId = project.id; byId("project-name").value = project.name; applyConfiguration(project.configuration);
      setView("verify"); setStep(2); byId("trust-inputs").checked = false;
    }));
    row.append(detailsFor(t("sourceHash"), { configuration_sha256: project.configuration_sha256, sources: project.sources }));
    projects.append(row);
  }
  if (!projects.childElementCount) projects.append(element("p", t("emptyProjects"), "hint"));
  for (const job of historyData.filter(j => j.mode !== "maintenance" && JSON.stringify(j).toLowerCase().includes(query))) {
    const row = element("article", undefined, "history-row");
    row.append(element("strong", `${job.sources?.[0]?.name || job.configuration?.plugin?.split(/[\\/]/).pop() || job.id.slice(0, 8)} · ${jobStatus(job)}`),
      element("time", new Date(job.created_at * 1000).toLocaleString(language)));
    row.append(actionButton(t("viewResult"), async () => {
      const data = await api(`/api/jobs/${job.id}`); eventHistory = []; renderJob(data, true);
      if (!activeJob && ["queued", "running", "cancelling"].includes(data.status)) { activeJob = data.id; eventCursor = 0; poll(); }
      document.querySelector(".results").scrollIntoView({ behavior: "smooth" });
    }));
    if (!["queued", "running", "cancelling"].includes(job.status)) row.append(actionButton(t("restoreRun"), () => restoreRun(job.id, false)));
    row.append(detailsFor(t("technicalDetails"), { configuration_sha256: job.configuration_sha256, sources: job.sources,
      environments: job.summary?.environments?.map(e => ({ provider: e.provider, version: e.minecraft_version, runtime: e.runtime_verdict, behavior: e.behavior?.verdict, verification_passed: e.verification_passed })) }));
    history.append(row);
  }
  if (!history.childElementCount) history.append(element("p", t("emptyHistory"), "hint"));
}
async function loadHistory() {
  try {
    const [jobs, projects] = await Promise.all([api("/api/jobs"), api("/api/projects")]);
    historyData = jobs.jobs; projectsData = projects.projects; renderHistory();
    if (projects.warnings?.length && currentView === "projects") setStatus(projects.warnings.join("\n"), true);
  } catch (error) { setStatus(error.message, true); }
}
function packageSummary(data) {
  const packageData = data.package || data;
  const row = element("div", undefined, "package-summary");
  row.append(element("h3", packageData.release || packageData.name || packageData.filename || packageData.id || data.id || ""),
    element("p", [packageData.os, packageData.architecture, packageData.major ? `JDK ${packageData.major}` : "",
      packageData.size ? `${(packageData.size / 1024 / 1024).toFixed(1)} MiB` : ""].filter(Boolean).join(" · ")),
    element("p", `SHA-256: ${packageData.sha256 || data.sha256 || "-"}`, "hash"),
    detailsFor(t("source"), data));
  return row;
}
async function runCache(action, payload) {
  if (cacheJob) throw new Error(t("pendingOperation"));
  byId("cache-status").textContent = t("pendingOperation");
  const job = await api(`/api/cache/${action}`, { method: "POST", body: payload });
  cacheJob = job.id; byId("cancel-cache").classList.remove("hidden"); byId("cancel-cache").disabled = false;
  try {
    let current = job;
    while (["queued", "running", "cancelling"].includes(current.status)) {
      await new Promise(resolve => setTimeout(resolve, 600));
      current = await api(`/api/jobs/${job.id}`);
      const event = current.events?.at(-1);
      byId("cache-status").textContent = event ? t(`event_${event.kind}`) : t("pendingOperation");
    }
    if (current.status !== "completed") throw new Error(current.error || jobStatus(current));
    byId("cache-status").textContent = t("operationComplete");
    return current.operation_result;
  } catch (error) { byId("cache-status").textContent = error.message; throw error; }
  finally { cacheJob = null; byId("cancel-cache").classList.add("hidden"); }
}
async function refreshCache() {
  try {
    const data = await api("/api/cache");
    if (!byId("jdk-directory").value && configurationBase.schema === 2) byId("jdk-directory").value = data.jdk_directory;
    if (!byId("cache-jdk-directory").value) byId("cache-jdk-directory").value = byId("jdk-directory").value || data.jdk_directory;
    const directory = byId("cache-jdk-directory").value.trim();
    const jdks = directory === data.jdk_directory ? data.jdks : await api("/api/cache/jdks", { method: "POST", body: { directory } });
    const list = byId("jdk-list"); list.replaceChildren();
    for (const item of jdks.jdks || []) {
      const row = element("article", undefined, "cache-entry");
      row.append(packageSummary(item), element("p", t("managedIntegrity", { state: item.integrity })));
      if (item.error) row.append(element("p", item.error, "error"));
      row.append(actionButton(t("verifyIntegrity"), async () => {
        const result = await runCache("jdk-verify", { id: item.id, directory });
        row.append(element("p", t("managedIntegrity", { state: result.integrity }), "success"));
      }));
      row.append(actionButton(t("deleteCache"), async () => {
        if (!confirm(t("confirmDelete", { name: item.id }))) return;
        await runCache("jdk-remove", { id: item.id, directory }); await refreshCache();
      }, "danger"));
      list.append(row);
    }
    if (!list.childElementCount) list.append(element("p", t("emptyCache"), "hint"));
    for (const warning of jdks.warnings || []) list.append(element("p", warning, "warning"));
    if (jdks.staging?.length) list.append(detailsFor(t("incompleteDownloads"), jdks.staging));
    list.append(element("p", t("jdkStorageScope"), "hint"));
    // Preserve the opaque managed ID and its matching store; never substitute its executable.
    if (directory === byId("jdk-directory").value.trim()) {
      javaCatalog.runtimes = [...javaCatalog.runtimes.filter(r => r.source !== "managed"), ...(jdks.jdks || []).filter(j => j.integrity !== "invalid").map(j => ({ ...j, path: `managed:${j.id}`, version: String(j.major) }))];
      document.querySelectorAll(".environment").forEach(card => {
        const value = card.dataset.manualJava === "true" ? card.querySelector(".java").value : card.querySelector(".java-select").value;
        populateJava(card, value);
      });
    }
    const servers = byId("server-cache-list"); servers.replaceChildren();
    for (const item of data.servers.entries) {
      const row = element("article", undefined, "cache-entry"); row.append(packageSummary(item));
      row.append(actionButton(t("verifyIntegrity"), async () => {
        const verified = await runCache("server-verify", { id: item.id });
        row.append(element("p", t("managedIntegrity", { state: verified.integrity }), "success"));
      }));
      row.append(actionButton(t("deleteCache"), async () => {
        if (!confirm(t("confirmDelete", { name: item.name }))) return;
        await runCache("server-remove", { id: item.id }); await refreshCache();
      }, "danger")); servers.append(row);
    }
    if (!servers.childElementCount) servers.append(element("p", t("emptyCache"), "hint"));
    for (const warning of data.servers.warnings || []) servers.append(element("p", warning, "warning"));
  } catch (error) { byId("cache-status").textContent = error.message; }
}
function setTheme() {
  const choice = byId("theme").value;
  document.documentElement.dataset.theme = choice === "system" ? (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light") : choice;
  try { localStorage.setItem("pluginmatrix-theme", choice); } catch (_) { /* Optional persistence. */ }
}
byId("theme").addEventListener("change", setTheme);
byId("plugin-file").addEventListener("change", () => {
  byId("plugin-path").value = ""; analysisResult = null; recommendationResult = null;
  behaviorReviewed = false; projectId = null; refreshSourceName(); renderAnalysis(); renderRecommendation();
});
byId("plugin-path").addEventListener("input", () => { byId("plugin-file").value = ""; refreshSourceName(); });
matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => { if (byId("theme").value === "system") setTheme(); });
document.querySelectorAll("[data-view]").forEach(button => button.addEventListener("click", () => setView(button.dataset.view)));
document.querySelectorAll("[data-step]").forEach(button => button.addEventListener("click", () => setStep(Number(button.dataset.step))));
document.querySelectorAll('[name="experience"]').forEach(input => input.addEventListener("change", () => setStep(wizardStep)));
byId("profile").addEventListener("change", () => {
  const profile = profileCatalog.find(p => p.id === byId("profile").value);
  configurationBase.schema = 2;
  configurationBase.profile = profile ? { id: profile.id, revision: profile.revision } : undefined;
  if (profile) {
    byId("timeout").value = profile.timeout; byId("stability").value = profile.stability_window;
    document.querySelector(`input[name="mode"][value="${profile.id === "matrix" || profile.id === "strict" ? "matrix" : "single"}"]`).checked = true;
    if (profile.id === "matrix" && document.querySelectorAll(".environment").length === 1) addEnvironment();
    renumber();
  }
  updateProfile();
});
byId("analyze").addEventListener("click", () => busy(byId("analyze"), analyzeInputs));
byId("input-next").addEventListener("click", () => busy(byId("input-next"), async () => { await analyzeInputs(); setStep(1); }));
byId("environment-next").addEventListener("click", () => busy(byId("environment-next"), prepareReview));
byId("open-jdks").addEventListener("click", () => setView("cache"));
byId("recommend").addEventListener("click", () => busy(byId("recommend"), async () => {
  const card = document.querySelector(".environment"), selectedBuild = card.querySelector(".build").value.trim();
  const payload = { ...await collectInputs(), minecraft: card.querySelector(".minecraft").value.trim(),
    provider: card.querySelector(".provider").value, ...(byId("jdk-directory").value ? { jdk_dir: byId("jdk-directory").value } : {}),
    ...(/^\d+$/.test(selectedBuild) ? { build: Number(selectedBuild) } : {}) };
  const fingerprintBefore = fingerprint();
  recommendationResult = await api("/api/guided/recommend", { method: "POST", body: payload });
  recommendationFingerprint = fingerprintBefore;
  analysisResult = recommendationResult.analysis; renderAnalysis(); renderRecommendation();
}));
byId("apply-recommendation").addEventListener("click", () => busy(byId("apply-recommendation"), async () => {
  if (!recommendationResult?.recommendation.ready) throw new Error(t("noRecommendation"));
  if (fingerprint() !== recommendationFingerprint) throw new Error(t("staleRecommendation"));
  const choice = recommendationResult.recommendation.selection, card = document.querySelector(".environment");
  card.querySelector(".build").value = choice.build;
  if (choice.jdk_dir) byId("jdk-directory").value = choice.jdk_dir;
  populateJava(card, choice.java);
  setStatus(t("reviewRequired"));
}));
byId("behavior-editor").addEventListener("input", () => { behaviorReviewed = true; });
byId("behavior-enabled").addEventListener("change", () => { behaviorReviewed = true; });
byId("configuration").addEventListener("input", () => { configDirty = true; setStatus(t("configEdited")); });
byId("apply-json").addEventListener("click", () => busy(byId("apply-json"), applyJson));
byId("config-file").addEventListener("change", () => busy(byId("apply-json"), async () => {
  const file = byId("config-file").files[0]; if (!file) return;
  if (file.size > 1024 * 1024) throw new Error("JSON exceeds 1 MiB");
  byId("configuration").value = await file.text(); configDirty = true; currentSource = byId("config-path").value.trim() || null;
  await applyJson();
}));
byId("save-project").addEventListener("click", () => busy(byId("save-project"), async () => {
  if (configDirty) await applyJson();
  const normalized = await api("/api/config/normalize", { method: "POST", body: await collect() });
  const project = await api("/api/projects", { method: "POST", body: {
    name: byId("project-name").value, configuration: normalized.configuration, ...(projectId ? { id: projectId } : {})
  } });
  projectId = project.id; applyConfiguration(project.configuration); setStatus(t("projectSaved")); await loadHistory();
}));
byId("history-filter").addEventListener("input", renderHistory);
byId("refresh-history").addEventListener("click", loadHistory);
byId("refresh-cache").addEventListener("click", refreshCache);
byId("preview-jdk").addEventListener("click", () => busy(byId("preview-jdk"), async () => {
  jdkPreview = null; byId("install-jdk").disabled = true;
  const major = Number(byId("jdk-major").value);
  const result = await runCache("jdk-preview", { major });
  if (Number(byId("jdk-major").value) !== major) return;
  jdkPreview = result.package; byId("jdk-preview").replaceChildren(packageSummary(jdkPreview)); byId("install-jdk").disabled = false;
}));
byId("jdk-major").addEventListener("change", () => { jdkPreview = null; byId("install-jdk").disabled = true; byId("jdk-preview").replaceChildren(); });
byId("install-jdk").addEventListener("click", () => busy(byId("install-jdk"), async () => {
  if (!jdkPreview) throw new Error(t("noRecommendation"));
  const directory = byId("cache-jdk-directory").value.trim();
  await runCache("jdk-install", { major: jdkPreview.major, id: jdkPreview.id, directory });
  if (!byId("jdk-directory").value) byId("jdk-directory").value = directory;
  await refreshCache();
}));
byId("cancel-cache").addEventListener("click", () => busy(byId("cancel-cache"), async () => {
  if (cacheJob) await api(`/api/jobs/${cacheJob}/cancel`, { method: "POST", body: {} });
}));
byId("download-server").addEventListener("click", () => busy(byId("download-server"), async () => {
  await runCache("server-download", { server: { type: byId("cache-provider").value, version: byId("cache-version").value.trim(), build: Number(byId("cache-build").value) } });
  await refreshCache();
}));
async function initialize() {
  try { byId("theme").value = localStorage.getItem("pluginmatrix-theme") || "system"; } catch (_) { /* Optional persistence. */ }
  setTheme(); applyLanguage(); addEnvironment(); setBehaviorEnabled(false); setStep(0); updateProfile();
  document.querySelectorAll("input, select, textarea").forEach((input) => { if (!input.name) input.name = input.id || input.className; });
  const data = await api("/api/profiles"); profileCatalog = data.profiles;
  const profile = profileCatalog.find(p => p.id === "standard");
  if (profile) { byId("timeout").value = profile.timeout; byId("stability").value = profile.stability_window; }
  await loadProviders(); await loadJava(); await refreshCache(); await loadHistory();
  const active = historyData.find(j => j.mode !== "maintenance" && ["queued", "running", "cancelling"].includes(j.status));
  if (active) { activeJob = active.id; eventCursor = 0; poll(); }
}
initialize().catch(error => setStatus(error.message, true));
