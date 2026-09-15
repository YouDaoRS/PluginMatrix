# PluginMatrix architecture — v0.9

One Runtime Verifier remains the only lifecycle/verdict implementation. Provider implementations are selected from a fixed registry; arbitrary code is not loaded from config.

The public stable version is 0.9.0. The v0.9 addition is a preparation layer:
`analysis`/`descriptor`/`dependencies` → versioned `profiles` and explained
`recommendations` → schema-2 normalization in `matrix` → the same application
execution services. `jdks` provides explicit official downloads and local
integrity-checked use leases; it never configures system Java. The core API,
security boundaries and product handoff are in [GUIDED_SETUP_CORE.md](GUIDED_SETUP_CORE.md).

Development addition: [v0.8 behavior core](BEHAVIOR_CORE.md) extends the same probe
and verifier process lifetime with a bounded sequential behavior phase after the
runtime stability window. `behavior.py` owns plan validation, host assertions,
timeouts and post-check health; `behavior_probe.py` generates the compile-time
server-side allowlist. Runtime and behavior verdicts stay separate, and every
Matrix worker owns independent behavior state. The following v0.7 architecture
and process ownership remain the foundation.

```text
CLI / loopback Web UI / future guided adapters
        |
application.py: static analysis, profiles, explained setup, validation, run services
        |                         |
        |                  jdks.py: explicit install / integrity / use lease
        |
matrix.py -> scheduler.py (1..8 workers; ordered results; shared RunControl)
        |
runtime.verify -> ServerProvider
        |            |- config/capability/official metadata
        |            |- version/build/artifact resolution
        |            |- cache identity/startup command/log interpretation
        |            |- expected CodeSource and plugin support declaration
        |
isolated files -> probe -> fresh samples + raw log -> verdict -> cleanup -> report
```

## Provider contract

`ServerSpec` is a normalized specification. `parse_server()` rejects unknown fields, invalid versions/builds, unsupported local contracts and oversized metadata. `ServerProvider.validate/resolve/prepare` separate local validation, optional metadata network resolution and artifact retrieval. `requested_metadata()` is available even when resolution fails. `command()`, `interpret_server_line()`, `allowed_sources()`, `runtime_cache()` and `check_plugin()` define server-specific behavior; none assigns a runtime PASS.

| Provider | Source/integrity | Runtime and PASS boundary |
| --- | --- | --- |
| Paper | Official Fill v3 / SHA-256 | Bukkit scheduler, isolated/remapped identity, normal full stability evidence |
| Purpur | Official Purpur v2 / MD5 plus recorded local SHA-256 | Same Bukkit lifecycle contract, independent namespace and resolved build |
| Folia | Official Fill v3 Folia project / SHA-256, recorded channel | Global region scheduler; requires support declaration; no thread/cross-region safety claim |
| local/custom | User JAR / copied SHA-256; no service download | Explicit paperclip/bukkit/folia profile; declared identity, `official=false`, unknown behavior fails closed |

Paper compatibility helpers in `paper.py` preserve old function names, flat download cache and `paper_*` report fields. Runtime bootstrap cache identities include provider, version, build and JAR digest; old bootstrap snapshots are not silently trusted as new identities. They may be rebuilt by the server. Purpur/Folia downloads use provider/version/build subdirectories.

Latest means stable-first, highest published fallback for Paper/Folia (matching 0.5.1), and official latest successful build for Purpur. No version substitution occurs. Fixed builds are looked up exactly, including non-stable channels, and the channel stays visible. Purpur's upstream MD5 is not presented as a cryptographic SHA-256 provenance guarantee. SHA-256 receipts pin subsequent use of a downloaded cache artifact.

Local profiles deliberately form a small closed set. `paperclip` and `folia` expect `META-INF/libraries/*.jar` API libraries, known ready/start/failure logs, supported `--nogui` flags and expected remapped paths. `bukkit` can compile against API classes in a monolithic JAR and accepts only the direct target CodeSource. There is no arbitrary argument, regex, extraction or download DSL. Unknown layouts return a clear environment/probe failure. This is a foundation for future adapters, not a claim that every Spigot/fork JAR works.

## Scheduling and cancellation

`schedule(items, worker, max_parallel, control)` guarantees a bounded worker count and configuration-order results. Each worker owns a complete verifier call; no JVM objects, plugin state, log files or probe paths are shared. Ports have in-process leases as well as OS availability checks. A competing external program can still occupy a released bind port; bind failure is an explicit server failure, never a PASS.

`RunControl` carries a thread-safe cancel flag. Ctrl+C cancels and drains workers before returning; queued work yields `CANCELLED` without launching. Downloads/locks/compile/startup all have bounded waits. Existing in-flight HTTP requests can take up to their timeout (30 seconds) and compiler invocation up to 60 seconds before reaching a cancellation check. Worker JVM cleanup remains in `finally` through suspended Windows Job Objects or POSIX process groups. Cleanup errors cannot support PASS. Environment verdicts never cancel siblings; unexpected scheduler failures trigger cancellation of owned work.

Cache download and bootstrap seed/capture are serialized with OS file locks, including independent processes. Locks are persistent files: deleting them while held would allow another inode to bypass ownership. Publication uses fresh temporary files and atomic replacement, so a process crash leaves no partially published JAR. Checksums are verified on existing cache reads; conflicting content is preserved and rejected. Different Matrix invocations cannot hold the same report lock simultaneously. A later explicit run can replace a completed report atomically.

