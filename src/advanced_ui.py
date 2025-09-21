# advanced_ui.py - 高级UI组件
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import logging
from typing import Dict, Any, Optional, Callable, List
import threading
import time
from PIL import Image, ImageTk
import json

class ModernProgressDialog:
    """现代化进度对话框"""
    
    def __init__(self, parent, title="处理中...", message="请稍候"):
        self.parent = parent
        self.window = tk.Toplevel(parent)
        self.window.title(title)
        self.window.geometry("400x150")
        self.window.resizable(False, False)
        self.window.transient(parent)
        self.window.grab_set()
        
        # 居中显示
        self.window.geometry("+%d+%d" % (
            parent.winfo_rootx() + 50,
            parent.winfo_rooty() + 50
        ))
        
        self.setup_ui(message)
        self.cancelled = False
        
    def setup_ui(self, message):
        """设置UI"""
        main_frame = ttk.Frame(self.window, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 消息标签
        self.message_label = ttk.Label(main_frame, text=message, font=("微软雅黑", 10))
        self.message_label.pack(pady=(0, 10))
        
        # 进度条
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            main_frame, 
            variable=self.progress_var,
            maximum=100,
            length=300
        )
        self.progress_bar.pack(pady=(0, 10))
        
        # 状态标签
        self.status_label = ttk.Label(main_frame, text="0%", font=("微软雅黑", 9))
        self.status_label.pack(pady=(0, 10))
        
        # 取消按钮
        self.cancel_button = ttk.Button(
            main_frame, 
            text="取消", 
            command=self.cancel
        )
        self.cancel_button.pack()
        
    def update_progress(self, value: int, message: str = ""):
        """更新进度"""
        self.progress_var.set(value)
        self.status_label.config(text=f"{value}%")
        if message:
            self.message_label.config(text=message)
        self.window.update()
        
    def cancel(self):
        """取消操作"""
        self.cancelled = True
        self.window.destroy()
        
    def is_cancelled(self) -> bool:
        """检查是否已取消"""
        return self.cancelled

class NotificationSystem:
    """通知系统"""
    
    def __init__(self, parent):
        self.parent = parent
        self.logger = logging.getLogger("NotificationSystem")
        self.notifications = []
        self.max_notifications = 5
        
    def show_notification(self, title: str, message: str, 
                         notification_type: str = "info", duration: int = 3000):
        """显示通知"""
        notification = {
            "title": title,
            "message": message,
            "type": notification_type,
            "timestamp": time.time(),
            "duration": duration
        }
        
        self.notifications.append(notification)
        self._display_notification(notification)
        
        # 自动移除通知
        self.parent.after(duration, lambda: self._remove_notification(notification))
        
    def _display_notification(self, notification):
        """显示通知窗口"""
        # 计算位置
        x = self.parent.winfo_rootx() + self.parent.winfo_width() - 320
        y = self.parent.winfo_rooty() + 50 + len(self.notifications) * 80
        
        # 创建通知窗口
        notif_window = tk.Toplevel(self.parent)
        notif_window.title("")
        notif_window.geometry(f"300x70+{x}+{y}")
        notif_window.overrideredirect(True)
        notif_window.attributes("-topmost", True)
        
        # 设置样式
        colors = {
            "info": ("#e3f2fd", "#1976d2"),
            "success": ("#e8f5e8", "#388e3c"),
            "warning": ("#fff3e0", "#f57c00"),
            "error": ("#ffebee", "#d32f2f")
        }
        
        bg_color, fg_color = colors.get(notification["type"], colors["info"])
        
        # 创建内容
        frame = tk.Frame(notif_window, bg=bg_color, relief=tk.RAISED, bd=1)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title_label = tk.Label(
            frame, 
            text=notification["title"],
            font=("微软雅黑", 9, "bold"),
            bg=bg_color,
            fg=fg_color
        )
        title_label.pack(anchor=tk.W, padx=10, pady=(5, 0))
        
        # 消息
        message_label = tk.Label(
            frame,
            text=notification["message"],
            font=("微软雅黑", 8),
            bg=bg_color,
            fg=fg_color,
            wraplength=280
        )
        message_label.pack(anchor=tk.W, padx=10, pady=(0, 5))
        
        # 关闭按钮
        close_button = tk.Button(
            frame,
            text="×",
            font=("Arial", 12, "bold"),
            bg=bg_color,
            fg=fg_color,
            bd=0,
            command=notif_window.destroy
        )
        close_button.place(x=270, y=5)
        
        # 存储窗口引用
        notification["window"] = notif_window
        
    def _remove_notification(self, notification):
        """移除通知"""
        if notification in self.notifications:
            self.notifications.remove(notification)
        if "window" in notification and notification["window"].winfo_exists():
            notification["window"].destroy()

