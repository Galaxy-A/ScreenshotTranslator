# -*- coding: utf-8 -*-
import os
import sys
import shutil
import subprocess
import traceback
import json
import platform
import ctypes
import winreg
from datetime import datetime
from pathlib import Path

def set_console_utf8():
    """设置控制台编码为UTF-8以支持中文显示"""
    if sys.platform == 'win32':
        os.system('chcp 65001 > nul')
        try:
            LF_FACESIZE = 32
            STD_OUTPUT_HANDLE = -11

            class COORD(ctypes.Structure):
                _fields_ = [("X", ctypes.c_short), ("Y", ctypes.c_short)]

            class CONSOLE_FONT_INFOEX(ctypes.Structure):
                _fields_ = [("cbSize", ctypes.c_ulong),
                            ("nFont", ctypes.c_ulong),
                            ("dwFontSize", COORD),
                            ("FontFamily", ctypes.c_uint),
                            ("FontWeight", ctypes.c_uint),
                            ("FaceName", ctypes.c_wchar * LF_FACESIZE)]

            font = CONSOLE_FONT_INFOEX()
            font.cbSize = ctypes.sizeof(CONSOLE_FONT_INFOEX)
            font.nFont = 12
            font.dwFontSize.X = 8
            font.dwFontSize.Y = 16
            font.FontFamily = 54
            font.FontWeight = 400
            font.FaceName = "Consolas"

            handle = ctypes.windll.kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
            ctypes.windll.kernel32.SetCurrentConsoleFontEx(
                handle, ctypes.c_long(False), ctypes.pointer(font))
        except Exception:
            pass

def get_python_install_dir():
    """获取Python安装目录"""
    try:
        version = f"{sys.version_info.major}.{sys.version_info.minor}"
        key_path = rf"SOFTWARE\Python\PythonCore\{version}\InstallPath"

        # 尝试64位注册表
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
                path, _ = winreg.QueryValueEx(key, "")
                return Path(path)
        except FileNotFoundError:
            pass

        # 尝试32位注册表
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path,
                                access=winreg.KEY_READ | winreg.KEY_WOW64_32KEY) as key:
                path, _ = winreg.QueryValueEx(key, "")
                return Path(path)
        except FileNotFoundError:
            pass

    except Exception as e:
        print(f"注册表查询失败: {str(e)}")

    return Path(sys.base_prefix)

def ensure_tkinter_dependencies(temp_dir):
    """确保Tkinter依赖文件存在并复制到临时目录"""
    print("正在准备Tkinter依赖文件...")

    python_dir = get_python_install_dir()
    print(f"Python安装目录: {python_dir}")

    # 需要的关键文件
    required_files = {
        "_tkinter.pyd": python_dir / "DLLs" / "_tkinter.pyd",
        "tcl86t.dll": python_dir / "DLLs" / "tcl86t.dll",
        "tk86t.dll": python_dir / "DLLs" / "tk86t.dll",
        "tcl": python_dir / "tcl",
        "tk": python_dir / "tk"
    }

    # 复制文件到临时目录
    for name, source_path in required_files.items():
        if source_path.exists():
            if source_path.is_dir():
                dest_dir = temp_dir / name
                if dest_dir.exists():
                    shutil.rmtree(dest_dir)
                shutil.copytree(source_path, dest_dir)
                print(f"已复制目录: {name}")
            else:
                dest_path = temp_dir / name
                shutil.copy2(source_path, dest_path)
                print(f"已复制文件: {name}")
        else:
            print(f"警告: 未找到 {name} 在 {source_path}")

    return temp_dir

def ensure_python_dll(temp_dir):
    """确保Python DLL文件存在并复制到临时目录"""
    print("正在准备Python DLL文件...")

    python_dir = get_python_install_dir()

    # 可能的Python DLL名称
    dll_patterns = [
        f"python{sys.version_info.major}{sys.version_info.minor}.dll",
        f"python{sys.version_info.major}.dll",
        "python3.dll"
    ]

    # 在Python安装目录查找
    for pattern in dll_patterns:
        dll_path = python_dir / pattern
        if dll_path.exists():
            shutil.copy2(dll_path, temp_dir / dll_path.name)
            print(f"已复制Python DLL: {dll_path.name}")
            return temp_dir / dll_path.name

    # 在DLLs子目录查找
    dlls_dir = python_dir / "DLLs"
    if dlls_dir.exists():
        for pattern in dll_patterns:
            for path in dlls_dir.glob(pattern):
                shutil.copy2(path, temp_dir / path.name)
                print(f"已复制Python DLL: {path.name}")
                return temp_dir / path.name

    print("错误: 无法找到Python DLL文件!")
    return None

