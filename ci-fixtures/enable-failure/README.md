# Enable-failure fixture

This is original PluginMatrix test code. It intentionally throws a fixed `IllegalStateException` from `onEnable()` so a real Paper run reaches `PLUGIN_ENABLE_FAILED`.

`../PluginMatrixEnableFailure.jar` is built from the adjacent Java source and `plugin.yml` by `../build_fixtures.py`. It is test-only and must not be installed on a production server.
