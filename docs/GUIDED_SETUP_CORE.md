# v0.9 Guided Setup core — GPT-5.6 Sol handoff

Development branch: `codex/v0.9-guided-core`, based on public `0.8.0`.
This is a core implementation handoff. The package version stays `0.8.0`;
no Tag, Release, TestPyPI or PyPI publication is part of this work.

## Invariants

- The existing Runtime Verifier, Behavior protocol, five check types, fresh
  post-check health requirements and all PASS definitions are unchanged.
- `result` / `runtime_verdict` describe the runtime window.
  `behavior.verdict` remains independent. `verification_passed` remains the
  combined result. Neither a profile nor a recommendation assigns a verdict.
- No player Bot, new Provider, third-party plugin download, AI analysis,
  cloud execution, arbitrary script or configurable code loader was added.
- CLI, application API and Matrix share the new modules. The existing Web and
  standalone continue using the same application/runtime code.

## Core modules

| Module | Responsibility |
| --- | --- |
| `preflight.py`, `descriptor.py` | Bounded JAR/descriptor inspection and literal metadata hints |
| `analysis.py` | Static application response, diagnostics and editable suggestions |
| `dependencies.py` | Shared name/filename/provides conflicts; local required/optional dependency graph |
| `profiles.py` | Immutable, versioned, data-only built-in profile registry |
| `recommendations.py` | Evidence-bearing Provider/build/Java selection; explicit uncertainty |
| `jdks.py` | Official portable JDK provenance, download, extraction, cache, integrity, use leases and deletion |
| `matrix.py` | Shared schema normalization and existing per-environment scheduling |
| `application.py` | Stable services for the later wizard, project history and result adapters |

### Static analysis

`application.analyze_plugin(plugin, dependencies=())` performs no network access,
class loading, Java execution or extraction. It returns `schema`, `valid`,
target/dependency metadata, local dependency graph, diagnostics, limitations and
editable Behavior suggestions. `valid` means static prerequisites are satisfied,
not runtime PASS or a safety verdict.

Metadata includes the existing identity/hash/main/API/dependency fields plus:

- declared command names, descriptions, usage, permissions and simple aliases;
- permission names, defaults, descriptions and simple boolean child mappings;
- `folia_declaration` (`true`, `false`, `absent`);
- base-class bytecode observations and whether multi-release entries exist;
- `analysis_complete`, `analysis_warnings` and whether Maven libraries are declared.

The parser intentionally supports a bounded subset of descriptor YAML. It does
not evaluate tags, anchors, merges, expressions or arbitrary YAML objects.
Ambiguous/unsupported command and permission mappings produce incomplete
analysis and no guessed declarations. Existing identity preflight still rejects
dual descriptors and complex `paper-plugin.yml` bootstrapper/loader/dependencies.
Paper plugin commands are dynamic; a `commands` key there produces no inferred
Bukkit command registration. Dynamic services and reflection remain unknown.

JAR bounds remain 512 MiB compressed/expanded, 100,000 entries and a 1 MiB
descriptor; CRC, duplicate entries, encryption and compression checks remain
shared with runtime preflight. Optional declaration sections are limited to
256 entries. Base class inspection does not assert that all observed classes
will load; multi-release classes do not become an invented minimum Java version.

Required dependencies, including transitive requirements, must be supplied as
local JARs. `provides` aliases can satisfy exact declared names. Case-only
matches are reported for explicit correction instead of being assumed valid.
Required cycles and name/filename/alias/probe conflicts block guided execution;
absent soft dependencies and load-order targets remain visible warnings.
The runtime's pre-existing conflict checks use the same identity implementation.
Behavior-free legacy execution does not acquire new dependency-graph verdicts.

### Safe Behavior suggestions

Only `command_registered` and `permission_registered` are generated.
Commands use a target namespace. Names that cannot be represented by the
existing Behavior schema (for example wildcard permission nodes), excess checks
and unsupported declarations are explicitly listed as omitted.

No `console_command` is generated, including for names such as `help`,
`status`, `reload`, `stop` or `wipe`. Command names/descriptions cannot establish
whether invoking a command is safe. Services, arguments and gameplay assertions
are never guessed.

The response includes source fields/reasons and `requires_review=true`.
Preparation materializes suggestions into editable ordinary Behavior JSON.
Saving, normalizing, loading and running that JSON never regenerate its checks.
Explicit Behavior input takes precedence; `use_suggestions=False` removes
automatic suggestion materialization. Users can still explicitly write the
same console checks supported by v0.8.

## Profiles and configuration schema

All current profiles have revision `1`. Revisions are immutable contracts;
future changes should add a revision, preserving saved configurations.
Extension means adding reviewed data to the in-source registry, not importing
user code or creating a new verifier.

