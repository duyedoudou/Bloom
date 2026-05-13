# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path


project_root = Path.cwd()
backend_dir = project_root / "backend"
frontend_dist = project_root / "frontend" / "dist"

datas = []
if frontend_dist.exists():
    datas.append((str(frontend_dist), "frontend/dist"))


a = Analysis(
    [str(backend_dir / "app" / "desktop_launcher.py")],
    pathex=[str(backend_dir)],
    binaries=[],
    datas=datas,
    hiddenimports=["email_validator"],
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
    name="Bloom",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    icon=str(project_root / "assets" / "app-icon.ico"),
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Bloom",
)
