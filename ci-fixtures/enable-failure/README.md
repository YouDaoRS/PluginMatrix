# Enable-failure fixture

This repository source intentionally throws a fixed `IllegalStateException` from `onEnable()` so a real Paper run reaches `PLUGIN_ENABLE_FAILED`.

`../PluginMatrixEnableFailure.jar` is built from the adjacent Java source and `plugin.yml` by `../build_fixtures.py`. It is test-only and must not be installed on a production server.

Repository provenance is documented in `../README.md`; the project owner confirmed Apache-2.0 release rights for v0.5.0.
