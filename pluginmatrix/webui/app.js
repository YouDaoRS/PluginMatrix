"use strict";
const token = document.querySelector('meta[name="pluginmatrix-token"]').content;
const byId = (id) => document.getElementById(id);
let activeJob = null,
  eventCursor = 0,
  pollTimer = null;
function api(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  if (options.body !== undefined && !(options.body instanceof Blob)) {
    headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(options.body);
  }
  if (options.method && options.method !== "GET")
    headers["X-PluginMatrix-Token"] = token;
  return fetch(path, { credentials: "same-origin", ...options, headers }).then(
    async (response) => {
      const data = await response
        .json()
        .catch(() => ({ error: `HTTP ${response.status}` }));
      if (!response.ok)
        throw new Error(data.error || `HTTP ${response.status}`);
      return data;
    },
  );
}
function setStatus(text, error = false) {
  byId("status").textContent = text;
  byId("status").classList.toggle("error", error);
}
function addEnvironment(value = {}) {
  const fragment = byId("environment-template").content.cloneNode(true);
  const card = fragment.querySelector(".environment");
  byId("environments").appendChild(fragment);
  const server = value.server || {};
  card.querySelector(".provider").value = server.type || "paper";
  card.querySelector(".minecraft").value =
    server.version || value.paper || "1.21.4";
  card.querySelector(".build").value =
    server.build ?? value.paper_build ?? "latest";
  card.querySelector(".java").value = String(value.java || "21");
  card.querySelector(".heap").value = server.heap_mb || 1024;
  card.querySelector(".server-path").value = server.jar || "";
  card.querySelector(".server-name").value = server.name || "";
  card.querySelector(".runtime").value = server.runtime || "paperclip";
  card
    .querySelector(".provider")
    .addEventListener("change", () => updateLocal(card));
  card.querySelector(".remove").addEventListener("click", () => {
    card.remove();
    renumber();
  });
  updateLocal(card);
  renumber();
}
function updateLocal(card) {
  const local = card.querySelector(".provider").value === "local";
  card.querySelector(".local-fields").classList.toggle("hidden", !local);
  card.querySelector(".build").disabled = local;
}
function renumber() {
  const cards = [...document.querySelectorAll(".environment")];
  cards.forEach(
    (card, index) =>
      (card.querySelector(".environment-number").textContent = String(
        index + 1,
      )),
  );
  const single =
    document.querySelector('input[name="mode"]:checked').value === "single";
  byId("add-environment").disabled = single;
  cards.forEach(
    (card, index) =>
      (card.querySelector(".remove").disabled =
        single || cards.length === 1 || (index === 0 && single)),
  );
  if (single) cards.slice(1).forEach((card) => card.remove());
}
async function upload(file, kind) {
  const response = await fetch("/api/import", {
    method: "POST",
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/octet-stream",
      "X-PluginMatrix-Token": token,
      "X-PluginMatrix-Filename": encodeURIComponent(file.name),
      "X-PluginMatrix-File-Kind": kind,
    },
    body: file,
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "File import failed");
  return { file_id: data.file_id };
}
async function fileReference(pathInput, fileInput, kind) {
  const path = pathInput.value.trim();
  if (path) return path;
  if (fileInput.files.length !== 1)
    throw new Error(`Select or enter the ${kind} JAR`);
  setStatus(`Importing ${fileInput.files[0].name} locally…`);
  return upload(fileInput.files[0], kind);
}
async function collect() {
  const mode = document.querySelector('input[name="mode"]:checked').value;
  const plugin = await fileReference(
    byId("plugin-path"),
    byId("plugin-file"),
    "plugin",
  );
  const dependencies = byId("dependency-paths")
    .value.split(/\r?\n/)
    .map((v) => v.trim())
    .filter(Boolean);
  for (const file of byId("dependency-files").files) {
    setStatus(`Importing ${file.name} locally…`);
    dependencies.push(await upload(file, "dependency"));
  }
  const environments = [];
  for (const card of document.querySelectorAll(".environment")) {
    const type = card.querySelector(".provider").value;
    const buildText = card.querySelector(".build").value.trim();
    const server = {
      type,
      version: card.querySelector(".minecraft").value.trim(),
      heap_mb: Number(card.querySelector(".heap").value),
    };
    if (type === "local") {
      server.jar = await fileReference(
        card.querySelector(".server-path"),
        card.querySelector(".server-file"),
        "server",
      );
      server.name = card.querySelector(".server-name").value.trim();
      server.runtime = card.querySelector(".runtime").value;
    } else
      server.build =
        buildText === "" || buildText === "latest"
          ? "latest"
          : Number(buildText);
    environments.push({
      server,
      java: card.querySelector(".java").value.trim(),
    });
  }
  return {
    mode,
    plugin,
    dependencies,
    environments,
    options: {
      timeout: Number(byId("timeout").value),
      stability_window: Number(byId("stability").value),
      max_parallel: Number(byId("parallel").value),
    },
  };
}
function applyConfiguration(config) {
  byId("plugin-path").value = config.plugin || "";
  byId("dependency-paths").value = (config.dependencies || []).join("\n");
  const options = config.options || {};
  byId("timeout").value = options.timeout || 120;
  byId("stability").value = options.stability_window || 5;
  byId("parallel").value = options.max_parallel || 1;
  document.querySelector('input[name="mode"][value="matrix"]').checked = true;
  byId("environments").replaceChildren();
  (config.environments || []).forEach(addEnvironment);
  if (!(config.environments || []).length) addEnvironment();
  renumber();
}
function renderJob(job) {
  setStatus(
    `${job.status.toUpperCase()} · task ${job.id.slice(0, 8)}${job.cancel_requested ? " · cancellation requested" : ""}`,
    job.status === "failed",
  );
  byId("cancel").disabled = !["queued", "running", "cancelling"].includes(
    job.status,
  );
  for (const event of job.events || []) {
    const line = document.createElement("div");
    line.className = "event";
    line.textContent = `#${event.sequence} ${event.kind}${event.environment_index !== null && event.environment_index !== undefined ? ` · environment ${event.environment_index + 1}` : ""}${Object.keys(event.data || {}).length ? ` · ${JSON.stringify(event.data)}` : ""}`;
    byId("progress").appendChild(line);
  }
  if (job.error) {
    const p = document.createElement("p");
    p.className = "error";
    p.textContent = job.error;
    byId("result").replaceChildren(p);
  }
  if (job.summary) {
    const container = document.createElement("div");
    for (const env of job.summary.environments || []) {
      const row = document.createElement("div");
      row.className = "verdict";
      const id = document.createElement("span");
      id.textContent = env.id || env.provider || "environment";
      const verdict = document.createElement("strong");
      verdict.dataset.state = env.verdict || "UNKNOWN_FAILURE";
      verdict.textContent = env.verdict || "UNKNOWN_FAILURE";
      const reason = document.createElement("span");
      reason.textContent =
        [env.failure_stage, env.reason].filter(Boolean).join(" · ") ||
        "Ready, enabled, and stable under the recorded scope.";
      row.append(id, verdict, reason);
      container.appendChild(row);
    }
    byId("result").replaceChildren(container);
  }
  if (job.artifacts && job.artifacts.length) {
    const list = document.createElement("div");
    list.className = "artifact-list";
    for (const artifact of job.artifacts) {
      const link = document.createElement("a");
      link.href = artifact.url;
      link.target = "_blank";
      link.rel = "noopener";
      link.textContent = `${artifact.label} (${Math.ceil(artifact.size / 1024)} KiB)`;
      list.appendChild(link);
    }
    byId("artifacts").replaceChildren(list);
  }
}
async function poll() {
  if (!activeJob) return;
  try {
    const job = await api(`/api/jobs/${activeJob}?after=${eventCursor}`);
    eventCursor = job.next_event;
    renderJob(job);
    if (["queued", "running", "cancelling"].includes(job.status))
      pollTimer = setTimeout(poll, 500);
    else activeJob = null;
  } catch (error) {
    setStatus(error.message, true);
    pollTimer = setTimeout(poll, 1500);
  }
}
byId("add-environment").addEventListener("click", () => addEnvironment());
document
  .querySelectorAll('input[name="mode"]')
  .forEach((input) => input.addEventListener("change", renumber));
