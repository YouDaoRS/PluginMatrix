# Release checklists

## v0.8.0rc1 Release Candidate Gate - 2026-09-15

本次授权仅覆盖 `codex/v0.8-behavior-core` 的正常 commit/push、hosted CI 和 standalone RC 验证。禁止创建 tag、GitHub Release、PyPI 发布、修改 v0.7.1，或加入玩家 Bot、复杂 DSL、云服务和新 Provider。

- [x] 保持一个 Runtime Verifier 和现有 Provider；不重新设计 behavior 核心协议或降低 runtime/behavior evidence 要求。
- [x] 完成 Web behavior 配置、导入/导出/再次运行、双 verdict/最终结果、逐检查 evidence 与 English / 简体中文体验。
- [x] 对齐 CLI、application API、JSON、HTML、artifact、progress event、Matrix/GitHub summary 语义。
- [x] 补齐用户文档、可运行配置示例、PASS 边界、Folia 与 hostile-code 限制。
- [x] 验证旧 v0.7 legacy Paper 配置与无 behavior 配置兼容。
- [x] 单次重试 local Provider 行为 Gate；确认 9 个场景通过，首次失败属于外部 Mojang bootstrap 下载。
- [x] 完整本机离线测试（217 passed、8 skipped）、`compileall`、JavaScript syntax、`git diff --check` 和干净 package build。
- [ ] GitHub-hosted Ubuntu/Windows x Python 3.10/3.11 CI 全绿，包含 POSIX FIFO/symlink/process-group 与 Windows Job Object 覆盖。
- [ ] Windows x86-64、Linux x86-64、macOS x86-64、macOS arm64 standalone 全绿；冻结 CLI/Web 均完成真实 Paper runtime + wait behavior PASS 并保留 JSON/HTML/log/protocol evidence。
- [ ] 选择 RC commit，确认工作区干净、开发分支与 origin 同步，并判断是否可进入 v0.8 最终 Release Gate。

RC Gate 不包含最终 `0.8.0` 版本、tag、Release、签名/notarization、TestPyPI 或 PyPI。

## v0.7.1 Final Release Gate — completed 2026-09-14

Owner authorization covers the normal release commit, fast-forward merge to `main`, annotated `v0.7.1` tag, GitHub Release assets and the existing Trusted Publishing workflow. Force pushes, history rewriting, old Release changes, EnhancedFly history work and the next version remain excluded.

