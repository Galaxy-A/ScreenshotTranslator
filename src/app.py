# app.py - 主应用程序类
import os
import sys
import ctypes
import threading
import time
import json
import tkinter as tk
from tkinter import messagebox, ttk
import logging
from screen_capture import ScreenCapture
from ocr_engine import OCREngine
from result_window import ResultWindow
# from settings_window import SettingsWindow  # 已替换为AdvancedSettingsWindow
from translation import TranslationEngine
from config import Config
from error_handler import ErrorHandler, error_handler_decorator
from performance import PerformanceMonitor, time_operation
from async_processor import AsyncProcessor, ProgressTracker
from advanced_cache import AdvancedCache
# from smart_ocr import SmartOCREngine  # 暂时禁用，存在NumPy兼容性问题
from advanced_ui import ModernProgressDialog, NotificationSystem, AdvancedSettingsWindow
import pytesseract
import keyboard

# 默认配置
DEFAULT_SETTINGS = {
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
    "api_provider": "openai",  # "openai" 或 "deepseek"
    "api_key": "",
    "api_model": "gpt-3.5-turbo",
    "preprocessing": {
        "grayscale": True,
        "invert": False,
        "threshold": 0
    },
    "hide_window_on_capture": False,
    "hotkey": "ctrl+alt+s"
}

SETTINGS_FILE = "settings.json"

def resource_path(relative_path):
    """获取资源绝对路径，支持开发环境和PyInstaller打包环境"""
    try:
        # PyInstaller创建的临时文件夹路径
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