def ensure_vc_redist_files(temp_dir):
    """确保VC++ Redistributable文件存在并复制到临时目录"""
    print("正在准备VC++ Redistributable文件...")

    # 需要复制的DLL文件
    required_dlls = [
        "vcruntime140.dll",
        "vcruntime140_1.dll",
        "msvcp140.dll",
        "concrt140.dll",
        "ucrtbase.dll"
    ]

    # 尝试从系统目录复制
    system_dirs = [
        os.environ['SystemRoot'] + r'\System32',
        os.environ['SystemRoot'] + r'\SysWOW64'
    ]

    all_copied = True

    for dll in required_dlls:
        dest_path = temp_dir / dll
        if dest_path.exists():
            continue

        copied = False
        for sys_dir in system_dirs:
            src_path = os.path.join(sys_dir, dll)
            if os.path.exists(src_path):
                shutil.copy2(src_path, dest_path)
                print(f"已从系统目录复制: {dll}")
                copied = True
                break

        if not copied:
            print(f"警告: 未找到 {dll} 在系统目录")
            all_copied = False

    return all_copied

def ensure_pillow_dependencies(temp_dir):
    """确保Pillow相关依赖文件"""
    print("正在准备Pillow依赖文件...")

    python_dir = get_python_install_dir()
    dlls_dir = python_dir / "DLLs"

    # Pillow可能需要的DLL
    pillow_dlls = [
        "libjpeg-9.dll",
        "libpng16-16.dll",
        "libtiff-5.dll",
        "libwebp-7.dll",
        "zlib1.dll"
    ]

    for dll in pillow_dlls:
        src_path = dlls_dir / dll
        if src_path.exists():
            shutil.copy2(src_path, temp_dir / dll)
            print(f"已复制Pillow DLL: {dll}")
        else:
            print(f"警告: 未找到Pillow依赖 {dll}")

def ensure_keyboard_dependencies(temp_dir):
    """确保keyboard模块依赖"""
    print("正在准备keyboard模块依赖...")

    try:
        import keyboard
        # keyboard模块可能需要的一些特殊处理
        print("已处理keyboard模块依赖")
    except Exception as e:
        print(f"处理keyboard模块依赖时出错: {str(e)}")

def ensure_openai_dependencies(temp_dir):
    """确保openai模块依赖"""
    print("正在准备openai模块依赖...")

    try:
        import openai
        # openai模块可能需要的一些特殊处理
        print("已处理openai模块依赖")
    except Exception as e:
        print(f"处理openai模块依赖时出错: {str(e)}")

def create_hook_tkinter(base_path):
    """创建hook-tkinter.py文件"""
    hook_content = """from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

# 收集Tkinter数据文件
datas = collect_data_files('tkinter')

# 收集Tkinter动态库
binaries = collect_dynamic_libs('tkinter')
"""
    hook_file = base_path / "hook-tkinter.py"
    with open(hook_file, "w", encoding="utf-8") as f:
        f.write(hook_content)
    return hook_file

def create_hook_pytesseract(base_path):
    """创建hook-pytesseract.py文件"""
    hook_content = """from PyInstaller.utils.hooks import collect_data_files

# 收集pytesseract数据文件
datas = collect_data_files('pytesseract')
"""
    hook_file = base_path / "hook-pytesseract.py"
    with open(hook_file, "w", encoding="utf-8") as f:
        f.write(hook_content)
    return hook_file

def create_spec_file(base_path, src_path, temp_deps_dir):
    """创建.spec文件避免长命令行问题"""
    print("正在创建.spec文件...")

    # 资源文件列表
    resources = [
        (str(src_path / "ocr_icon.ico"), '.'),
        (str(src_path / "settings.json"), '.'),
        (str(src_path / "ocr_result.txt"), '.'),
        (str(src_path / "screenshot.png"), '.'),
    ]

    # 添加Tcl/Tk目录
    tcl_dir = temp_deps_dir / "tcl"
    tk_dir = temp_deps_dir / "tk"
    if tcl_dir.exists():
        resources.append((str(tcl_dir), 'tcl'))
        print(f"添加tcl目录到spec文件: {tcl_dir}")
    if tk_dir.exists():
        resources.append((str(tk_dir), 'tk'))
        print(f"添加tk目录到spec文件: {tk_dir}")

    # 二进制依赖文件列表
    binaries = []

    # 添加所有DLL文件
    for dll_file in temp_deps_dir.glob("*.dll"):
        binaries.append((str(dll_file), '.'))
        print(f"添加DLL到spec文件: {dll_file.name}")

    # 添加所有Pyd文件
    for pyd_file in temp_deps_dir.glob("*.pyd"):
        binaries.append((str(pyd_file), '.'))
        print(f"添加Pyd到spec文件: {pyd_file.name}")

    # 构建spec文件内容
    spec_content = f"""# -*- mode: python ; coding: utf-8 -*-
block_cipher = None

a = Analysis(
    ['{src_path / "main.py"}'],
    pathex=[],
    binaries={binaries},
    datas={resources},
    hiddenimports=[
        'pytesseract', 'PIL', 'PIL.Image', 'PIL.ImageOps', 'PIL.ImageEnhance',
        'requests', 'tkinter', 'tkinter.ttk', 'ctypes', 
        'keyboard', 'json', 'logging', 'logging.handlers',
        '_tkinter', 'threading', 'time', 'socket', 're',
        'openai', 'pytesseract', 'screen_capture', 'ocr_engine',
        'result_window', 'settings_window', 'translation',
        'pkg_resources.py2_warn', 'pkg_resources.markers'
    ],
    hookspath=['.'],
    hooksconfig={{}},
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
    icon='{str(src_path / "ocr_icon.ico")}',
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
"""
    spec_file = base_path / "ScreenshotTranslator.spec"
    with open(spec_file, "w", encoding="utf-8") as f:
        f.write(spec_content)

    return spec_file

