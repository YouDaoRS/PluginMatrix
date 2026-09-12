# PluginMatrix

PluginMatrix is a small, configuration-light runtime verifier for Minecraft Paper plugins. It runs one plugin JAR in one real Paper/Java environment and produces a structured result plus the original `server.log`.

## Quick start

```powershell
python -m pluginmatrix test `
  --plugin .\EnhancedFly.jar `
  --paper 1.20.1 `
  --java 17
```

The first run downloads the latest stable Paper build for the requested version into `.pluginmatrix/cache`. Each run is isolated under `.pluginmatrix/runs`.
For reproducible reruns, pin the resolved build:

```powershell
python -m pluginmatrix test --plugin .\EnhancedFly.jar --paper 1.20.1 --paper-build 196 --java 17
```

Useful options:

```text
--dependency path.jar       Add a locally supplied dependency plugin
--timeout 120               Server readiness timeout in seconds
--stability-window 5        Seconds to observe after readiness
--report path.json          Write the structured report to a chosen path
```

The process exits `0` only for `PASS`; every other verifier state exits `1`.

The verifier currently proves server startup and plugin initialization, not complete gameplay compatibility. Paper's own bootstrap may need to download Mojang runtime artifacts on first launch; those downloads and their failures are retained in `server.log`.

## Compatibility Matrix

Run the same plugin JAR sequentially against several Paper/Java environments with a JSON config:

```powershell
python -m pluginmatrix matrix .\matrix.json
```

Example `matrix.json`:

```json
{
  "plugin": ".\\EnhancedFly-2.2.0.jar",
  "environments": [
    { "paper": "1.19.4", "java": 17, "paper_build": 550 },
    { "paper": "1.20.1", "java": 17, "paper_build": 196 },
    { "paper": "1.20.4", "java": 17, "paper_build": 499 }
  ],
  "options": {
    "timeout": 120,
    "stability_window": 5,
    "work_dir": ".pluginmatrix/runs",
    "cache_dir": ".pluginmatrix/cache",
    "report": ".pluginmatrix/matrix-report.json"
  }
}
```

Paths in the config are resolved relative to the config file. Matrix exits with `0` when every environment passes, `1` when execution completes with one or more failed environments, `2` for configuration errors, and `3` for an unexpected PluginMatrix error.

## GitHub Actions

The repository includes two workflows:

- `CI` runs on `push` and `pull_request`. It installs the package, runs `compileall`, and executes the offline test suite. It does not download Paper or run real plugin servers.
- `Compatibility Matrix` is manual (`workflow_dispatch`). Start it from the Actions tab, provide a repository-relative JSON config and a repository-relative plugin JAR, and use Java 17. The workflow copies the JAR into an isolated CI path, validates that every configured environment uses Java 17, then calls the existing `python -m pluginmatrix matrix` command.

The manual workflow is intended for repositories or branches that contain the plugin artifact to test. This project does not automatically build arbitrary plugin projects, download JDKs, or manage third-party plugin dependencies. A missing config, plugin JAR, or unsupported Java value fails before Matrix execution with a clear setup error.

After a manual run, download `pluginmatrix-matrix-report` for the unified JSON report and `pluginmatrix-runtime-artifacts` for per-environment `result.json` and `server.log` files. The Job Summary reads the generated Matrix Report and shows the plugin, each environment verdict, totals, and artifact names. A failed environment keeps the report and artifacts while the workflow exits with Matrix code `1`; configuration and internal errors retain codes `2` and `3`.

### Manual hosted validation

The only step that cannot be completed locally is triggering the workflow on a GitHub-hosted runner. Use a test repository or test branch that you control and that contains this workflow, the Matrix config, and a plugin JAR already present in the checkout. Build the JAR yourself or provide it legally; do not rely on an untracked local file or an automatically downloaded third-party plugin.

1. Add a config such as `examples/ci-matrix.json`, with at least one environment using `"java": 17`.
2. Add a self-built or legally provided plugin JAR, for example `ci-fixtures/ExamplePlugin.jar`.
3. In **Actions**, choose **Compatibility Matrix**, select **Run workflow**, and enter:
   - `config`: `examples/ci-matrix.json`
   - `plugin_jar`: `ci-fixtures/ExamplePlugin.jar`
4. Expect the hosted runner to install Python 3.11 and Temurin Java 17, download Paper and any required Paper bootstrap files over the network, run each environment serially, and write a Job Summary.
5. For a passing plugin, expect `PASS` for each environment and a successful workflow. For an intentionally failing plugin or environment, expect a failed verdict and a failed workflow, while completed runs still retain their evidence.

Download `pluginmatrix-matrix-report` for `.pluginmatrix/matrix-report.json`, and `pluginmatrix-runtime-artifacts` for each environment's `result.json` and `server.log`. If config or JAR preparation fails before Matrix starts, the report/log artifacts may be empty; use the setup error in the job log and the Job Summary's missing-report message.
