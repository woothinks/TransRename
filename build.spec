# -*- mode: python -*-
block_cipher = None

a = Analysis(
    ['TransRename.py'],
    pathex=['d:\\Trea\\Code\\TransRename'],
    binaries=[],
    datas=[
        # 修改为动态路径处理
        (os.path.join(os.getcwd(), 'config'), 'config') if os.path.exists('config') else ('', 'config'),
    ],
    hiddenimports=[
        'requests',
        'tqdm',
        'collections.abc'
    ],
    hookspath=[],
    hooksconfig={},
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
    name='TransRename',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # 必须启用控制台才能使用input()
    icon=None,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)