- [x] Preserve the existing Provider registry, Runtime Verifier and PASS semantics; add no Provider, cloud service or large UI rewrite.
- [x] Complete the v0.7.1 usability work: Windows double-click Web startup, official Provider version/build catalogs with bounded cache fallback, local Java/JDK discovery, English/Simplified Chinese UI, user-facing progress and correct terminal task controls.
- [x] Pass the local 192-test offline suite with 7 platform skips, compileall, JavaScript/DOM checks, archive audit and real desktop/mobile Web acceptance.
- [x] Pass candidate hosted CI on Ubuntu/Windows and Python 3.10/3.11 ([run 34846882967](https://github.com/YouDaoRS/PluginMatrix/actions/runs/34846882967)).
- [x] Pass candidate Windows/Linux/macOS x86-64/macOS arm64 standalone builds and frozen CLI/Web real Paper checks ([run 34845461889](https://github.com/YouDaoRS/PluginMatrix/actions/runs/34845461889), attempt 2). The first macOS x86-64 attempt failed only on transient Paper API DNS resolution and passed when rerun.
- [x] Set the authoritative version to `0.7.1`, date the changelog, and align README/status/versioning/tests with the final usability scope and unsigned standalone limitations.
- [x] Create and push release commit `49543d122fa3ec241f937e70b6d2cf1440705803`, fast-forward `main`, and pass final-commit hosted CI ([run 34854638499](https://github.com/YouDaoRS/PluginMatrix/actions/runs/34854638499)) before tagging.
- [x] Build and audit wheel, sdist and all four native standalone archives from the final release commit; verify version, provenance, licenses, Web language/catalog/Java smoke, Windows double-click startup, exclusions and SHA-256 ([run 34854638550](https://github.com/YouDaoRS/PluginMatrix/actions/runs/34854638550)).
- [x] Fresh-install the exact wheel and exercise venv, pipx, CLI/providers and loopback Web health before publication.
- [x] Create and push annotated `v0.7.1`, publish the verified assets and checksums in one [GitHub Release](https://github.com/YouDaoRS/PluginMatrix/releases/tag/v0.7.1), explicitly describing standalone packages as unsigned and not notarized.
- [x] Redownload every public GitHub Release asset, compare hashes and bytes, and install/smoke the public wheel and Windows standalone.
- [x] Publish the identical GitHub Release wheel/sdist through TestPyPI ([run 34858876724](https://github.com/YouDaoRS/PluginMatrix/actions/runs/34858876724)) and PyPI ([run 34858963676](https://github.com/YouDaoRS/PluginMatrix/actions/runs/34858963676)) using Trusted Publishing; compare public hashes and repeat isolated pipx/CLI/Web smoke.
- [x] Leave `main` clean and synchronized with origin without changing old tags, Releases or historical objects.

No code signing, MSI, notarization, auto-update, cloud service, new Provider or next-version work is part of this release.

## v0.7.0 Final Release Gate — completed 2026-09-14

Owner authorization covers the normal release commit, fast-forward merge to `main`, annotated `v0.7.0` tag, GitHub Release assets and existing Trusted Publishing workflow. Force pushes, history rewriting, old Release changes, EnhancedFly history work and v0.8 remain excluded.

- [x] Keep the Web UI on the application API and preserve one Runtime Verifier/verdict implementation.
- [x] Add loopback, Host/Origin/session/CSRF, bounded-input, injection, artifact allowlist and multi-task slot controls.
- [x] Route UI cancellation and service shutdown through `RunControl`, retaining complete JVM process-tree draining.
- [x] Add native PyInstaller `onedir` build/archive/audit scripts and a four-target hosted workflow without Java/server/plugin bundling or publication.
- [x] Pass Windows/Linux/macOS x86-64 and macOS arm64 frozen CLI/Web/JDK/real probe jobs from implementation commit `4d9e7e1` ([run 34825807071](https://github.com/YouDaoRS/PluginMatrix/actions/runs/34825807071)).
- [x] Complete independent Astra critical-path review of HTTP parsing/authentication, artifact TOCTOU handling, UI cancellation/shutdown, frozen subprocess environments and release-asset isolation.
- [x] Resolve HTTP and artifact findings in `a3969e9` and `73b4a16`; pass the final complete offline run with 186 tests and 7 local platform/permission skips.
- [x] Pass final hosted offline CI on Ubuntu/Windows and Python 3.10/3.11 at `d3aeecc` ([run 34831078163](https://github.com/YouDaoRS/PluginMatrix/actions/runs/34831078163)).
- [x] Audit actual hosted archives, identify incomplete Unix native-library notices, fix them in `d3aeecc`, and rerun all four native standalone targets plus combined checksums ([run 34831078226](https://github.com/YouDaoRS/PluginMatrix/actions/runs/34831078226)).
- [x] Verify frozen CLI/Web real Paper PASS, runtime probe, JSON/HTML/server.log, archive hashes, safe internal links, license/notice files and sensitive/runtime asset exclusions on all targets.
- [x] Build and audit clean candidate sdist/wheel, run `compileall` and `git diff --check`, confirm no untracked source, and record candidate hashes in `STATUS.md`.

- [x] Select `d3aeecc1b20d26b22ab9a9d75ff744d7a57a9b42` as the runtime/packaging code candidate and confirm `caeefd6` changes only RC documentation.
- [x] Set the authoritative version to `0.7.0`, date the changelog, and align README/status/versioning/tests with the final capability and unsigned standalone scope.
- [x] Create and push final release commit `2421a4213ca7cbbd8669926dc7fb365f8512913b`, fast-forward `main`, and pass final hosted CI ([run 34833821162](https://github.com/YouDaoRS/PluginMatrix/actions/runs/34833821162)) before tagging.
- [x] Build sdist/wheel from a clean final-commit archive and all four native standalone archives in [run 34833820926](https://github.com/YouDaoRS/PluginMatrix/actions/runs/34833820926); audit version, provenance, licenses, links, exclusions and SHA-256.
- [x] Fresh-install the exact wheel and exercise venv, pipx, CLI/providers and loopback Web health before publication.
- [x] Create and push annotated `v0.7.0`, publish the 11 verified assets and combined checksums in one [GitHub Release](https://github.com/YouDaoRS/PluginMatrix/releases/tag/v0.7.0), explicitly describing standalone packages as unsigned and not notarized.
- [x] Redownload every public GitHub Release asset, compare hashes and bytes, and install/smoke the public wheel.
- [x] Publish the identical GitHub Release wheel/sdist through TestPyPI ([run 34835141840](https://github.com/YouDaoRS/PluginMatrix/actions/runs/34835141840)) and PyPI ([run 34835387582](https://github.com/YouDaoRS/PluginMatrix/actions/runs/34835387582)); compare hashes and repeat isolated pipx/CLI/Web smoke.
- [x] Reconfirm v0.5.0/v0.5.1/v0.6.0 tags and Release assets are unchanged; leave `main` clean and synchronized with origin.

No code signing, MSI, notarization, auto-update, cloud service or v0.8 work is part of this release.

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

Final evidence and precise limitations: [STATUS.md](STATUS.md). GitHub Release was the original package publication channel for v0.6.0.

## v0.6.0 PyPI distribution extension — completed 2026-09-14

- [x] Fast-forward `main` by exactly eight commits to the v0.6.0 release commit; confirm the range contains no `build/`, `dist/`, wheel, cache or other generated artifacts, then push normally.
- [x] Confirm `pluginmatrix` has no existing PyPI/TestPyPI project, configure GitHub Environments and Pending Trusted Publishers without passwords or long-lived API tokens.
- [x] Add a manual OIDC publishing workflow that downloads the existing GitHub Release assets, verifies the release/tag commit, exact filenames, package identity/version and GitHub SHA-256 digests, and never rebuilds distributions.
- [x] Publish to TestPyPI, compare both uploaded hashes with GitHub Release, and validate isolated pipx installation, version, CLI, providers and upgrade behavior.
- [x] Obtain explicit owner confirmation of project name, version, asset hashes and Trusted Publisher configuration before approving the protected formal `pypi` deployment.
- [x] Publish the identical wheel and sdist to PyPI, verify hashes through the public API, and repeat isolated pipx installation and upgrade checks.
- [x] Keep GitHub Release as the source/assets/checksum channel and document a separate future namespace for standalone Windows/Linux/macOS assets.

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
