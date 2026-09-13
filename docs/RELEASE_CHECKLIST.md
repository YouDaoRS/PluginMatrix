# v0.5.1 Final Release Gate

Preparation date: 2026-09-13. Baseline: v0.5.0 / `46b91b0b26e7d88d388df637cb07df2260932271`.

v0.5.1 is an unreleased verdict-trust and safety patch. On 2026-09-13 the owner authorized normal commits/pushes and hosted validation, followed by an annotated tag and GitHub Release only after all core gates pass. Preserve the existing v0.5.0 tag and assets. PyPI, history rewriting, remote deletion and v0.6 work are excluded.

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

## Required GitHub-hosted validation — pending

- [ ] Run the changed offline CI on `ubuntu-latest` and `windows-latest`, Python 3.10/3.11, against the candidate revision. Linux symlink tests must run, not skip.
- [ ] On GitHub Linux, confirm parent-first exit, live child/grandchild timeout, inherited/flooding stdout, SIGKILL group cleanup and no surviving runnable descendant. POSIX groups do not contain children deliberately calling setsid; no hostile-code sandbox is claimed.
- [ ] Execute manual Matrix success and expected enable-failure runs on the candidate revision; verify final exit codes, summaries and both uploaded artifacts. Old hosted runs are historical evidence only.
- [ ] On GitHub Linux, run `python tests/real_paper_gate.py --paper-jar <verified-Paper-1.20.1-196.jar> --cache <bootstrap-cache>` to validate raw-byte/noise/late-disable cases.
- [ ] Verify source identity on a Paper version using `.paper-remapped` with its required JDK; retain source/name/version/main evidence. The implementation fails closed on unrecognized source paths; this branch has not been tested on real Paper in this Windows/JDK 17 session.
- [ ] Confirm workflow path escaping, symlink escape rejection, protected `.ci` outputs and actual `if: always()` artifact uploads on hosted Linux.

## Owner decisions — pending

- [x] Owner explicitly deferred historical EnhancedFly JAR handling to a separate decision; retain facts and risks without claiming resolution. Current source/package exclusion does not erase historical objects.
- [x] Owner authorized v0.5.1 commit/push/hosted validation and conditional tag/Release after all core gates pass on 2026-09-13.
- [ ] Keep release notes precise about PASS, zero-window rejection, descriptor/probe restrictions and untested platform boundaries.

No PyPI/TestPyPI upload is part of this gate. After any separately authorized GitHub release, validate the exact wheel downloaded from that GitHub Release in a clean environment, compare SHA-256/metadata, and check both CLI entry points. Do not install from a public package index that this project has not published to.
