import pytesseract
from PIL import Image, ImageGrab, ImageTk
import tkinter as tk
from tkinter import messagebox, filedialog, ttk
import time
import os
import threading
import sys
import ctypes

# 配置常量
TESSERACT_PATH = r'F:\softeare\OCR\tesseract.exe'
TESSDATA_PATH = r'F:\softeare\OCR\tessdata'

# 初始化Tesseract
pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH
if os.path.exists(TESSDATA_PATH):
    os.environ['TESSDATA_PREFIX'] = TESSDATA_PATH


class ScreenCapture:
    """处理屏幕截图相关功能的类"""

    def __init__(self, dpi_scale, screen_width, screen_height, virtual_width, virtual_height):
        self.dpi_scale = dpi_scale
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.virtual_width = virtual_width
        self.virtual_height = virtual_height

    def get_physical_coords(self, virtual_coords):
        """将虚拟坐标转换为物理坐标"""
        x1, y1, x2, y2 = virtual_coords
        return (
            int(x1 * self.dpi_scale),
            int(y1 * self.dpi_scale),
            int(x2 * self.dpi_scale),
            int(y2 * self.dpi_scale)
        )

    def get_virtual_coords(self, physical_coords):
        """将物理坐标转换为虚拟坐标"""
        x1, y1, x2, y2 = physical_coords
        return (
            x1 / self.dpi_scale,
            y1 / self.dpi_scale,
            x2 / self.dpi_scale,
            y2 / self.dpi_scale
        )

    def capture_area(self, bbox):
        """捕获指定区域的屏幕"""
        try:
            return ImageGrab.grab(bbox=bbox)
        except Exception as e:
            # 备选截图方法
            full_screen = ImageGrab.grab()
            return full_screen.crop(bbox)

    def select_area(self, master):
        """使用鼠标选择截图区域"""
        top = tk.Toplevel(master)
        top.title("截图文字识别 - 按ESC退出")
        top.overrideredirect(True)
        top.geometry(f"{self.screen_width}x{self.screen_height}+0+0")
        top.attributes('-alpha', 0.3)
        top.attributes('-topmost', True)
        top.update_idletasks()

        container = tk.Frame(top)
        container.pack(fill=tk.BOTH, expand=True)

        prompt_label = tk.Label(
            container,
            text="按住鼠标左键拖拽选择区域，按ESC取消",
            fg="white", bg="black",
            font=("微软雅黑", 14)
        )
        prompt_label.place(relx=0.5, rely=0.95, anchor=tk.CENTER)

        canvas = tk.Canvas(container, bg='white', highlightthickness=0, cursor="cross")
        canvas.pack(fill=tk.BOTH, expand=True)

        self._create_overlay(canvas)

        start_x, start_y = 0, 0
        rect_id = None
        selected_coords = None

        def on_click(event):
            nonlocal start_x, start_y, rect_id
            start_x, start_y = event.x, event.y
            rect_id = canvas.create_rectangle(
                start_x, start_y, start_x, start_y,
                outline='red', width=3, fill=''
            )

        def on_drag(event):
            nonlocal rect_id
            if rect_id:
                canvas.coords(rect_id, start_x, start_y, event.x, event.y)

        def on_release(event):
            nonlocal selected_coords, rect_id
            if rect_id:
                selected_coords = (start_x, start_y, event.x, event.y)
            top.destroy()

        canvas.bind('<Button-1>', on_click)
        canvas.bind('<B1-Motion>', on_drag)
        canvas.bind('<ButtonRelease-1>', on_release)
        top.bind('<Escape>', lambda e: top.destroy())
        top.focus_force()
        master.wait_window(top)

        return selected_coords

    def _create_overlay(self, canvas):
        """创建覆盖层确保完全覆盖屏幕"""
        canvas.create_rectangle(
            0, 0, self.screen_width, self.screen_height,
            fill='white', outline=''
        )
        canvas.create_text(
            self.screen_width // 2, self.screen_height - 50,
            text="按住鼠标左键拖拽选择区域，按ESC取消",
            fill="black",
            font=("微软雅黑", 14),
            anchor=tk.CENTER
        )


class OCREngine:
    """处理OCR识别相关功能的类"""

    def __init__(self):
        self.config = {
            'language': 'chi_sim+eng',
            'psm': '3',
            'oem': '3'
        }

    def perform_ocr(self, image):
        """执行OCR识别"""
        config_str = f'--psm {self.config["psm"]} --oem {self.config["oem"]}'
        return pytesseract.image_to_string(
            image,
            lang=self.config['language'],
            config=config_str
        )

    def update_config(self, language, psm, oem):
        """更新OCR配置"""
        self.config['language'] = language
        self.config['psm'] = psm
        self.config['oem'] = oem


