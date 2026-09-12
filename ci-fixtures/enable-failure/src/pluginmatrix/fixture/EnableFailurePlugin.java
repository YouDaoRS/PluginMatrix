package pluginmatrix.fixture;

import org.bukkit.plugin.java.JavaPlugin;

public final class EnableFailurePlugin extends JavaPlugin {
    @Override
    public void onEnable() {
        throw new IllegalStateException("Intentional PluginMatrix enable failure fixture");
    }
}
