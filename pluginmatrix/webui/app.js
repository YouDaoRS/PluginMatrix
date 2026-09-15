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

let language = null;
try { language = localStorage.getItem("pluginmatrix-language"); } catch (_) { /* Browser storage is optional. */ }
if (!messages[language]) language = navigator.language.toLowerCase().startsWith("zh") ? "zh-CN" : "en";
let activeJob = null, eventCursor = 0, pollTimer = null, lastJob = null, eventHistory = [];
let javaCatalog = { runtimes: [], recommended: null }, providerNames = { paper: "Paper", purpur: "Purpur", folia: "Folia", local: "Local server" };
const catalogRequests = new Map();
let cardSequence = 0;

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
    option.textContent = `Java ${runtime.version}${runtime.jdk ? " JDK" : " JRE"} - ${runtime.path}`;
    select.appendChild(option);
  }
  const match = javaCatalog.runtimes.find((runtime) => runtime.path === requested)
    || (/^\d+$/.test(requested) ? javaCatalog.runtimes.find((runtime) => runtime.jdk && runtime.major === Number(requested)) : null)
    || javaCatalog.runtimes.find((runtime) => runtime.path === javaCatalog.recommended);
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
  card.dataset.requestedJava = String(value.java || "21");
  card.querySelector(".provider").value = server.type || "paper";
  card.querySelector(".minecraft").value = server.version || value.paper || "1.21.4";
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
    card.querySelector(".build").value = "latest";
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
  if (!/^\d+\.\d+(?:\.\d+)?$/.test(version)) return null;
  const parts = version.split(".").map(Number), major = parts[0], minor = parts[1], patch = parts[2] || 0;
  if (major >= 26) return 25;
  if (major !== 1) return null;
  if (minor >= 21 || (minor === 20 && patch >= 5)) return 21;
  if (minor >= 17) return 17;
  if (minor === 16 && patch >= 5) return 16;
  if (minor >= 12) return 11;
  return 8;
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
    if ((providerChanged || !input.value.trim()) && data.versions.length) input.value = data.versions[0];
    else if (data.versions.length && !data.versions.includes(input.value.trim())) input.value = data.versions[0];
    status.textContent = catalogText(data, data.versions.length, "versions");
    status.classList.toggle("warning", data.source === "stale_cache" || !data.available);
    await loadBuilds(card, providerChanged);
  } catch (error) {
    status.textContent = `${t("catalogUnavailable")} ${error.message}`; status.classList.add("error");
  }
}
async function loadBuilds(card, resetBuild) {
  const provider = card.querySelector(".provider").value;
  const version = card.querySelector(".minecraft").value.trim();
  if (provider === "local" || !/^\d+\.\d+(?:\.\d+)?$/.test(version)) { updateJavaHint(card); return; }
  const input = card.querySelector(".build");
  if (resetBuild || !input.value.trim()) input.value = "latest";
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
  if (!required) { hint.textContent = t("javaDetected", { count: javaCatalog.runtimes.length }); return; }
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
  const response = await fetch("/api/import", { method: "POST", credentials: "same-origin", headers: {
    "Content-Type": "application/octet-stream", "X-PluginMatrix-Token": token,
    "X-PluginMatrix-Filename": encodeURIComponent(file.name), "X-PluginMatrix-File-Kind": kind
  }, body: file });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || t("fileImportFailed"));
  return { file_id: data.file_id };
}
async function fileReference(pathInput, fileInput, kind) {
  const path = pathInput.value.trim();
  if (path) return path;
  if (fileInput.files.length !== 1) throw new Error(t("selectJar", { kind: t(kind) }));
  setStatus(t("importing", { name: fileInput.files[0].name }));
  return upload(fileInput.files[0], kind);
}
async function collect() {
  const mode = document.querySelector('input[name="mode"]:checked').value;
  const plugin = await fileReference(byId("plugin-path"), byId("plugin-file"), "plugin");
  const dependencies = byId("dependency-paths").value.split(/\r?\n/).map((value) => value.trim()).filter(Boolean);
  for (const file of byId("dependency-files").files) { setStatus(t("importing", { name: file.name })); dependencies.push(await upload(file, "dependency")); }
  const environments = [];
  for (const card of document.querySelectorAll(".environment")) {
    const type = card.querySelector(".provider").value, buildText = card.querySelector(".build").value.trim();
    const server = { type, version: card.querySelector(".minecraft").value.trim(), heap_mb: Number(card.querySelector(".heap").value) };
    if (type === "local") {
      server.jar = await fileReference(card.querySelector(".server-path"), card.querySelector(".server-file"), "server");
      server.name = card.querySelector(".server-name").value.trim(); server.runtime = card.querySelector(".runtime").value;
    } else server.build = buildText === "" || buildText === "latest" ? "latest" : Number(buildText);
    const java = card.dataset.manualJava === "true" ? card.querySelector(".java").value.trim() : card.querySelector(".java-select").value;
    environments.push({ server, java });
  }
  const payload = { mode, plugin, dependencies, environments, options: {
    timeout: Number(byId("timeout").value), stability_window: Number(byId("stability").value), max_parallel: Number(byId("parallel").value)
  } };
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
  return payload;
}
function applyConfiguration(config) {
  byId("plugin-path").value = config.plugin || ""; byId("dependency-paths").value = (config.dependencies || []).join("\n");
  const options = config.options || {}; byId("timeout").value = options.timeout || 120; byId("stability").value = options.stability_window || 5;
  byId("parallel").value = options.max_parallel || 1; document.querySelector('input[name="mode"][value="matrix"]').checked = true;
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
  renderResults(job); renderArtifacts(job);
}
async function poll() {
  if (!activeJob) return;
  try {
    const job = await api(`/api/jobs/${activeJob}?after=${eventCursor}`); eventCursor = job.next_event; renderJob(job);
    if (["queued", "running", "cancelling"].includes(job.status)) pollTimer = setTimeout(poll, 500); else activeJob = null;
  } catch (error) { setStatus(t("errorPrefix", { message: error.message }), true); pollTimer = setTimeout(poll, 1500); }
}

