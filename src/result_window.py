# result_window.py - 结果窗口功能 (支持打包)
import tkinter as tk
from tkinter import messagebox, filedialog, ttk
from PIL import Image, ImageTk, ImageOps, ImageEnhance
import re
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
        self.master = master
        self.app = app  # 保存应用实例引用
        self.window = tk.Toplevel(master)
        self.window.title("OCR识别结果")
        self.window.geometry("800x600")
        self.window.minsize(600, 500)

        self.screenshot = screenshot
        self.ocr_result = ocr_result
        self.translated_text = ""

        # 创建UI
        self._create_ui()

        # 如果有初始结果，显示它
        if ocr_result:
            self.display_result(ocr_result, screenshot)

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

        ttk.Button(
            btn_frame,
            text="翻译",
            command=self.translate_text,
            width=12,
            style="Accent.TButton"
        ).pack(side=tk.LEFT, padx=5)

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
            pady=10
        )
        self.translate_output.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.translate_output.yview)

    def display_result(self, text, screenshot=None):
        """显示OCR结果和截图"""
        if screenshot:
            self.screenshot = screenshot

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
        self.translate_output.delete(1.0, tk.END)
        self.window.title("OCR识别结果")

    def update_image_preview(self):
        """更新图像预览"""
        if self.screenshot:
            try:
                # 在打包环境中，screenshot可能没有filename属性
                try:
                    if not hasattr(self.screenshot, 'filename') or not self.screenshot.filename:
                        # 尝试加载示例图像
                        screenshot_path = resource_path('screenshot.png')
                        if os.path.exists(screenshot_path):
                            self.screenshot = Image.open(screenshot_path)
                except:
                    pass

                width, height = self.screenshot.size
                max_size = 600
                if width > max_size or height > max_size:
                    ratio = min(max_size/width, max_size/height)
                    new_size = (int(width * ratio), int(height * ratio))
                    preview_img = self.screenshot.resize(new_size, Image.LANCZOS)
                else:
                    preview_img = self.screenshot

                # 显示原始图像
                tk_img = ImageTk.PhotoImage(preview_img)
                self.original_img_label.configure(image=tk_img)
                self.original_img_label.image = tk_img

                # 显示预处理后的图像
                processed_img = self.preprocess_image(preview_img)
                tk_processed_img = ImageTk.PhotoImage(processed_img)
                self.processed_img_label.configure(image=tk_processed_img)
                self.processed_img_label.image = tk_processed_img

            except Exception as e:
                print(f"图像预览错误: {str(e)}")

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
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            title="保存识别结果"
        )
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.text_area.get(1.0, tk.END))
                messagebox.showinfo("保存成功", f"结果已保存到:\n{file_path}")
            except Exception as e:
                messagebox.showerror("保存失败", f"无法保存文件:\n{str(e)}")

    def save_translation_result(self):
        """保存翻译结果到文件"""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            title="保存翻译结果"
        )
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.translate_output.get(1.0, tk.END))
                messagebox.showinfo("保存成功", f"翻译结果已保存到:\n{file_path}")
            except Exception as e:
                messagebox.showerror("保存失败", f"无法保存文件:\n{str(e)}")

    def save_screenshot(self):
        """保存截图到文件"""
        if not self.screenshot:
            messagebox.showwarning("警告", "没有可用的截图")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG files", "*.png"), ("JPEG files", "*.jpg"), ("All files", "*.*")],
            title="保存截图"
        )
        if file_path:
            try:
                self.screenshot.save(file_path)
                messagebox.showinfo("保存成功", f"截图已保存到:\n{file_path}")
            except Exception as e:
                messagebox.showerror("保存失败", f"无法保存截图:\n{str(e)}")

    def copy_to_clipboard(self):
        """复制识别文本到剪贴板"""
        self.window.clipboard_clear()
        self.window.clipboard_append(self.text_area.get(1.0, tk.END))
        messagebox.showinfo("成功", "识别文本已复制到剪贴板")

    def copy_translation_to_clipboard(self):
        """复制翻译文本到剪贴板"""
        self.window.clipboard_clear()
        self.window.clipboard_append(self.translate_output.get(1.0, tk.END))
        messagebox.showinfo("成功", "翻译文本已复制到剪贴板")

    def close_and_recapture(self):
        """关闭窗口并触发重新截图"""
        self.window.destroy()
        return "recapture"

    def detect_language(self, text):
        """检测文本的主要语言"""
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

    def translate_text(self):
        """翻译文本"""
        # 检查是否已设置API密钥
        if not self.app.settings["deepseek_api_key"]:
            messagebox.showerror("API密钥缺失", "请先在设置中配置DeepSeek API密钥")
            return

        # 获取要翻译的文本
        text_to_translate = self.translate_input.get(1.0, tk.END).strip()

        if not text_to_translate:
            messagebox.showinfo("提示", "没有可翻译的文本")
            return

        # 切换到翻译标签页
        self.notebook.select(2)  # 切换到第三个标签页（翻译）

        # 显示翻译中状态
        self.translate_output.config(state=tk.NORMAL)
        self.translate_output.delete(1.0, tk.END)
        self.translate_output.insert(tk.END, "翻译中，请稍候...")
        self.translate_output.config(state=tk.DISABLED)
        self.window.update()

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

        # 执行翻译
        self.app.translation_engine.translate_text(
            text_to_translate,
            direction=direction,
            callback=self.handle_translation_result
        )

    def handle_translation_result(self, result):
        """处理翻译结果回调"""
        self.translated_text = result

        # 在翻译结果框中显示翻译结果
        self.translate_output.config(state=tk.NORMAL)
        self.translate_output.delete(1.0, tk.END)
        self.translate_output.insert(tk.END, result)
        self.translate_output.config(state=tk.NORMAL)
        self.translate_output.see(tk.END)  # 滚动到文本末尾

        # 添加翻译结果标记
        self.window.title("OCR识别结果 (已翻译)")

        #messagebox.showinfo("翻译完成", "文本翻译已完成")