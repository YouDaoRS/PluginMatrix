package pluginmatrix.fixture;

/** Deliberately omits folia-supported from its descriptor. */
public final class FoliaUnsupportedPlugin extends org.bukkit.plugin.java.JavaPlugin {
    @Override
    public void onEnable() {
        getLogger().info("PluginMatrix unsupported fixture unexpectedly accepted");
    }
}
