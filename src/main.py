# main.py - 程序入口
import sys
import os
import logging
import traceback

# 添加当前目录到系统路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 配置统一日志
def setup_logging():
    """配置统一的日志系统"""
    # 创建日志目录
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # 创建日志文件路径
    log_file = os.path.join(log_dir, "ocr_tool.log")

    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        filename=log_file,
        encoding='utf-8',
        filemode='a'  # 追加模式
    )

    # 添加控制台输出
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    logging.getLogger().addHandler(console_handler)

    # 设置全局异常处理
    sys.excepthook = handle_exception

    logging.info("统一日志系统已初始化")

# 全局异常处理
def handle_exception(exc_type, exc_value, exc_traceback):
    """全局异常处理函数"""
    # 忽略键盘中断
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    # 记录异常信息
    logger = logging.getLogger('global_exception')
    logger.error("未捕获的异常", exc_info=(exc_type, exc_value, exc_traceback))

    # 提取错误信息
    error_msg = f"发生未处理的错误:\n\n{str(exc_value)}"
    if exc_traceback:
        tb_lines = traceback.format_tb(exc_traceback)
        error_msg += f"\n\n追踪信息:\n{''.join(tb_lines)}"

    # 在控制台显示错误
    print(f"严重错误: {error_msg}")

    # 尝试显示错误对话框
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "未处理的错误",
            f"程序发生严重错误:\n\n{str(exc_value)}\n\n详细信息已记录到日志文件"
        )
        root.destroy()
    except:
        pass

if __name__ == "__main__":
    # 初始化日志
    setup_logging()

    # 延迟导入以避免日志配置问题
    import tkinter as tk
    from tkinter import messagebox
    from app import OCRApplication

    root = tk.Tk()
    app = OCRApplication(root)

    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()