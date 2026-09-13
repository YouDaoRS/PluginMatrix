# Critical-path review of 395f435

Reviewed `codex/multi-server-core` at `395f4354c0a178c941290fc46fa7317e35a7b50b` against `v0.5.1`, including the complete change set, current implementation/tests, AGENTS.md, PRODUCT_SPEC.md, STATUS.md and ARCHITECTURE.md. The starting checkout was clean. This review makes local development changes only.

## Findings and fixes

| Priority | Reproduced problem | Fix |
| --- | --- | --- |
| P1 | Internal `verify(paper_jar=..., paper_metadata=...)` accepted an arbitrary JAR as official Paper, bypassed explicit local contracts and accepted caller-controlled build metadata used in bootstrap cache paths. | Reject this old override before Java or filesystem preparation. User-supplied JARs must use an explicit local ServerSpec; migrated the legacy real-Paper gate and copy-integrity regression. Official CLI/JSON Paper options remain supported. |
| P1 | HTML links resolved relative paths against the report directory, while overwrite protection resolved them against the working directory. A saved report could overwrite its plugin, server JAR or raw log; copied reports could overwrite referenced original Matrix JSON. | Use one report-relative path rule for protection and links, protect referenced JSON and runtime roots, and save programmatic Matrix paths as absolute paths. |
| P1 | Different Matrix runs could share and replace one HTML output despite separate JSON locks. A report could also replace a persistent `.lock` inode, defeating exclusion on POSIX. | Claim all explicit JSON/HTML destinations before starting single/Matrix runs, lock standalone HTML renders, reserve `.lock` destinations, check lock/input aliases and acquire multiple locks in deterministic order with immediate conflict failure. |
| P1 | A worker exception was inspected only after all futures completed, so siblings waiting for cancellation could prevent exception propagation indefinitely. | Inspect completed futures immediately, cancel siblings on escaped worker errors, and drain actual future completion before joining executor threads. Ordinary environment failures still continue siblings. |
| P1 | Ctrl+C during process-tree cleanup escaped the verifier; an interrupted Windows Job drain also discarded its handle before descendant termination was confirmed. | Retry interrupted cleanup and retain Job ownership until the drain finishes. Cancellation cannot become PASS. |
| P1 | Bootstrap cache copies used `atomic_copy`, which could open a FIFO indefinitely; checksum receipts were read without checking for regular files. Both paths run while holding shared cache locks. | Reject special files before copying/reading. Include a native POSIX FIFO regression and portable boundary tests. |
| P2 | Offline Matrix preflight accepted Folia dependencies lacking a support declaration, although execution later rejected them. | Apply the existing Folia dependency rule during offline preflight. Target unsupported remains `PLUGIN_UNSUPPORTED`; Folia PASS has no thread/region/gameplay safety meaning. |

The single Runtime Verifier remains intact. No success rule was relaxed: identity, CodeSource, current run ID, advancing timestamps/sequences, the two-second freshness bound, the complete stability window, raw log consumption, live server and successful cleanup remain required.

## Validation

- Windows / Python 3.11.9: `python -m unittest discover -s tests -v`: **155 tests, 152 passed, 3 skipped**, 39.729 seconds. The skips are two existing symlink permission tests and the new native POSIX FIFO test. Log: `.pluginmatrix/critical-review-offline-final.log`.
- Added 16 critical-path test methods, including 24 full-verifier subprocess scenarios across Paper/Purpur/Folia/local: success, wrong CodeSource, disable, enable failure, startup failure and timeout. These tests use local synthetic server processes; they are separate from the real JVM evidence below.
- Strengthened parallel cancellation to wait for a live grandchild in each of three environments before cancellation. Windows Job Object, suspended-start failure, real child-tree cleanup, cross-process lock exclusion/crash release, hardlink and junction checks ran successfully.
- Ran the new regressions in a temporary copy of the original `395f435` package. Reverting the implementation causes the defect assertions to fail; the original checkout was not reverted. Evidence: `.pluginmatrix/critical-review-reverted.log`.
- `python -m compileall -q pluginmatrix tests ci-fixtures/build_fixtures.py` and `git diff --check`: passed. Full offline discovery also runs the existing packaging/install checks.

## Fresh real-server evidence and remaining gate

The Windows JDK 21.0.12.1 Provider Gate produced **13/14 expected outcomes**. Paper 1.21.4/232, Purpur 1.21.4/2416 and Folia 1.21.4/6 each passed success and expected enable-failure scenarios. Folia unsupported was rejected before startup. Serial mixed Matrix passed 3/3; local passed with `official=false` and unchanged input SHA-256. Successful official servers used the expected isolated remapped CodeSource.

The three-worker mixed Matrix passed Paper and Purpur but returned `UNKNOWN_FAILURE` for Folia: `runtime probe stopped producing fresh evidence`. Its log shows world initialization continuing after `Done`; only the initial enabled sample reached the observer before the freshness deadline. This is a fail-closed result, not evidence of plugin incompatibility or a justified reason to weaken the two-second rule.

A targeted fixed-build rerun with the final report-lock/path code reproduced the Folia failure; Paper/Purpur again passed their complete windows, and local again passed. The scripts' process exit codes alone are not gate evidence: inspect the stored verdicts. No further retry was used to hide the failed gate.

Local evidence directories (generated, not committed):

- `C:\Users\11580\AppData\Local\Temp\pluginmatrix-06-gate-kzb11kbq`: initial full gate, `gate-summary.json`, per-server reports, serial/parallel Matrix, HTML, progress and raw logs.
- `C:\Users\11580\AppData\Local\Temp\pluginmatrix-critical-final-xdljbn0h`: final fixed-build `matrix.json/html`, `local.json/html`, config and isolated run artifacts. Folia log: `runs/run-1789313080-e73f555abc33/server.log`.

Handoff to GPT-5.6 Sol for ordinary review and Release Gate work is appropriate. **Release Gate is not passed**: investigate/reproduce the recurring Folia cold-start sampling stall, run fresh Linux/hosted Python 3.10/3.11 checks including POSIX group/FIFO/symlink tests, and rerun real official/legacy Paper gates from the eventual committed candidate. Existing historical v0.5.1 results do not satisfy these gates. No push, Tag, Release or PyPI publication was performed or authorized here.