| ID | Startup timeout default | Stability default | Preparation suggestions | Constraints |
| --- | --- | --- | --- | --- |
| `quick` | 120 s | 5 s | None | One environment |
| `standard` | 180 s | 10 s | Safe registrations | One environment |
| `matrix` | 180 s | 10 s | Safe registrations | 2–256 explicit environments, concurrency still 1–8 |
| `strict` | 240 s | 30 s | Safe registrations | Fixed official builds, stability at least 30 s, complete supported static analysis |

All profiles check the supplied local dependency graph. A profile alone does
not add Behavior checks during execution. Strict means these concrete
prerequisites and a longer observation window; it does not prove every feature,
thread safety, permission evaluation or complete static analyzability.

`matrix.parse_matrix_config(document, source_path=...)` is now the common
in-memory/file normalization boundary. `source_path` supplies relative-path
resolution and input/output protection and need not exist yet. It does not
download or launch anything.

- Absent schema/profile preserves v0.7/v0.8 configuration and defaults.
- Explicit `schema: 1` also accepts the legacy configuration surface.
- `schema: 2` adds a profile and optional managed JDK storage/selection.
- Unknown schema/revision/fields, booleans used as version numbers and duplicate
  JSON keys are rejected. New and legacy server fields still cannot be mixed.
- Normalization preserves explicit Behavior and produces materialized options.
  JDK selection never downloads during config load, validation or execution.
- Direct `MatrixConfig` construction with a profile requires the registered
  immutable profile and `schema_version=2`; forged profile policies are rejected.

Example using an already installed JDK:

```json
{
  "schema": 2,
  "profile": {"id": "standard", "revision": 1},
  "plugin": "Example.jar",
  "dependencies": [],
  "environments": [
    {
      "server": {"type": "paper", "version": "1.20.1", "build": 196},
      "java": {"managed": "<id returned by jdk install>"}
    }
  ],
  "options": {"jdk_dir": ".pluginmatrix/jdks"}
}
```

The placeholder must be replaced with an actual installed ID. A normal
Java executable/major remains valid; no managed store is required. CLI
`--java managed:<id>` represents the same selection.

## Environment recommendations

`recommend_environment` returns a proposed selection, reason/source entries,
unresolved questions and conflicts. It never returns a compatibility verdict.

- Minecraft is an explicit intended target. `api-version` constrains its lower
  bound; it does not select a target or prove a supported version range.
- Paper is the explained baseline choice if no Provider was selected. Purpur
  and Folia remain explicit choices. Folia requires target and dependency
  declarations and still makes no thread/region safety claim.
- Official builds must match Provider, Minecraft version and a fresh catalog
  (six-hour maximum, bounded clock skew). Stale/unavailable metadata is visible
  but cannot yield an automatic ready recommendation.
- Only stable Paper/Folia builds are automatically selected. An explicit
  published alpha/beta build can be used after review. Purpur's official
  latest successful build is not relabeled as a stability channel.
- Java is selected at the documented server baseline, with matching `javac`.
  A higher observed base bytecode target creates an unresolved combination;
  choosing a newer JDK is not assumed to make the server/plugin compatible.
- The reviewed Java table deliberately has finite bounds. Current covered
  ranges end at `1.21.4`, plus the separately recorded `26.1` baseline. Unknown
  later versions/local contracts require explicit validation and policy review,
  rather than a formula assigning Java to all future Minecraft releases.
- Managed recommendations preserve the opaque ID and `jdk_dir`; they do not
  become an ordinary executable path that loses lease protection. A store
  listing is labeled `integrity=not_checked` and is not sufficient for a ready
  managed recommendation. `recommend_setup(..., jdk_dir=...)` verifies at most
  eight matching cached JDKs and reports omitted/invalid candidates.

## Managed JDK security contract

The supported source is Eclipse Adoptium Temurin GA, HotSpot, normal heap,
portable full JDK archives for the detected Windows/Linux/macOS x64/aarch64
platform. Available majors are a reviewed closed set: 8, 11, 16, 17, 21 and 25;
the official API must actually publish the requested platform package.

1. Preview queries the official Adoptium feature-release API over HTTPS.
   Metadata must match GA/vendor/major/OS/architecture/image type/project.
2. Installation resolves official metadata itself. `expected_id` optionally
   pins a reviewed preview; a changed upstream selection is rejected.
   Configurations cannot supply arbitrary download URLs/checksums/install hooks.
3. Initial archive URLs must identify the matching `adoptium/temurin*-binaries`
   GitHub repository, release and filename. Redirects are HTTPS and host
   allowlisted to GitHub's artifact hosts.
4. The stream must match both official size and SHA-256 before extraction or
   executing `java -version` / `javac -version`. Downloads are bounded to
   512 MiB and 600 seconds, with bounded HTTP waits and cooperative cancellation.
