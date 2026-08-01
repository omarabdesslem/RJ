# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_dynamic_libs


APP_NAME = "RJ"
BUNDLE_IDENTIFIER = "com.example.rj"


a = Analysis(
    ["rj.py"],
    pathex=[],
    binaries=collect_dynamic_libs("rawpy"),
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file="entitlements.mas.plist",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=APP_NAME,
)

app = BUNDLE(
    coll,
    name=f"{APP_NAME}.app",
    icon="assets/AppIcon.icns",
    bundle_identifier=BUNDLE_IDENTIFIER,
    info_plist={
        "CFBundleDisplayName": APP_NAME,
        "CFBundleName": APP_NAME,
        "CFBundleShortVersionString": "1.0.0",
        "CFBundleVersion": "1",
        "LSApplicationCategoryType": "public.app-category.photography",
        "LSMinimumSystemVersion": "13.0",
        "NSHumanReadableCopyright": "Copyright © 2026",
    },
)
