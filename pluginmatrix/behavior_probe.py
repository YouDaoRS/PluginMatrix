"""Compile-time behavior allowlist for the existing server-side runtime probe."""
import json


def java_behavior(plan, run_id, regionized):
    if plan is None:
        return '', ''
    cases = []
    for index, check in enumerate(plan.to_dict()['checks']):
        kind = check['type']
        name = json.dumps(check.get('name', ''), ensure_ascii=True)
        if kind in ('command_registered', 'console_command'):
            body = f'''org.bukkit.command.PluginCommand command = getServer().getPluginCommand({name});
                boolean registered = command != null && command.isRegistered();
                boolean owned = registered && command.getPlugin() == targetPlugin;
                observation = "{{" + field("registered", registered) + "," + field("owned", owned)
                    + "," + field("owner", command == null ? "" : command.getPlugin().getName());'''
            if kind == 'console_command':
                args = ','.join(json.dumps(arg, ensure_ascii=True) for arg in check['args'])
                body += f'''
                if (!owned) {{ status = "ERROR"; reason = "command is missing or not owned by the target plugin"; }}
                else {{
                    org.bukkit.command.ConsoleCommandSender sender = getServer().getConsoleSender();
                    if (!command.testPermissionSilent(sender)) {{ status = "ERROR"; reason = "console permission denied"; }}
                    else {{
                        boolean returned = command.execute(sender, {name}, new String[] {{{args}}});
                        observation += "," + field("sender", "CONSOLE") + "," + field("returned", returned);
                    }}
                }}'''
            body += ' observation += "}";'
            if kind == 'console_command' and regionized:
                body = 'status = "UNSUPPORTED"; reason = "console commands have no safe region ownership contract on Folia";'
        elif kind == 'permission_registered':
            body = f'''org.bukkit.permissions.Permission permission = getServer().getPluginManager().getPermission({name});
                observation = "{{" + field("registered", permission != null) + ","
                    + field("default", permission == null ? "" : permission.getDefault().name()) + "}}";'''
        elif kind == 'service_registered':
            body = f'''StringBuilder registrations = new StringBuilder();
                int count = 0;
                for (org.bukkit.plugin.RegisteredServiceProvider<?> registration : getServer().getServicesManager().getRegistrations(targetPlugin)) {{
                    if (!registration.getService().getName().equals({name})) continue;
                    if (++count > 128) throw new IllegalStateException("more than 128 matching service registrations");
                    if (count > 1) registrations.append(",");
                    registrations.append("{{").append(field("owner", registration.getPlugin().getName())).append(",")
                        .append(field("service", registration.getService().getName())).append(",")
                        .append(field("implementation", registration.getProvider().getClass().getName())).append(",")
                        .append(field("priority", registration.getPriority().name())).append("}}");
                }}
                observation = "{{\\"registrations\\":[" + registrations + "]}}";'''
        else:
            body = 'status = "ERROR"; reason = "wait is a host operation";'
        cases.append(f'''case {index}: {{
                checkId = {json.dumps(check['id'])}; kind = {json.dumps(kind)};
                {body}
                break;
            }}''')
    source = r'''
    private int lastBehaviorIndex = -1;
    private String pendingBehaviorResponse = null;

    private static String quote(String value) { return "\"" + escape(value) + "\""; }
    private static String field(String key, String value) { return quote(key) + ":" + quote(value); }
    private static String field(String key, boolean value) { return quote(key) + ":" + value; }
    private static String bounded(String value) { return value.length() > 1024 ? value.substring(0, 1024) : value; }

    private void writeBehavior(Plugin targetPlugin) {
        Path folder = getDataFolder().getParentFile().toPath();
        Path response = folder.resolve("pluginmatrix-behavior-response.json");
        try {
            if (pendingBehaviorResponse == null) {
                Path request = folder.resolve("pluginmatrix-behavior-request.properties");
                if (!Files.isRegularFile(request, java.nio.file.LinkOption.NOFOLLOW_LINKS) || Files.size(request) > 1024) return;
                java.util.Properties properties = new java.util.Properties();
                try (java.io.InputStream input = Files.newInputStream(request)) { properties.load(input); }
                String requestId = properties.getProperty("request_id", "");
                int index = Integer.parseInt(properties.getProperty("index", "-1"));
                if (!requestId.matches("[a-f0-9]{32}") || index <= lastBehaviorIndex || index >= CHECK_COUNT) return;
                // Consume BEFORE execution. Publishing retries cannot re-execute side effects.
                lastBehaviorIndex = index;
                String status = "OK", reason = "", observation = "{}", checkId = "", kind = "";
                try {
                    if (targetPlugin == null || !targetPlugin.isEnabled() || disabled)
                        throw new IllegalStateException("target absent or disabled before behavior check");
                    switch (index) {
                        CHECK_CASES
                        default: throw new IllegalArgumentException("unknown check index");
                    }
                } catch (NoSuchMethodError | AbstractMethodError unsupported) {
                    status = "UNSUPPORTED"; reason = bounded(unsupported.toString());
                } catch (Exception exception) {
                    status = "ERROR"; reason = bounded(exception.toString());
                }
                pendingBehaviorResponse = "{" + field("probe", "pluginmatrix-behavior") + ",\"schema\":1,"
                    + field("run_id", RUN_ID) + "," + field("plan_sha256", PLAN_HASH) + ","
                    + field("request_id", requestId) + ",\"index\":" + index + ","
                    + field("check_id", checkId) + "," + field("type", kind) + ","
                    + field("status", status) + "," + field("reason", reason) + ",\"observation\":" + observation
                    + ",\"completed_at_ms\":" + System.currentTimeMillis() + "}";
            }
            Path temporary = response.resolveSibling(response.getFileName() + ".tmp");
            Files.write(temporary, pendingBehaviorResponse.getBytes("UTF-8"));
            try { Files.move(temporary, response, StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE); }
            catch (java.nio.file.AtomicMoveNotSupportedException ignored) {
                Files.move(temporary, response, StandardCopyOption.REPLACE_EXISTING);
            }
            pendingBehaviorResponse = null;
        } catch (java.nio.file.AccessDeniedException transientLock) {
            // Retry publishing cached evidence on the next callback, never the command.
        } catch (Exception exception) {
            getLogger().warning("Unable to exchange behavior evidence: " + exception);
        }
    }
'''
    source = source.replace('CHECK_COUNT', str(len(plan.to_dict()['checks'])))
    source = source.replace('RUN_ID', json.dumps(run_id)).replace('PLAN_HASH', json.dumps(plan.digest))
    source = source.replace('CHECK_CASES', '\n'.join(cases))
    return source, 'writeBehavior(plugin);'
