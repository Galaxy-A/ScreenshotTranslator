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

    def __init__(self, master, screenshot=None, ocr_result="", app=None):
        # 获取日志记录器
        self.logger = logging.getLogger("ResultWindow")
        self.logger.info("创建结果窗口")

        self.master = master
        self.app = app  # 保存应用实例引用
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

        # 创建UI
        self._create_ui()

        # 如果有初始结果，显示它
        if ocr_result:
            self.display_result(ocr_result, screenshot)

        self.logger.info("结果窗口初始化完成")

    def on_close(self):
        """处理窗口关闭事件"""
        self.logger.info("关闭结果窗口")
        self.translation_in_progress = False  # 停止翻译
        self.window.destroy()

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

        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)

        ttk.Button(
            button_frame,
            text="保存文本",
            command=self.save_result,
            width=12
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            button_frame,
            text="保存截图",
            command=self.save_screenshot,
            width=12
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            button_frame,
            text="复制文本",
            command=self.copy_to_clipboard,
            width=12
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            button_frame,
            text="重新截图",
            command=self.close_and_recapture,
            width=12
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            button_frame,
            text="关闭",
            command=self.window.destroy,
            width=12
        ).pack(side=tk.LEFT, padx=5)

        # 添加翻译结果保存按钮
        ttk.Button(
            button_frame,
            text="保存翻译结果",
            command=self.save_translation_result,
            width=12
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            button_frame,
            text="复制翻译文本",
            command=self.copy_translation_to_clipboard,
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
            pady=10
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

    def translate_from_result(self):
        """从结果标签页翻译文本"""
        self.logger.info("从结果标签页触发翻译")
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

        # 翻译方向选择
        ttk.Label(setting_frame, text="翻译方向:").pack(side=tk.LEFT, padx=5)

        self.direction_var = tk.StringVar(value="auto")
        directions = [
            ("自动检测", "auto"),
            ("英译中", "en2zh"),
            ("中译英", "zh2en")
        ]

        for text, value in directions:
            rb = ttk.Radiobutton(
                setting_frame,
                text=text,
                variable=self.direction_var,
                value=value
            )
            rb.pack(side=tk.LEFT, padx=5)

        # 翻译按钮
        btn_frame = ttk.Frame(translation_frame)
        btn_frame.pack(fill=tk.X, pady=5)

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

    def display_result(self, text, screenshot=None):
        """显示OCR结果和截图"""
        self.logger.info("显示OCR结果")
        # 更新当前截图
        if screenshot:
            self.current_screenshot = screenshot

        # 在识别结果标签页显示文本
        self.text_area.config(state=tk.NORMAL)
        self.text_area.delete(1.0, tk.END)
        self.text_area.insert(tk.END, text.strip())
        self.text_area.config(state=tk.NORMAL)

        # 在翻译标签页的输入框中显示文本
        self.translate_input.delete(1.0, tk.END)
        self.translate_input.insert(tk.END, text.strip())

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

    def save_result(self):
        """保存识别结果到文件"""
        self.logger.info("保存识别结果")
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            title="保存识别结果"
        )
        if file_path:
            try:
                text_content = self.text_area.get(1.0, tk.END)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(text_content)
                self.logger.info(f"结果已保存到: {file_path}")
                messagebox.showinfo("保存成功", f"结果已保存到:\n{file_path}")
            except Exception as e:
                self.logger.error(f"保存识别结果失败: {str(e)}")
                messagebox.showerror("保存失败", f"无法保存文件:\n{str(e)}")

    def save_translation_result(self):
        """保存翻译结果到文件"""
        self.logger.info("保存翻译结果")
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            title="保存翻译结果"
        )
        if file_path:
            try:
                translated_content = self.translate_output.get(1.0, tk.END)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(translated_content)
                self.logger.info(f"翻译结果已保存到: {file_path}")
                messagebox.showinfo("保存成功", f"翻译结果已保存到:\n{file_path}")
            except Exception as e:
                self.logger.error(f"保存翻译结果失败: {str(e)}")
                messagebox.showerror("保存失败", f"无法保存文件:\n{str(e)}")

    def save_screenshot(self):
        """保存截图到文件"""
        self.logger.info("保存截图")
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

    def copy_to_clipboard(self):
        """复制识别文本到剪贴板"""
        self.logger.info("复制识别文本到剪贴板")
        self.window.clipboard_clear()
        text_content = self.text_area.get(1.0, tk.END)
        self.window.clipboard_append(text_content)
        char_count = len(text_content.strip())
        self.logger.info(f"已复制 {char_count} 个字符到剪贴板")
        messagebox.showinfo("成功", "识别文本已复制到剪贴板")

    def copy_translation_to_clipboard(self):
        """复制翻译文本到剪贴板"""
        self.logger.info("复制翻译文本到剪贴板")
        self.window.clipboard_clear()
        translated_content = self.translate_output.get(1.0, tk.END)
        self.window.clipboard_append(translated_content)
        char_count = len(translated_content.strip())
        self.logger.info(f"已复制 {char_count} 个字符的翻译文本到剪贴板")
        messagebox.showinfo("成功", "翻译文本已复制到剪贴板")

    def close_and_recapture(self):
        """关闭窗口并触发重新截图"""
        self.logger.info("触发重新截图")
        self.window.destroy()
        return "recapture"

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

        # 检查英文单词比例
        english_words = len(re.findall(r'\b[a-zA-Z]+\b', text))
        if english_words > 0:
            return "english"

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

    def translate_text(self):
        """翻译文本"""
        # 如果已经在翻译中，则不执行新的翻译
        if self.translation_in_progress:
            self.logger.warning("尝试启动新翻译但已有翻译在进行中")
            return

        # 检查是否已设置API密钥
        if not self.app.settings["deepseek_api_key"]:
            self.logger.error("尝试翻译但未配置API密钥")
            messagebox.showerror("API密钥缺失", "请先在设置中配置DeepSeek API密钥")
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
        self.logger.info(f"开始翻译: {char_count}字符")

        # 标记翻译开始
        self.translation_in_progress = True
        self.translate_btn.config(state=tk.DISABLED)
        self.cancel_btn.config(state=tk.NORMAL)
        self.translation_start_time = time.time()

        # 切换到翻译标签页
        self.notebook.select(2)  # 切换到第三个标签页（翻译）

        # 显示翻译中状态
        self.update_translation_output("翻译中，请稍候...")

        # 确定翻译方向
        direction = self.direction_var.get()

        # 如果是自动检测，则检测文本语言
        if direction == "auto":
            lang = self.detect_language(text_to_translate)
            if lang == "chinese":
                direction = "zh2en"  # 中译英
            elif lang == "english":
                direction = "en2zh"  # 英译中
            else:
                # 无法检测时默认英译中
                direction = "en2zh"

        self.logger.info(f"翻译方向: {direction}")

        # 执行翻译 - 使用主线程安全方式
        self.schedule_translation(text_to_translate, direction)

    def schedule_translation(self, text, direction):
        """安排翻译任务在主线程安全执行"""
        def translation_task():
            try:
                self.logger.debug("启动翻译线程")
                # 执行翻译
                self.app.translation_engine.translate_text(
                    text,
                    direction=direction,
                    callback=self.handle_translation_result
                )
            except Exception as e:
                self.logger.error(f"翻译线程出错: {str(e)}")
                self.handle_translation_result(f"翻译失败: {str(e)}")

        # 在主线程中启动翻译任务
        threading.Thread(target=translation_task, daemon=True).start()

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
            # self.logger.info("翻译结果返回但标记为已取消 - 显示结果")

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
            # self.logger.info(f"翻译最终完成: 耗时{elapsed_time:.2f}秒, 结果长度{result_length}字符")
            return

        # 正常处理翻译结果
        # 恢复按钮状态
        self.translation_in_progress = False
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
        # self.logger.info(f"翻译完成: 耗时{elapsed_time:.2f}秒, 结果长度{result_length}字符")

    def cancel_translation(self):
        """取消翻译"""
        self.logger.info("用户取消翻译")
        self.translation_in_progress = False
        self.translate_btn.config(state=tk.NORMAL)
        self.cancel_btn.config(state=tk.DISABLED)

        # 更新状态
        self.update_translation_output("翻译已取消")