## Evidence, paths and reports

Plugin and dependency identities, provides aliases and probe reserved names are checked before runtime. Plugins and server JARs are copied into a unique run directory and rehashed. Raw log bytes survive invalid UTF-8. A PASS still requires ready, matching run/name/version/main/CodeSource, increasing sequence/time, no sample gap over two seconds, a final new sample after the complete window, no disable, a live server and successful cleanup. Interactive console flags are disabled so unattended stdin cannot flood logs; partial/log flood checks are not bypassed.

Folia can print `Done` before cold worlds finish initialization. Its global scheduler shares the region tick pool, which may contain only one thread on a constrained runner. The probe therefore keeps early Folia callbacks private until the scheduler has maintained a continuous fresh two-second span. PluginMatrix waits for that first safe sample only within the original configured startup deadline, then applies the unchanged host freshness rule and a new full stability window. Standard Bukkit schedulers retain the bounded post-ready probe grace.

Output validation includes config/plugin/dependencies/local-server inputs, hardlinks, symlinks/junctions, report/HTML, runtime and cache roots. Report writes and downloads are atomic. APIs, filenames, checksum values and embedded archive paths remain untrusted. HTML is derived from JSON, escapes text and percent-encodes relative artifact links, has no script or external assets and uses a restrictive CSP. Terminal control/bidirectional characters are escaped.

This is not a hostile-code sandbox. Trusted plugins execute with the same JVM and OS account as the probe. Deliberately malicious code can forge evidence or leave a POSIX process group. No telemetry, plugin/log uploads, implicit JDK installation or platform service is added. v0.9 managed JDK installation is an explicit portable-download operation; config normalization and runtime selection never download a JDK.

## Behavioral Verification

An optional immutable behavior plan is normalized once and passed through CLI, application API, Web and Matrix into the same Runtime Verifier. It runs only after the complete runtime stability window. The host requests one allowlisted check index at a time; the probe returns correlated typed observations, never a verdict. The host validates correlation, computes assertions and requires a newer healthy runtime sample after every check.

`result`/`verdict` remain the runtime verdict and are explicitly mirrored as `runtime_verdict`. `behavior.verdict` records the behavior dimension, while `verification_passed` requires runtime PASS and behavior PASS, or `NOT_RUN` when no plan exists. Assertion failure, behavior timeout/cancellation, unsupported API and lost post-check health do not rewrite the saved runtime window. Raw `server.log`, runtime probe and behavior response remain evidence artifacts in the isolated run directory.

The bounded check set is command registration, permission registration, target-owned service registration, target-owned console command return and host-monotonic wait. There are no scripts, expressions, loops, automatic retries, output regexes, player simulation or third-party loaders. Folia registry/wait work uses the global region scheduler; console commands are `UNSUPPORTED` without a general region ownership contract.

## Local Web UI

`pluginmatrix.web` is a transport/UI adapter. It normalizes bounded HTTP input into `ServerSpec`, `BehaviorPlan` and Matrix JSON, then calls `application.run_single` or `application.run_matrix`; it never assigns a verdict. Each job owns one `RunControl`, a bounded event deque, summary references and an allowlist of completed report/log/protocol artifact files. Import, export and rerun preserve the normalized behavior plan. Multiple UI jobs may coexist, but their reserved `max_parallel` values cannot exceed the existing global limit of eight.

The server binds only `127.0.0.1`. Exact Host/Origin validation, a SameSite/HttpOnly session cookie and an unguessable CSRF header token protect state-changing endpoints from DNS rebinding and browser CSRF. JAR bodies are streamed into a session-only local temporary directory under the existing 512 MiB bound. JSON remains limited to 1 MiB. Artifact URLs contain opaque job/artifact IDs, not filesystem paths; file identity is rechecked after opening. UI rendering uses `textContent`, and saved HTML remains the existing escaped, no-script renderer.

Server shutdown first stops accepting requests, then cancels active controls and joins their non-daemon job threads. Runtime cleanup therefore remains the same Windows Job Object/POSIX process-group `finally` path used by CLI cancellation.

## Standalone runtime

`standalone/pluginmatrix.spec` produces a PyInstaller `onedir` bundle. The build is deliberately native rather than cross-compiled and is archived as a platform/architecture-specific zip or tarball. `pluginmatrix.external` restores PyInstaller-modified system library lookup when spawning installed Java/Javac or platform opener processes; Runtime Verifier process ownership remains unchanged.

The standalone workflow checks version, all Provider metadata, Web assets, Java/Javac discovery and a real Paper runtime plus wait-behavior PASS path through frozen CLI and Web on every target. It verifies JSON/HTML/log/protocol artifacts and does not repeat Purpur/Folia/local Provider gates. Archives contain no JARs and are never uploaded to PyPI.

## Official references (contract research)

- [PaperMC Downloads Service](https://docs.papermc.io/misc/downloads-service/)
- [Purpur official API](https://api.purpurmc.org/)
- [Paper and Folia support declaration](https://docs.papermc.io/paper/dev/folia-support/)
- [Folia GlobalRegionScheduler API](https://jd.papermc.io/folia/1.21/io/papermc/paper/threadedregions/scheduler/GlobalRegionScheduler.html)

No third-party implementation, GPL code, tests or workflow were copied.