def main():
    set_console_utf8()
    print("="*50)
    print("截图翻译工具打包流程 - 完整依赖版")
    print("="*50)

    try:
        # 1. 设置基本路径
        base_path = Path(__file__).parent.resolve()
        src_path = base_path / "src"
        dist_path = base_path / "dist"
        build_path = base_path / "build"
        temp_deps_dir = base_path / "temp_deps"

        print(f"项目根目录: {base_path}")
        print(f"源代码目录: {src_path}")

        # 2. 清理旧构建
        print("[步骤 1/10] 清理旧构建文件...")
        for folder in [build_path, dist_path, temp_deps_dir]:
            if folder.exists():
                print(f"删除目录: {folder}")
                shutil.rmtree(folder, ignore_errors=True)

        # 创建临时目录
        temp_deps_dir.mkdir(exist_ok=True)

        # 删除旧的.spec文件
        spec_file = base_path / "ScreenshotTranslator.spec"
        if spec_file.exists():
            print(f"删除文件: {spec_file}")
            spec_file.unlink()

        print("清理完成!")

        # 3. 准备资源文件
        print("[步骤 2/10] 准备资源文件...")

        # 确保必要的资源文件存在
        resources = {
            "ocr_icon.ico": src_path / "ocr_icon.ico",
            "settings.json": src_path / "settings.json",
            "ocr_result.txt": src_path / "ocr_result.txt",
            "screenshot.png": src_path / "screenshot.png",
        }

        # 创建默认设置文件（如果不存在）
        default_settings = {
            "ocr_config": {
                "language": "chi_sim+eng",
                "psm": "3",
                "oem": "3"
            },
            "offset": {
                "horizontal": 0,
                "vertical": 0
            },
            "tesseract_path": r'C:\Program Files\Tesseract-OCR\tesseract.exe',
            "tessdata_path": r'C:\Program Files\Tesseract-OCR\tessdata',
            "deepseek_api_key": "",
            "deepseek_model": "deepseek-chat",
            "preprocessing": {
                "grayscale": True,
                "invert": False,
                "threshold": 0
            },
            "hide_window_on_capture": False,
            "hotkey": "ctrl+alt+s"
        }

        for name, path in resources.items():
            if not path.exists():
                print(f"创建占位文件: {name}")
                if name == "settings.json":
                    with open(path, "w", encoding="utf-8") as f:
                        json.dump(default_settings, f, indent=2, ensure_ascii=False)
                elif name == "screenshot.png":
                    try:
                        from PIL import Image
                        img = Image.new('RGB', (100, 100), color=(73, 109, 137))
                        img.save(path)
                        print(f"已创建示例图片: {name}")
                    except ImportError:
                        with open(path, "wb") as f:
                            f.write(b"")
                        print(f"已创建空文件: {name}")
                else:
                    with open(path, "w", encoding="utf-8") as f:
                        f.write("")

        # 4. 准备依赖文件
        print("[步骤 3/10] 准备Tkinter依赖文件...")
        ensure_tkinter_dependencies(temp_deps_dir)

        print("[步骤 4/10] 准备Python DLL文件...")
        python_dll = ensure_python_dll(temp_deps_dir)
        if not python_dll or not python_dll.exists():
            print("错误: Python DLL文件缺失，无法继续!")
            return False

        print("[步骤 5/10] 准备VC++运行时文件...")
        vc_redist_ready = ensure_vc_redist_files(temp_deps_dir)
        if not vc_redist_ready:
            print("警告: 部分VC++运行时文件缺失，程序可能无法运行!")

        print("[步骤 6/10] 准备Pillow依赖文件...")
        ensure_pillow_dependencies(temp_deps_dir)

        print("[步骤 7/10] 准备keyboard模块依赖...")
        ensure_keyboard_dependencies(temp_deps_dir)

        print("[步骤 8/10] 准备openai模块依赖...")
        ensure_openai_dependencies(temp_deps_dir)

        # 9. 创建hook文件
        print("[步骤 9/10] 创建hook文件...")
        create_hook_tkinter(base_path)
        create_hook_pytesseract(base_path)

        # 10. 创建.spec文件
        print("[步骤 10/10] 创建.spec文件...")
        spec_file = create_spec_file(base_path, src_path, temp_deps_dir)
        print(f"已创建spec文件: {spec_file}")

        # 执行打包
        print("运行PyInstaller打包...")
        command = [
            sys.executable,
            "-m", "PyInstaller",
            str(spec_file),
            "--clean",
            "--noconfirm"
        ]
        print("执行命令: " + " ".join(command))

        # 使用subprocess.run执行PyInstaller
        log_file_path = base_path / "build_log.txt"
        with open(log_file_path, "w", encoding="utf-8") as log_file:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='replace'
            )

            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    try:
                        print(output.strip())
                    except UnicodeEncodeError:
                        print(output.strip().encode('gbk', errors='replace').decode('gbk'))
                    log_file.write(output)

        return_code = process.poll()

        # 验证结果
        print("验证打包结果...")
        exe_path = dist_path / "ScreenshotTranslator.exe"
        if return_code == 0 and exe_path.exists():
            # 复制资源文件到dist目录
            for name, path in resources.items():
                if path.exists():
                    dest_path = dist_path / name
                    shutil.copy2(path, dest_path)
                    print(f"已复制资源文件: {name}")

            # 创建版本信息文件
            version_file = dist_path / "build_info.txt"
            with open(version_file, "w", encoding="utf-8") as f:
                f.write(f"构建时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Python版本: {sys.version}\n")
                f.write(f"操作系统: {platform.platform()}\n")
                f.write(f"系统架构: {platform.architecture()[0]}\n")
                f.write(f"基础Python目录: {get_python_install_dir()}\n")
                f.write(f"使用命令: {' '.join(command)}\n")

            # 创建Tesseract-OCR提示文件
            tesseract_note = dist_path / "TESSERACT_安装说明.txt"
            with open(tesseract_note, "w", encoding="utf-8") as f:
                f.write("""重要提示：Tesseract-OCR 安装说明

本程序需要 Tesseract-OCR 才能正常工作。请按以下步骤安装：

1. 下载 Tesseract-OCR 安装程序：
   https://github.com/UB-Mannheim/tesseract/wiki

2. 运行安装程序，在安装过程中：
   - 选择 "Additional language data" 并勾选中文包 (chi_sim)
   - 确保勾选 "Add Tesseract-OCR to PATH" 选项

3. 安装完成后，启动程序并在设置中：
   - 检查 Tesseract 路径是否自动检测到
   - 如果没有，手动设置路径为：
     C:\\Program Files\\Tesseract-OCR\\tesseract.exe

4. 重启程序后即可正常使用 OCR 功能
""")

            print(f"\n{'='*50}")
            print(f"打包成功! 可执行文件路径: {exe_path}")
            print(f"文件大小: {os.path.getsize(exe_path)/1024/1024:.2f} MB")
            print(f"日志文件: {log_file_path}")
            print(f"{'='*50}")

            # 询问是否测试应用程序
            print("\n是否要测试应用程序? (y/n): ", end='', flush=True)
            test_app = sys.stdin.readline().strip().lower()
            if test_app == 'y':
                print("正在启动应用程序...")
                try:
                    subprocess.Popen([str(exe_path)], cwd=dist_path)
                except Exception as e:
                    print(f"启动应用程序失败: {str(e)}")

            return True
        else:
            print(f"\n{'='*50}")
            print("打包失败!")
            print(f"PyInstaller退出代码: {return_code}")
            print(f"可执行文件存在: {'是' if exe_path.exists() else '否'}")
            print(f"详细日志: {log_file_path}")
            print(f"{'='*50}")
            return False

    except Exception as e:
        print(f"打包过程中出错: {str(e)}")
        print(traceback.format_exc())
        return False
    finally:
        # 清理临时文件
        print("清理临时文件...")
        if temp_deps_dir.exists():
            print(f"删除临时目录: {temp_deps_dir}")
            shutil.rmtree(temp_deps_dir, ignore_errors=True)
        hook_file = base_path / "hook-tkinter.py"
        if hook_file.exists():
            print(f"删除hook文件: {hook_file}")
            hook_file.unlink()
        hook_file = base_path / "hook-pytesseract.py"
        if hook_file.exists():
            print(f"删除hook文件: {hook_file}")
            hook_file.unlink()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)