package pluginmatrix.fixture;

/** Project-owned acceptance fixture. It makes no region/thread-safety claim. */
public final class FoliaSuccessPlugin extends org.bukkit.plugin.java.JavaPlugin {
    @Override
    public void onEnable() {
        getLogger().info("PluginMatrix Folia acceptance fixture enabled");
    }
}
