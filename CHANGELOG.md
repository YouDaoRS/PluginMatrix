# Changelog

PluginMatrix follows the version policy in `docs/VERSIONING.md`. No entry below implies that a Git tag, GitHub Release, or PyPI release exists. Earlier entries without dates were development milestones rather than formal releases.

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
