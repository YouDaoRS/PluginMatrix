# v0.8 Behavioral Verification core

Development branch: `codex/v0.8-behavior-core`, based on stable v0.7.1. This is a
core implementation handoff, not a release declaration. Package version and
v0.7.1 tags/releases are unchanged.

## Configuration and API

`pluginmatrix test ... --behavior behavior.json` accepts a JSON document like:

```json
{
  "schema": 1,
  "timeout": 60,
  "checks": [
    {"id": "command", "type": "command_registered", "name": "myplugin:status"},
    {"id": "permission", "type": "permission_registered", "name": "myplugin.use"},
    {"id": "service", "type": "service_registered", "name": "example.api.StatusService"},
    {"id": "invoke", "type": "console_command", "name": "myplugin:status", "args": [], "expect": true, "timeout": 5},
    {"id": "settle", "type": "wait", "seconds": 1, "timeout": 5}
  ]
}
```

The same object is the optional top-level `behavior` field in Matrix JSON.
`application.run_single(..., behavior=document)` accepts a dictionary or the
immutable result of `behavior.parse_behavior(document)`. For direct
`MatrixConfig` construction, pass `behavior=parse_behavior(document)`.
The configuration is validated before launching servers. It is normalized to
canonical JSON and identified by SHA-256; each environment gets the same plan
but independent execution state and artifacts.

There are 1..64 uniquely named checks, at most 300 seconds for the behavior
phase, and at most 30 seconds per check, including its health confirmation.
Defaults are 60 and 5 seconds. `wait.seconds` must be smaller than its timeout.
Command arguments are an explicit array, at most 16 strings of 256 characters;
control characters are rejected. Unknown fields/check types and nonfinite or
boolean timeouts are configuration errors. There are no expressions, scripts,
loops, automatic retries, selectors, regex assertions or external code loaders.

## Verdict contracts

`result` (single environment) and `verdict` (Matrix environment) retain the
runtime verdict; `runtime_verdict` explicitly aliases it. Without a behavior
plan, the original runtime lifecycle is unchanged and behavior is `NOT_RUN`.
Behavior runs only after the complete runtime stability window passes.

Once the window passes, its verdict and evidence are retained. Failures,
disablement, process exit, missing evidence or cancellation **during behavior**
are attributed to `behavior`, including `post_health`; they do not become
startup/load/enable failures. Cleanup errors still prevent runtime PASS, as in
v0.7.1. Runtime PASS alongside behavior ERROR means the initial stability
window passed, not that the process remained healthy after the checks.

Behavior verdicts/check statuses:

| Status | Meaning |
| --- | --- |
| PASS | Every requested assertion and fresh post-check health barrier passed |
| FAIL | Typed observation contradicted `expect` |
| ERROR | Command exception, ownership rejection, invalid protocol, lost identity/enabled state or process health |
| TIMEOUT | Check, phase or required post-check sample exceeded its deadline |
| CANCELLED | RunControl/interrupt stopped the active behavior phase |
| UNSUPPORTED | The server API or runtime contract cannot safely perform a check |
| SKIPPED | Runtime prerequisite failed, or an earlier abort prevented execution |
| NOT_RUN | No behavior plan requested (aggregate only) |

Ordinary assertion failures and reported command exceptions continue to the
next declared check **after** a healthy fresh sample. Timeout, cancellation,
protocol errors or lost health abort the remaining checks. Unsupported checks
also continue after the barrier. Aggregate precedence is abort, then ERROR,
TIMEOUT, FAIL, UNSUPPORTED, SKIPPED, PASS; no all-skipped/unsupported success.

`VerificationResult.passed` / JSON `verification_passed` requires runtime PASS
and behavior PASS (or NOT_RUN when no plan was requested). CLI and Matrix exit
code 0 use this combined success condition. Matrix `summary.passed/failed`
counts combined results; `runtime_summary` and `behavior_summary` retain the
separate dimensions. Exit codes 1/2/3 retain completed failure / invalid config /
internal or report error meanings.

## Checks and direct evidence

| Type | Observation and boundary |
| --- | --- |
| command_registered | `Server.getPluginCommand`, `isRegistered`, and owner Plugin object equality. Checks Bukkit PluginCommand registration owned by the target, not all Brigadier/command frameworks. |
| permission_registered | `PluginManager.getPermission`, registration boolean and PermissionDefault enum. Checks the global registry; does not claim plugin ownership or player permission evaluation. |
| service_registered | `ServicesManager.getRegistrations(targetPlugin)`, filtered by exact service binary class name. Records service, implementation, owner and priority; never loads a configured class or invokes its methods. Registration does not imply highest-priority selection or service correctness. |
| console_command | Resolves the registered target-owned PluginCommand, checks console permission, and calls `PluginCommand.execute` with the real ConsoleCommandSender and explicit argument array. Records ownership, sender kind and typed returned boolean. This bypasses global command dispatch/preprocessing, supports no server administration commands or foreign plugin commands, and does not capture/assert text output. |
| wait | Host monotonic elapsed time with continued fresh identity/enabled observations. No server thread sleep. |

