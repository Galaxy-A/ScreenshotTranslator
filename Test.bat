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

REM 检查必要文件是否存在
if not exist "src\main.py" (
    echo.
    echo ======================================================
    echo 错误：未找到 src\main.py 文件！
    echo ======================================================
    echo.
    pause
    exit /b 1
)

REM 3. 检查Python是否可用
echo 正在检查Python环境...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo ======================================================
    echo 错误：未找到Python环境！
    echo 请确保已安装Python并添加到系统PATH中。
    echo ======================================================
    echo.
    pause
    exit /b 1
)

REM 4. 创建Python虚拟环境
echo 正在创建Python虚拟环境...
python -m venv venv
if %errorlevel% neq 0 (
    echo.
    echo ======================================================
    echo 错误：创建虚拟环境失败！
    echo ======================================================
    echo.
    pause
    exit /b 1
)
call venv\Scripts\activate

REM 5. 安装Python依赖
echo.
echo ======================================================
echo 步骤5/9：虚拟环境安装Python依赖包
echo ======================================================
echo 此步骤将安装打包所需的Python依赖包。
echo 按 Y 安装依赖包，或按 N 跳过（如果已安装）。
echo 注意：跳过安装可能导致打包失败。
echo.
choice /c YN /t 15 /d N /m "是否安装Python依赖包？[15秒后自动选N]"

if errorlevel 2 (
    echo 已跳过依赖包安装。
) else (
    echo 正在安装依赖包...
    pip install --upgrade pip
    pip install -r requirements.txt
)

REM 6. 检查Tesseract-OCR安装
echo.
echo ======================================================
echo 步骤6/9：OCR引擎检查
echo ======================================================
echo 重要：OCR功能需要Tesseract-OCR支持！
echo 如果未安装，OCR功能将无法正常工作。
echo.
choice /c YN /t 10 /d N /m "是否打开Tesseract-OCR下载页面？[10秒后自动选N]"

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

REM 7. 选择是否运行打包程序
echo.
echo ======================================================
echo 步骤7/9：选择是否打包
echo ======================================================
echo 即将运行打包程序，生成可执行文件。
echo 按 Y 开始打包，或按 N 跳过打包。
echo.
choice /c YN /t 15 /d N /m "是否运行打包程序？[15秒后自动选N]"

if errorlevel 2 (
    echo 已跳过打包。
    set SKIP_BUILD=1
) else (
    echo 正在打包应用程序...
    set SKIP_BUILD=0
)

REM 8. 运行打包脚本（如果选择Y）
if %SKIP_BUILD% equ 0 (
    echo.
    echo ======================================================
    echo 步骤8/9：运行打包程序
    echo ======================================================
    
    REM 检查build.py是否存在
    if not exist "build.py" (
        echo.
        echo ======================================================
        echo 错误：未找到 build.py 文件！
        echo ======================================================
        echo.
        pause
        exit /b 1
    )
    
    python build.py
    if %errorlevel% neq 0 (
        echo.
        echo ======================================================
        echo 错误：打包失败！
        echo 请检查错误信息并重试。
        echo ======================================================
        echo.
        pause
        exit /b 1
    )
)

REM 9. 检查打包结果（如果运行了打包）
if %SKIP_BUILD% equ 0 (
    echo.
    echo ======================================================
    echo 步骤9/9：检查打包结果
    echo ======================================================


    echo.
    echo ======================================================
    echo 打包成功！
    echo ======================================================
    echo 可执行文件路径：dist\ScreenshotTranslator.exe
    echo 版本信息：dist\build_info.txt
    echo.
    echo 重要提示：使用OCR功能需要安装Tesseract-OCR。
    echo 如果尚未安装，请访问：
    echo   https://github.com/UB-Mannheim/tesseract/wiki
    echo.
    choice /c YN /t 10 /d N /m "是否立即测试应用程序？[10秒后自动选N]"

    if errorlevel 2 (
        echo 已跳过测试。
    ) else (
        echo 正在启动应用程序...
        start "" "dist\ScreenshotTranslator.exe"
    )
) else (
    echo 已跳过打包结果检查。
)

REM 9. 清理临时文件
echo.
echo ======================================================
echo 步骤9/9：清理临时文件
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