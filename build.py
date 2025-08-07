import os
import sys
import shutil
import subprocess
import traceback
from pathlib import Path

def main():
    print("="*50)
    print("Starting packaging process for Screenshot Translator...")
    print("="*50)

    try:
        # 1. 设置基本路径
        base_path = Path(__file__).parent.resolve()
        src_path = base_path / "src"
        dist_path = base_path / "dist"
        build_path = base_path / "build"

        print(f"Base path: {base_path}")
        print(f"Source path: {src_path}")

        # 2. 清理旧构建
        print("[Step 1/5] Cleaning old builds...")
        for folder in [build_path, dist_path]:
            if folder.exists():
                print(f"Removing {folder}")
                shutil.rmtree(folder, ignore_errors=True)

        spec_file = base_path / "ScreenshotTranslator.spec"
        if spec_file.exists():
            print(f"Removing {spec_file}")
            spec_file.unlink()

        print("Cleanup complete!")

        # 3. 准备打包选项
        print("[Step 2/5] Preparing packaging options...")

        # 确保资源文件存在
        resources = {
            "ocr_icon.ico": src_path / "ocr_icon.ico",
            "settings.json": src_path / "settings.json",
            "ocr_result.txt": src_path / "ocr_result.txt",
        }

        # 检查并创建缺失的文件
        for name, path in resources.items():
            if not path.exists():
                print(f"Creating placeholder: {name}")
                with open(path, "w") as f:
                    if name == "settings.json":
                        f.write('{"hotkey": "ctrl+alt+s"}')
                    else:
                        f.write("")

        # 准备PyInstaller选项
        options = [
            str(src_path / "main.py"),
            '--onefile',
            '--windowed',
            '--name=ScreenshotTranslator',
            f'--icon={str(src_path / "ocr_icon.ico")}',
            f'--add-data={str(src_path / "ocr_icon.ico")};.',
            f'--add-data={str(src_path / "settings.json")};.',
            f'--add-data={str(src_path / "ocr_result.txt")};.',
            '--hidden-import=pytesseract',
            '--hidden-import=PIL',
            '--hidden-import=requests',
            '--hidden-import=tkinter',
            '--hidden-import=ctypes',
            '--hidden-import=keyboard',
            '--hidden-import=json',
            '--hidden-import=keyboard',
            '--clean',
            '--noconfirm',
            '--noupx'
        ]

        # 4. 添加必要的 DLL（Windows 特定）
        if sys.platform == 'win32':
            print("[Step 3/5] Adding Windows DLLs...")
            python_dir = Path(sys.executable).parent
            dlls = [
                ('_tkinter.pyd', '.'),
                ('tcl86t.dll', '.'),
                ('tk86t.dll', '.'),
                ('vcruntime140.dll', '.'),
                ('vcruntime140_1.dll', '.'),
                ('msvcp140.dll', '.')
            ]

            for dll, dest in dlls:
                dll_path = python_dir / "DLLs" / dll
                if dll_path.exists():
                    options.append(f'--add-binary={str(dll_path)};{dest}')
                    print(f"Added DLL: {dll} -> {dest}")
                else:
                    print(f"Warning: DLL not found {dll_path}")

        # 5. 执行打包
        print("[Step 4/5] Running PyInstaller...")
        print("Command: pyinstaller " + " ".join(options))

        # 使用subprocess.run执行PyInstaller
        result = subprocess.run(
            ["pyinstaller"] + options,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='replace'
        )

        # 输出日志
        with open(base_path / "build_log.txt", "w", encoding="utf-8") as log_file:
            log_file.write("===== STDOUT =====\n")
            log_file.write(result.stdout)
            log_file.write("\n===== STDERR =====\n")
            log_file.write(result.stderr)

        # 6. 验证结果
        print("[Step 5/5] Verifying build result...")
        exe_path = dist_path / "ScreenshotTranslator.exe"

        if exe_path.exists():
            # 复制资源文件到dist目录
            for name, path in resources.items():
                if path.exists():
                    shutil.copy(path, dist_path / name)

            print(f"Packaging successful! Executable: {exe_path}")
            print(f"File size: {os.path.getsize(exe_path)/1024/1024:.2f} MB")

            # 创建Tesseract-OCR提示文件
            tesseract_note = dist_path / "TESSERACT_INSTALLATION.txt"
            with open(tesseract_note, "w") as f:
                f.write("""
重要提示：Tesseract-OCR 安装说明

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

            return True
        else:
            print("Packaging failed: No executable generated")
            print("PyInstaller output:")
            print(result.stdout)
            print("PyInstaller errors:")
            print(result.stderr)
            return False

    except Exception as e:
        print(f"Error during packaging: {str(e)}")
        print(traceback.format_exc())
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)