byId("language").addEventListener("change", () => {
  language = byId("language").value;
  try { localStorage.setItem("pluginmatrix-language", language); } catch (_) { /* Keep the in-memory choice. */ }
  applyLanguage();
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
  try {
    clearTimeout(pollTimer); const payload = await collect(); const job = await api("/api/jobs", { method: "POST", body: payload });
    activeJob = job.id; eventCursor = job.next_event; eventHistory = []; lastJob = null;
    byId("progress").replaceChildren(); byId("result").replaceChildren(); byId("artifacts").replaceChildren(); renderJob(job); poll();
  } catch (error) { setStatus(t("errorPrefix", { message: error.message }), true); }
}
byId("run").addEventListener("click", startRun);
byId("rerun").addEventListener("click", startRun);
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
    byId("configuration").value = JSON.stringify(data.configuration, null, 2); setStatus(t("configGenerated"));
  } catch (error) { setStatus(t("errorPrefix", { message: error.message }), true); }
});
byId("import-config").addEventListener("click", async () => {
  try {
    const data = await api("/api/config/import", { method: "POST", body: { path: byId("config-path").value.trim() } });
    applyConfiguration(data.configuration); byId("configuration").value = JSON.stringify(data.configuration, null, 2); setStatus(t("configImported", { source: data.source }));
  } catch (error) { setStatus(t("errorPrefix", { message: error.message }), true); }
});
byId("download-config").addEventListener("click", () => {
  const text = byId("configuration").value;
  if (!text.trim()) { setStatus(t("generateFirst"), true); return; }
  try { JSON.parse(text); } catch (error) { setStatus(t("invalidJson", { error: error.message }), true); return; }
  const link = document.createElement("a"); link.href = URL.createObjectURL(new Blob([text + "\n"], { type: "application/json" }));
  link.download = "pluginmatrix-matrix.json"; link.click(); URL.revokeObjectURL(link.href);
});

applyLanguage(); addEnvironment(); setBehaviorEnabled(false); loadProviders(); loadJava();