`expect` defaults to true and may be false for registration or command-return
assertions. `expect=false` never bypasses command ownership/permission checks.
A true command return is only the API return value; it does not prove business
or gameplay correctness. Plugin-owned commands themselves may have side effects.

Paper, Purpur and explicit local Bukkit/Paperclip contracts use the existing
Bukkit scheduler. Folia and `local runtime=folia` use the existing global region
scheduler for registry reads, but console commands return UNSUPPORTED because
there is no safe general region ownership contract. Missing API methods also
return UNSUPPORTED. Requested provider metadata exposes `behavior_capabilities`.

## Protocol, health and cleanup

The existing runtime probe is compiled once against the exact server artifact,
with the normalized check allowlist embedded. No dynamic plugin/script code is
loaded from configuration. Host requests contain only an index and random
request ID. The probe consumes each increasing index **before** execution and
caches its response until atomic publication succeeds, so Windows publication
retries cannot repeat commands.

Responses bind schema, run ID, plan hash, request ID, check ID/type/index and
completion timestamp. The host rejects mismatched/replayed/stale/malformed
evidence and computes assertions from strict booleans/objects, never from a
probe-provided PASS or log text. File reads are bounded, use opened-handle
identity checks, reject links/special files, and cannot block on a POSIX FIFO.

Every completed check requires an advancing runtime sample after the host
receives its response. The same RuntimeEvidence identity/CodeSource validation
checks the target, enabled flag and latched disable events; the process must
still be alive. The final barrier is also the phase's post-health confirmation.
During synchronous command execution, probe callbacks may be blocked; the host
enforces the command/phase timeout, then requires a fresh sample. A timeout or
cancel cannot yield a behavior PASS based on the earlier runtime window.

Per-check JSON contains the normalized plan, request, raw structured response,
start sequence/time, final sample, elapsed time and observed process health.
Abort results preserve the last valid and rejected observed samples when
available. Raw protocol files remain in the isolated plugins directory; request
files are disarmed before JVM cleanup. Raw `server.log` remains intact. Behavior
log text is not reinterpreted as startup failure evidence.

All behavior code runs inside the existing verifier's process ownership/finally
boundary. Matrix workers share only the immutable plan and RunControl; requests,
responses, ports, JVMs and plugin state are isolated. Cleanup still drains the
owned Windows Job Object or POSIX process group. Cancel cannot undo a command
that has already begun; disarming prevents pending requests from being retried.

This is not hostile-code isolation: plugin and probe share a JVM and OS account.
Run IDs/hashes prevent accidental replay and cross-environment confusion, not
forgery by an actively malicious plugin capable of reading/rewriting memory or
files. No Bot, players, movement/combat, world simulation, AI or third-party
scripts have been added.

## Core validation and handoff

Offline regressions: `tests/test_behavior.py` plus the affected runtime,
application, Matrix, provider, parallel, security, critical-path, regression and
summary suites. The explicit real Gate is `python -m tests.real_behavior_gate`;
it builds only the project-owned `ci-fixtures/behavior` source into a temporary
directory and retains JSON/raw logs. `--provider`, `--minecraft`, `--build`,
`--java` and `--scenarios` select only relevant core Gate paths.

Sol follow-up scope:

1. Add behavior plan input/import and two-verdict presentation to the existing
   Web UI, using `application` and `verification_passed`; do not create a second
   executor or reinterpret runtime PASS as combined success.
   The current Web import explicitly rejects behavior plans to prevent silently
   dropping their checks; remove that guard only when the UI preserves them.
2. Translate the new UI/progress/error text; extend the artifact allowlist for
   behavior evidence using the existing safe artifact mechanism.
3. Complete user examples, README/product/status/release documentation and
   static report usability. This page records the core contract only.
4. Run cross-platform core CI (including the POSIX FIFO test), then standalone
   packaging and focused Web acceptance tests. Revalidate local bootstrap when
   upstream dependency downloads are available.
5. Review the eventual v0.8 candidate, change the development/release version,
   and perform final release gates under the user's later release authorization.
   Do not move v0.7.1, publish PyPI, tag or release from this core handoff.

Official API references used for these contracts:
[PluginCommand](https://jd.papermc.io/paper/1.21.4/org/bukkit/command/PluginCommand.html),
[ServicesManager](https://jd.papermc.io/paper/1.21.4/org/bukkit/plugin/ServicesManager.html),
[PluginManager](https://jd.papermc.io/paper/1.21.4/org/bukkit/plugin/PluginManager.html).
