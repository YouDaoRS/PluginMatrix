import os
from pathlib import Path

ROOT = Path(SPECPATH).parent
datas = [(str(ROOT / "pluginmatrix" / "webui" / name), "pluginmatrix/webui")
         for name in ("index.html", "app.js", "style.css")]

a = Analysis(
    [str(ROOT / "standalone" / "entrypoint.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="pluginmatrix",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version=os.environ.get("PLUGINMATRIX_VERSION_FILE") or None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="pluginmatrix",
)