class ResultWindow:
    """处理结果显示窗口的类"""

    def __init__(self, master):
        self.master = master
        self.window = tk.Toplevel(master)
        self.window.title("OCR识别结果")
        self.window.geometry("700x500")
        self.window.minsize(500, 400)

        self.text_area = None
        self.img_label = None
        self._create_ui()

    def _create_ui(self):
        """创建结果窗口UI"""
        main_frame = ttk.Frame(self.window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True)

        # 结果标签页
        result_frame = ttk.Frame(notebook, padding=10)
        notebook.add(result_frame, text="识别结果")

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

        # 图像标签页
        image_frame = ttk.Frame(notebook, padding=10)
        notebook.add(image_frame, text="截图预览")

        self.img_label = ttk.Label(image_frame)
        self.img_label.pack(fill=tk.BOTH, expand=True)

        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)

        buttons = [
            ("保存文本", self.save_result),
            ("保存截图", self.save_screenshot),
            ("复制文本", self.copy_to_clipboard),
            ("重新截图", self.close_and_recapture),
            ("关闭", self.window.destroy)
        ]

        for text, command in buttons:
            ttk.Button(
                button_frame,
                text=text,
                command=command,
                width=12
            ).pack(side=tk.LEFT, padx=5)

    def display_result(self, text, screenshot):
        """显示OCR结果和截图"""
        self.text_area.config(state=tk.NORMAL)
        self.text_area.delete(1.0, tk.END)
        self.text_area.insert(tk.END, text.strip())
        self.text_area.config(state=tk.NORMAL)
        self.update_image_preview(screenshot)

    def update_image_preview(self, screenshot):
        """更新图像预览"""
        if screenshot:
            try:
                width, height = screenshot.size
                max_size = 600
                if width > max_size or height > max_size:
                    ratio = min(max_size/width, max_size/height)
                    new_size = (int(width * ratio), int(height * ratio))
                    preview_img = screenshot.resize(new_size, Image.LANCZOS)
                else:
                    preview_img = screenshot

                tk_img = ImageTk.PhotoImage(preview_img)
                self.img_label.configure(image=tk_img)
                self.img_label.image = tk_img
            except Exception as e:
                print(f"图像预览错误: {str(e)}")

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

    def save_screenshot(self):
        """保存截图到文件"""
        # 此功能需要访问原始截图，在实际应用中需要额外处理
        messagebox.showinfo("提示", "此功能需要访问原始截图数据")

    def copy_to_clipboard(self):
        """复制文本到剪贴板"""
        self.window.clipboard_clear()
        self.window.clipboard_append(self.text_area.get(1.0, tk.END))

    def close_and_recapture(self):
        """关闭窗口并触发重新截图"""
        self.window.destroy()
        return "recapture"


