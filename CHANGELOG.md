# Changelog

PluginMatrix follows the version policy in `docs/VERSIONING.md`. No entry below implies that a Git tag, GitHub Release, or PyPI release exists. Earlier entries without dates were development milestones rather than formal releases.

## 0.7.1 - Unreleased

- Make the Windows standalone executable launch the local Web UI on an automatically selected loopback port when opened without command-line arguments, using a clear native error message when startup fails; explicit CLI subcommands remain unchanged.
- Add cached official Provider catalogs for available Minecraft versions and builds. The Web UI prefers live metadata, identifies fresh/stale cache fallback, safely refreshes corrupt regular cache files, and retains manual entry when metadata cannot be loaded.
- Discover installed Java runtimes and matching `javac`, show version and executable path, recommend the documented Java baseline for the selected Minecraft version, and retain an advanced manual executable field.
- Add a lightweight English and Simplified Chinese UI translation layer with a remembered language choice. Replace raw progress event names/JSON with user-facing progress and expandable technical details.
- Normalize Provider/result names and terminal task behavior. Completed, failed, and cancelled tasks no longer expose an actionable Cancel button, and cancellation is represented separately from successful task completion without changing verifier verdict semantics.

## 0.7.0 — 2026-09-14

- Add a loopback-only local Web UI for single and Matrix verification, local JAR import/path selection, dependencies, all existing Providers, Java/build/stability/concurrency controls, live progress, cancellation, results, and allowlisted report/log access.
- Keep verdicts in `application.run_single`/`run_matrix`; the UI does not parse logs, recompute PASS, or implement a second verifier. Configuration import/generation round-trips through the existing Matrix schema.
- Add Host/Origin/session/CSRF checks, strict request/body limits, escaped DOM rendering, bounded job/event history, a global eight-environment slot cap, immutable artifact fingerprints, and complete `RunControl` cancellation/draining.
- Add PyInstaller `onedir` builds for Windows x86-64, Linux x86-64, and macOS x86-64/arm64. Frozen CLI/Web UI launches system Java/Javac with restored platform library-search behavior and retains Web assets, Provider metadata, version/build provenance, project notices, the CPython license, and notices for bundled native libraries.
- Add a cross-platform standalone workflow that smoke-tests the frozen CLI, Provider registry, JDK access, Web resources, and one real Paper/probe/report/log path on every target without invoking the full Provider Gate or publishing a release.
- Keep pipx as the recommended developer/CI channel. Exact PyPI asset matching now ignores standalone `.tar.gz` release assets.

## 0.6.0 — 2026-09-14

- Introduce Server Provider contracts for official Paper, Purpur and experimental Folia, plus explicitly declared local/custom JAR runtime profiles; retain one Runtime Verifier.
- Preserve legacy Paper configuration/CLI/report keys. Reject mixed legacy/new fields and unknown configuration keys explicitly.
- Keep target identity, expected CodeSource, monotonically fresh probe samples and the full positive stability window. Add Folia global-region probe scheduling and `PLUGIN_UNSUPPORTED` declaration verdict.
- Add official host allowlists, bounded downloads, per-provider cache identity, OS locks and atomic checksum-verified publication. Record Purpur's upstream MD5 separately from the local SHA-256.
- Add init, validate, doctor, providers, static HTML report rendering, and application API with bounded progress events and cancellation.
- Add bounded Matrix parallelism (default 1, maximum 8), ordered reports, independent ports/artifacts, shared cancellation and complete worker/process-tree draining.
- Disable interactive server console and inherited stdin; raw log consumption remains strict. Add project-owned Folia fixtures and explicit provider gates outside offline test discovery.
- Stabilize Folia cold starts without relaxing PASS: withhold isolated early callbacks until a continuous two-second scheduler span, keep the host-side two-second freshness rule, and use the configured startup deadline while Folia completes world initialization. Finish a caught-up direct negative sample without waiting for an impossible enabled sample. Use a fixed empty-world seed for reproducible gates.
- Fail closed on malformed nested saved reports, normalize local server path aliases on Windows, preserve server-shutdown verdict precedence, and extend hosted gates to audit JSON, HTML, summaries, logs, runtime reports, progress events and artifact references.

The final GitHub release was built and verified from the tagged release commit. Its unchanged wheel and sdist were subsequently validated on TestPyPI and published to PyPI through GitHub Actions Trusted Publishing; the three channels carry byte-identical package assets. Validation results and limitations are tracked in docs/STATUS.md.

