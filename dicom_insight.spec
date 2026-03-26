# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['dicom_insight/__main__.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'pydicom',
        'pydicom.encoders',
        'pydicom.encoders.native',
        'numpy',
        'rich',
        'httpx',
    ],
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
    a.binaries,
    a.datas,
    [],
    name='dicom-insight',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