class OCRApplication:
    """主应用程序类"""

    def __init__(self, master):
        self.master = master
        self.master.title("OCR截图工具")
        self.master.geometry("400x300")
        self.master.resizable(True, True)

        # 获取日志记录器
        self.logger = logging.getLogger("OCRApplication")
        self.logger.info("应用程序初始化开始")

        # 初始化优化组件
        self.error_handler = ErrorHandler()
        self.performance_monitor = PerformanceMonitor()
        self.async_processor = AsyncProcessor(max_workers=6)
        self.progress_tracker = ProgressTracker()
        
        # 高级缓存系统
        self.advanced_cache = AdvancedCache("app_cache", max_size_mb=200)
        
        # 智能OCR引擎（暂时禁用）
        # self.smart_ocr = SmartOCREngine(self.advanced_cache)
        
        # 通知系统
        self.notification_system = NotificationSystem(self.master)
        
        # 配置管理
        self.config = Config()
        self.settings = self.config.get_all()

        # 获取系统信息
        self.dpi_scale = self.get_dpi_scaling()
        self.screen_width, self.screen_height = self.get_physical_screen_size()
        self.virtual_width = int(self.screen_width / self.dpi_scale)
        self.virtual_height = int(self.screen_height / self.dpi_scale)

        # 初始化组件
        self.screen_capture = ScreenCapture(
            self.dpi_scale,
            self.screen_width,
            self.screen_height,
            self.virtual_width,
            self.virtual_height
        )

        # 初始化OCR引擎
        self.ocr_engine = OCREngine()
        self.ocr_engine.config = self.settings["ocr_config"]
        self.ocr_engine.set_preprocessing(self.settings["preprocessing"])

        # 初始化翻译引擎
        self.translation_engine = TranslationEngine(
            self.settings["api_key"],
            self.settings["api_model"],
            self.settings["api_provider"]
        )

        # 设置Tesseract路径
        pytesseract.pytesseract.tesseract_cmd = self.settings["tesseract_path"]
        if os.path.exists(self.settings["tessdata_path"]):
            os.environ['TESSDATA_PREFIX'] = self.settings["tessdata_path"]

        self.result_window = None

        # 当前状态
        self.current_screenshot = None
        self.ocr_result = ""
        self.status_var = tk.StringVar(value="就绪")

        # 快捷键相关变量
        self.hotkey = self.settings.get("hotkey", "ctrl+alt+s")
        self.hotkey_enabled = True
        self.hotkey_thread = None

        # 创建界面
        self.create_main_ui()
        self.check_paths()

        # 设置应用图标
        try:
            icon_path = resource_path('ocr_icon.ico')
            if os.path.exists(icon_path):
                self.master.iconbitmap(icon_path)
        except Exception as e:
            self.logger.error(f"设置应用图标失败: {str(e)}")

        # 启动快捷键监听
        self.start_hotkey_listener()

        self.logger.info("OCR应用程序已启动")

    def start_hotkey_listener(self):
        """启动快捷键监听线程"""
        if self.hotkey_thread and self.hotkey_thread.is_alive():
            self.hotkey_thread.join(0.1)

        self.hotkey_thread = threading.Thread(
            target=self.listen_for_hotkey,
            daemon=True
        )
        self.hotkey_thread.start()
        self.logger.info(f"快捷键监听已启动: {self.hotkey}")

    def listen_for_hotkey(self):
        """监听快捷键"""
        self.logger.info("开始监听快捷键...")
        while self.hotkey_enabled:
            try:
                # 使用超时避免阻塞
                if keyboard.is_pressed(self.hotkey):
                    # 防止连续触发
                    keyboard.wait(self.hotkey, suppress=True)
                    # 在UI线程执行截图
                    self.master.after(0, self.start_capture)
                    # 等待一段时间防止重复触发
                    time.sleep(0.5)
                time.sleep(0.05)
            except Exception as e:
                self.logger.error(f"快捷键监听错误: {str(e)}")
                time.sleep(1)

    def load_settings(self):
        """加载设置文件"""
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                self.logger.info("设置文件已加载")
                return settings
            except Exception as e:
                self.logger.error(f"加载设置文件失败: {str(e)}, 使用默认设置")
                # 文件损坏时使用默认设置
                return DEFAULT_SETTINGS
        self.logger.info("未找到设置文件，使用默认设置")
        return DEFAULT_SETTINGS

    def save_settings(self):
        """保存设置到文件"""
        try:
            # 更新OCR配置
            self.settings["ocr_config"] = self.ocr_engine.config
            # 更新预处理配置
            self.settings["preprocessing"] = self.ocr_engine.preprocessing

            with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2)
            self.logger.info("设置已保存")
            return True
        except Exception as e:
            self.logger.error(f"保存设置失败: {str(e)}")
            messagebox.showerror("保存设置失败", f"无法保存设置: {str(e)}")
            return False

    def get_dpi_scaling(self):
        """获取系统DPI缩放比例"""
        try:
            if sys.platform == 'win32':
                ctypes.windll.shcore.SetProcessDpiAwareness(2)
                hdc = ctypes.windll.user32.GetDC(0)
                dpi_x = ctypes.windll.gdi32.GetDeviceCaps(hdc, 88)
                ctypes.windll.user32.ReleaseDC(0, hdc)
                return dpi_x / 96.0
        except Exception as e:
            self.logger.warning(f"获取DPI缩放比例失败: {str(e)}")
            return 1.0

    def get_physical_screen_size(self):
        """获取物理屏幕尺寸"""
        try:
            if sys.platform == 'win32':
                user32 = ctypes.windll.user32
                return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
        except Exception as e:
            self.logger.warning(f"获取物理屏幕尺寸失败: {str(e)}")
            return self.master.winfo_screenwidth(), self.master.winfo_screenheight()

    def create_main_ui(self):
        """创建主界面UI"""
        main_frame = ttk.Frame(self.master, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 标题
        ttk.Label(
            main_frame,
            text="OCR截图文字识别工具",
            font=("微软雅黑", 16, "bold")
        ).pack(pady=(0, 20))

        # 快速操作区域
        quick_frame = ttk.LabelFrame(main_frame, text="快速操作", padding=10)
        quick_frame.pack(fill=tk.X, pady=(0, 15))

        # 主要功能按钮
        main_button_frame = ttk.Frame(quick_frame)
        main_button_frame.pack(fill=tk.X, pady=5)

        self.capture_btn = ttk.Button(
            main_button_frame,
            text="📷 开始截图",
            command=self.start_capture,
            width=18
        )
        self.capture_btn.pack(side=tk.LEFT, padx=5)

        self.open_result_btn = ttk.Button(
            main_button_frame,
            text="📄 查看结果",
            command=self.show_last_result,
            width=18,
            state=tk.DISABLED
        )
        self.open_result_btn.pack(side=tk.LEFT, padx=5)

        # 辅助功能按钮
        aux_button_frame = ttk.Frame(quick_frame)
        aux_button_frame.pack(fill=tk.X, pady=5)

        ttk.Button(
            aux_button_frame,
            text="⚙️ 设置",
            command=self.show_settings,
            width=12
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            aux_button_frame,
            text="📊 统计",
            command=self.show_stats,
            width=12
        ).pack(side=tk.LEFT, padx=5)

        # 状态指示区域
        status_frame = ttk.LabelFrame(main_frame, text="状态信息", padding=10)
        status_frame.pack(fill=tk.X, pady=(0, 15))

        # 快捷键状态
        self.hotkey_status = tk.StringVar(value=f"快捷键: {self.hotkey}")
        ttk.Label(
            status_frame,
            textvariable=self.hotkey_status,
            font=("微软雅黑", 10),
            foreground="blue"
        ).pack(anchor=tk.W, pady=2)

        # 应用状态
        self.app_status = tk.StringVar(value="状态: 就绪")
        ttk.Label(
            status_frame,
            textvariable=self.app_status,
            font=("微软雅黑", 10)
        ).pack(anchor=tk.W, pady=2)

        # 最近操作
        self.last_action = tk.StringVar(value="最近操作: 无")
        ttk.Label(
            status_frame,
            textvariable=self.last_action,
            font=("微软雅黑", 9),
            foreground="gray"
        ).pack(anchor=tk.W, pady=2)

        # 状态栏
        status_frame = ttk.Frame(self.master)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)

        # 快捷键状态显示
        self.hotkey_status = tk.StringVar(value=f"当前快捷键: {self.hotkey}")
        ttk.Label(
            status_frame,
            textvariable=self.hotkey_status,
            anchor=tk.W,
            font=("微软雅黑", 9)
        ).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        ttk.Label(
            status_frame,
            textvariable=self.status_var,
            relief=tk.SUNKEN,
            anchor=tk.W
        ).pack(side=tk.RIGHT, fill=tk.X, expand=True)

        # 使用说明
        help_frame = ttk.LabelFrame(main_frame, text="使用说明")
        help_frame.pack(fill=tk.BOTH, expand=True, pady=(20, 0))

        instructions = [
            "1. 点击'开始截图'按钮或使用快捷键截图",
            "2. 在屏幕上拖拽选择识别区域",
            "3. 查看识别结果并保存",
            f"4. 当前截图快捷键: {self.hotkey}",
            "5. 识别完成后可手动进行翻译"
        ]
        for instruction in instructions:
            ttk.Label(help_frame, text=instruction, anchor=tk.W).pack(fill=tk.X, padx=10, pady=5)

    def check_paths(self):
        """检查路径有效性"""
        tesseract_path = self.settings["tesseract_path"]
        tessdata_path = self.settings["tessdata_path"]

        if not os.path.exists(tesseract_path):
            self.logger.error(f"找不到Tesseract可执行文件: {tesseract_path}")
            messagebox.showerror("路径错误", f"找不到Tesseract可执行文件: {tesseract_path}")
            return False

        if not os.path.exists(tessdata_path):
            self.logger.warning(f"找不到语言包目录: {tessdata_path}")
            messagebox.showwarning("路径警告", f"找不到语言包目录: {tessdata_path}")

        return True

    def start_capture(self):
        """开始截图流程"""
        self.app_status.set("状态: 准备截图")
        self.last_action.set("最近操作: 开始截图")
        self.status_var.set("准备截图...")
        self.master.update()
        self.logger.info("开始截图流程")
        self.master.after(300, self.capture_and_ocr)

    def capture_and_ocr(self):
        """截图并识别文字"""
        # 根据设置决定是否隐藏主窗口
        if self.settings.get("hide_window_on_capture", False):
            self.master.withdraw()  # 隐藏主窗口
            self.master.update()  # 确保窗口状态更新

        # 选择区域
        physical_coords = self.screen_capture.select_area(self.master)

        # 如果隐藏了主窗口，现在恢复显示
        if self.settings.get("hide_window_on_capture", False):
            self.master.deiconify()  # 恢复显示主窗口

        if not physical_coords:
            self.status_var.set("截图已取消")
            self.logger.info("截图已取消")
            return

        # 转换为虚拟坐标
        virtual_coords = self.screen_capture.get_virtual_coords(physical_coords)
        x1, y1, x2, y2 = virtual_coords

        # 区域有效性检查
        if abs(x2 - x1) < 5 or abs(y2 - y1) < 5:
            self.logger.warning("选择的区域太小")
            messagebox.showwarning("区域无效", "选择的区域太小，请重新选择")
            self.capture_and_ocr()
            return

        # 转换为物理坐标
        x1_phys, y1_phys, x2_phys, y2_phys = self.screen_capture.get_physical_coords(virtual_coords)

        # 确保坐标顺序正确
        if x1_phys > x2_phys: x1_phys, x2_phys = x2_phys, x1_phys
        if y1_phys > y2_phys: y1_phys, y2_phys = y2_phys, y1_phys

        # 应用偏移校正
        offset = self.settings["offset"]
        x1_phys += offset["horizontal"]
        y1_phys += offset["vertical"]
        x2_phys += offset["horizontal"]
        y2_phys += offset["vertical"]

        # 截图
        self.status_var.set(f"截取区域: ({x1:.1f}, {y1:.1f}) -> ({x2:.1f}, {y2:.1f})")
        self.master.update()
        time.sleep(0.3)  # 等待窗口关闭

        try:
            self.current_screenshot = self.screen_capture.capture_area((x1_phys, y1_phys, x2_phys, y2_phys))
            self.logger.info(f"成功截取区域: ({x1_phys},{y1_phys})->({x2_phys},{y2_phys})")
        except Exception as e:
            self.logger.error(f"截图失败: {str(e)}")
            self.status_var.set(f"截图失败: {str(e)}")
            return

        # 智能显示结果窗口
        self._smart_show_result_window()

        # 使用异步处理器执行OCR
        self.async_processor.submit_task(
            "ocr_task",
            self.perform_ocr,
            callback=self._on_ocr_complete
        )

    @time_operation("OCR识别")
    def perform_ocr(self):
        """执行OCR识别 - 优化版本"""
        # 开始进度跟踪
        self.progress_tracker.start_progress("ocr_task", 4, "开始OCR识别")
        
        def progress_callback(percentage, description):
            self.master.after(0, lambda: self._update_ocr_progress(percentage, description))
        
        try:
            # 临时禁用智能OCR，使用传统OCR引擎进行调试
            if False and self.settings.get("smart_optimization", True):
                text = self.smart_ocr.perform_smart_ocr(self.current_screenshot, progress_callback=progress_callback)
            else:
                # 使用传统OCR引擎
                text = self.ocr_engine.perform_ocr(self.current_screenshot, progress_callback=progress_callback)
            
            self.logger.info("OCR识别完成")

            # 如果识别结果为空，尝试纯文本识别
            if not text.strip():
                self.progress_tracker.update_progress("ocr_task", 2, "尝试纯文本识别...")
                if False and self.settings.get("smart_optimization", True):
                    # 智能OCR会自动尝试不同配置
                    text = self.smart_ocr.perform_smart_ocr(self.current_screenshot, progress_callback=progress_callback)
                else:
                    text = self.ocr_engine.perform_ocr(self.current_screenshot, lang='eng', progress_callback=progress_callback)

            self.progress_tracker.complete_progress("ocr_task", "OCR识别完成")
            return text

        except Exception as e:
            self.progress_tracker.complete_progress("ocr_task", f"OCR识别失败: {str(e)}")
            raise e
    
    def _update_ocr_progress(self, percentage, description):
        """更新OCR进度显示"""
        if self.result_window:
            self.result_window.text_area.config(state=tk.NORMAL)
            self.result_window.text_area.delete(1.0, tk.END)
            self.result_window.text_area.insert(tk.END, f"{description} ({percentage:.0f}%)")
            self.result_window.text_area.config(state=tk.DISABLED)
            self.result_window.window.update()
        
        # 更新主窗口状态
        self.app_status.set(f"状态: 识别中 ({percentage:.0f}%)")
        self.last_action.set(f"最近操作: {description}")
        self.status_var.set(f"识别中: {description}")
    
    def _on_ocr_complete(self, result, error):
        """OCR完成回调"""
        if error:
            self.error_handler.handle_exception(error, "OCR识别", show_dialog=True)
            self.app_status.set("状态: 识别失败")
            self.last_action.set("最近操作: OCR识别失败")
            return
        
        if result:
            self.ocr_result = result
            
            # 显示结果
            if self.result_window:
                self.result_window.display_result(result, self.current_screenshot)

            # 计算字符数
            char_count = len(result.strip())
            word_count = len(result.split())
            
            # 更新状态显示
            self.app_status.set("状态: 识别完成")
            self.last_action.set(f"最近操作: 识别了 {char_count} 个字符")
            self.status_var.set(f"识别完成！共识别 {char_count} 个字符，{word_count} 个单词")
            self.logger.info(f"识别完成: {char_count}字符, {word_count}单词")

            # 保存结果
            self._save_ocr_result(result)

            # 启用查看结果按钮
            self.open_result_btn.config(state=tk.NORMAL)

    
    def _save_ocr_result(self, text):
        """保存OCR结果"""
        try:
            with open('ocr_result.txt', 'w', encoding='utf-8') as f:
                f.write(text)
            self.current_screenshot.save("screenshot.png")
            self.logger.info("OCR结果和截图已保存")
        except Exception as e:
            self.error_handler.handle_exception(e, "保存结果", show_dialog=False)
    

    def _smart_show_result_window(self):
        """智能显示结果窗口"""
        # 检查是否已有结果窗口
        if hasattr(self, 'result_window') and self.result_window and self.result_window.window.winfo_exists():
            # 如果窗口存在，先隐藏它
            self.result_window.window.withdraw()
        
        # 创建新的结果窗口
        self.result_window = ResultWindow(
            self.master,
            self.current_screenshot,
            self.ocr_result,
            self,
            recapture_callback=self.start_capture
        )
        
        # 智能定位窗口
        self._position_result_window()
        
        self.logger.info("结果窗口已智能显示")

    def _position_result_window(self):
        """智能定位结果窗口"""
        if not hasattr(self, 'result_window') or not self.result_window:
            return
        
        # 获取主窗口位置和大小
        main_x = self.master.winfo_x()
        main_y = self.master.winfo_y()
        main_width = self.master.winfo_width()
        main_height = self.master.winfo_height()
        
        # 获取屏幕尺寸
        screen_width = self.master.winfo_screenwidth()
        screen_height = self.master.winfo_screenheight()
        
        # 计算结果窗口位置（主窗口右侧）
        result_width = 800
        result_height = 600
        
        # 尝试放在主窗口右侧
        new_x = main_x + main_width + 10
        new_y = main_y
        
        # 如果右侧空间不够，放在主窗口下方
        if new_x + result_width > screen_width:
            new_x = main_x
            new_y = main_y + main_height + 10
        
        # 如果下方空间也不够，放在屏幕中央
        if new_y + result_height > screen_height:
            new_x = (screen_width - result_width) // 2
            new_y = (screen_height - result_height) // 2
        
        # 设置窗口位置
        self.result_window.window.geometry(f"{result_width}x{result_height}+{new_x}+{new_y}")
        
        # 绑定窗口关闭事件，实现状态同步
        # 注意：这里会覆盖result_window.py中的绑定，需要在result_window中调用我们的回调
        self.result_window.window.protocol("WM_DELETE_WINDOW", self._on_result_window_close)

    def show_result_window(self):
        """显示结果窗口（兼容性方法）"""
        self._smart_show_result_window()

    def _on_result_window_close(self):
        """结果窗口关闭回调"""
        self.logger.info("结果窗口关闭回调被调用")
        
        try:
            # 调用result_window的on_close方法
            if hasattr(self, 'result_window') and self.result_window:
                self.result_window.on_close()
        except Exception as e:
            self.logger.warning(f"调用result_window.on_close时出现异常: {str(e)}")
        
        # 更新主窗口状态
        self.last_action.set("最近操作: 结果窗口已关闭")
        
        # 清理结果窗口引用
        if hasattr(self, 'result_window'):
            self.result_window = None
    def show_last_result(self):
        """显示上次识别结果"""
        if self.ocr_result:
            # 使用智能窗口管理显示结果
            self._smart_show_result_window()
            self.logger.info("显示上次结果")
        else:
            self.logger.info("没有可用的历史结果")
            messagebox.showinfo("提示", "没有可用的历史结果")

    def show_settings(self):
        """显示设置窗口"""
        self.logger.info("打开设置窗口")
        advanced_settings = AdvancedSettingsWindow(
            self.master,
            self.config,
            on_save_callback=self._on_settings_saved
        )

    def show_stats(self):
        """显示统计信息窗口"""
        self.logger.info("打开统计窗口")
        
        # 创建统计窗口
        stats_window = tk.Toplevel(self.master)
        stats_window.title("使用统计")
        stats_window.geometry("500x400")
        stats_window.resizable(True, True)
        stats_window.transient(self.master)
        
        # 创建主框架
        main_frame = ttk.Frame(stats_window, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        ttk.Label(
            main_frame,
            text="📊 使用统计",
            font=("微软雅黑", 14, "bold")
        ).pack(pady=(0, 20))
        
        # 统计信息框架
        stats_frame = ttk.LabelFrame(main_frame, text="统计信息", padding=15)
        stats_frame.pack(fill=tk.BOTH, expand=True)
        
        # 获取统计信息
        ocr_stats = self.ocr_engine.get_performance_stats()
        perf_stats = self.performance_monitor.get_stats()
        
        # 显示统计信息
        stats_info = [
            ("OCR识别次数", f"{ocr_stats.get('total_ocr_calls', 0)} 次"),
            ("识别成功率", f"{ocr_stats.get('success_count', 0)}/{ocr_stats.get('total_ocr_calls', 0)}"),
            ("平均识别时间", f"{ocr_stats.get('average_processing_time', 0):.2f} 秒"),
            ("缓存命中率", f"{self.advanced_cache.get_stats().get('hit_rate', 0):.1%}"),
            ("总运行时间", f"{perf_stats.get('total_runtime', 0):.1f} 秒"),
        ]
        
        for label, value in stats_info:
            row_frame = ttk.Frame(stats_frame)
            row_frame.pack(fill=tk.X, pady=5)
            
            ttk.Label(row_frame, text=f"{label}:", width=15, anchor=tk.W).pack(side=tk.LEFT)
            ttk.Label(row_frame, text=value, font=("微软雅黑", 10, "bold")).pack(side=tk.LEFT, padx=(10, 0))
        
        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(20, 0))
        
        ttk.Button(
            button_frame,
            text="重置统计",
            command=lambda: self.reset_stats(stats_window)
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame,
            text="关闭",
            command=stats_window.destroy
        ).pack(side=tk.RIGHT, padx=5)

    def reset_stats(self, parent_window):
        """重置统计信息"""
        if messagebox.askyesno("确认重置", "确定要重置所有统计信息吗？"):
            self.ocr_engine.reset_stats()
            self.performance_monitor.reset_stats()
            self.advanced_cache.clear_stats()
            self.last_action.set("最近操作: 统计已重置")
            parent_window.destroy()
            self.show_stats()  # 重新显示统计窗口
    
    def _on_settings_saved(self, new_settings):
        """设置保存回调"""
        self.settings = new_settings
        
        # 更新OCR引擎配置
        self.ocr_engine.config = self.settings["ocr_config"]
        self.ocr_engine.set_preprocessing(self.settings["preprocessing"])

        # 更新翻译引擎API密钥、模型和提供商
        self.translation_engine.set_api_key(self.settings["api_key"])
        self.translation_engine.set_model(self.settings["api_model"])
        self.translation_engine.set_provider(self.settings["api_provider"])

        # 更新路径
        pytesseract.pytesseract.tesseract_cmd = self.settings["tesseract_path"]
        if os.path.exists(self.settings["tessdata_path"]):
            os.environ['TESSDATA_PREFIX'] = self.settings["tessdata_path"]

        # 更新快捷键
        new_hotkey = self.settings.get("hotkey", "ctrl+alt+s")
        if new_hotkey != self.hotkey:
            self.hotkey = new_hotkey
            self.hotkey_status.set(f"当前快捷键: {self.hotkey}")
            # 重新启动快捷键监听
            self.hotkey_enabled = False
            if self.hotkey_thread and self.hotkey_thread.is_alive():
                self.hotkey_thread.join(0.5)
            self.hotkey_enabled = True
            self.start_hotkey_listener()
            self.logger.info(f"快捷键已更新为: {self.hotkey}")

        # 更新使用说明
        for widget in self.master.winfo_children():
            if isinstance(widget, ttk.LabelFrame) and widget.cget("text") == "使用说明":
                # 清除旧说明
                for child in widget.winfo_children():
                    child.destroy()
                # 添加新说明
                instructions = [
                    "1. 点击'开始截图'按钮或使用快捷键截图",
                    "2. 在屏幕上拖拽选择识别区域",
                    "3. 查看识别结果并保存",
                    f"4. 当前截图快捷键: {self.hotkey}",
                    "5. 识别完成后可手动进行翻译"
                ]
                for instruction in instructions:
                    ttk.Label(widget, text=instruction, anchor=tk.W).pack(fill=tk.X, padx=10, pady=5)
                break
        
        # 更新智能OCR设置（暂时禁用）
        # if hasattr(self, 'smart_ocr'):
        #     # 智能OCR会自动适应新设置
        #     pass
        
        # 更新缓存设置
        if hasattr(self, 'advanced_cache'):
            # 更新缓存大小限制
            max_size_mb = new_settings.get("cache_size_mb", 200)
            self.advanced_cache.max_size_mb = max_size_mb
        
        # 更新异步处理器设置
        max_workers = new_settings.get("max_workers", 4)
        if hasattr(self, 'async_processor'):
            self.async_processor.shutdown(wait=True)
            self.async_processor = AsyncProcessor(max_workers=max_workers)
        
        # 显示通知
        self.notification_system.show_notification(
            "设置已更新",
            "设置已保存并生效",
            "success"
        )
        
        self.logger.info("设置已更新")

    def on_closing(self):
        """程序关闭时调用"""
        self.logger.info("应用程序正在关闭...")
        self.hotkey_enabled = False
        if self.hotkey_thread and self.hotkey_thread.is_alive():
            self.hotkey_thread.join(0.5)
        
        # 关闭异步处理器
        self.async_processor.shutdown(wait=False)
        
        # 清理高级缓存
        if hasattr(self, 'advanced_cache'):
            self.advanced_cache.cleanup()
        
        # 保存配置
        self.config.save_settings()
        
        self.master.destroy()
        self.logger.info("应用程序已关闭")