5. Extraction is into a unique staging directory. It never uses `extractall`.
   Paths, reserved filenames, traversal, ADS, case/Unicode normalization
   collisions, encryption, archive links, hardlinks and special files are
   rejected. Limits are 30,000 filesystem entries and 2 GiB expanded.
6. Exactly one full JDK home must contain matching release metadata and working
   Java/Javac. Special permission bits are removed. Windows CRLF release
   metadata is supported. There is no MSI/package installer execution.
7. A receipt records official provenance and a SHA-256/size manifest of all
   extracted files. Publication is atomic under a persistent per-package OS lock.
   The extracted tree is the executable cache; the download archive is removed
   after successful validation, while its original size/hash/source remain
   recorded.
8. Each selected cached JDK is checked against its complete manifest before use.
   Links, hardlinks, substituted files, missing/extra files and changed hashes
   fail closed. A cached receipt is local evidence, not a vendor signature
   over the extracted files.
9. Shared use is represented by per-process OS-locked leases. Parallel Matrix
   environments can use one JDK. Deletion holds the package lock and refuses any
   active lease; abandoned leases can be reclaimed after the OS releases them.
   Explicit executable paths inside the selected store receive the same lease.
10. Delete accepts only a valid managed ID in a marked store, with a matching
    receipt. It checks the resolved subtree and link/special-file state before
    recursive removal. The store cannot overlap verification inputs, work/cache
    directories or reports. No system installation can be adopted for deletion.

No PATH, JAVA_HOME, JDK_HOME, OS registry or system Java configuration is changed.
Validation/verification can use an installed managed JDK offline. Installing a
new/latest JDK remains an explicit network operation.

Archive symlinks/hardlinks are deliberately unsupported, including internal
ones. A platform package containing them is rejected, not silently rewritten.
Only the actual Windows x64 package below has passed this handoff's native
download/start/delete Gate. Linux/macOS native acceptance remains required.
Arbitrary Java processes launched outside these cooperating application/store
APIs do not hold leases. The store is not protection against hostile programs
with the same OS account; such programs can also modify the application itself.

## Application API and CLI

Existing `API_VERSION=1` stays additive. New service response documents use
`GUIDED_API_VERSION=1`; configuration schema 2 and Behavior schema 1 are separate
version domains.

| Service | Purpose |
| --- | --- |
| `analyze_plugin` | Static metadata, dependencies, diagnostics, editable suggestions |
| `inspect_profiles` | Data-only profile catalog with immutable revisions |
| `recommend_setup` / `recommend_environment` | Explained proposed environment and unresolved prerequisites |
| `prepare_configuration` | Materialize an editable configuration and SHA-256, with static source evidence |
| `normalize_configuration` | Preserve the supported config for import/export/history |
| `run_configuration` | Normalize then call the existing Matrix/application executor |
| `run_single(..., profile=..., jdk_dir=...)` | Same single verifier with profile prerequisites and optional JDK lease |
| `preview_managed_jdk` | Explicit official metadata preview |
| `install_managed_jdk` | Explicit, optionally preview-pinned download |
| `inspect_managed_jdks` | Bounded local listing; integrity status is explicit |
| `delete_managed_jdk` | Guarded ID-based deletion, rejecting active uses |

New CLI entry points:

```text
pluginmatrix analyze --plugin Example.jar --dependency LocalAPI.jar --json
pluginmatrix profiles --json
pluginmatrix recommend --plugin Example.jar --minecraft 1.20.1 --network --json
pluginmatrix init matrix.json --plugin Example.jar --minecraft 1.20.1 --java 17 --profile standard
pluginmatrix test --plugin Example.jar --paper 1.20.1 --java 17 --profile quick
pluginmatrix jdk preview --major 17 --json
pluginmatrix jdk install --major 17 --id <reviewed-id> --json
pluginmatrix jdk list --json
pluginmatrix jdk remove --id <installed-id> --json
```

The analysis/profile/recommendation/JDK commands currently emit JSON even without
`--json`; polished human-facing CLI rendering remains product work.
The old Web editor explicitly rejects schema 2 imports until it can preserve
their semantics. Do not remove that guard until profile revisions, JDK IDs,
storage location, explicit checks and unknown-field rejection round-trip.

## Validation recorded on 2026-09-15

Local Windows / Python 3.11.9:

- 225 related offline tests ran: 219 passed, 6 platform/permission skips.
  These cover the affected runtime, Behavior, preflight, application, Matrix,
  Provider, concurrency, security, regressions and Web surfaces.
- Final managed-reference and prerequisite-outcome hardening added two more
  tests; the affected 89-test subset then passed (87 passed, 2 skips).
- CLI smoke passed for profiles, static analysis, empty post-deletion JDK
  listing and schema-2 `init`. This also exposed an old complete-arguments
  `init` path that still prompted on an attached terminal; it now uses the
  existing Paper default without prompting. Its new regression and application
  suite passed (15 tests).
