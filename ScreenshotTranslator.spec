# -*- mode: python ; coding: utf-8 -*-
block_cipher = None

a = Analysis(
    ['F:\Rrojects\ScreenshotTranslator\src\main.py'],
    pathex=[],
    binaries=[('F:\\Rrojects\\ScreenshotTranslator\\temp_deps\\concrt140.dll', '.'), ('F:\\Rrojects\\ScreenshotTranslator\\temp_deps\\msvcp140.dll', '.'), ('F:\\Rrojects\\ScreenshotTranslator\\temp_deps\\python312.dll', '.'), ('F:\\Rrojects\\ScreenshotTranslator\\temp_deps\\tcl86t.dll', '.'), ('F:\\Rrojects\\ScreenshotTranslator\\temp_deps\\tk86t.dll', '.'), ('F:\\Rrojects\\ScreenshotTranslator\\temp_deps\\ucrtbase.dll', '.'), ('F:\\Rrojects\\ScreenshotTranslator\\temp_deps\\vcruntime140.dll', '.'), ('F:\\Rrojects\\ScreenshotTranslator\\temp_deps\\vcruntime140_1.dll', '.'), ('F:\\Rrojects\\ScreenshotTranslator\\temp_deps\\zlib1.dll', '.'), ('F:\\Rrojects\\ScreenshotTranslator\\temp_deps\\_tkinter.pyd', '.')],
    datas=[('F:\\Rrojects\\ScreenshotTranslator\\src\\ocr_icon.ico', '.'), ('F:\\Rrojects\\ScreenshotTranslator\\src\\settings.json', '.'), ('F:\\Rrojects\\ScreenshotTranslator\\src\\ocr_result.txt', '.'), ('F:\\Rrojects\\ScreenshotTranslator\\src\\screenshot.png', '.'), ('F:\\Rrojects\\ScreenshotTranslator\\temp_deps\\tcl', 'tcl')],
    hiddenimports=[
        'pytesseract', 'PIL', 'PIL.Image', 'PIL.ImageOps', 'PIL.ImageEnhance',
        'requests', 'tkinter', 'tkinter.ttk', 'ctypes', 
        'keyboard', 'json', 'logging', 'logging.handlers',
        '_tkinter', 'threading', 'time', 'socket', 're',
        'openai', 'pytesseract', 'screen_capture', 'ocr_engine',
        'result_window', 'translation', 'config', 'error_handler',
        'performance', 'async_processor', 'advanced_cache', 'advanced_ui',
        'smart_ocr', 'pkg_resources.py2_warn', 'pkg_resources.markers'
    ],
    hookspath=['.'],
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
    [],
    exclude_binaries=True,
    name='ScreenshotTranslator',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='F:\Rrojects\ScreenshotTranslator\src\ocr_icon.ico',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name='ScreenshotTranslator',
)
