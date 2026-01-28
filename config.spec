# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_all

block_cipher = None
llvmlite_datas, llvmlite_binaries, llvmlite_hiddenimports = collect_all('llvmlite')

a = Analysis(
    ['src/main.py'],
    pathex=[],
    binaries=llvmlite_binaries,
    datas=[
        ('src/misc', 'misc'),
        ('src/native', 'native'),
        ('src/std', 'std'),
        ('src/libs', 'libs'),
    ] + llvmlite_datas,
    hiddenimports=[
        'oryon_interpreter'
    ] + llvmlite_hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    exclude_binaries=False,
    name='main',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
