package pluginmatrix.fixture;

/** Declares Folia support but intentionally fails during enable. */
public final class FoliaEnableFailurePlugin extends org.bukkit.plugin.java.JavaPlugin {
    @Override
    public void onEnable() {
        throw new IllegalStateException("Intentional PluginMatrix Folia enable failure fixture");
    }
}
