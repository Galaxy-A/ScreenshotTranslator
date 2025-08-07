@echo off
REM =================================
REM 截图翻译工具 - 打包自动化脚本
REM =================================

REM 1. 设置控制台编码为UTF-8（支持中文显示）
chcp 65001 > nul
set PYTHONIOENCODING=utf-8

REM 2. 检查路径是否包含中文字符
echo 正在检查路径是否包含中文字符...
for /f "delims=" %%i in ('chdir') do set current_path=%%i
echo %current_path% | findstr /r "[^ -~]" >nul
if %errorlevel% equ 0 (
    echo.
    echo ======================================================
    echo 警告：当前路径包含中文字符！
    echo 这可能导致打包过程中出现编码问题。
    echo 请将项目移动到纯英文路径下再运行此脚本。
    echo ======================================================
    echo.
    pause
    exit /b 1
)

REM 3. 创建Python虚拟环境
echo 正在创建Python虚拟环境...
python -m venv venv
call venv\Scripts\activate

REM 4. 安装Python依赖
echo.
echo ======================================================
echo 步骤4/8：虚拟环境安装Python依赖包
echo ======================================================
echo 此步骤将安装打包所需的Python依赖包。
echo 按 Y 安装依赖包，或按 N 跳过（如果已安装）。
echo 注意：跳过安装可能导致打包失败。
echo.
choice /c YN /n /m "是否安装Python依赖包？[Y/N]"

if errorlevel 2 (
    echo 已跳过依赖包安装。
) else (
    echo 正在安装依赖包...
    pip install pyinstaller pillow pytesseract requests keyboard opencv-python
)

REM 5. 检查Tesseract-OCR安装
echo.
echo ======================================================
echo 步骤5/8：OCR引擎检查
echo ======================================================
echo 重要：OCR功能需要Tesseract-OCR支持！
echo 如果未安装，OCR功能将无法正常工作。
echo.
choice /c YN /n /m "是否打开Tesseract-OCR下载页面？[Y/N]"

if errorlevel 2 (
    echo 已跳过Tesseract-OCR安装。
) else (
    start "" "https://github.com/UB-Mannheim/tesseract/wiki"
    echo.
    echo 请按以下步骤安装：
    echo 1. 访问打开的网页下载安装程序
    echo 2. 运行安装程序，确保勾选中文语言包
    echo 3. 安装完成后回到此窗口
    echo.
    pause
)

REM 6. 运行打包脚本
echo.
echo ======================================================
echo 步骤6/8：运行打包程序
echo ======================================================
echo 正在打包应用程序...
python build.py

REM 7. 检查打包结果
if exist dist\ScreenshotTranslator.exe (
    echo.
    echo ======================================================
    echo 打包成功！
    echo ======================================================
    echo 可执行文件路径：dist\ScreenshotTranslator.exe
    echo.
    echo 重要提示：使用OCR功能需要安装Tesseract-OCR。
    echo 如果尚未安装，请访问：
    echo   https://github.com/UB-Mannheim/tesseract/wiki
    echo.
    choice /c YN /n /m "是否立即测试应用程序？[Y/N]"

    if errorlevel 2 (
        echo 已跳过测试。
    ) else (
        echo 正在启动应用程序...
        start "" "dist\ScreenshotTranslator.exe"
    )
) else (
    echo.
    echo ======================================================
    echo 打包失败！
    echo ======================================================
    echo 请检查 build_log.txt 文件查看详细错误信息。
)

REM 8. 清理临时文件
echo.
echo ======================================================
echo 步骤8/8：清理临时文件
echo ======================================================
echo 正在清理虚拟环境...
deactivate
rmdir /s /q venv

echo.
echo ======================================================
echo 所有操作已完成！
echo ======================================================
echo.
pause

