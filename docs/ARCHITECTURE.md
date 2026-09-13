# PluginMatrix 0.6 development architecture

One Runtime Verifier remains the only lifecycle/verdict implementation. Provider implementations are selected from a fixed registry; arbitrary code is not loaded from config.

```text
CLI / future GUI
        |
application.py: validation, run services, report loading/rendering
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

This is not a hostile-code sandbox. Trusted plugins execute with the same JVM and OS account as the probe. Deliberately malicious code can forge evidence or leave a POSIX process group. No telemetry, plugin/log uploads, automatic JDK installation or platform service is added.

## Official references (contract research)

- [PaperMC Downloads Service](https://docs.papermc.io/misc/downloads-service/)
- [Purpur official API](https://api.purpurmc.org/)
- [Paper and Folia support declaration](https://docs.papermc.io/paper/dev/folia-support/)
- [Folia GlobalRegionScheduler API](https://jd.papermc.io/folia/1.21/io/papermc/paper/threadedregions/scheduler/GlobalRegionScheduler.html)

No third-party implementation, GPL code, tests or workflow were copied.