## 0.5.1 — 2026-09-13

This patch addresses verdict trust and safety defects found in the independent v0.5.0 review. It retains the existing Runtime Verifier, sequential Matrix, evidence and artifact architecture.

- Reject target/dependency filename, plugin-name, `provides` alias and runtime-probe conflicts before execution; record dependencies and verify copied JAR hashes.
- Require current-run probe schema, increasing sequence and timestamps, matching name/version/main/source, and fresh samples spanning the entire stability window before PASS. Preserve target disable events and identity failures. Zero stability is now a configuration error; old/custom probe snapshots are unsupported.
- Preserve raw log bytes; decode with replacement, bound log consumption and exit draining, and fail safely on read/cleanup errors. Other plugins' exceptions and missing dependencies no longer determine the target verdict.
- Assign suspended Windows children to a Job Object before execution and wait for job cleanup; terminate owned POSIX process groups with bounded cleanup. GitHub-hosted Linux and Windows validation passed.
- Protect input/report/cache/runtime paths, including hardlinks, symlinks and Windows junctions; use atomic report, cache-copy and download writes. A runtime-report failure preserves evidence and does not stop later Matrix environments.
- Bound JAR/descriptor/library sizes; reject duplicate entries, encryption, unsupported compression, ambiguous descriptors and unsafe library paths. Support inline comments and three-part `api-version` values. Unsupported YAML and dual descriptors fail explicitly.
- Harden workflow input/output paths and shell exit handling; execute workflow scripts in regression tests and add Windows/Linux Python 3.10/3.11 offline CI coverage.
- Record the still-public historical EnhancedFly JAR as an owner decision, separate from clean release-package contents. Do not modify v0.5.0 history, tag or Release.

GitHub-hosted CI passed on Ubuntu/Windows with Python 3.10/3.11. The hosted success and expected enable-failure Matrix runs preserved their summaries, reports, runtime evidence, raw logs and exit codes. The real Paper Release Gate passed on Paper 1.20.1/build 196/JDK 17 and Paper 1.21.4/build 232/JDK 21, including `.paper-remapped` identity, invalid UTF-8/noise and late-disable scenarios.

See `docs/V0.5.1_PREPARATION.md` and `docs/RELEASE_CHECKLIST.md` for the full verification record.

## 0.5.0 — 2026-09-12

- Prepared the repository for public source review without adding runtime-verification capability.
- Added governance, contribution, security, issue, pull-request, source-audit, versioning, and release-checklist documentation.
- Made `pluginmatrix.__version__` the packaging version source and expanded package metadata.
- Replaced the publicly stored EnhancedFly JAR and examples with repository-provided success and enable-failure fixtures whose source, descriptors, build method, and checksums are retained; the project owner confirmed their Apache-2.0 release rights for v0.5.0.
- Added offline release-readiness tests and clean sdist/wheel/install verification.

## 0.4.0 — Implemented, not formally released

- Added Matrix preflight checks for plugin metadata, Java/JDK availability, output paths, conflicts, and configuration diagnostics.
- Added direct failure-stage, reason, artifact, and primary-evidence output to Matrix CLI, Matrix Report, and GitHub Job Summary.
- Upgraded the official GitHub Actions to Node.js 24-compatible major versions.
- Hosted Matrix #3 passed on Paper 1.20.1/build 196/Java 17; Matrix #4 exercised a real owned `onEnable()` failure and retained artifacts. Both runs had zero Action deprecation warnings.

## 0.3.0 — Implemented, not formally released

- Added offline push/pull-request CI.
- Added a manual Java 17 Compatibility Matrix workflow that preserves report and runtime artifacts on success or failure.
- Added tested Job Summary rendering from the Matrix Report rather than duplicating verdict logic.

## 0.2.0 — Implemented, not formally released

- Added JSON-configured sequential Compatibility Matrix execution over one plugin JAR.
- Added full pre-execution config validation, isolated per-environment runs, a unified Matrix Report, and stable Matrix exit codes.

## 0.1.0 — Implemented, not formally released

- Added plugin-JAR preflight, Paper artifact resolution and checksum verification, isolated real Paper startup, Java validation, lifecycle evidence, runtime probe confirmation, raw `server.log`, and structured runtime reports.
- Defined stable verdicts that distinguish environment, server startup, plugin discovery, load, enable, disable, pass, and unknown failures.
