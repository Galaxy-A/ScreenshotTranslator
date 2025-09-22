# result_window.py - 结果窗口功能
import tkinter as tk
from tkinter import messagebox, filedialog, ttk
from PIL import Image, ImageTk, ImageOps, ImageEnhance
import re
import socket
import threading
import time
import logging
import sys
import os

def resource_path(relative_path):
    """获取资源绝对路径，支持开发环境和PyInstaller打包环境"""
    try:
        # PyInstaller创建的临时文件夹路径
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

class ResultWindow:
    """处理结果显示窗口的类"""

    def __init__(self, master, screenshot=None, ocr_result="", app=None,recapture_callback=None):
        # 获取日志记录器
        self.logger = logging.getLogger("ResultWindow")
        # 创建结果窗口

        self.master = master
        self.app = app  # 保存应用实例引用
        self.recapture_callback = recapture_callback
        self.window = tk.Toplevel(master)
        self.window.title("OCR识别结果")
        self.window.geometry("800x600")
        self.window.minsize(600, 500)
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)  # 处理关闭事件

        # 保存当前截图
        self.current_screenshot = screenshot
        self.ocr_result = ocr_result
        self.translated_text = ""
        self.translation_in_progress = False  # 跟踪翻译状态
        self.translation_start_time = 0  # 记录翻译开始时间
        self.last_update_time = 0  # 记录上次更新UI的时间
        self.original_ocr_text = ocr_result  # 保存原始OCR文本

        # 创建UI
        self._create_ui()

        # 如果有初始结果，显示它
        if ocr_result:
            self.display_result(ocr_result, screenshot)

        # 结果窗口初始化完成

    def on_close(self):
        """处理窗口关闭事件"""
        # 关闭结果窗口
        self.translation_in_progress = False  # 停止翻译
        
        # 检查窗口是否还存在，避免重复销毁
        try:
            if hasattr(self, 'window') and self.window and self.window.winfo_exists():
                self.window.destroy()
        except tk.TclError:
            # 窗口已经被销毁，忽略错误
            pass
        except Exception as e:
            # 其他异常也忽略，避免影响程序运行
            self.logger.warning(f"关闭窗口时出现异常: {str(e)}")

    def recapture(self):
        """重新截图"""
        # 重新截图
        self.window.withdraw()  # 隐藏结果窗口
        
        if self.recapture_callback:
            self.recapture_callback()
        else:
            messagebox.showwarning("警告", "重新截图功能不可用")

    def edit_text(self):
        """编辑OCR文本"""
        # 编辑OCR文本
        
        # 创建编辑窗口
        edit_window = tk.Toplevel(self.window)
        edit_window.title("编辑识别文本")
        edit_window.geometry("600x400")
        edit_window.transient(self.window)
        
        # 创建主框架
        main_frame = ttk.Frame(edit_window, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        ttk.Label(
            main_frame,
            text="编辑识别文本",
            font=("微软雅黑", 12, "bold")
        ).pack(pady=(0, 15))
        
        # 文本编辑区域
        text_frame = ttk.LabelFrame(main_frame, text="文本内容", padding=10)
        text_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        # 创建文本编辑框
        text_editor = tk.Text(text_frame, wrap=tk.WORD, font=("微软雅黑", 11))
        text_editor.pack(fill=tk.BOTH, expand=True)
        
        # 插入当前文本
        text_editor.insert(1.0, self.ocr_result)
        
        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        def save_edited_text():
            """保存编辑后的文本"""
            edited_text = text_editor.get(1.0, tk.END).strip()
            if edited_text != self.ocr_result:
                self.ocr_result = edited_text
                # 更新显示
                if hasattr(self, 'text_area'):
                    self.text_area.config(state=tk.NORMAL)
                    self.text_area.delete(1.0, tk.END)
                    self.text_area.insert(1.0, edited_text)
                    self.text_area.config(state=tk.DISABLED)
                
                # 更新应用中的结果
                if self.app:
                    self.app.ocr_result = edited_text
                    self.app.last_action.set(f"最近操作: 编辑了 {len(edited_text)} 个字符")
                
                # 文本已编辑
                messagebox.showinfo("成功", "文本已更新")
            
            edit_window.destroy()
        
        ttk.Button(
            button_frame,
            text="保存",
            command=save_edited_text
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame,
            text="取消",
            command=edit_window.destroy
        ).pack(side=tk.RIGHT, padx=5)

    def show_stats(self):
        """显示统计信息"""
        if self.app and hasattr(self.app, 'show_stats'):
            self.app.show_stats()

    def show_settings(self):
        """显示设置窗口"""
        if self.app and hasattr(self.app, 'show_settings'):
            self.app.show_settings()

    def load_history(self):
        """加载历史记录"""
        try:
            # 清空现有记录
            for item in self.history_tree.get_children():
                self.history_tree.delete(item)
            
            # 从缓存中加载历史记录
            if self.app and hasattr(self.app, 'advanced_cache'):
                cache_stats = self.app.advanced_cache.get_stats()
                # 这里可以扩展为从文件或数据库加载历史记录
                # 目前显示缓存统计信息
                if cache_stats.get('total_requests', 0) > 0:
                    self.history_tree.insert("", 0, values=(
                        time.strftime('%Y-%m-%d %H:%M:%S'),
                        "缓存",
                        f"总请求: {cache_stats.get('total_requests', 0)}"
                    ))
            
            # 添加当前结果到历史记录
            if self.ocr_result:
                preview = self.ocr_result[:50] + "..." if len(self.ocr_result) > 50 else self.ocr_result
                self.history_tree.insert("", 0, values=(
                    time.strftime('%Y-%m-%d %H:%M:%S'),
                    len(self.ocr_result),
                    preview
                ))
                
        except Exception as e:
            self.logger.error(f"加载历史记录失败: {str(e)}")

    def refresh_history(self):
        """刷新历史记录"""
        self.load_history()
        messagebox.showinfo("刷新", "历史记录已刷新")

    def view_history_detail(self):
        """查看历史记录详情"""
        selection = self.history_tree.selection()
        if not selection:
            messagebox.showwarning("提示", "请选择一条历史记录")
            return
        
        item = self.history_tree.item(selection[0])
        values = item['values']
        
        # 创建详情窗口
        detail_window = tk.Toplevel(self.window)
        detail_window.title("历史记录详情")
        detail_window.geometry("600x400")
        detail_window.transient(self.window)
        
        # 创建主框架
        main_frame = ttk.Frame(detail_window, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        ttk.Label(
            main_frame,
            text="历史记录详情",
            font=("微软雅黑", 12, "bold")
        ).pack(pady=(0, 15))
        
        # 信息框架
        info_frame = ttk.LabelFrame(main_frame, text="记录信息", padding=10)
        info_frame.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Label(info_frame, text=f"识别时间: {values[0]}").pack(anchor=tk.W)
        ttk.Label(info_frame, text=f"字符数: {values[1]}").pack(anchor=tk.W)
        
        # 内容框架
        content_frame = ttk.LabelFrame(main_frame, text="识别内容", padding=10)
        content_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        # 文本显示区域
        text_display = tk.Text(content_frame, wrap=tk.WORD, font=("微软雅黑", 11))
        text_display.pack(fill=tk.BOTH, expand=True)
        
        # 显示当前OCR结果
        text_display.insert(1.0, self.ocr_result)
        text_display.config(state=tk.DISABLED)
        
        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        ttk.Button(
            button_frame,
            text="关闭",
            command=detail_window.destroy
        ).pack(side=tk.RIGHT, padx=5)

    def clear_history(self):
        """清除历史记录"""
        if messagebox.askyesno("确认清除", "确定要清除所有历史记录吗？"):
            # 清空Treeview
            for item in self.history_tree.get_children():
                self.history_tree.delete(item)
            
            # 清除缓存统计
            if self.app and hasattr(self.app, 'advanced_cache'):
                self.app.advanced_cache.clear_stats()
            
            messagebox.showinfo("成功", "历史记录已清除")

    def _create_ui(self):
        """创建结果窗口UI"""
        main_frame = ttk.Frame(self.window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # 识别结果标签页
        self.create_result_tab()

        # 截图预览标签页
        self.create_image_tab()

        # 翻译标签页
        self.create_translation_tab()
        
        # 历史记录标签页
        self.create_history_tab()

        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)

        # 主要操作按钮
        main_buttons = ttk.Frame(button_frame)
        main_buttons.pack(side=tk.LEFT, fill=tk.X, expand=True)

        ttk.Button(
            main_buttons,
            text="📷 重新截图",
            command=self.recapture,
            width=15
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            main_buttons,
            text="✏️ 编辑文本",
            command=self.edit_text,
            width=15
        ).pack(side=tk.LEFT, padx=5)


        # 辅助操作按钮
        aux_buttons = ttk.Frame(button_frame)
        aux_buttons.pack(side=tk.RIGHT)

        ttk.Button(
            aux_buttons,
            text="📊 统计",
            command=self.show_stats,
            width=12
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            aux_buttons,
            text="⚙️ 设置",
            command=self.show_settings,
            width=12
        ).pack(side=tk.LEFT, padx=5)




    def create_result_tab(self):
        """创建识别结果标签页"""
        result_frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(result_frame, text="识别结果")

        scrollbar = ttk.Scrollbar(result_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.text_area = tk.Text(
            result_frame,
            wrap=tk.WORD,
            yscrollcommand=scrollbar.set,
            font=("微软雅黑", 11),
            padx=10,
            pady=10,
            height=15
        )
        self.text_area.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.text_area.yview)

        # 添加翻译按钮到结果标签页
        translate_btn_frame = ttk.Frame(result_frame)
        translate_btn_frame.pack(fill=tk.X, pady=5)

        # 为翻译按钮添加特殊样式
        style = ttk.Style()
        style.configure("Accent.TButton", foreground="white", background="#4CAF50", font=("微软雅黑", 10, "bold"))
        ttk.Button(
            translate_btn_frame,
            text="翻译此文本",
            command=self.translate_from_result,
            style="Accent.TButton",
            width=15
        ).pack(side=tk.RIGHT, padx=5)

        ttk.Button(
            translate_btn_frame,
            text="重新截图",
            command=self.close_and_recapture,
            width=12
        ).pack(side=tk.LEFT, padx=5)


    def translate_from_result(self):
        """从结果标签页翻译文本"""
        # 从结果标签页触发翻译
        text_to_translate = self.text_area.get(1.0, tk.END).strip()
        if text_to_translate:
            self.translate_input.delete(1.0, tk.END)
            self.translate_input.insert(tk.END, text_to_translate)
            self.notebook.select(2)  # 切换到翻译标签页
            self.translate_text()
        else:
            self.logger.warning("尝试翻译空文本")

    def create_image_tab(self):
        """创建截图预览标签页"""
        image_frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(image_frame, text="截图预览")

        # 创建选项卡容器
        image_notebook = ttk.Notebook(image_frame)
        image_notebook.pack(fill=tk.BOTH, expand=True)

        # 原始图像标签页
        original_frame = ttk.Frame(image_notebook, padding=5)
        image_notebook.add(original_frame, text="原始图像")

        self.original_img_label = ttk.Label(original_frame)
        self.original_img_label.pack(fill=tk.BOTH, expand=True)

        # 预处理图像标签页
        processed_frame = ttk.Frame(image_notebook, padding=5)
        image_notebook.add(processed_frame, text="预处理后")

        self.processed_img_label = ttk.Label(processed_frame)
        self.processed_img_label.pack(fill=tk.BOTH, expand=True)

        # 添加预处理说明
        ttk.Label(
            image_frame,
            text="预处理可提高OCR识别精度，具体设置可在主界面设置中调整",
            font=("微软雅黑", 8),
            foreground="#666666"
        ).pack(side=tk.BOTTOM, fill=tk.X, pady=(5, 0))

    def create_translation_tab(self):
        """创建翻译标签页"""
        translation_frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(translation_frame, text="翻译")

        # 输入框区域
        input_frame = ttk.LabelFrame(translation_frame, text="待翻译文本")
        input_frame.pack(fill=tk.X, pady=5)

        self.translate_input = tk.Text(
            input_frame,
            height=8,
            wrap=tk.WORD,
            font=("微软雅黑", 11),
            padx=10,
            pady=10
        )
        self.translate_input.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 翻译设置区域
        setting_frame = ttk.Frame(translation_frame)
        setting_frame.pack(fill=tk.X, pady=5)

        # 语言选择区域
        lang_frame = ttk.Frame(setting_frame)
        lang_frame.pack(side=tk.LEFT, padx=5)
        
        # 源语言选择
        ttk.Label(lang_frame, text="源语言:").pack(side=tk.LEFT, padx=(0, 5))
        self.source_lang_var = tk.StringVar(value="自动检测")
        source_combo = ttk.Combobox(
            lang_frame,
            textvariable=self.source_lang_var,
            width=12,
            state="readonly"
        )
        
        # 目标语言选择
        ttk.Label(lang_frame, text="目标语言:").pack(side=tk.LEFT, padx=(10, 5))
        self.target_lang_var = tk.StringVar(value="中文")
        target_combo = ttk.Combobox(
            lang_frame,
            textvariable=self.target_lang_var,
            width=12,
            state="readonly"
        )
        
        # 定义支持的语言
        self.supported_languages = [
            ("自动检测", "auto"),
            ("中文", "zh"),
            ("英文", "en"),
            ("日文", "ja"),
            ("韩文", "ko"),
            ("法文", "fr"),
            ("德文", "de"),
            ("西班牙文", "es"),
            ("俄文", "ru"),
            ("阿拉伯文", "ar"),
            ("意大利文", "it"),
            ("葡萄牙文", "pt"),
            ("荷兰文", "nl"),
            ("瑞典文", "sv"),
            ("挪威文", "no"),
            ("丹麦文", "da"),
            ("芬兰文", "fi"),
            ("波兰文", "pl"),
            ("捷克文", "cs"),
            ("匈牙利文", "hu"),
            ("希腊文", "el"),
            ("土耳其文", "tr"),
            ("希伯来文", "he"),
            ("泰文", "th"),
            ("越南文", "vi"),
            ("印尼文", "id"),
            ("马来文", "ms"),
            ("印地文", "hi"),
            ("乌尔都文", "ur"),
            ("波斯文", "fa")
        ]
        
        # 设置下拉框选项
        source_combo['values'] = [lang[0] for lang in self.supported_languages]
        target_combo['values'] = [lang[0] for lang in self.supported_languages[1:]]  # 目标语言不包含"自动检测"
        
        source_combo.pack(side=tk.LEFT, padx=(0, 5))
        target_combo.pack(side=tk.LEFT, padx=(0, 5))
        
        # 语言代码映射
        self.lang_code_mapping = {lang[0]: lang[1] for lang in self.supported_languages}
        
        # 绑定语言选择变化事件
        source_combo.bind('<<ComboboxSelected>>', self._on_language_changed)
        target_combo.bind('<<ComboboxSelected>>', self._on_language_changed)

        # 翻译按钮区域
        btn_frame = ttk.Frame(translation_frame)
        btn_frame.pack(fill=tk.X, pady=5)

        # 为翻译按钮添加特殊样式
        style = ttk.Style()
        style.configure("Accent.TButton", foreground="white", background="#4CAF50", font=("微软雅黑", 10, "bold"))
        
        self.translate_btn = ttk.Button(
            btn_frame,
            text="翻译",
            command=self.translate_text,
            width=12,
            style="Accent.TButton"
        )
        self.translate_btn.pack(side=tk.LEFT, padx=5)

        # 取消按钮
        self.cancel_btn = ttk.Button(
            btn_frame,
            text="取消翻译",
            command=self.cancel_translation,
            width=12,
            state=tk.DISABLED
        )
        self.cancel_btn.pack(side=tk.LEFT, padx=5)

        # 句数选择框
        ttk.Label(btn_frame, text="句数:").pack(side=tk.LEFT, padx=(10, 5))
        self.sentence_count_var = tk.StringVar(value="3")
        sentence_count_combo = ttk.Combobox(
            btn_frame,
            textvariable=self.sentence_count_var,
            width=5,
            state="readonly"
        )
        sentence_count_combo['values'] = ("1", "2", "3", "4", "5")
        sentence_count_combo.pack(side=tk.LEFT, padx=(0, 5))

        # 生成对话按钮
        self.generate_dialogue_btn = ttk.Button(
            btn_frame,
            text="生成对话",
            command=self.generate_dialogue,
            width=12,
            state=tk.DISABLED
        )
        self.generate_dialogue_btn.pack(side=tk.LEFT, padx=5)


        # 结果框区域
        result_frame = ttk.LabelFrame(translation_frame, text="翻译结果")
        result_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        scrollbar = ttk.Scrollbar(result_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.translate_output = tk.Text(
            result_frame,
            wrap=tk.WORD,
            yscrollcommand=scrollbar.set,
            font=("微软雅黑", 11),
            padx=10,
            pady=10,
            state=tk.DISABLED  # 初始禁用
        )
        self.translate_output.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.translate_output.yview)
    
    def _on_language_changed(self, event=None):
        """语言选择变化时的处理"""
        source_lang = self.source_lang_var.get()
        target_lang = self.target_lang_var.get()
        
        # 如果源语言和目标语言相同，自动调整目标语言
        if source_lang == target_lang and source_lang != "自动检测":
            # 找到当前源语言的索引
            source_index = next(i for i, (name, code) in enumerate(self.supported_languages) if name == source_lang)
            # 选择下一个不同的语言作为目标语言
            next_index = (source_index + 1) % len(self.supported_languages[1:])  # 跳过"自动检测"
            self.target_lang_var.set(self.supported_languages[1:][next_index][0])
        
        self.logger.debug(f"语言选择更新: {source_lang} → {self.target_lang_var.get()}")

    def _show_language_error_dialog(self):
        """显示语言选择错误对话框并提供恢复选项"""
        # 创建错误对话框
        error_dialog = tk.Toplevel(self.window)
        error_dialog.title("语言选择错误")
        error_dialog.geometry("400x200")
        error_dialog.resizable(False, False)
        
        # 居中显示
        error_dialog.transient(self.window)
        error_dialog.grab_set()
        
        # 主框架
        main_frame = ttk.Frame(error_dialog, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 错误图标和消息
        icon_frame = ttk.Frame(main_frame)
        icon_frame.pack(fill=tk.X, pady=(0, 15))
        
        # 错误图标（使用Unicode字符）
        error_icon = ttk.Label(icon_frame, text="⚠️", font=("微软雅黑", 24))
        error_icon.pack(side=tk.LEFT, padx=(0, 10))
        
        # 错误消息
        message_frame = ttk.Frame(icon_frame)
        message_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        ttk.Label(message_frame, text="语言选择错误", font=("微软雅黑", 14, "bold")).pack(anchor=tk.W)
        ttk.Label(message_frame, text="源语言和目标语言不能相同，请重新选择", font=("微软雅黑", 10)).pack(anchor=tk.W, pady=(5, 0))
        
        # 当前语言选择显示
        current_frame = ttk.LabelFrame(main_frame, text="当前选择", padding=10)
        current_frame.pack(fill=tk.X, pady=(0, 15))
        
        source_lang = self.source_lang_var.get()
        target_lang = self.target_lang_var.get()
        
        ttk.Label(current_frame, text=f"源语言: {source_lang}", font=("微软雅黑", 10)).pack(anchor=tk.W)
        ttk.Label(current_frame, text=f"目标语言: {target_lang}", font=("微软雅黑", 10)).pack(anchor=tk.W)
        
        # 按钮区域
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        # 自动修复按钮
        auto_fix_btn = ttk.Button(
            button_frame,
            text="自动修复",
            command=lambda: self._auto_fix_language_selection(error_dialog),
            width=12
        )
        auto_fix_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # 手动选择按钮
        manual_select_btn = ttk.Button(
            button_frame,
            text="手动选择",
            command=lambda: self._manual_select_language(error_dialog),
            width=12
        )
        manual_select_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # 取消按钮
        cancel_btn = ttk.Button(
            button_frame,
            text="取消",
            command=error_dialog.destroy,
            width=12
        )
        cancel_btn.pack(side=tk.RIGHT)
        
        # 设置焦点
        auto_fix_btn.focus_set()
    
    def _auto_fix_language_selection(self, dialog):
        """自动修复语言选择"""
        source_lang = self.source_lang_var.get()
        target_lang = self.target_lang_var.get()
        
        # 如果源语言是"自动检测"，保持目标语言为"中文"
        if source_lang == "自动检测":
            self.target_lang_var.set("中文")
            self.logger.info("自动修复：保持自动检测源语言，目标语言设为中文")
        else:
            # 否则，将目标语言设为"中文"
            self.target_lang_var.set("中文")
            self.logger.info(f"自动修复：源语言保持{source_lang}，目标语言设为中文")
        
        dialog.destroy()
        
        # 显示修复成功消息
        messagebox.showinfo("修复完成", "语言选择已自动修复，现在可以开始翻译了！")
    
    def _manual_select_language(self, dialog):
        """手动选择语言"""
        dialog.destroy()
        
        # 创建语言选择对话框
        lang_dialog = tk.Toplevel(self.window)
        lang_dialog.title("手动选择语言")
        lang_dialog.geometry("500x300")
        lang_dialog.resizable(False, False)
        
        # 居中显示
        lang_dialog.transient(self.window)
        lang_dialog.grab_set()
        
        # 主框架
        main_frame = ttk.Frame(lang_dialog, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        ttk.Label(main_frame, text="请选择翻译语言", font=("微软雅黑", 14, "bold")).pack(pady=(0, 20))
        
        # 语言选择框架
        lang_frame = ttk.Frame(main_frame)
        lang_frame.pack(fill=tk.X, pady=(0, 20))
        
        # 源语言选择
        source_frame = ttk.LabelFrame(lang_frame, text="源语言", padding=10)
        source_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(source_frame, text="源语言:").pack(side=tk.LEFT, padx=(0, 10))
        source_combo = ttk.Combobox(
            source_frame,
            textvariable=self.source_lang_var,
            width=20,
            state="readonly"
        )
        source_combo['values'] = [lang[0] for lang in self.supported_languages]
        source_combo.pack(side=tk.LEFT)
        
        # 目标语言选择
        target_frame = ttk.LabelFrame(lang_frame, text="目标语言", padding=10)
        target_frame.pack(fill=tk.X)
        
        ttk.Label(target_frame, text="目标语言:").pack(side=tk.LEFT, padx=(0, 10))
        target_combo = ttk.Combobox(
            target_frame,
            textvariable=self.target_lang_var,
            width=20,
            state="readonly"
        )
        target_combo['values'] = [lang[0] for lang in self.supported_languages[1:]]  # 跳过"自动检测"
        target_combo.pack(side=tk.LEFT)
        
        # 按钮区域
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        # 确认按钮
        confirm_btn = ttk.Button(
            button_frame,
            text="确认",
            command=lang_dialog.destroy,
            width=12
        )
        confirm_btn.pack(side=tk.RIGHT, padx=(10, 0))
        
        # 取消按钮
        cancel_btn = ttk.Button(
            button_frame,
            text="取消",
            command=lang_dialog.destroy,
            width=12
        )
        cancel_btn.pack(side=tk.RIGHT)
        
        # 设置焦点
        source_combo.focus_set()

    def create_history_tab(self):
        """创建历史记录标签页"""
        history_frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(history_frame, text="历史记录")

        # 历史记录列表框架
        list_frame = ttk.LabelFrame(history_frame, text="识别历史", padding=10)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # 创建Treeview显示历史记录
        columns = ("时间", "字符数", "预览")
        self.history_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=10)
        
        # 设置列标题
        self.history_tree.heading("时间", text="识别时间")
        self.history_tree.heading("字符数", text="字符数")
        self.history_tree.heading("预览", text="文本预览")
        
        # 设置列宽
        self.history_tree.column("时间", width=150)
        self.history_tree.column("字符数", width=80)
        self.history_tree.column("预览", width=300)

        # 添加滚动条
        history_scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=history_scrollbar.set)

        # 布局
        self.history_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        history_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 历史记录操作按钮
        history_btn_frame = ttk.Frame(history_frame)
        history_btn_frame.pack(fill=tk.X, pady=5)

        ttk.Button(
            history_btn_frame,
            text="🔄 刷新",
            command=self.refresh_history,
            width=12
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            history_btn_frame,
            text="📄 查看详情",
            command=self.view_history_detail,
            width=12
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            history_btn_frame,
            text="🗑️ 清除历史",
            command=self.clear_history,
            width=12
        ).pack(side=tk.LEFT, padx=5)

        # 绑定双击事件
        self.history_tree.bind("<Double-1>", lambda e: self.view_history_detail())

        # 加载历史记录
        self.load_history()

    def display_result(self, text, screenshot=None):
        """显示OCR结果和截图"""
        # 显示OCR结果
        # 更新当前截图
        if screenshot:
            self.current_screenshot = screenshot

        # 保存原始OCR文本
        self.original_ocr_text = text

        # 在识别结果标签页显示文本
        self.text_area.config(state=tk.NORMAL)
        self.text_area.delete(1.0, tk.END)
        self.text_area.insert(tk.END, text.strip())
        self.text_area.config(state=tk.NORMAL)

        # 在翻译标签页的输入框中显示文本
        self.translate_input.delete(1.0, tk.END)
        self.translate_input.insert(tk.END, text.strip())
        
        # 自动检测语言并设置目标语言
        self._auto_detect_and_set_target_language(text.strip())
        
        # 自动跳转到翻译标签页
        self.notebook.select(2)  # 切换到翻译标签页（索引2）

        # 更新图像预览
        self.update_image_preview()

        # 清除之前的翻译结果
        self.clear_translation_output()

    def clear_translation_output(self):
        """清除翻译结果"""
        self.logger.debug("清除翻译结果")
        self.translate_output.config(state=tk.NORMAL)
        self.translate_output.delete(1.0, tk.END)
        self.translate_output.config(state=tk.DISABLED)
        self.window.title("OCR识别结果")

    def update_image_preview(self):
        """更新图像预览"""
        if self.current_screenshot:
            try:
                # 直接使用当前截图
                image = self.current_screenshot

                # 创建图像的副本，避免修改原始图像
                image_copy = image.copy()

                width, height = image_copy.size
                max_size = 600
                if width > max_size or height > max_size:
                    ratio = min(max_size/width, max_size/height)
                    new_size = (int(width * ratio), int(height * ratio))
                    preview_img = image_copy.resize(new_size, Image.LANCZOS)
                else:
                    preview_img = image_copy

                # 显示原始图像
                tk_img = ImageTk.PhotoImage(preview_img)
                self.original_img_label.configure(image=tk_img)
                self.original_img_label.image = tk_img

                # 显示预处理后的图像
                processed_img = self.preprocess_image(preview_img)
                tk_processed_img = ImageTk.PhotoImage(processed_img)
                self.processed_img_label.configure(image=tk_processed_img)
                self.processed_img_label.image = tk_processed_img

                self.logger.debug("图像预览已更新")

            except Exception as e:
                self.logger.error(f"图像预览错误: {str(e)}")
        else:
            self.logger.warning("没有可用的截图用于预览")

    def preprocess_image(self, image):
        """对图像进行预处理（与OCR引擎相同的处理）"""
        # 灰度处理
        if self.app.settings["preprocessing"]["grayscale"]:
            image = image.convert('L')

        # 反色处理
        if self.app.settings["preprocessing"]["invert"]:
            image = ImageOps.invert(image)

        # 二值化处理
        threshold = self.app.settings["preprocessing"]["threshold"]
        if threshold > 0:
            image = image.point(lambda p: p > threshold and 255)

        # 增强对比度
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.5)

        return image

    def save_screenshot(self):
        """保存截图到文件"""
        # 保存截图
        if not self.current_screenshot:
            self.logger.warning("尝试保存截图但无可用截图")
            messagebox.showwarning("警告", "没有可用的截图")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG files", "*.png"), ("JPEG files", "*.jpg"), ("All files", "*.*")],
            title="保存截图"
        )
        if file_path:
            try:
                self.current_screenshot.save(file_path)
                self.logger.info(f"截图已保存到: {file_path}")
                messagebox.showinfo("保存成功", f"截图已保存到:\n{file_path}")
            except Exception as e:
                self.logger.error(f"保存截图失败: {str(e)}")
                messagebox.showerror("保存失败", f"无法保存截图:\n{str(e)}")

    def close_and_recapture(self):
        """关闭窗口并触发重新截图"""
        # 触发重新截图

        # 如果有重新截图回调函数，调用它
        if self.recapture_callback:
            # 延迟执行，确保窗口先关闭
            self.master.after(100, self.recapture_callback)

        # 关闭当前窗口
        self.window.destroy()

    def detect_language(self, text):
        """检测文本的主要语言"""
        self.logger.debug("检测文本语言")
        # 简单的语言检测：检查中文字符比例
        total_chars = len(text)
        if total_chars == 0:
            return "unknown"

        # 统计中文字符数量
        chinese_chars = sum(1 for char in text if '\u4e00' <= char <= '\u9fff')
        chinese_ratio = chinese_chars / total_chars

        # 如果中文字符超过30%，则认为是中文
        if chinese_ratio > 0.3:
            return "chinese"

        # 检查其他语言特征
        # 日文平假名和片假名
        hiragana_chars = sum(1 for char in text if '\u3040' <= char <= '\u309f')
        katakana_chars = sum(1 for char in text if '\u30a0' <= char <= '\u30ff')
        japanese_ratio = (hiragana_chars + katakana_chars) / total_chars
        
        # 韩文
        korean_chars = sum(1 for char in text if '\uac00' <= char <= '\ud7af')
        korean_ratio = korean_chars / total_chars
        
        # 阿拉伯文
        arabic_chars = sum(1 for char in text if '\u0600' <= char <= '\u06ff')
        arabic_ratio = arabic_chars / total_chars
        
        # 俄文
        cyrillic_chars = sum(1 for char in text if '\u0400' <= char <= '\u04ff')
        cyrillic_ratio = cyrillic_chars / total_chars
        
        # 法文、德文、西班牙文等拉丁语系
        latin_chars = sum(1 for char in text if '\u00c0' <= char <= '\u017f')
        latin_ratio = latin_chars / total_chars
        
        # 英文单词
        english_words = len(re.findall(r'\b[a-zA-Z]+\b', text))
        
        # 判断语言类型
        if japanese_ratio > 0.1:
            return "japanese"
        elif korean_ratio > 0.1:
            return "korean"
        elif arabic_ratio > 0.1:
            return "arabic"
        elif cyrillic_ratio > 0.1:
            return "russian"
        elif latin_ratio > 0.1 or english_words > 0:
            return "other_latin"  # 包括英文、法文、德文、西班牙文等
        else:
            return "unknown"

        return "unknown"

    def check_network_connection(self):
        """检查网络连接状态"""
        self.logger.debug("检查网络连接")
        try:
            # 尝试连接一个可靠的服务
            socket.create_connection(("www.baidu.com", 80), timeout=5)
            return True
        except OSError:
            self.logger.warning("网络连接不可用")
            return False



    def append_to_translation_output(self, text):
        """向翻译输出框追加文本"""
        self.translate_output.config(state=tk.NORMAL)
        self.translate_output.insert(tk.END, text)
        self.translate_output.see(tk.END)
        self.translate_output.config(state=tk.NORMAL)

    def translate_text(self):
        """翻译文本"""
        # 如果已经在翻译中，则不执行新的翻译
        if self.translation_in_progress:
            self.logger.warning("尝试启动新翻译但已有翻译在进行中")
            return

        # 检查是否已设置API密钥
        if not self.app.settings["api_key"]:
            provider_name = "DeepSeek" if self.app.settings.get("api_provider") == "deepseek" else "OpenAI"
            self.logger.error("尝试翻译但未配置API密钥")
            messagebox.showerror("API密钥缺失", f"请先在设置中配置{provider_name} API密钥")
            return

        # 检查网络连接
        if not self.check_network_connection():
            self.logger.error("尝试翻译但无网络连接")
            messagebox.showerror("网络错误", "无法连接到互联网，请检查网络连接后重试")
            return

        # 获取要翻译的文本
        text_to_translate = self.translate_input.get(1.0, tk.END).strip()

        if not text_to_translate:
            self.logger.warning("尝试翻译空文本")
            messagebox.showinfo("提示", "没有可翻译的文本")
            return

        # 记录翻译文本长度
        char_count = len(text_to_translate)
        # 开始翻译

        # 标记翻译开始
        self.translation_in_progress = True
        self.translate_btn.config(state=tk.DISABLED)
        self.cancel_btn.config(state=tk.NORMAL)
        self.generate_dialogue_btn.config(state=tk.DISABLED)  # 禁用生成对话按钮
        self.translation_start_time = time.time()

        # 切换到翻译标签页
        self.notebook.select(2)  # 切换到第三个标签页（翻译）

        # 显示翻译中状态
        self.update_translation_output("翻译中，请稍候...")

        # 确定翻译方向
        source_lang = self.source_lang_var.get()
        target_lang = self.target_lang_var.get()
        
        # 获取语言代码
        source_code = self.lang_code_mapping.get(source_lang, "auto")
        target_code = self.lang_code_mapping.get(target_lang, "zh")
        
        # 如果是自动检测源语言，则检测文本语言
        if source_code == "auto":
            detected_lang = self.detect_language(text_to_translate)
            # 将检测结果映射到语言代码
            lang_mapping = {
                "chinese": "zh",
                "english": "en", 
                "japanese": "ja",
                "korean": "ko",
                "russian": "ru",
                "arabic": "ar",
                "other_latin": "en"  # 默认映射到英文
            }
            source_code = lang_mapping.get(detected_lang, "en")
            self.logger.info(f"自动检测到源语言: {detected_lang} → {source_code}")
        
        # 构建翻译方向代码
        direction = f"{source_code}2{target_code}"
        
        # 如果源语言和目标语言相同，显示恢复翻译按钮
        if source_code == target_code:
            self.logger.warning("源语言和目标语言相同，无法翻译")
            # 恢复翻译按钮状态
            self.translation_in_progress = False
            self.translate_btn.config(state=tk.NORMAL)
            self.cancel_btn.config(state=tk.DISABLED)
            self.generate_dialogue_btn.config(state=tk.DISABLED)  # 禁用生成对话按钮
            self._show_language_error_dialog()
            return

        # 翻译方向确定

        # 执行翻译 - 使用主线程安全方式
        self.schedule_translation(text_to_translate, direction)


    def schedule_translation(self, text, direction):
        """安排翻译任务在主线程安全执行"""
        def translation_task():
            try:
                self.logger.debug("启动翻译线程")
                # 执行翻译（支持流式输出）
                self.app.translation_engine.translate_text(
                    text,
                    direction=direction,
                    callback=self.handle_translation_result,
                    stream_callback=self.handle_stream_translation
                )
            except Exception as e:
                self.logger.error(f"翻译线程出错: {str(e)}")
                self.handle_translation_result(f"翻译失败: {str(e)}")

        # 在主线程中启动翻译任务
        threading.Thread(target=translation_task, daemon=True).start()

    def handle_stream_translation(self, content):
        """处理流式翻译输出"""
        # 在主线程中安全地更新UI
        self.window.after(0, self._safe_handle_stream_translation, content)

    def _safe_handle_stream_translation(self, content):
        """安全处理流式翻译输出（在主线程执行）"""
        if not self.window.winfo_exists():
            return

        # 如果当前显示的是"翻译中，请稍候..."，则清除它
        current_text = self.translate_output.get(1.0, tk.END)
        if "翻译中，请稍候..." in current_text:
            self.translate_output.config(state=tk.NORMAL)
            self.translate_output.delete(1.0, tk.END)
            self.translate_output.config(state=tk.NORMAL)

        # 追加新的内容
        self.append_to_translation_output(content)
        
        # 更新UI
        self.window.update_idletasks()

    def update_translation_output(self, text):
        """安全更新翻译结果框"""
        self.translate_output.config(state=tk.NORMAL)
        self.translate_output.delete(1.0, tk.END)
        self.translate_output.insert(tk.END, text)
        self.translate_output.config(state=tk.NORMAL)
        self.translate_output.see(tk.END)

    def handle_translation_result(self, result):
        """处理翻译结果回调"""
        # 确保在主线程更新UI
        self.window.after(0, self._safe_handle_translation_result, result)

    def _safe_handle_translation_result(self, result):
        """安全处理翻译结果（在主线程执行）"""
        # 如果窗口已经销毁，则不处理结果
        if not self.window.winfo_exists():
            self.logger.info("翻译结果返回但结果窗口已关闭")
            return

        # 如果翻译已被取消，但窗口仍然存在，则显示结果
        if not self.translation_in_progress:
            # 恢复按钮状态
            self.translate_btn.config(state=tk.NORMAL)
            self.cancel_btn.config(state=tk.DISABLED)

            # 在翻译结果框中显示翻译结果
            self.translate_output.config(state=tk.NORMAL)

            # 检查结果是否以"翻译中"开头，如果是则替换
            current_text = self.translate_output.get(1.0, tk.END)
            if "翻译中" in current_text:
                self.translate_output.delete(1.0, tk.END)

            # 插入结果并滚动到末尾
            self.translate_output.insert(tk.END, result)
            self.translate_output.see(tk.END)
            self.translate_output.config(state=tk.NORMAL)

            # 添加翻译结果标记
            self.window.title("OCR识别结果 (已翻译)")

            # 记录翻译完成
            elapsed_time = time.time() - self.translation_start_time
            result_length = len(result.strip())
            return

        # 正常处理翻译结果
        # 恢复按钮状态
        self.translation_in_progress = False
        self.translate_btn.config(state=tk.NORMAL)
        self.cancel_btn.config(state=tk.DISABLED)
        self.generate_dialogue_btn.config(state=tk.NORMAL)  # 启用生成对话按钮

        # 在翻译结果框中显示翻译结果
        self.translate_output.config(state=tk.NORMAL)

        # 检查结果是否以"翻译中"开头，如果是则替换
        current_text = self.translate_output.get(1.0, tk.END)
        if "翻译中" in current_text:
            self.translate_output.delete(1.0, tk.END)

        # 插入结果并滚动到末尾
        self.translate_output.insert(tk.END, result)
        self.translate_output.see(tk.END)
        self.translate_output.config(state=tk.NORMAL)

        # 添加翻译结果标记
        self.window.title("OCR识别结果 (已翻译)")

        # 记录翻译完成
        elapsed_time = time.time() - self.translation_start_time
        result_length = len(result.strip())


    def cancel_translation(self):
        """取消翻译"""
        # 用户取消翻译
        self.translation_in_progress = False
        self.translate_btn.config(state=tk.NORMAL)
        self.cancel_btn.config(state=tk.DISABLED)
        self.generate_dialogue_btn.config(state=tk.DISABLED)  # 禁用生成对话按钮

        # 更新状态
        self.update_translation_output("翻译已取消")

    def generate_dialogue(self):
        """生成对话"""
        # 开始生成对话
        
        # 检查是否有翻译结果
        translated_content = self.translate_output.get(1.0, tk.END).strip()
        if not translated_content or "翻译中" in translated_content or "翻译已取消" in translated_content:
            messagebox.showwarning("警告", "请先完成翻译，再生成对话")
            return
        
        # 获取原文
        original_text = self.text_area.get(1.0, tk.END).strip()
        if not original_text:
            messagebox.showwarning("警告", "没有可用的原文")
            return
        
        # 获取句数
        sentence_count = int(self.sentence_count_var.get())
        
        # 检查API密钥
        if not self.app.settings.get("api_key"):
            provider_name = "DeepSeek" if self.app.settings.get("api_provider") == "deepseek" else "OpenAI"
            messagebox.showerror("错误", f"请先设置{provider_name} API密钥")
            return
        
        # 禁用生成对话按钮
        self.generate_dialogue_btn.config(state=tk.DISABLED)
        
        # 初始化对话标题标记
        self._dialogue_title_added = False
        
        # 清理可能存在的旧对话内容
        self._clean_existing_dialogue()
        
        # 在翻译结果框中显示生成状态
        self.translate_output.config(state=tk.NORMAL)
        self.translate_output.insert(tk.END, "\n\n--- 正在生成对话 ---\n")
        self.translate_output.see(tk.END)
        
        # 调用翻译引擎生成对话
        self.app.translation_engine.generate_dialogue(
            original_text,
            translated_content,
            sentence_count,
            callback=self.handle_dialogue_result,
            stream_callback=self.handle_stream_dialogue
        )

    def handle_dialogue_result(self, result):
        """处理对话生成结果"""
        # 在主线程中安全地更新UI
        self.window.after(0, self._safe_handle_dialogue_result, result)

    def _safe_handle_dialogue_result(self, result):
        """安全处理对话生成结果（在主线程执行）"""
        if not self.window.winfo_exists():
            return
        
        # 恢复生成对话按钮状态
        self.generate_dialogue_btn.config(state=tk.NORMAL)
        
        # 在翻译结果框中显示对话结果
        self.translate_output.config(state=tk.NORMAL)
        
        # 移除"正在生成对话"提示
        current_text = self.translate_output.get(1.0, tk.END)
        if "--- 正在生成对话 ---" in current_text:
            # 找到并删除生成状态提示
            lines = current_text.split('\n')
            new_lines = []
            skip_next = False
            for line in lines:
                if "--- 正在生成对话 ---" in line:
                    skip_next = True
                    continue
                if skip_next and line.strip() == "":
                    skip_next = False
                    continue
                if not skip_next:
                    new_lines.append(line)
            
            self.translate_output.delete(1.0, tk.END)
            self.translate_output.insert(1.0, '\n'.join(new_lines))
            
            # 添加对话标题（只添加一次）
            self.translate_output.insert(tk.END, "\n\n--- 生成的中英文对照对话 ---\n")
        
        # 添加对话结果
        self.translate_output.insert(tk.END, result)
        self.translate_output.see(tk.END)
        
        # 对话生成完成

    def handle_stream_dialogue(self, content):
        """处理流式对话生成输出"""
        # 在主线程中安全地更新UI
        self.window.after(0, self._safe_handle_stream_dialogue, content)

    def _safe_handle_stream_dialogue(self, content):
        """安全处理流式对话生成输出（在主线程执行）"""
        if not self.window.winfo_exists():
            return
        
        # 如果当前显示的是"正在生成对话"，则清除它并添加对话标题
        current_text = self.translate_output.get(1.0, tk.END)
        if "--- 正在生成对话 ---" in current_text and not getattr(self, '_dialogue_title_added', False):
            # 找到并删除生成状态提示
            lines = current_text.split('\n')
            new_lines = []
            skip_next = False
            for line in lines:
                if "--- 正在生成对话 ---" in line:
                    skip_next = True
                    continue
                if skip_next and line.strip() == "":
                    skip_next = False
                    continue
                if not skip_next:
                    new_lines.append(line)
            
            self.translate_output.delete(1.0, tk.END)
            self.translate_output.insert(1.0, '\n'.join(new_lines))
            
            # 添加对话标题（只添加一次）
            self.translate_output.insert(tk.END, "\n\n--- 生成的中英文对照对话 ---\n")
            
            # 标记已经添加了对话标题，避免重复
            self._dialogue_title_added = True
        
        # 追加新的内容
        self.translate_output.insert(tk.END, content)
        self.translate_output.see(tk.END)
        
        # 更新UI
        self.window.update_idletasks()

    def _clean_existing_dialogue(self):
        """清理现有的对话内容"""
        current_text = self.translate_output.get(1.0, tk.END)
        if "--- 生成的中英文对照对话 ---" in current_text:
            # 找到对话标题的位置
            lines = current_text.split('\n')
            new_lines = []
            skip_dialogue = False
            
            for line in lines:
                if "--- 生成的中英文对照对话 ---" in line:
                    skip_dialogue = True
                    continue
                if skip_dialogue and line.strip() == "" and len(new_lines) > 0 and new_lines[-1].strip() == "":
                    # 跳过对话后的空行
                    continue
                if not skip_dialogue:
                    new_lines.append(line)
                elif line.strip() == "":
                    # 对话结束，保留空行
                    skip_dialogue = False
                    new_lines.append(line)
            
            # 更新文本内容
            self.translate_output.delete(1.0, tk.END)
            self.translate_output.insert(1.0, '\n'.join(new_lines))

    def _auto_detect_and_set_target_language(self, text):
        """自动检测语言并设置目标语言"""
        if not text.strip():
            return
        
        # 自动检测语言并设置目标语言
        
        # 检测文本的主要语言
        detected_lang = self.detect_language(text)
        
        # 根据检测结果设置目标语言
        if detected_lang == "chinese":
            # 如果检测到中文，目标语言设为英文
            self.target_lang_var.set("英文")
            self.logger.info("检测到中文，目标语言设为英文")
        elif detected_lang in ["other_latin", "unknown"]:
            # 如果检测到英文或其他拉丁语系，目标语言设为中文
            self.target_lang_var.set("中文")
            self.logger.info(f"检测到{detected_lang}，目标语言设为中文")
        elif detected_lang in ["japanese", "korean", "arabic", "russian"]:
            # 如果检测到其他语言，目标语言设为中文
            self.target_lang_var.set("中文")
            self.logger.info(f"检测到{detected_lang}，目标语言设为中文")
        else:
            # 默认情况，目标语言设为中文
            self.target_lang_var.set("中文")
            self.logger.info(f"检测到{detected_lang}，默认目标语言设为中文")
        
        # 源语言保持"自动检测"
        self.source_lang_var.set("自动检测")
