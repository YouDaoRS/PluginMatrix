# Application API v1

`pluginmatrix.application.API_VERSION == 1`. These services are synchronous; a GUI can call them from a background thread and request cancellation from its UI thread. They do not parse CLI arguments or print logs.

```python
from pathlib import Path
from pluginmatrix.application import (
    RunControl, validate_configuration, inspect_providers,
    inspect_provider_catalog, discover_java_runtimes,
    run_single, run_matrix, load_report, render_html_report,
)
from pluginmatrix.providers import ServerSpec

validation = validate_configuration(Path('matrix.json'), network=False)
providers = inspect_providers()
versions = inspect_provider_catalog('paper', cache_dir=Path('.pluginmatrix/cache'))
builds = inspect_provider_catalog('paper', '1.21.4', Path('.pluginmatrix/cache'))
java = discover_java_runtimes()
control = RunControl(lambda event: print(event.to_dict()))  # GUI: enqueue promptly
report = run_matrix(Path('matrix.json'), max_parallel=2, control=control)
saved = load_report(Path(report['artifacts']['matrix_report']))
render_html_report(Path(report['artifacts']['matrix_report']), Path('matrix.html'))

result = run_single(
    plugin=Path('plugin.jar'), server=ServerSpec('purpur', '1.21.4'), java='21',
    work_root=Path('.pluginmatrix/runs'), cache_dir=Path('.pluginmatrix/cache'),
    timeout=120, stability=5, report_path=Path('runtime.json'), control=RunControl(),
)
# From another thread while the run is active:
# control.cancel()
```

- `validate_configuration(path, network=False)` returns JSON-compatible schema/valid/exit_code/errors/config/preflight/resolved fields. It does not download server JARs or execute servers. Write-permission probes may create output directories and remove temporary test files.
- `inspect_providers()` returns capability and configuration metadata from the runtime Provider registry.
- `inspect_provider_catalog(provider_type, version=None, cache_dir=...)` returns normalized official versions or builds without downloading a server JAR. Metadata is bounded, cached for six hours, and can return `source=stale_cache` or `available=false` instead of hiding network failure. `discover_java_runtimes()` returns locally found Java/JDK versions, executable paths and matching `javac` state; it never installs or modifies Java. `minecraft_java_requirement(version)` returns the documented Paper Java baseline used for UI guidance.
- `run_single(...)` returns `VerificationResult` and saves an authoritative runtime report when a run directory exists or a report path is supplied. `run_matrix(...)` accepts a path or a parsed `MatrixConfig`, validates local preconditions, runs isolated environments, saves JSON and optionally HTML, and returns the report dictionary. Invalid configuration raises `MatrixConfigError`/`ValueError`; artifact-save errors are surfaced to the caller. The CLI maps them to its documented exit codes.
- `load_report(path)` accepts runtime/Matrix JSON up to 32 MiB. `render_html_report(source, destination)` returns the output path without recalculating verdicts. Inputs, logs and mutable roots are protected from rendering output.
- Saved paths are absolute; relative paths in imported reports are resolved from the JSON file's directory for both links and output protection. The old internal `runtime.verify(paper_jar=..., paper_metadata=...)` bypass is rejected; use `run_single(server=ServerSpec('local', ..., jar=..., name=..., runtime='paperclip'))` for user-supplied JARs, which records `official=false`.
- `RunControl.cancel()` is idempotent. Cancellation is cooperative and bounded by current HTTP/compile/cleanup operations. Use a new control for a new run. Already completed results are retained; cancelled/unstarted environments receive `CANCELLED` and cannot pass.

## Progress event schema

`ProgressEvent.to_dict()` contains `schema: 1`, `kind`, wall-clock `timestamp`, optional zero-based `environment_index`, and bounded `data`. It never includes arbitrary configuration, secrets, local paths or log lines. No event history is retained by the service. Observer callbacks are serialized; quick enqueue-only observers are recommended. Callback exceptions are counted in `RunControl.observer_errors` and do not change verdicts.

Events: `matrix_started`, `environment_started`, `download_started`, `download_completed`, `server_started`, `plugin_enabled`, `stability_progress` (at most once per second per environment), `environment_completed`, `matrix_completed`. `data` may contain provider identifier, counts, concurrency, elapsed/duration, cache-hit flag or verdict. Cross-environment events follow actual progress, while final report environments always follow configuration order. A cache hit emits download events with `cached=true`; local sources do not emit download events.

The services do not install Java, upload anything, spawn a GUI, or manage accounts/background daemons. No separate verifier is needed for a GUI.

The v0.7 `pluginmatrix.web` module is a thin GUI adapter: it converts bounded loopback requests to these services and forwards their `RunControl`/`ProgressEvent` objects. It does not add an alternate result model. A UI task marked `completed` exposes the exact returned runtime or Matrix verdicts; all-cancelled runs are marked `cancelled`, while transport/configuration failures are marked separately as failed UI tasks.