class SettingsWindow:
    """处理设置窗口的类"""

    def __init__(self, master, dpi_scale, screen_size, virtual_size, ocr_engine, screen_capture):
        self.master = master
        self.ocr_engine = ocr_engine
        self.screen_capture = screen_capture

        self.window = tk.Toplevel(master)
        self.window.title("设置")
        self.window.geometry("500x400")
        self.window.transient(master)
        self.window.grab_set()

        self.h_offset = tk.IntVar(value=0)
        self.v_offset = tk.IntVar(value=0)

        self._create_ui(dpi_scale, screen_size, virtual_size)

    def _create_ui(self, dpi_scale, screen_size, virtual_size):
        """创建设置窗口UI"""
        frame = ttk.Frame(self.window, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)

        notebook = ttk.Notebook(frame)
        notebook.pack(fill=tk.BOTH, expand=True)

        # 通用设置
        general_frame = ttk.Frame(notebook, padding=10)
        notebook.add(general_frame, text="通用设置")

        # DPI设置
        ttk.Label(general_frame, text="DPI设置", font=("微软雅黑", 10, "bold")).pack(anchor=tk.W, pady=(0, 5))
        dpi_frame = ttk.Frame(general_frame)
        dpi_frame.pack(fill=tk.X, pady=5)

        ttk.Label(dpi_frame, text=f"当前DPI缩放比例: {dpi_scale:.2f}").pack(side=tk.LEFT, padx=5)
        ttk.Label(dpi_frame, text=f"物理屏幕尺寸: {screen_size[0]}x{screen_size[1]}").pack(side=tk.LEFT, padx=5)
        ttk.Label(dpi_frame, text=f"虚拟屏幕尺寸: {virtual_size[0]}x{virtual_size[1]}").pack(side=tk.LEFT, padx=5)

        # 偏移校正
        ttk.Label(general_frame, text="偏移校正", font=("微软雅黑", 10, "bold")).pack(anchor=tk.W, pady=(10, 5))
        offset_frame = ttk.Frame(general_frame)
        offset_frame.pack(fill=tk.X, pady=5)

        ttk.Label(offset_frame, text="水平偏移校正:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Entry(offset_frame, textvariable=self.h_offset, width=5).grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(offset_frame, text="垂直偏移校正:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Entry(offset_frame, textvariable=self.v_offset, width=5).grid(row=1, column=1, padx=5, pady=5)

        # OCR设置
        ocr_frame = ttk.Frame(notebook, padding=10)
        notebook.add(ocr_frame, text="OCR设置")

        # 语言选择
        lang_frame = ttk.Frame(ocr_frame)
        lang_frame.pack(fill=tk.X, pady=5)

        ttk.Label(lang_frame, text="语言选择:").pack(side=tk.LEFT, padx=(0, 10))

        self.lang_var = tk.StringVar(value=self.ocr_engine.config['language'])
        langs = ttk.Combobox(lang_frame, textvariable=self.lang_var, width=20)
        langs['values'] = (
            'chi_sim', 'chi_sim+eng', 'eng', 'jpn',
            'kor', 'fra', 'deu', 'rus'
        )
        langs.pack(side=tk.LEFT)

        # PSM模式选择
        psm_frame = ttk.Frame(ocr_frame)
        psm_frame.pack(fill=tk.X, pady=5)

        ttk.Label(psm_frame, text="页面分割模式(PSM):").pack(side=tk.LEFT, padx=(0, 10))

        self.psm_var = tk.StringVar(value=self.ocr_engine.config['psm'])
        psms = ttk.Combobox(psm_frame, textvariable=self.psm_var, width=20)
        psms['values'] = tuple(str(i) for i in range(14))
        psms.pack(side=tk.LEFT)

        # OEM模式选择
        oem_frame = ttk.Frame(ocr_frame)
        oem_frame.pack(fill=tk.X, pady=5)

        ttk.Label(oem_frame, text="OCR引擎模式(OEM):").pack(side=tk.LEFT, padx=(0, 10))

        self.oem_var = tk.StringVar(value=self.ocr_engine.config['oem'])
        oems = ttk.Combobox(oem_frame, textvariable=self.oem_var, width=20)
        oems['values'] = ('0', '1', '2', '3')
        oems.pack(side=tk.LEFT)

        # OCR路径设置
        path_frame = ttk.Frame(ocr_frame)
        path_frame.pack(fill=tk.X, pady=5)

        ttk.Label(path_frame, text="Tesseract路径:").pack(side=tk.LEFT, padx=(0, 10))

        self.tesseract_path_var = tk.StringVar(value=TESSERACT_PATH)
        ttk.Entry(path_frame, textvariable=self.tesseract_path_var, width=30).pack(side=tk.LEFT, fill=tk.X, expand=True)

        # 语言包路径
        tessdata_frame = ttk.Frame(ocr_frame)
        tessdata_frame.pack(fill=tk.X, pady=5)

        ttk.Label(tessdata_frame, text="语言包路径:").pack(side=tk.LEFT, padx=(0, 10))

        self.tessdata_path_var = tk.StringVar(value=TESSDATA_PATH)
        ttk.Entry(tessdata_frame, textvariable=self.tessdata_path_var, width=30).pack(side=tk.LEFT, fill=tk.X, expand=True)

        # 按钮
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=20)

        ttk.Button(btn_frame, text="应用", command=self.apply_settings).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="取消", command=self.window.destroy).pack(side=tk.RIGHT, padx=5)

    def apply_settings(self):
        """应用设置"""
        try:
            # 更新OCR配置
            self.ocr_engine.update_config(
                self.lang_var.get(),
                self.psm_var.get(),
                self.oem_var.get()
            )

            # 更新Tesseract路径
            pytesseract.pytesseract.tesseract_cmd = self.tesseract_path_var.get()

            # 设置语言包路径
            if os.path.exists(self.tessdata_path_var.get()):
                os.environ['TESSDATA_PREFIX'] = self.tessdata_path_var.get()

            messagebox.showinfo("设置已应用", "OCR配置已更新！")
        except Exception as e:
            messagebox.showerror("设置错误", f"应用设置时出错:\n{str(e)}")