byId("run").addEventListener("click", async () => {
  try {
    clearTimeout(pollTimer);
    const payload = await collect();
    const job = await api("/api/jobs", { method: "POST", body: payload });
    activeJob = job.id;
    eventCursor = job.next_event;
    byId("progress").replaceChildren();
    byId("result").replaceChildren();
    byId("artifacts").replaceChildren();
    renderJob(job);
    poll();
  } catch (error) {
    setStatus(error.message, true);
  }
});
byId("cancel").addEventListener("click", async () => {
  if (!activeJob) return;
  try {
    renderJob(
      await api(`/api/jobs/${activeJob}/cancel`, { method: "POST", body: {} }),
    );
  } catch (error) {
    setStatus(error.message, true);
  }
});
byId("generate").addEventListener("click", async () => {
  try {
    const payload = await collect();
    const data = await api("/api/config/generate", {
      method: "POST",
      body: payload,
    });
    byId("configuration").value = JSON.stringify(data.configuration, null, 2);
    setStatus(
      "Configuration generated. Imported browser files use session-temporary paths; enter durable local paths before saving a reusable config.",
    );
  } catch (error) {
    setStatus(error.message, true);
  }
});
byId("import-config").addEventListener("click", async () => {
  try {
    const data = await api("/api/config/import", {
      method: "POST",
      body: { path: byId("config-path").value.trim() },
    });
    applyConfiguration(data.configuration);
    byId("configuration").value = JSON.stringify(data.configuration, null, 2);
    setStatus(`Imported ${data.source}`);
  } catch (error) {
    setStatus(error.message, true);
  }
});
byId("download-config").addEventListener("click", () => {
  const text = byId("configuration").value;
  if (!text.trim()) {
    setStatus("Generate or import a configuration first.", true);
    return;
  }
  try {
    JSON.parse(text);
  } catch (error) {
    setStatus(`Configuration is not valid JSON: ${error.message}`, true);
    return;
  }
  const link = document.createElement("a");
  link.href = URL.createObjectURL(
    new Blob([text + "\n"], { type: "application/json" }),
  );
  link.download = "pluginmatrix-matrix.json";
  link.click();
  URL.revokeObjectURL(link.href);
});
addEnvironment();
