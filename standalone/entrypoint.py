from __future__ import annotations

import os
import sys
from pathlib import Path

from pluginmatrix.cli import main as cli_main


def _show_windows_error(message: str) -> None:
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, message, "PluginMatrix", 0x10)
    except (AttributeError, OSError):
        pass


def main(argv: list[str] | None = None, platform_name: str | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if (platform_name or os.name) == "nt" and not args:
        root = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "PluginMatrix"
        try:
            from pluginmatrix.web import serve
            open_browser = os.environ.get("PLUGINMATRIX_NO_BROWSER") != "1"
            return serve(port=0, open_browser=open_browser, state_dir=root / "web", cache_dir=root / "cache")
        except (OSError, ValueError) as exc:
            message = (
                "PluginMatrix could not start its local Web UI.\n\n"
                f"{exc}\n\n"
                "You can also open Command Prompt in this folder and run:\n"
                "pluginmatrix.exe web --port 0"
            )
            print(message, file=sys.stderr)
            _show_windows_error(message)
            return 2
    return cli_main(args)


if __name__ == "__main__":
    raise SystemExit(main())
