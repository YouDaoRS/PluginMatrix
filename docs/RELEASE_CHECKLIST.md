# Release checklists

## v0.6.0 Final Release Gate — completed 2026-09-14

Owner authorization covers the normal release commit/push, annotated `v0.6.0` tag and GitHub Release. PyPI, force pushes, history rewriting, old Release changes, EnhancedFly history work, v0.7 and GUI work remain excluded. The v0.5.0/v0.5.1 tags, releases and history remain unchanged.

- [x] Preserve one Runtime Verifier and v0.5.1 identity/freshness/stability/cleanup guarantees.
- [x] Implement Paper/Purpur/Folia/local Providers, mixed Matrix, CLI usability, HTML and application services.
- [x] Verify official sources, integrity metadata, separate cache namespaces, local input protection and concurrent atomic publication.
- [x] Keep default serial behavior, bounded parallelism, ordered results and cooperative cancellation with process-tree cleanup.
- [x] Add offline provider/CLI/HTML/injection/cache/concurrency/cancellation regression tests.
- [x] Real Windows JDK 21 Gate: Paper 1.21.4/232, Purpur 1.21.4/2416, Folia 1.21.4/6; success/enable failure, Folia unsupported, mixed parallelism 1/3, local JAR, remapped CodeSource, JSON/HTML/Summary/log artifacts.
- [x] Complete Astra critical-path review, resolve its P1/P2 findings, then perform the bounded ordinary review and Folia root-cause investigation.
- [x] Run fresh GitHub-hosted Linux/Windows Python 3.10/3.11 CI on the release candidate, including actual Linux symlink/hardlink/FIFO/path-alias/POSIX process-group coverage.
- [x] Run the real Provider Gate (`provider-gate.yml`) and legacy Paper Release Gate on GitHub-hosted runners; preserve all reports/logs/summaries on success and expected failure.
- [x] Resolve findings and select `30cbe2548c06e30dd8a12e93acaa7b20206f67b5` as the final code candidate; confirm Astra review commit `c2a42fe` is in its history.
- [x] Confirm CI and Provider Gate results resolve to the selected candidate SHA, with no untracked source/tests or release-blocking generated artifacts in the v0.5.1 diff.
- [x] Set the authoritative version to `0.6.0`, date the changelog, and align README/status/versioning documentation with the released capability.
- [x] Run the bounded offline release checks, `compileall`, packaging tests and `git diff --check`; do not repeat real Provider gates for version/documentation-only changes.
- [x] Require final-commit GitHub CI to pass before tagging.
- [x] Build sdist/wheel from clean final-commit source, inspect archives, METADATA, version, license, exclusions and SHA-256, then fresh-install the exact wheel for both CLI entry points.
- [x] Create and push annotated `v0.6.0`, publish the verified assets in one GitHub Release, redownload them publicly, match SHA-256 and install the public wheel in a new venv.
- [x] Reconfirm v0.5.0/v0.5.1 are unchanged and the release branch is clean and synchronized with origin.

Final evidence and precise limitations: [STATUS.md](STATUS.md). GitHub Release is the only package publication channel for v0.6.0.

## Historical v0.5.1 Final Release Gate

Preparation date: 2026-09-13. Baseline: v0.5.0 / `46b91b0b26e7d88d388df637cb07df2260932271`.

v0.5.1 is the released verdict-trust and safety patch. On 2026-09-13 the owner authorized normal commits/pushes and hosted validation, followed by the annotated tag and GitHub Release after all core gates passed. Preserve the existing v0.5.0 tag and assets. PyPI, history rewriting, remote deletion and v0.6 work are excluded.

## Local preparation

- [x] Review all existing uncommitted fixes against the independent Astra findings and preserve their useful changes.
- [x] Keep one Runtime Verifier, sequential Matrix and structured evidence/artifact contracts.
- [x] Cover input/identity conflicts, current-run probe identity/freshness/full-window requirements, invalid bytes and log errors, bounded process cleanup, report failures and ZIP/path/workflow boundaries.
- [x] Set the authoritative package version to `0.5.1`; label the changelog Unreleased and document tightened input semantics.
- [x] Run complete offline tests and compileall under Windows Python 3.10 and 3.11; record skips explicitly.
- [x] Run real Paper 1.20.1/build 196/JDK 17 success, enable failure, unrelated warning/invalid-byte success and late-disable scenarios.
- [x] Check representative regression tests against temporary reverted fixes; retain failure evidence.
- [x] Build sdist/wheel in a temporary source copy, inspect archive contents and metadata, and install the wheel in a clean environment for CLI smoke checks. Refresh the artifacts after documentation closeout; record final hashes outside the package.
- [x] Run `git diff --check`; keep generated artifacts, caches, virtual environments and JARs out of the patch/package.

Exact results and local evidence paths: [v0.5.1 preparation report](V0.5.1_PREPARATION.md). Rebuild from the final approved revision; these local artifacts are not an authorization to publish.

## Required GitHub-hosted validation — completed 2026-09-13

- [x] Run the changed offline CI on `ubuntu-latest` and `windows-latest`, Python 3.10/3.11, against candidate commit `7c643c695ff3daf239ad09c3906ddcd86f953027`. Linux symlink tests ran; no Linux skips were reported.
- [x] On GitHub Linux, confirm parent-first exit, live child/grandchild timeout, inherited/flooding stdout, SIGKILL group cleanup and no surviving runnable descendant. POSIX groups do not contain children deliberately calling setsid; no hostile-code sandbox is claimed.
- [x] Execute manual Matrix success (`34741724358`) and expected enable-failure (`34741725508`) runs; verify exit codes 0/1, summaries and both uploaded artifacts.
- [x] Run the real Paper gate (`34741726723`) on Paper 1.20.1/build 196/JDK 17 and Paper 1.21.4/build 232/JDK 21; success, enable failure, invalid UTF-8/noise and late-disable cases matched their expected verdicts.
- [x] Verify source identity on `.paper-remapped` with JDK 21; reports retained source/name/version/main evidence and passed closed-world identity checks.
- [x] Confirm workflow path escaping, symlink escape rejection, protected `.ci` outputs and actual `if: always()` artifact uploads on hosted Linux.

## Owner decisions — pending

- [x] Owner explicitly deferred historical EnhancedFly JAR handling to a separate decision; retain facts and risks without claiming resolution. Current source/package exclusion does not erase historical objects.
- [x] Owner authorized v0.5.1 commit/push/hosted validation and conditional tag/Release after all core gates pass on 2026-09-13.
- [x] Keep release notes precise about PASS, zero-window rejection, descriptor/probe restrictions and untested platform boundaries.

No PyPI/TestPyPI upload is part of this gate. After any separately authorized GitHub release, validate the exact wheel downloaded from that GitHub Release in a clean environment, compare SHA-256/metadata, and check both CLI entry points. Do not install from a public package index that this project has not published to.