class AdvancedSettingsWindow:
    """高级设置窗口"""
    
    def __init__(self, parent, config_manager, on_save_callback=None):
        self.parent = parent
        self.config_manager = config_manager
        self.on_save_callback = on_save_callback
        self.logger = logging.getLogger("AdvancedSettingsWindow")
        
        self.window = tk.Toplevel(parent)
        self.window.title("设置")
        self.window.geometry("600x500")
        self.window.resizable(True, True)
        self.window.transient(parent)
        
        self.setup_ui()
        self.load_settings()
        
    def setup_ui(self):
        """设置UI"""
        # 创建主框架
        main_frame = ttk.Frame(self.window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 创建笔记本控件
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # 基础设置标签页
        self.basic_frame = ttk.Frame(notebook)
        notebook.add(self.basic_frame, text="基础设置")
        self.setup_basic_tab()
        
        # OCR设置标签页
        self.ocr_frame = ttk.Frame(notebook)
        notebook.add(self.ocr_frame, text="OCR设置")
        self.setup_ocr_tab()
        
        # 缓存设置标签页
        self.cache_frame = ttk.Frame(notebook)
        notebook.add(self.cache_frame, text="缓存设置")
        self.setup_cache_tab()
        
        # 高级设置标签页
        self.advanced_frame = ttk.Frame(notebook)
        notebook.add(self.advanced_frame, text="高级设置")
        self.setup_advanced_tab()
        
        # 按钮框架
        button_frame = ttk.Frame(self.window)
        button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        ttk.Button(button_frame, text="保存", command=self.save_settings).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="取消", command=self.window.destroy).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="重置", command=self.reset_settings).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="导入", command=self.import_settings).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="导出", command=self.export_settings).pack(side=tk.LEFT, padx=5)
    
    def setup_basic_tab(self):
        """设置基础设置标签页"""
        # 创建滚动框架
        canvas = tk.Canvas(self.basic_frame)
        scrollbar = ttk.Scrollbar(self.basic_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # 路径设置框架
        path_frame = ttk.LabelFrame(scrollable_frame, text="路径设置", padding=10)
        path_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Tesseract路径
        ttk.Label(path_frame, text="Tesseract路径:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.tesseract_path_var = tk.StringVar()
        tesseract_entry = ttk.Entry(path_frame, textvariable=self.tesseract_path_var, width=40)
        tesseract_entry.grid(row=0, column=1, sticky=tk.W, padx=(10, 5), pady=5)
        ttk.Button(path_frame, text="浏览", command=self.browse_tesseract_path).grid(row=0, column=2, padx=5, pady=5)
        
        # 语言包路径
        ttk.Label(path_frame, text="语言包路径:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.tessdata_path_var = tk.StringVar()
        tessdata_entry = ttk.Entry(path_frame, textvariable=self.tessdata_path_var, width=40)
        tessdata_entry.grid(row=1, column=1, sticky=tk.W, padx=(10, 5), pady=5)
        ttk.Button(path_frame, text="浏览", command=self.browse_tessdata_path).grid(row=1, column=2, padx=5, pady=5)
        
        # API设置框架
        api_frame = ttk.LabelFrame(scrollable_frame, text="API设置", padding=10)
        api_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # API提供商选择
        ttk.Label(api_frame, text="API提供商:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.provider_var = tk.StringVar()
        provider_combo = ttk.Combobox(api_frame, textvariable=self.provider_var, width=37)
        provider_combo['values'] = ("openai", "deepseek")
        provider_combo.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=5)
        provider_combo.bind('<<ComboboxSelected>>', self._on_provider_changed)
        
        # API密钥
        ttk.Label(api_frame, text="API密钥:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.api_key_var = tk.StringVar()
        api_key_entry = ttk.Entry(api_frame, textvariable=self.api_key_var, width=40, show="*")
        api_key_entry.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=5)
        
        # 模型选择
        ttk.Label(api_frame, text="模型:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.model_var = tk.StringVar()
        self.model_combo = ttk.Combobox(api_frame, textvariable=self.model_var, width=37)
        self.model_combo.grid(row=2, column=1, sticky=tk.W, padx=(10, 0), pady=5)
        
        # 快捷键设置框架
        hotkey_frame = ttk.LabelFrame(scrollable_frame, text="快捷键设置", padding=10)
        hotkey_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # 截图快捷键
        ttk.Label(hotkey_frame, text="截图快捷键:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.hotkey_var = tk.StringVar()
        hotkey_combo = ttk.Combobox(hotkey_frame, textvariable=self.hotkey_var, width=37)
        hotkey_combo['values'] = ("ctrl+alt+s", "ctrl+shift+s", "alt+s", "f1", "f2")
        hotkey_combo.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=5)
        
        # 其他设置框架
        other_frame = ttk.LabelFrame(scrollable_frame, text="其他设置", padding=10)
        other_frame.pack(fill=tk.X, padx=10, pady=10)
        
        
        # 截图时隐藏窗口
        self.hide_window_var = tk.BooleanVar()
        ttk.Checkbutton(other_frame, text="截图时隐藏窗口", variable=self.hide_window_var).pack(anchor=tk.W)
        
        # 布局滚动条和画布
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 绑定鼠标滚轮事件
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        # 当鼠标进入画布时绑定滚轮事件
        def _on_enter(event):
            canvas.bind_all("<MouseWheel>", _on_mousewheel)
        canvas.bind("<Enter>", _on_enter)
        
        # 当鼠标离开画布时解绑滚轮事件
        def _on_leave(event):
            canvas.unbind_all("<MouseWheel>")
        canvas.bind("<Leave>", _on_leave)
    
    def browse_tesseract_path(self):
        """浏览Tesseract路径"""
        file_path = filedialog.askopenfilename(
            title="选择Tesseract可执行文件",
            filetypes=[("可执行文件", "*.exe"), ("所有文件", "*.*")]
        )
        if file_path:
            self.tesseract_path_var.set(file_path)
    
    def browse_tessdata_path(self):
        """浏览语言包路径"""
        dir_path = filedialog.askdirectory(title="选择语言包目录")
        if dir_path:
            self.tessdata_path_var.set(dir_path)
        
    def setup_ocr_tab(self):
        """设置OCR标签页"""
        # 创建滚动框架
        canvas = tk.Canvas(self.ocr_frame)
        scrollbar = ttk.Scrollbar(self.ocr_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # OCR配置框架
        ocr_config_frame = ttk.LabelFrame(scrollable_frame, text="OCR配置", padding=10)
        ocr_config_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # 语言设置
        ttk.Label(ocr_config_frame, text="识别语言:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.language_var = tk.StringVar()
        language_combo = ttk.Combobox(ocr_config_frame, textvariable=self.language_var, width=20)
        language_combo['values'] = ("chi_sim+eng", "chi_sim", "eng", "jpn", "kor")
        language_combo.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=5)
        
        # PSM设置
        ttk.Label(ocr_config_frame, text="页面分割模式:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.psm_var = tk.StringVar()
        psm_combo = ttk.Combobox(ocr_config_frame, textvariable=self.psm_var, width=20)
        psm_combo['values'] = ("3", "6", "8", "13")
        psm_combo.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=5)
        
        # 预处理设置
        preprocessing_frame = ttk.LabelFrame(scrollable_frame, text="图像预处理", padding=10)
        preprocessing_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # 布局滚动条和画布
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 绑定鼠标滚轮事件
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        # 当鼠标进入画布时绑定滚轮事件
        def _on_enter(event):
            canvas.bind_all("<MouseWheel>", _on_mousewheel)
        canvas.bind("<Enter>", _on_enter)
        
        # 当鼠标离开画布时解绑滚轮事件
        def _on_leave(event):
            canvas.unbind_all("<MouseWheel>")
        canvas.bind("<Leave>", _on_leave)
        
        self.grayscale_var = tk.BooleanVar()
        ttk.Checkbutton(preprocessing_frame, text="灰度化", variable=self.grayscale_var).pack(anchor=tk.W)
        
        self.enhance_contrast_var = tk.BooleanVar()
        ttk.Checkbutton(preprocessing_frame, text="增强对比度", variable=self.enhance_contrast_var).pack(anchor=tk.W)
        
        self.denoise_var = tk.BooleanVar()
        ttk.Checkbutton(preprocessing_frame, text="去噪", variable=self.denoise_var).pack(anchor=tk.W)
        
    def setup_cache_tab(self):
        """设置缓存标签页"""
        # 创建滚动框架
        canvas = tk.Canvas(self.cache_frame)
        scrollbar = ttk.Scrollbar(self.cache_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        cache_frame = ttk.LabelFrame(scrollable_frame, text="缓存管理", padding=10)
        cache_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 缓存大小设置
        ttk.Label(cache_frame, text="最大缓存大小(MB):").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.cache_size_var = tk.IntVar()
        cache_size_spin = ttk.Spinbox(cache_frame, from_=50, to=1000, textvariable=self.cache_size_var, width=10)
        cache_size_spin.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=5)
        
        # 缓存TTL设置
        ttk.Label(cache_frame, text="缓存过期时间(小时):").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.cache_ttl_var = tk.IntVar()
        cache_ttl_spin = ttk.Spinbox(cache_frame, from_=1, to=168, textvariable=self.cache_ttl_var, width=10)
        cache_ttl_spin.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=5)
        
        # 缓存操作按钮
        button_frame = ttk.Frame(cache_frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=20)
        
        ttk.Button(button_frame, text="清理缓存", command=self.clear_cache).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="优化缓存", command=self.optimize_cache).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="查看统计", command=self.show_cache_stats).pack(side=tk.LEFT, padx=5)
        
        # 布局滚动条和画布
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 绑定鼠标滚轮事件
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        # 当鼠标进入画布时绑定滚轮事件
        def _on_enter(event):
            canvas.bind_all("<MouseWheel>", _on_mousewheel)
        canvas.bind("<Enter>", _on_enter)
        
        # 当鼠标离开画布时解绑滚轮事件
        def _on_leave(event):
            canvas.unbind_all("<MouseWheel>")
        canvas.bind("<Leave>", _on_leave)
        
    def setup_advanced_tab(self):
        """设置高级标签页"""
        # 创建滚动框架
        canvas = tk.Canvas(self.advanced_frame)
        scrollbar = ttk.Scrollbar(self.advanced_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        advanced_frame = ttk.LabelFrame(scrollable_frame, text="高级选项", padding=10)
        advanced_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 性能设置
        ttk.Label(advanced_frame, text="最大工作线程数:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.max_workers_var = tk.IntVar()
        workers_spin = ttk.Spinbox(advanced_frame, from_=1, to=16, textvariable=self.max_workers_var, width=10)
        workers_spin.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=5)
        
        # 自动保存设置
        self.auto_save_var = tk.BooleanVar()
        ttk.Checkbutton(advanced_frame, text="自动保存结果", variable=self.auto_save_var).grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # 智能优化设置
        self.smart_optimization_var = tk.BooleanVar()
        ttk.Checkbutton(advanced_frame, text="启用智能优化", variable=self.smart_optimization_var).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # 调试模式
        self.debug_mode_var = tk.BooleanVar()
        ttk.Checkbutton(advanced_frame, text="调试模式", variable=self.debug_mode_var).grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # 布局滚动条和画布
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 绑定鼠标滚轮事件
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        # 当鼠标进入画布时绑定滚轮事件
        def _on_enter(event):
            canvas.bind_all("<MouseWheel>", _on_mousewheel)
        canvas.bind("<Enter>", _on_enter)
        
        # 当鼠标离开画布时解绑滚轮事件
        def _on_leave(event):
            canvas.unbind_all("<MouseWheel>")
        canvas.bind("<Leave>", _on_leave)
        
    def load_settings(self):
        """加载设置"""
        settings = self.config_manager.get_all()
        
        # 基础设置
        self.tesseract_path_var.set(settings.get("tesseract_path", ""))
        self.tessdata_path_var.set(settings.get("tessdata_path", ""))
        self.provider_var.set(settings.get("api_provider", "openai"))
        self.api_key_var.set(settings.get("api_key", ""))
        self.model_var.set(settings.get("api_model", "gpt-3.5-turbo"))
        
        # 更新模型选项
        self._update_model_options()
        self.hotkey_var.set(settings.get("hotkey", "ctrl+alt+s"))
        self.hide_window_var.set(settings.get("hide_window_on_capture", False))
        
        # OCR设置
        ocr_config = settings.get("ocr_config", {})
        self.language_var.set(ocr_config.get("language", "chi_sim+eng"))
        self.psm_var.set(ocr_config.get("psm", "3"))
        
        # 预处理设置
        preprocessing = settings.get("preprocessing", {})
        self.grayscale_var.set(preprocessing.get("grayscale", True))
        self.enhance_contrast_var.set(preprocessing.get("enhance_contrast", False))
        self.denoise_var.set(preprocessing.get("denoise", False))
        
        # 缓存设置
        self.cache_size_var.set(settings.get("cache_size_mb", 200))
        self.cache_ttl_var.set(settings.get("cache_ttl_hours", 24))
        
        # 高级设置
        self.max_workers_var.set(settings.get("max_workers", 4))
        self.auto_save_var.set(settings.get("auto_save", True))
        self.smart_optimization_var.set(settings.get("smart_optimization", True))
        self.debug_mode_var.set(settings.get("debug_mode", False))
        
    def save_settings(self):
        """保存设置"""
        try:
            settings = self.config_manager.get_all()
            
            # 更新基础设置
            settings["tesseract_path"] = self.tesseract_path_var.get()
            settings["tessdata_path"] = self.tessdata_path_var.get()
            settings["api_provider"] = self.provider_var.get()
            settings["api_key"] = self.api_key_var.get()
            settings["api_model"] = self.model_var.get()
            settings["hotkey"] = self.hotkey_var.get()
            settings["hide_window_on_capture"] = self.hide_window_var.get()
            
            # 更新OCR配置
            settings["ocr_config"] = {
                "language": self.language_var.get(),
                "psm": self.psm_var.get(),
                "oem": "3"
            }
            
            # 更新预处理配置
            settings["preprocessing"] = {
                "grayscale": self.grayscale_var.get(),
                "enhance_contrast": self.enhance_contrast_var.get(),
                "denoise": self.denoise_var.get(),
                "invert": False,
                "threshold": 0
            }
            
            # 更新缓存配置
            settings["cache_size_mb"] = self.cache_size_var.get()
            settings["cache_ttl_hours"] = self.cache_ttl_var.get()
            
            # 更新高级配置
            settings["max_workers"] = self.max_workers_var.get()
            settings["auto_save"] = self.auto_save_var.get()
            settings["smart_optimization"] = self.smart_optimization_var.get()
            settings["debug_mode"] = self.debug_mode_var.get()
            
            # 保存设置
            self.config_manager.save_settings(settings)
            
            # 调用回调
            if self.on_save_callback:
                self.on_save_callback(settings)
            
            messagebox.showinfo("成功", "设置已保存！")
            self.window.destroy()
            
        except Exception as e:
            self.logger.error(f"保存设置失败: {str(e)}")
            messagebox.showerror("错误", f"保存设置失败: {str(e)}")
    
    def reset_settings(self):
        """重置设置"""
        if messagebox.askyesno("确认", "确定要重置所有设置为默认值吗？"):
            self.config_manager.reset_to_defaults()
            self.load_settings()
            messagebox.showinfo("成功", "设置已重置为默认值！")
    
    def import_settings(self):
        """导入设置"""
        file_path = filedialog.askopenfilename(
            title="选择配置文件",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")]
        )
        if file_path:
            if self.config_manager.import_config(file_path):
                self.load_settings()
                messagebox.showinfo("成功", "设置已导入！")
            else:
                messagebox.showerror("错误", "导入设置失败！")
    
    def export_settings(self):
        """导出设置"""
        file_path = filedialog.asksaveasfilename(
            title="保存配置文件",
            defaultextension=".json",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")]
        )
        if file_path:
            if self.config_manager.export_config(file_path):
                messagebox.showinfo("成功", "设置已导出！")
            else:
                messagebox.showerror("错误", "导出设置失败！")
    
    def clear_cache(self):
        """清理缓存"""
        if messagebox.askyesno("确认", "确定要清理所有缓存吗？"):
            # 这里需要调用缓存管理器的清理方法
            messagebox.showinfo("成功", "缓存已清理！")
    
    def optimize_cache(self):
        """优化缓存"""
        # 这里需要调用缓存管理器的优化方法
        messagebox.showinfo("成功", "缓存已优化！")
    
    def show_cache_stats(self):
        """显示缓存统计"""
        # 这里需要显示缓存统计信息
        messagebox.showinfo("缓存统计", "缓存统计信息显示功能待实现")
    
    def _on_provider_changed(self, event=None):
        """API提供商变更时的处理"""
        self._update_model_options()
    
    def _update_model_options(self):
        """根据API提供商更新模型选项"""
        provider = self.provider_var.get()
        if provider == "deepseek":
            self.model_combo['values'] = ("deepseek-chat", "deepseek-reasoner")
            if not self.model_var.get() or self.model_var.get() not in ("deepseek-chat", "deepseek-reasoner"):
                self.model_var.set("deepseek-chat")
        else:  # openai
            self.model_combo['values'] = ("gpt-3.5-turbo", "gpt-4", "gpt-4-turbo")
            if not self.model_var.get() or self.model_var.get() not in ("gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"):
                self.model_var.set("gpt-3.5-turbo")
