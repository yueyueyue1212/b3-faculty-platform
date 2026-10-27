# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller definition for the environment-free Windows demo package."""
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

backend_dir = Path(SPECPATH)
project_dir = backend_dir.parent
frontend_dist = project_dir / "frontend" / "dist"

datas = [(str(frontend_dist), "frontend/dist")]
datas += collect_data_files("jieba")

hiddenimports = [
    "multipart",
    "sqlalchemy.dialects.sqlite",
    "sqlalchemy.dialects.sqlite.pysqlite",
]
hiddenimports += collect_submodules("uvicorn")
hiddenimports += collect_submodules("app")

a = Analysis(
    ["portable_launcher.py"],
    pathex=[str(backend_dir)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "IPython",
        "PyQt5",
        "PySide6",
        "matplotlib",
        "pandas.tests",
        "numpy.tests",
        "pytest",
        "scipy",
        "tkinter",
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="B3Platform",
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
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="B3Platform",
)
