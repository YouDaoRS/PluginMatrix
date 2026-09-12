# Enable-failure fixture

This fixture is original PluginMatrix test code. It is intentionally minimal and throws a fixed `IllegalStateException` from `onEnable()` so the hosted Compatibility Matrix can exercise a real Paper `PLUGIN_ENABLE_FAILED` path.

The committed `PluginMatrixEnableFailure.jar` is compiled from the adjacent Java source with JDK 17 against the Paper 1.20.1/build 196 libraries already used by PluginMatrix. It is test-only and must not be installed on a production server.
