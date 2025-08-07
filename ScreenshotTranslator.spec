# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['F:\\Rrojects\\ScreenshotTranslator\\src\\main.py'],
    pathex=[],
    binaries=[],
    datas=[('F:\\Rrojects\\ScreenshotTranslator\\src\\ocr_icon.ico', '.'), ('F:\\Rrojects\\ScreenshotTranslator\\src\\settings.json', '.'), ('F:\\Rrojects\\ScreenshotTranslator\\src\\ocr_result.txt', '.')],
    hiddenimports=['pytesseract', 'PIL', 'requests', 'tkinter', 'ctypes', 'keyboard', 'json', 'keyboard'],
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
    a.binaries,
    a.datas,
    [],
    name='ScreenshotTranslator',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['F:\\Rrojects\\ScreenshotTranslator\\src\\ocr_icon.ico'],
)
