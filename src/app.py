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
from settings_window import SettingsWindow
from translation import TranslationEngine
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

        # 加载设置
        self.settings = self.load_settings()

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
            self.settings["deepseek_api_key"],
            self.settings["deepseek_model"]
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

        # 功能按钮
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)

        ttk.Button(
            button_frame,
            text="开始截图",
            command=self.start_capture,
            width=15
        ).pack(side=tk.LEFT, padx=5)

        self.open_result_btn = ttk.Button(
            button_frame,
            text="查看上次结果",
            command=self.show_last_result,
            width=15,
            state=tk.DISABLED
        )
        self.open_result_btn.pack(side=tk.LEFT, padx=5)

        ttk.Button(
            button_frame,
            text="设置",
            command=self.show_settings,
            width=10
        ).pack(side=tk.RIGHT, padx=5)

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
            f"4. 当前截图快捷键: {self.hotkey}"
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

        # 显示结果窗口
        self.show_result_window()

        # 在单独的线程中执行OCR
        threading.Thread(target=self.perform_ocr, daemon=True).start()

    def perform_ocr(self):
        """执行OCR识别"""
        try:
            if self.result_window:
                self.result_window.text_area.config(state=tk.NORMAL)
                self.result_window.text_area.delete(1.0, tk.END)
                self.result_window.text_area.insert(tk.END, "正在识别中，请稍候...")
                self.result_window.text_area.config(state=tk.DISABLED)
                self.result_window.window.update()

            # 执行OCR
            text = self.ocr_engine.perform_ocr(self.current_screenshot)
            self.logger.info("OCR识别完成")

            if not text.strip():
                self.status_var.set("识别中：尝试纯文本识别...")
                self.logger.info("尝试纯文本识别...")
                text = self.ocr_engine.perform_ocr(self.current_screenshot, lang='eng')

            # 显示结果
            self.ocr_result = text
            if self.result_window:
                self.result_window.display_result(text, self.current_screenshot)

            # 计算字符数
            char_count = len(text.strip())
            word_count = len(text.split())
            self.status_var.set(f"识别完成！共识别 {char_count} 个字符，{word_count} 个单词")
            self.logger.info(f"识别完成: {char_count}字符, {word_count}单词")

            # 保存结果
            try:
                with open('ocr_result.txt', 'w', encoding='utf-8') as f:
                    f.write(text)
                self.current_screenshot.save("screenshot.png")
                self.logger.info("OCR结果和截图已保存")
            except Exception as e:
                self.logger.error(f"保存结果失败: {str(e)}")

            # 启用查看结果按钮
            self.open_result_btn.config(state=tk.NORMAL)

        except Exception as e:
            self.logger.error(f"识别失败: {str(e)}")
            self.status_var.set(f"识别失败: {str(e)}")
            if self.result_window:
                self.result_window.text_area.config(state=tk.NORMAL)
                self.result_window.text_area.delete(1.0, tk.END)
                self.result_window.text_area.insert(tk.END, f"OCR错误: {str(e)}")
            messagebox.showerror("OCR错误", f"识别过程中出错:\n{str(e)}")

    def show_result_window(self):
        """显示结果窗口"""
        if hasattr(self, 'result_window') and self.result_window and self.result_window.window.winfo_exists():
            self.result_window.window.destroy()

        # 将self传递给ResultWindow
        self.result_window = ResultWindow(self.master, self.current_screenshot, self.ocr_result, self)
        self.logger.info("结果窗口已显示")

    def show_last_result(self):
        """显示上次识别结果"""
        if self.ocr_result:
            self.show_result_window()
            self.result_window.display_result(self.ocr_result, self.current_screenshot)
            self.logger.info("显示上次结果")
        else:
            self.logger.info("没有可用的历史结果")
            messagebox.showinfo("提示", "没有可用的历史结果")

    def show_settings(self):
        """显示设置窗口"""
        self.logger.info("打开设置窗口")
        # 创建设置窗口
        settings_win = SettingsWindow(
            self.master,
            self.dpi_scale,
            (self.screen_width, self.screen_height),
            (self.virtual_width, self.virtual_height),
            self.ocr_engine,
            self.settings
        )

        # 等待设置窗口关闭
        self.master.wait_window(settings_win.window)

        # 保存设置
        if settings_win.settings_updated:
            # 更新设置
            self.settings = settings_win.new_settings

            # 更新OCR引擎配置
            self.ocr_engine.config = self.settings["ocr_config"]
            self.ocr_engine.set_preprocessing(self.settings["preprocessing"])

            # 更新翻译引擎API密钥和模型
            self.translation_engine.set_api_key(self.settings["deepseek_api_key"])
            self.translation_engine.set_model(self.settings["deepseek_model"])

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
                        f"4. 当前截图快捷键: {self.hotkey}"
                    ]
                    for instruction in instructions:
                        ttk.Label(widget, text=instruction, anchor=tk.W).pack(fill=tk.X, padx=10, pady=5)
                    break

            # 保存到文件
            self.save_settings()

            messagebox.showinfo("设置已保存", "设置已更新并保存！")
            self.logger.info("设置已保存")

    def on_closing(self):
        """程序关闭时调用"""
        self.logger.info("应用程序正在关闭...")
        self.hotkey_enabled = False
        if self.hotkey_thread and self.hotkey_thread.is_alive():
            self.hotkey_thread.join(0.5)
        self.master.destroy()
        self.logger.info("应用程序已关闭")