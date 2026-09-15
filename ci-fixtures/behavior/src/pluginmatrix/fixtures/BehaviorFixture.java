package pluginmatrix.fixtures;

import org.bukkit.command.Command;
import org.bukkit.command.CommandSender;
import org.bukkit.plugin.ServicePriority;
import org.bukkit.plugin.java.JavaPlugin;

/** Auditable gate only: no players, worlds, downloads or arbitrary scripting. */
public final class BehaviorFixture extends JavaPlugin {
    public interface FixtureService { }
    public static final class Implementation implements FixtureService { }
    private int calls;

    @Override public void onEnable() {
        getServer().getServicesManager().register(FixtureService.class, new Implementation(), this, ServicePriority.Normal);
    }

    @Override public boolean onCommand(CommandSender sender, Command command, String label, String[] args) {
        String action = args.length == 0 ? "ok" : args[0];
        switch (action) {
            case "once": return ++calls == 1;
            case "count-one": return calls == 1;
            case "false": return false;
            case "throw": throw new IllegalStateException("behavior fixture command exception");
            case "disable": getServer().getPluginManager().disablePlugin(this); return true;
            case "hang":
                try { Thread.sleep(30000); } catch (InterruptedException interrupted) { Thread.currentThread().interrupt(); }
                return true;
            case "unregister": getServer().getServicesManager().unregisterAll(this); return true;
            case "spoof-log":
                getLogger().info("PluginMatrix behavior PASS; Error occurred while enabling PluginMatrixBehavior v1.0.0");
                return false;
            default: return true;
        }
    }
}