- `compileall` and `git diff --check` passed.
- Test-owned JDK fixtures cover checksum-before-execution, source binding,
  size/expanded limits, path/receipt escape, case collisions, links/special
  files, corrupt caches, cancellation, simultaneous installs, live leases
  across independent Python processes, stale-lease cleanup, and refusal to
  adopt/delete unrelated directories.

Explicit real Gate:

```text
python -m tests.real_guided_gate --delete-jdk
```

Official package: Temurin `jdk-17.0.20.1+1`, Windows x64, 190,817,615 bytes,
SHA-256 `e53a79c3c3d86865bd7e787903884331068e71321714ffd44f145785affc7cb0`.
Only the repository-owned behavior fixture source was built.

| Real check | Outcome |
| --- | --- |
| Official metadata, archive SHA-256, Java/Javac, extracted manifest | Passed |
| Static suggestions and official Paper/build/JDK recommendation | Passed |
| Paper 1.20.1/build 196, quick | Runtime PASS, Behavior NOT_RUN, final success |
| Paper 1.20.1/build 196, standard | Runtime PASS, both generated registration checks PASS |
| Paper 1.20.1/build 196, strict | Complete 30-second runtime window and generated checks PASS |
| Paper 1.20.1/196 + 1.20.4/499, Matrix `max_parallel=2` | Independent runtime/Behavior PASS in both environments |
| Delete while leased / delete after all JVM cleanup | Refused while active / succeeded after completion |
| System Java configuration / Gate JVM inventory afterward | Unchanged / no managed Gate JVM remaining |

Evidence directory:
`C:\Users\11580\AppData\Local\Temp\pluginmatrix-09-guided-f38quwio`.
It contains generated configurations, analysis/recommendation/JDK provenance,
per-environment JSON, raw `server.log` and Behavior protocol artifacts.
`gate-summary.json` SHA-256:
`9b734217e2faba63ce66047e87cfe7ec417ca193b0715e4b293613396efc6013`.
These are local validation artifacts, not repository/release assets.

The first install attempt at
`C:\Users\11580\AppData\Local\Temp\pluginmatrix-09-guided-4g0iqn8o`
correctly refused publication because CRLF release metadata was not recognized.
The parser was fixed, a CRLF regression added, and the complete real Gate above
then passed. Final subsequent changes added cache-reference preservation,
shared ENVIRONMENT_INVALID/CANCELLED outcomes for JDK prerequisites, and
additional metadata/path checks, covered by the focused regressions; they did
not change Runtime/Behavior verdicts or the server-side probe.

## Remaining work assigned to GPT-5.6 Sol

1. **Web wizard and one-click flow:** JAR selection → analysis/dependencies →
   explicit Minecraft target → explained environment/JDK choice → editable
   profile/check review → existing application execution. Preserve unresolved
   recommendations; never silently replace a requested target/build.
2. **Interface details, dark mode and translation:** approachable labels,
   responsive layouts, input errors, pending/cancel states, English/简体中文.
   Present runtime, Behavior and combined results separately.
3. **Project history and result pages:** persist normalized schema/revisions,
   configuration hash, source JAR hashes and report/artifact references.
   Reuse existing safe artifact IDs/file identity checks; no arbitrary path
   read endpoint or new verdict computation.
4. **Cache management pages:** explicit metadata preview/download and ID-based
   deletion using these services. Display source/hash/platform/integrity and
   active-use errors. Handle failed/interrupted staging directories separately;
   do not implement generic recursive deletion or delete persistent lock files.
5. **User documentation/examples and CLI polish:** onboarding, profile
   differences, Behavior scope, explicit local dependencies, managed-JDK
   source/storage/removal, conservative Java-policy updates and troubleshooting.
6. **Cross-platform acceptance:** native Windows/Linux/macOS, x64/arm64,
   real Temurin archive layout and permissions, cancellation/crash recovery,
   long paths, reparse points, read-only/disk-full/cache-corrupt cases and
   PyInstaller frozen CLI/Web. A linked archive remains unsupported unless a
   separately reviewed safe policy is implemented.
7. **Release preparation:** eventual development/candidate version, notices,
   packaging, release checklist and full final gates. Current source remains
   a development branch; publication needs separate authorization. Do not
   create/move tags, publish releases or upload to PyPI as part of this handoff.

Official contract references:

- Paper setup / Java policy: <https://docs.papermc.io/paper/getting-started/>
- Paper descriptors: <https://docs.papermc.io/paper/dev/plugin-yml/>
- Adoptium API implementation/OpenAPI: <https://github.com/adoptium/api.adoptium.net>
- Temurin artifacts: <https://github.com/adoptium/temurin17-binaries>
