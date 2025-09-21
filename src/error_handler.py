# error_handler.py - 增强错误处理模块
import logging
import traceback
import tkinter as tk
from tkinter import messagebox
from typing import Optional, Dict, Any, Callable
import time
from functools import wraps

class ErrorHandler:
    """增强的错误处理器"""
    
    def __init__(self, logger_name: str = "ErrorHandler"):
        self.logger = logging.getLogger(logger_name)
        self.error_count = {}
        self.last_error_time = {}
        self.error_callbacks = []
    
    def handle_exception(self, e: Exception, context: str = "", show_dialog: bool = True) -> str:
        """处理异常"""
        error_msg = str(e)
        error_type = type(e).__name__
        
        # 记录错误统计
        error_key = f"{error_type}:{context}"
        self.error_count[error_key] = self.error_count.get(error_key, 0) + 1
        self.last_error_time[error_key] = time.time()
        
        # 记录错误信息
        self.logger.error(f"错误 [{context}]: {error_msg}")
        self.logger.debug(f"错误详情: {traceback.format_exc()}")
        
        # 显示用户友好的错误信息
        user_msg = self._get_user_friendly_message(error_type, error_msg, context)
        
        # 调用错误回调
        for callback in self.error_callbacks:
            try:
                callback(e, context, user_msg)
            except Exception as callback_error:
                self.logger.error(f"错误回调执行失败: {str(callback_error)}")
        
        if show_dialog:
            self._show_error_dialog(user_msg, context)
        
        return user_msg
    
    def _get_user_friendly_message(self, error_type: str, error_msg: str, context: str) -> str:
        """获取用户友好的错误信息"""
        error_messages = {
            "TesseractNotFoundError": "OCR引擎未找到，请检查Tesseract安装路径",
            "TesseractError": "OCR识别失败，请检查图像质量或语言设置",
            "ConnectionError": "网络连接失败，请检查网络连接",
            "TimeoutError": "请求超时，请稍后重试",
            "FileNotFoundError": "文件未找到，请检查文件路径",
            "PermissionError": "权限不足，请检查文件权限",
            "ValueError": "参数错误，请检查输入值",
            "KeyError": "配置错误，请检查设置文件"
        }
        
        if error_type in error_messages:
            return f"{error_messages[error_type]}\n\n详细信息: {error_msg}"
        
        return f"发生未知错误: {error_msg}"
    
    def _show_error_dialog(self, message: str, context: str):
        """显示错误对话框"""
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror(f"错误 - {context}", message)
            root.destroy()
        except Exception as e:
            self.logger.error(f"显示错误对话框失败: {str(e)}")
    
    def add_error_callback(self, callback: Callable):
        """添加错误回调函数"""
        self.error_callbacks.append(callback)
    
    def remove_error_callback(self, callback: Callable):
        """移除错误回调函数"""
        if callback in self.error_callbacks:
            self.error_callbacks.remove(callback)
    
    def get_error_stats(self) -> Dict[str, Any]:
        """获取错误统计信息"""
        return {
            "error_count": self.error_count.copy(),
            "last_error_time": self.last_error_time.copy(),
            "total_errors": sum(self.error_count.values())
        }
    
    def clear_error_stats(self):
        """清空错误统计"""
        self.error_count.clear()
        self.last_error_time.clear()
        self.logger.info("错误统计已清空")

def safe_execute(func, *args, context: str = "", show_dialog: bool = True, **kwargs):
    """安全执行函数，自动处理异常"""
    error_handler = ErrorHandler()
    try:
        return func(*args, **kwargs)
    except Exception as e:
        return error_handler.handle_exception(e, context, show_dialog)

def error_handler_decorator(context: str = "", show_dialog: bool = True):
    """错误处理装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            error_handler = ErrorHandler()
            try:
                return func(*args, **kwargs)
            except Exception as e:
                return error_handler.handle_exception(e, context, show_dialog)
        return wrapper
    return decorator