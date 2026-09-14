# PluginMatrix

PluginMatrix is an early-stage command-line verifier for Minecraft plugin JARs. It prepares an isolated server/Java environment, starts a real server, observes plugin discovery and lifecycle evidence, and writes an authoritative JSON report alongside the original `server.log` and optional static HTML.

Version **0.6.0** adds Paper, Purpur, Folia and user-supplied local server Providers. One Runtime Verifier serves all Providers. Matrix defaults to serial execution and optionally runs 1–8 environments concurrently. There is no GUI, cloud service, automatic JDK management, gameplay bot or complete feature testing.

The public stable release is **0.6.0**, available from [PyPI](https://pypi.org/project/pluginmatrix/0.6.0/) and the immutable [GitHub Release](https://github.com/YouDaoRS/PluginMatrix/releases/tag/v0.6.0). GitHub remains the source, release-asset and checksum channel. See [release status](docs/STATUS.md), [publishing policy](docs/PUBLISHING.md), [architecture](docs/ARCHITECTURE.md), and the [v0.5.1 validation record](docs/V0.5.1_PREPARATION.md).

## What `PASS` means

`PASS` means that, for the exact server JAR/build and Java runtime recorded in the report:

1. The selected server reached its ready state.
2. The runtime probe found the target through `PluginManager`.
3. `Plugin#isEnabled()` was `true`.
4. The server and plugin remained running during the configured stability window.

The window starts with a valid enabled probe sample after ready. Samples must match the run, name, version, main class and isolated source, advance in sequence/time with no gap over two seconds, and include a new sample at the end. Zero stability is rejected. A stale/malformed probe, incomplete window or cleanup failure cannot produce PASS.

The verifier supports simple `plugin.yml` and standalone `paper-plugin.yml` descriptors. Duplicate/ambiguous keys, unsupported YAML, missing version and dual descriptors are rejected explicitly. Complex Paper bootstrapper/loader/nested dependency descriptors remain unsupported. Plugin names and `provides` aliases must not collide with each other or the probe. Remapped sources are accepted only at the expected isolated `.paper-remapped/<target filename>` path when allowed by the Provider.

Folia requires the unquoted boolean `folia-supported: true`; its absence returns `PLUGIN_UNSUPPORTED` before download/startup. The Folia probe runs on the global region scheduler and withholds startup samples until that scheduler has produced a continuous fresh two-second span. Cold-world initialization remains inside the configured startup deadline; the full stability window begins only with the first published sample. **Folia PASS does not prove thread safety, cross-region safety or complete gameplay compatibility.**

These checks are for compatibility of plugins you trust to execute. A run directory and a probe in the same JVM are not a security sandbox against intentionally malicious plugin code or processes that deliberately leave the POSIX process group.

It does **not** prove that commands, events, GUIs, databases, dependencies, performance, player behavior, or other Paper/Java versions work correctly.

## Requirements and installation

- Python 3.10 or newer.
- A full JDK containing both `java` and `javac`; Java 17 is required for the included Paper 1.20.1 example.
- Network access to the selected official Provider API/download host (not needed for local JAR resolution).
- Network access required by Paper bootstrap on its first run, including Mojang runtime artifacts.
- A Paper plugin JAR you are allowed to use. Dependencies must be supplied as local JARs explicitly.

For CLI use, install into an isolated environment with [pipx](https://pipx.pypa.io/):

```console
pipx install pluginmatrix
pluginmatrix --version
pluginmatrix providers
```

Upgrade to a later published version with `pipx upgrade pluginmatrix`. PyPI versions are immutable; an existing version is never overwritten.

For development from a clean checkout:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install .
.\.venv\Scripts\pluginmatrix --version
```

On Linux or macOS, replace `.venv\Scripts\python` with `.venv/bin/python` and `.venv\Scripts\pluginmatrix` with `.venv/bin/pluginmatrix`.

## Minimal single-environment verification

The repository includes `ci-fixtures/PluginMatrixSmoke.jar`, a minimal fixture that can be rebuilt from the adjacent Java source. Its source, descriptor, deterministic build script, purpose, and checksum are recorded under `ci-fixtures/`; the project owner confirmed its Apache-2.0 release rights for v0.5.0. It is not a production plugin.

```powershell
python -m pluginmatrix test `
  --plugin .\ci-fixtures\PluginMatrixSmoke.jar `
  --paper 1.20.1 `
  --paper-build 196 `
  --java 17
```

The first run downloads Paper into `.pluginmatrix/cache`. Each verification gets a unique `.pluginmatrix/runs/run-<timestamp>-<id>` directory. By default its structured runtime report is `result.json` in that directory; `server.log` is beside it. Use `--report path.json` to choose a runtime report path.

Useful options:

```text
--dependency path.jar       Add a locally supplied dependency plugin; repeatable
--timeout 120               Server startup and initial-probe timeout in seconds
--stability-window 5        Positive observation time after ready and the first valid enabled sample
--work-dir path             Root for isolated run directories
--cache-dir path            Paper download and bootstrap cache
--report path.json          Runtime JSON report path
```

The single-environment command exits `0` only for `PASS`; other verifier verdicts exit `1`, invalid CLI configuration exits `2`, and report-save failures exit `3`. Reports must be outside work/cache roots and must not alias input files. Matrix per-environment reports remain under their isolated run directories.

## Compatibility Matrix

Generate and validate a mixed Matrix without writing JSON by hand:

```powershell
python -m pluginmatrix init mixed.json --plugin path/to/plugin.jar --server paper --server purpur --server folia --minecraft 1.21.4 --java 21
python -m pluginmatrix validate mixed.json --json
python -m pluginmatrix validate mixed.json --network --json
python -m pluginmatrix doctor --java 21 --json
python -m pluginmatrix providers --json
python -m pluginmatrix matrix mixed.json --max-parallel 3
```

`init` prompts only in an interactive terminal and only for missing arguments. Existing configs are preserved unless `--force` is supplied; input JAR aliases remain protected even with force. `validate` performs configuration/plugin/dependency/Provider/Java/path preflight without downloading or launching servers. `--network` resolves version/build metadata only. `doctor` checks Python, Java/JDK, disk, directory permissions and Provider APIs; `--offline` omits network checks. Required failures exit 2; warnings do not. Neither command installs Java.

New environments use `{"server":{"type":"purpur","version":"1.21.4","build":"latest"},"java":21}`. Omit `build` for automatic selection or set a positive integer. `heap_mb` limits each JVM (default 1024). Paper/Folia latest prefers stable builds, otherwise the latest published channel, which is recorded explicitly. A fixed build always requests that exact channel/build. Purpur resolves `latest` to a fixed number before download, checks the official MD5 and additionally records and pins SHA-256 in its own cache namespace. It does not claim an official SHA-256 when the API provides only MD5.

Local JAR usage requires an explicit supported runtime contract:

```powershell
python -m pluginmatrix test --plugin path/to/plugin.jar --server local --server-jar path/to/server.jar --server-name "My server" --minecraft 1.21.4 --runtime paperclip --java 21 --report local.json --html local.html
```

`local` (alias `custom`) accepts `runtime` values `paperclip`, `bukkit` or `folia`. These describe known startup/log/probe/CodeSource contracts, not official identities. `paperclip`/`folia` require embedded API libraries; `bukkit` requires the API classes in the server JAR. Unsupported layouts or unrecognized readiness/probe behavior fail closed. The original JAR is hashed, copied and rechecked in an isolated directory; it is never modified or downloaded. User-declared name/version/metadata stay distinct from official Provider information. No BuildTools is run.

The original `--paper`, `--paper-build` and JSON `paper`/`paper_build` fields remain supported with their Paper report fields. Combining legacy fields with `server` produces an explicit migration error. Unknown fields are now rejected instead of silently ignored. Separate output roots and positive stability windows remain mandatory. The bounded heap and noninteractive console flags are recorded in each launch command.

Run the repository-provided one-environment example, or copy its configuration and add environments:

```powershell
python -m pluginmatrix matrix .\examples\matrix.json
```

```json
{
  "plugin": "../ci-fixtures/PluginMatrixSmoke.jar",
  "environments": [
    { "paper": "1.20.1", "java": 17, "paper_build": 196 }
  ],
  "options": {
    "timeout": 120,
    "stability_window": 5,
    "work_dir": "../.pluginmatrix/runs",
    "cache_dir": "../.pluginmatrix/cache",
    "report": "../.pluginmatrix/matrix-report.json"
  }
}
```

Every relative path in a Matrix config is resolved from the directory containing that config, not from the shell's current directory. Before downloading Paper or starting a server, Matrix validates the plugin, Java/JDK, duplicate environments, and output paths.

Each environment keeps its own runtime `result.json`, `server.log`, and run directory. The unified Matrix Report defaults to `.pluginmatrix/matrix-report.json` relative to the config and references those artifacts without embedding the raw log. Matrix exits `0` when all environments pass, `1` after one or more environment failures, `2` for invalid configuration, and `3` for an internal PluginMatrix error.

Use `options.max_parallel` or `matrix --max-parallel` (default 1, maximum 8). Result order follows configuration order. Each environment has an independent port, probe run ID, log and directory. Cache publication uses OS file locks, checksums and atomic replacements. One environment failure does not cancel others. Ctrl+C requests cancellation, waits for all owned process trees to be cleaned up, and retains completed and cancelled results. `CANCELLED` exits 1; cleanup/report/internal errors take precedence as failures. Concurrent invocations targeting the same Matrix report are rejected while it is in use.

`options.dependencies` is not supported: supply local dependency JAR paths in the top-level `dependencies` array. All target/dependency/alias/probe conflicts are rejected before execution.

## Static HTML and Python application API

`init` enables `options.html_report` by default. Existing JSON-only configs remain JSON-only. Alternatively use `matrix --html matrix.html`, `test --html runtime.html`, or render existing evidence:

```powershell
python -m pluginmatrix report .pluginmatrix/matrix-report.json --html matrix.html
```

HTML reads the recorded JSON verdicts without recalculating them. It is a single offline file with escaped text, metadata/evidence details, relative artifact paths, PASS scope and Folia limitations. It does not embed raw logs or external scripts. Keep referenced artifacts with the report if you move it.

The stable application entry points are documented in [APPLICATION_API.md](docs/APPLICATION_API.md): `validate_configuration`, `inspect_providers`, `run_single`, `run_matrix`, `load_report`, `render_html_report`, and `RunControl.cancel()`. Structured progress callbacks are serialized, bounded and contain no configuration, paths or log contents. There is no background daemon or GUI.

## Common failures

- `Java ... did not resolve` or a major-version mismatch: install the requested JDK and correct `PATH`, or set `java` to its executable path. PluginMatrix does not install JDKs.
- `javac ... was not found`: install a full JDK rather than a JRE and ensure its `java` and `javac` are available together.
- Paper version or fixed build not found: correct `paper`/`paper_build`, or remove `paper_build` to select the latest stable build.
- Paper API, download, or bootstrap network failure: confirm network access and retry; inspect the runtime report and original `server.log` before blaming the plugin.
- `PLUGIN_LOAD_FAILED` or `PLUGIN_ENABLE_FAILED`: inspect `failure_stage`, `primary_evidence`, runtime `result.json`, and `server.log`; explicitly provide required local dependencies with `--dependency`.
- Matrix path not found: remember that config paths are relative to the JSON file.

Reports and logs can expose usernames, local paths, IP addresses, plugin configuration, and stack traces. Redact sensitive data before sharing them. Do not publish a third-party JAR without redistribution permission.

## GitHub Actions

`CI` runs on pushes and pull requests and performs package installation, `compileall`, and the offline test suite. It does not download Paper or start a Minecraft server.

`Compatibility Matrix` is a manual `workflow_dispatch` workflow for real Paper verification on a GitHub-hosted Java 17 runner. In the Actions tab, provide:

- `config`: a repository-relative JSON file such as `examples/ci-matrix.json`.
- `plugin_jar`: a repository-relative JAR such as `ci-fixtures/PluginMatrixSmoke.jar`.

The workflow does not build arbitrary plugins or download their dependencies. It runs the existing Matrix CLI, writes a Job Summary from the Matrix Report, and always attempts to upload `pluginmatrix-matrix-report` and `pluginmatrix-runtime-artifacts`.

A successful workflow means every environment returned `PASS`. An expected failure workflow, such as `examples/ci-enable-failure-matrix.json` with `ci-fixtures/PluginMatrixEnableFailure.jar`, exits nonzero but should still retain both artifacts. Setup failures before Matrix starts may have no report or server log; use the setup error in the job log.

The v0.4 code was hosted-validated at commit `c5fe4ef`: Matrix #3 passed EnhancedFly 2.2.0 on Paper 1.20.1/build 196/Java 17, while Matrix #4 produced the expected `PLUGIN_ENABLE_FAILED` for the repository-provided failure fixture. Both retained artifacts and had zero Action deprecation warnings. EnhancedFly's binary is no longer distributed here because the repository audit found no explicit redistribution license; the result remains historical evidence, not a public example.

## Offline development checks

```powershell
python -m unittest discover -s tests -v
python -m compileall pluginmatrix tests ci-fixtures/build_fixtures.py
```

Fixture source, build instructions, and checksums are documented in `ci-fixtures/README.md`. Packaging and clean-install checks are listed in `docs/RELEASE_CHECKLIST.md`.

See `CONTRIBUTING.md` before contributing, `SECURITY.md` for vulnerability reporting, `CHANGELOG.md` for version history, and `THIRD_PARTY_NOTICES.md` plus `docs/THIRD_PARTY_REVIEW.md` for source and licensing boundaries.

PluginMatrix is licensed under the Apache License 2.0. See `LICENSE`.