class OCRApplication:
    """主应用程序类"""

    def __init__(self, master):
        self.master = master
        self.master.title("OCR截图工具")
        self.master.geometry("400x300")
        self.master.resizable(True, True)

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
        self.ocr_engine = OCREngine()
        self.result_window = None

        # 当前状态
        self.current_screenshot = None
        self.ocr_result = ""
        self.status_var = tk.StringVar(value="就绪")

        # 创建界面
        self.create_main_ui()
        self.check_paths()

        # 设置应用图标
        try:
            self.master.iconbitmap('ocr_icon.ico')
        except:
            pass

    def get_dpi_scaling(self):
        """获取系统DPI缩放比例"""
        try:
            if sys.platform == 'win32':
                ctypes.windll.shcore.SetProcessDpiAwareness(2)
                hdc = ctypes.windll.user32.GetDC(0)
                dpi_x = ctypes.windll.gdi32.GetDeviceCaps(hdc, 88)
                ctypes.windll.user32.ReleaseDC(0, hdc)
                return dpi_x / 96.0
        except:
            return 1.0

    def get_physical_screen_size(self):
        """获取物理屏幕尺寸"""
        try:
            if sys.platform == 'win32':
                user32 = ctypes.windll.user32
                return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
        except:
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
        ttk.Label(
            self.master,
            textvariable=self.status_var,
            relief=tk.SUNKEN,
            anchor=tk.W
        ).pack(side=tk.BOTTOM, fill=tk.X)

        # 使用说明
        help_frame = ttk.LabelFrame(main_frame, text="使用说明")
        help_frame.pack(fill=tk.BOTH, expand=True, pady=(20, 0))

        instructions = [
            "1. 点击'开始截图'按钮",
            "2. 在屏幕上拖拽选择识别区域",
            "3. 查看识别结果并保存",
            "4. 可以重复操作多次"
        ]

        for instruction in instructions:
            ttk.Label(help_frame, text=instruction, anchor=tk.W).pack(fill=tk.X, padx=10, pady=5)

    def check_paths(self):
        """检查路径有效性"""
        if not os.path.exists(TESSERACT_PATH):
            messagebox.showerror("路径错误", f"找不到Tesseract可执行文件: {TESSERACT_PATH}")
            return False

        if not os.path.exists(TESSDATA_PATH):
            messagebox.showwarning("路径警告", f"找不到语言包目录: {TESSDATA_PATH}")

        return True

    def start_capture(self):
        """开始截图流程"""
        self.status_var.set("准备截图...")
        self.master.update()
        self.master.after(300, self.capture_and_ocr)

    def capture_and_ocr(self):
        """截图并识别文字"""
        # 选择区域
        physical_coords = self.screen_capture.select_area(self.master)

        if not physical_coords:
            self.status_var.set("截图已取消")
            return

        # 转换为虚拟坐标
        virtual_coords = self.screen_capture.get_virtual_coords(physical_coords)
        x1, y1, x2, y2 = virtual_coords

        # 区域有效性检查
        if abs(x2 - x1) < 5 or abs(y2 - y1) < 5:
            messagebox.showwarning("区域无效", "选择的区域太小，请重新选择")
            self.capture_and_ocr()
            return

        # 转换为物理坐标
        x1_phys, y1_phys, x2_phys, y2_phys = self.screen_capture.get_physical_coords(virtual_coords)

        # 确保坐标顺序正确
        if x1_phys > x2_phys: x1_phys, x2_phys = x2_phys, x1_phys
        if y1_phys > y2_phys: y1_phys, y2_phys = y2_phys, y1_phys

        # 截图
        self.status_var.set(f"截取区域: ({x1:.1f}, {y1:.1f}) -> ({x2:.1f}, {y2:.1f})")
        self.master.update()
        time.sleep(0.3)  # 等待窗口关闭

        try:
            self.current_screenshot = self.screen_capture.capture_area((x1_phys, y1_phys, x2_phys, y2_phys))
        except Exception as e:
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

            if not text.strip():
                self.status_var.set("识别中：尝试纯文本识别...")
                text = pytesseract.image_to_string(self.current_screenshot)

            # 显示结果
            self.ocr_result = text
            if self.result_window:
                self.result_window.display_result(text, self.current_screenshot)

            # 计算字符数
            char_count = len(text.strip())
            word_count = len(text.split())
            self.status_var.set(f"识别完成！共识别 {char_count} 个字符，{word_count} 个单词")

            # 保存结果
            try:
                with open('ocr_result.txt', 'w', encoding='utf-8') as f:
                    f.write(text)
                self.current_screenshot.save("screenshot.png")
            except:
                pass

            # 启用查看结果按钮
            self.open_result_btn.config(state=tk.NORMAL)

        except Exception as e:
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

        self.result_window = ResultWindow(self.master)

    def show_last_result(self):
        """显示上次识别结果"""
        if self.ocr_result:
            self.show_result_window()
            self.result_window.display_result(self.ocr_result, self.current_screenshot)
        else:
            messagebox.showinfo("提示", "没有可用的历史结果")

    def show_settings(self):
        """显示设置窗口"""
        SettingsWindow(
            self.master,
            self.dpi_scale,
            (self.screen_width, self.screen_height),
            (self.virtual_width, self.virtual_height),
            self.ocr_engine,
            self.screen_capture
        )


def main():
    """主函数"""
    root = tk.Tk()
    app = OCRApplication(root)
    root.mainloop()


if __name__ == "__main__":
    main()