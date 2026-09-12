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

Before starting any Paper server, Matrix checks the plugin JAR, each requested Java runtime, the required JDK `javac`, and whether the work, cache, and report locations can be created and written. Configuration errors include the field and current value, what was expected, and a concrete fix. Exact duplicate environments and output-path conflicts are rejected before execution. Paper availability is checked by the Runtime Verifier before that environment starts; an unavailable fixed build is reported as `ENVIRONMENT_INVALID` with guidance to correct or remove `paper_build`.

On failure, the CLI prints the failing environment, verdict, failure stage, reason, primary evidence, runtime report, `server.log`, and run directory. If failure happens before server launch, it explicitly says that `server.log` was not generated. The final line always identifies the unified Matrix Report path. The JSON report retains the v0.2/v0.3 fields and adds `config_source`, `preflight`, top-level `artifacts`, and per-environment `primary_evidence`/`artifact_availability` fields; it references original logs instead of embedding them.

## GitHub Actions

The repository includes two workflows. Their official JavaScript actions use Node.js 24-compatible current major versions (`checkout@v7`, `setup-python@v7`, `setup-java@v6`, and `upload-artifact@v7`):

- `CI` runs on `push` and `pull_request`. It installs the package, runs `compileall`, and executes the offline test suite. It does not download Paper or run real plugin servers.
- `Compatibility Matrix` is manual (`workflow_dispatch`). Start it from the Actions tab, provide a repository-relative JSON config and a repository-relative plugin JAR, and use Java 17. The workflow copies the JAR into an isolated CI path, validates that every configured environment uses Java 17, then calls the existing `python -m pluginmatrix matrix` command.

The manual workflow is intended for repositories or branches that contain the plugin artifact to test. This project does not automatically build arbitrary plugin projects, download JDKs, or manage third-party plugin dependencies. A missing config, plugin JAR, or unsupported Java value fails before Matrix execution with a clear setup error.

After a manual run, download `pluginmatrix-matrix-report` for the unified JSON report and `pluginmatrix-runtime-artifacts` for per-environment `result.json` and `server.log` files. The Job Summary reads the generated Matrix Report and shows each environment verdict, failure stage, primary evidence, totals, and artifact names. It does not recalculate verifier verdicts. A failed environment keeps the report and artifacts while the workflow exits with Matrix code `1`; configuration and internal errors retain codes `2` and `3`.

Both workflow inputs must be repository-relative files present in the selected branch. The `plugin` field inside the source config is replaced with the `plugin_jar` workflow input after the JAR is copied to `.ci/plugin.jar`; other config paths are rewritten to `.pluginmatrix` locations. If an input is missing, points outside the repository, or names an uncommitted local file, the setup error identifies the input, resolved expectation, and correction before Matrix runs.

### Manual hosted validation

The v0.4 workflow is hosted-validated at commit `c5fe4ef`. [`Compatibility Matrix #3`](https://github.com/YouDaoRS/PluginMatrix/actions/runs/34687494718) passed with EnhancedFly 2.2.0 on Paper 1.20.1/build 196/Java 17, no deprecation warnings, the expected Summary, and both artifacts. [`Compatibility Matrix #4`](https://github.com/YouDaoRS/PluginMatrix/actions/runs/34687590131) exercised the owned enable-failure fixture and retained the correct `PLUGIN_ENABLE_FAILED` stage, primary evidence, Summary, and both artifacts while the workflow failed as expected. The steps below reproduce those checks.

1. Commit and push the v0.4 changes, both example configs, and both fixture JARs to a branch you control.
2. In **Actions**, choose **Compatibility Matrix** and run the success case:
   - `config`: `examples/ci-matrix.json`
   - `plugin_jar`: `ci-fixtures/EnhancedFly-2.2.0.jar`
3. Confirm `PASS`, `1 passed, 0 failed`, no Node.js 20/setup-java v4 warnings, and both downloadable artifacts.
4. Run the owned runtime-failure case:
   - `config`: `examples/ci-enable-failure-matrix.json`
   - `plugin_jar`: `ci-fixtures/PluginMatrixEnableFailure.jar`
5. Confirm workflow failure with `PLUGIN_ENABLE_FAILED`, stage `plugin_enable`, a `primary_evidence` server-log path, `0 passed, 1 failed`, and both downloadable artifacts. The fixture source is under `ci-fixtures/enable-failure`; it intentionally throws from `onEnable()` and is not a malformed-config test.

Download `pluginmatrix-matrix-report` for `.pluginmatrix/matrix-report.json`, and `pluginmatrix-runtime-artifacts` for each environment's `result.json` and `server.log`. If config or JAR preparation fails before Matrix starts, the report/log artifacts may be empty; use the setup error in the job log and the Job Summary's missing-report message.
