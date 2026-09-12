# PluginMatrix

PluginMatrix is an early-stage command-line verifier for Minecraft Paper plugin JARs. It prepares an isolated Paper/Java environment, starts a real Paper server, observes plugin discovery and lifecycle evidence, and writes a structured report alongside the original `server.log`.

It supports one environment with `test` and a sequential list of environments with `matrix`. It does not support Spigot, Folia, Fabric, Forge, Velocity, parallel Matrix execution, gameplay bots, or complete feature testing.

## What `PASS` means

`PASS` means that, for the exact Paper build and Java runtime recorded in the report:

1. Paper reached its ready state.
2. The runtime probe found the target through Paper's `PluginManager`.
3. `Plugin#isEnabled()` was `true`.
4. The server and plugin remained running during the configured stability window.

It does **not** prove that commands, events, GUIs, databases, dependencies, performance, player behavior, or other Paper/Java versions work correctly.

## Requirements and installation

- Python 3.10 or newer.
- A full JDK containing both `java` and `javac`; Java 17 is required for the included Paper 1.20.1 example.
- Network access to the official Paper API and download host.
- Network access required by Paper bootstrap on its first run, including Mojang runtime artifacts.
- A Paper plugin JAR you are allowed to use. Dependencies must be supplied as local JARs explicitly.

From a clean checkout:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install .
.\.venv\Scripts\pluginmatrix --version
```

On Linux or macOS, replace `.venv\Scripts\python` with `.venv/bin/python` and `.venv\Scripts\pluginmatrix` with `.venv/bin/pluginmatrix`.

## Minimal single-environment verification

The repository includes `ci-fixtures/PluginMatrixSmoke.jar`, a minimal project-owned fixture built from the adjacent Java source. It is legal to copy for this example and is not a production plugin.

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
--timeout 120               Paper readiness timeout in seconds
--stability-window 5        Observation time after Paper becomes ready
--work-dir path             Root for isolated run directories
--cache-dir path            Paper download and bootstrap cache
--report path.json          Runtime JSON report path
```

The single-environment command exits `0` only for `PASS`; every other verifier verdict exits `1`.

## Compatibility Matrix

Run the owned one-environment example, or copy it and add environments:

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

The v0.4 code was hosted-validated at commit `c5fe4ef`: Matrix #3 passed EnhancedFly 2.2.0 on Paper 1.20.1/build 196/Java 17, while Matrix #4 produced the expected `PLUGIN_ENABLE_FAILED` for the owned failure fixture. Both retained artifacts and had zero Action deprecation warnings. EnhancedFly's binary is no longer distributed here because the repository audit found no explicit redistribution license; the result remains historical evidence, not a public example.

## Offline development checks

```powershell
python -m unittest discover -s tests -v
python -m compileall pluginmatrix tests ci-fixtures/build_fixtures.py
```

Fixture source, build instructions, and checksums are documented in `ci-fixtures/README.md`. Packaging and clean-install checks are listed in `docs/RELEASE_CHECKLIST.md`.

See `CONTRIBUTING.md` before contributing, `SECURITY.md` for vulnerability reporting, `CHANGELOG.md` for version history, and `THIRD_PARTY_NOTICES.md` plus `docs/THIRD_PARTY_REVIEW.md` for source and licensing boundaries.

PluginMatrix is licensed under the Apache License 2.0. See `LICENSE`.
