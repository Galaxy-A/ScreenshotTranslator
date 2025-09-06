# settings_window.py - 设置窗口
import tkinter as tk
from tkinter import messagebox, ttk
import pytesseract
import logging
import os
from translation import TranslationEngine  # 导入翻译引擎
import requests
import json

class SettingsWindow:
    """处理设置窗口的类"""

    def __init__(self, master, dpi_scale, screen_size, virtual_size, ocr_engine, settings):
        # 获取日志记录器
        self.logger = logging.getLogger("SettingsWindow")
        self.logger.info("创建设置窗口")

        self.master = master
        self.ocr_engine = ocr_engine
        self.original_settings = settings
        self.new_settings = settings.copy()  # 创建副本用于修改
        self.settings_updated = False

        self.window = tk.Toplevel(master)
        self.window.title("设置")
        self.window.geometry("550x600")  # 增加高度以适应新选项
        self.window.transient(master)
        self.window.grab_set()

        # 创建UI
        self._create_ui(dpi_scale, screen_size, virtual_size)
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)

        self.logger.info("设置窗口已打开")

    def on_close(self):
        """窗口关闭时的处理"""
        self.logger.info("关闭设置窗口")
        # 检查设置是否有变化
        self.settings_updated = self.check_settings_changed()
        if self.settings_updated:
            self.logger.info("设置已更改")
        self.window.destroy()

    def check_settings_changed(self):
        """检查设置是否有变化"""
        # 比较新设置和原始设置
        return self.new_settings != self.original_settings

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

        # 水平偏移
        ttk.Label(offset_frame, text="水平偏移校正:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.h_offset_var = tk.IntVar(value=self.new_settings["offset"]["horizontal"])
        ttk.Entry(offset_frame, textvariable=self.h_offset_var, width=5).grid(row=0, column=1, padx=5, pady=5)

        # 垂直偏移
        ttk.Label(offset_frame, text="垂直偏移校正:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.v_offset_var = tk.IntVar(value=self.new_settings["offset"]["vertical"])
        ttk.Entry(offset_frame, textvariable=self.v_offset_var, width=5).grid(row=1, column=1, padx=5, pady=5)

        # 截屏设置
        ttk.Label(general_frame, text="截屏设置", font=("微软雅黑", 10, "bold")).pack(anchor=tk.W, pady=(10, 5))
        capture_frame = ttk.Frame(general_frame)
        capture_frame.pack(fill=tk.X, pady=5)

        # 截屏时隐藏主窗口
        self.hide_window_var = tk.BooleanVar(value=self.new_settings.get("hide_window_on_capture", False))
        hide_window_check = ttk.Checkbutton(
            capture_frame,
            text="截屏时隐藏主窗口",
            variable=self.hide_window_var
        )
        hide_window_check.pack(anchor=tk.W, padx=5, pady=5)

        # 自动翻译设置 - 添加在隐藏窗口设置下方
        self.auto_translate_var = tk.BooleanVar(value=self.new_settings.get("auto_translate", True))
        auto_translate_check = ttk.Checkbutton(
            capture_frame,
            text="OCR完成后自动翻译并生成对话",
            variable=self.auto_translate_var
        )
        auto_translate_check.pack(anchor=tk.W, padx=5, pady=5)

        # 快捷键设置
        hotkey_frame = ttk.Frame(general_frame)
        hotkey_frame.pack(fill=tk.X, pady=5)

        ttk.Label(hotkey_frame, text="截图快捷键:").pack(side=tk.LEFT, padx=(0, 10))

        self.hotkey_var = tk.StringVar(value=self.new_settings.get("hotkey", "ctrl+alt+s"))
        hotkey_entry = ttk.Entry(
            hotkey_frame,
            textvariable=self.hotkey_var,
            width=20
        )
        hotkey_entry.pack(side=tk.LEFT, padx=5)

        ttk.Label(hotkey_frame, text="(如: ctrl+alt+s)").pack(side=tk.LEFT, padx=5)

        # 快捷键说明
        ttk.Label(
            general_frame,
            text="使用组合键作为快捷键，如'ctrl+alt+s'、'win+a'等",
            font=("微软雅黑", 8),
            foreground="#666666"
        ).pack(anchor=tk.W, padx=5, pady=(0, 5))

        # OCR设置
        ocr_frame = ttk.Frame(notebook, padding=10)
        notebook.add(ocr_frame, text="OCR设置")

        # 语言选择
        lang_frame = ttk.Frame(ocr_frame)
        lang_frame.pack(fill=tk.X, pady=5)

        ttk.Label(lang_frame, text="语言选择:").pack(side=tk.LEFT, padx=(0, 10))

        self.lang_var = tk.StringVar(value=self.new_settings["ocr_config"]["language"])
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

        self.psm_var = tk.StringVar(value=self.new_settings["ocr_config"]["psm"])
        psms = ttk.Combobox(psm_frame, textvariable=self.psm_var, width=20)
        psms['values'] = tuple(str(i) for i in range(14))
        psms.pack(side=tk.LEFT)

        # OEM模式选择
        oem_frame = ttk.Frame(ocr_frame)
        oem_frame.pack(fill=tk.X, pady=5)

        ttk.Label(oem_frame, text="OCR引擎模式(OEM):").pack(side=tk.LEFT, padx=(0, 10))

        self.oem_var = tk.StringVar(value=self.new_settings["ocr_config"]["oem"])
        oems = ttk.Combobox(oem_frame, textvariable=self.oem_var, width=20)
        oems['values'] = ('0', '1', '2', '3')
        oems.pack(side=tk.LEFT)

        # OCR路径设置
        path_frame = ttk.Frame(ocr_frame)
        path_frame.pack(fill=tk.X, pady=5)

        ttk.Label(path_frame, text="Tesseract路径:").pack(side=tk.LEFT, padx=(0, 10))

        self.tesseract_path_var = tk.StringVar(value=self.new_settings["tesseract_path"])
        ttk.Entry(path_frame, textvariable=self.tesseract_path_var, width=30).pack(side=tk.LEFT, fill=tk.X, expand=True)

        # 语言包路径
        tessdata_frame = ttk.Frame(ocr_frame)
        tessdata_frame.pack(fill=tk.X, pady=5)

        ttk.Label(tessdata_frame, text="语言包路径:").pack(side=tk.LEFT, padx=(0, 10))

        self.tessdata_path_var = tk.StringVar(value=self.new_settings["tessdata_path"])
        ttk.Entry(tessdata_frame, textvariable=self.tessdata_path_var, width=30).pack(side=tk.LEFT, fill=tk.X, expand=True)

        # OCR预处理设置
        preprocess_frame = ttk.LabelFrame(ocr_frame, text="OCR预处理")
        preprocess_frame.pack(fill=tk.X, pady=10)

        # 灰度处理
        grayscale_frame = ttk.Frame(preprocess_frame)
        grayscale_frame.pack(fill=tk.X, pady=5)

        self.grayscale_var = tk.BooleanVar(value=self.new_settings["preprocessing"]["grayscale"])
        ttk.Checkbutton(
            grayscale_frame,
            text="启用灰度处理 (提高文本识别精度)",
            variable=self.grayscale_var
        ).pack(side=tk.LEFT, padx=5)

        # 反色处理
        invert_frame = ttk.Frame(preprocess_frame)
        invert_frame.pack(fill=tk.X, pady=5)

        self.invert_var = tk.BooleanVar(value=self.new_settings["preprocessing"]["invert"])
        ttk.Checkbutton(
            invert_frame,
            text="启用反色处理 (适用于浅色背景深色文字)",
            variable=self.invert_var
        ).pack(side=tk.LEFT, padx=5)

        # 二值化阈值
        threshold_frame = ttk.Frame(preprocess_frame)
        threshold_frame.pack(fill=tk.X, pady=5)

        ttk.Label(threshold_frame, text="二值化阈值 (0-255, 0=禁用):").pack(side=tk.LEFT, padx=(0, 10))

        self.threshold_var = tk.IntVar(value=self.new_settings["preprocessing"]["threshold"])
        ttk.Scale(
            threshold_frame,
            from_=0,
            to=255,
            orient=tk.HORIZONTAL,
            variable=self.threshold_var,
            length=200
        ).pack(side=tk.LEFT, padx=5)

        threshold_value = ttk.Label(threshold_frame, textvariable=self.threshold_var)
        threshold_value.pack(side=tk.LEFT, padx=5)

        # 更新阈值显示
        self.threshold_var.trace_add("write", lambda *args: threshold_value.config(text=self.threshold_var.get()))

        # 添加预处理示例图像
        example_frame = ttk.Frame(preprocess_frame)
        example_frame.pack(fill=tk.X, pady=10)

        # ttk.Label(example_frame, text="预处理效果预览:").pack(side=tk.LEFT, padx=(0, 10))
        #
        #
        # ttk.Label(
        #     example_frame,
        #     text="灰度处理可减少颜色干扰，二值化可增强文本边缘",
        #     font=("微软雅黑", 8),
        #     foreground="#666666"
        # ).pack(side=tk.LEFT)


        deepseek_frame = ttk.Frame(notebook, padding=10)
        notebook.add(deepseek_frame, text="AI翻译设置")

        # DeepSeek API密钥设置
        api_frame = ttk.Frame(deepseek_frame)
        api_frame.pack(fill=tk.X, pady=5)

        ttk.Label(api_frame, text="DeepSeek API密钥:").pack(side=tk.LEFT, padx=(0, 10))

        self.api_key_var = tk.StringVar(value=self.new_settings["deepseek_api_key"])
        api_entry = ttk.Entry(
            api_frame,
            textvariable=self.api_key_var,
            width=30,
            show="*"  # 以密码形式显示
        )
        api_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # 添加显示/隐藏按钮
        self.show_api_key = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            api_frame,
            text="显示",
            variable=self.show_api_key,
            command=lambda: self.toggle_api_key_visibility(api_entry)
        ).pack(side=tk.LEFT, padx=5)

        # API密钥说明
        api_info_frame = ttk.Frame(deepseek_frame)
        api_info_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(
            api_info_frame,
            text="获取API密钥: https://platform.deepseek.com/api-keys",
            font=("微软雅黑", 8),
            foreground="#666666"
        ).pack(side=tk.LEFT, padx=5)

        # AI模型设置
        ai_frame = ttk.Frame(deepseek_frame)
        ai_frame.pack(fill=tk.X, pady=5)

        ttk.Label(ai_frame, text="AI模型选择:").pack(side=tk.LEFT, padx=(0, 10))

        self.model_var = tk.StringVar(value=self.new_settings["deepseek_model"])
        models = ttk.Combobox(ai_frame, textvariable=self.model_var, width=20)
        models['values'] = ('deepseek-chat', 'deepseek-reasoner')
        models.pack(side=tk.LEFT)

        # 添加模型说明
        model_info_frame = ttk.Frame(deepseek_frame)
        model_info_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(
            model_info_frame,
            text="deepseek-chat: 通用聊天模型 | deepseek-reasoner: 逻辑推理模型",
            font=("微软雅黑", 8),
            foreground="#666666"
        ).pack(side=tk.LEFT, padx=5)

        # 翻译服务状态
        status_frame = ttk.Frame(deepseek_frame)
        status_frame.pack(fill=tk.X, pady=10)

        self.status_label = ttk.Label(
            status_frame,
            text="API密钥状态: " + ("已配置" if self.api_key_var.get() else "未配置"),
            font=("微软雅黑", 9),
            foreground="#4CAF50" if self.api_key_var.get() else "#F44336"
        )
        self.status_label.pack(side=tk.LEFT, padx=5)

        # 添加测试按钮
        test_btn = ttk.Button(
            status_frame,
            text="测试连接",
            command=self.test_deepseek_connection,
            width=10
        )
        test_btn.pack(side=tk.RIGHT, padx=5)

        # 添加使用说明
        instruction_frame = ttk.LabelFrame(deepseek_frame, text="使用说明")
        instruction_frame.pack(fill=tk.X, pady=10)

        instructions = [
            "1. 在DeepSeek官网获取API密钥",
            "2. 将API密钥粘贴到上方输入框",
            "3. 点击'测试连接'验证密钥有效性",
            "4. 保存设置后可在翻译功能中使用"
        ]

        for instruction in instructions:
            ttk.Label(
                instruction_frame,
                text=instruction,
                anchor=tk.W
            ).pack(fill=tk.X, padx=10, pady=2)
        # =================================================

        # 按钮
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=20)

        ttk.Button(btn_frame, text="应用", command=self.apply_settings).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="取消", command=self.on_cancel).pack(side=tk.RIGHT, padx=5)

    def toggle_api_key_visibility(self, entry):
        """切换API密钥的可见性"""
        if self.show_api_key.get():
            entry.config(show="")
            self.logger.debug("显示API密钥")
        else:
            entry.config(show="*")
            self.logger.debug("隐藏API密钥")

    def test_deepseek_connection(self):
        """测试DeepSeek API连接"""
        api_key = self.api_key_var.get().strip()
        if not api_key:
            self.logger.warning("测试API连接但未输入密钥")
            messagebox.showwarning("测试失败", "请输入API密钥")
            return

        self.logger.info("开始测试DeepSeek API连接")
        # 显示测试中状态
        self.status_label.config(text="API密钥状态: 测试中...", foreground="#FF9800")
        self.window.update()

        try:
            # 直接使用requests测试API连接
            result = self._test_deepseek_api_direct(api_key)

            # 检查结果是否有效
            if result and len(result.strip()) > 0:
                self.status_label.config(text="API密钥状态: 连接成功", foreground="#4CAF50")
                self.logger.info(f"DeepSeek API连接测试成功，")
                messagebox.showinfo("测试成功", f"成功连接到DeepSeek API服务！\n\nAPI响应: {result}")
            else:
                # 检查是否有错误信息
                self.status_label.config(text="API密钥状态: 测试失败", foreground="#F44336")
                self.logger.warning(f"API测试返回空结果")
                messagebox.showerror("测试失败", "API返回了空结果，请检查API密钥和模型设置")

        except Exception as e:
            self.status_label.config(text="API密钥状态: 测试失败", foreground="#F44336")
            self.logger.error(f"DeepSeek API连接测试失败: {str(e)}")
            messagebox.showerror("测试失败", f"连接测试时出错:\n{str(e)}")

    def _test_deepseek_api_direct(self, api_key):
        """直接使用requests测试DeepSeek API连接"""
        url = "https://api.deepseek.com/chat/completions"  # 使用官方API端点
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }

        # 使用官方测试代码的格式
        model = self.model_var.get()

        data = {
            "model": model,
            "messages": [
                {"role": "system", "content": "你是一个专业的助手"},
                {"role": "user", "content": "你是谁？"}
            ],
            "stream": False  # 关闭流式传输
        }

        self.logger.debug(f"发送测试请求到DeepSeek API: 模型={model}")

        try:
            # 发送请求
            response = requests.post(url, headers=headers, json=data, timeout=15)

            # 检查响应
            if response.status_code != 200:
                error_msg = f"API请求失败: HTTP {response.status_code}"
                self.logger.error(f"{error_msg}, 响应: {response.text}")
                return ""  # 返回空字符串

            # 解析响应
            response_data = response.json()
            self.logger.debug(f"API测试响应: {json.dumps(response_data)}")

            # 检查响应结构
            if "choices" not in response_data or len(response_data["choices"]) == 0:
                self.logger.warning(f"API响应缺少choices字段: {response_data}")
                return ""

            if "message" not in response_data["choices"][0]:
                self.logger.warning(f"API响应缺少message字段: {response_data}")
                return ""

            if "content" not in response_data["choices"][0]["message"]:
                self.logger.warning(f"API响应缺少content字段: {response_data}")
                return ""

            # 提取结果
            result = response_data["choices"][0]["message"]["content"].strip()
            self.logger.info(f"API测试返回结果: '{result}' (模型={model})")
            return result

        except Exception as e:
            self.logger.error(f"测试请求失败 (模型={model}): {str(e)}")
            return ""


    def on_cancel(self):
        """取消按钮处理"""
        self.logger.info("用户取消设置更改")
        self.settings_updated = False
        self.window.destroy()

    def apply_settings(self):
        """应用设置"""
        self.logger.info("应用设置")
        try:
            # 更新OCR配置
            self.new_settings["ocr_config"] = {
                "language": self.lang_var.get(),
                "psm": self.psm_var.get(),
                "oem": self.oem_var.get()
            }
            self.logger.info(f"更新OCR配置: 语言={self.lang_var.get()}, PSM={self.psm_var.get()}, OEM={self.oem_var.get()}")

            # 更新偏移设置
            self.new_settings["offset"] = {
                "horizontal": self.h_offset_var.get(),
                "vertical": self.v_offset_var.get()
            }
            self.logger.info(f"更新偏移设置: 水平={self.h_offset_var.get()}, 垂直={self.v_offset_var.get()}")

            # 更新路径设置
            self.new_settings["tesseract_path"] = self.tesseract_path_var.get()
            self.new_settings["tessdata_path"] = self.tessdata_path_var.get()
            self.logger.info(f"更新路径设置: Tesseract路径={self.tesseract_path_var.get()}, 语言包路径={self.tessdata_path_var.get()}")

            # 更新API密钥设置
            self.new_settings["deepseek_api_key"] = self.api_key_var.get()
            self.logger.info(f"更新API密钥: {self.api_key_var.get()[:6]}...")  # 只记录部分密钥

            # 更新AI模型设置
            self.new_settings["deepseek_model"] = self.model_var.get()
            self.logger.info(f"更新AI模型: {self.model_var.get()}")

            # 更新预处理设置
            self.new_settings["preprocessing"] = {
                "grayscale": self.grayscale_var.get(),
                "invert": self.invert_var.get(),
                "threshold": self.threshold_var.get()
            }
            self.logger.info(f"更新预处理设置: 灰度={self.grayscale_var.get()}, 反色={self.invert_var.get()}, 阈值={self.threshold_var.get()}")

            # 更新截屏时隐藏窗口设置
            self.new_settings["hide_window_on_capture"] = self.hide_window_var.get()
            self.logger.info(f"更新截屏隐藏窗口设置: {self.hide_window_var.get()}")

            # 更新自动翻译设置
            self.new_settings["auto_translate"] = self.auto_translate_var.get()
            self.logger.info(f"更新自动翻译设置: {self.auto_translate_var.get()}")

            # 更新快捷键设置
            self.new_settings["hotkey"] = self.hotkey_var.get()
            self.logger.info(f"更新快捷键: {self.hotkey_var.get()}")

            # 标记设置已更新
            self.settings_updated = True

            # 关闭窗口
            self.window.destroy()
            self.logger.info("设置已应用并关闭窗口")

        except Exception as e:
            self.logger.error(f"应用设置时出错: {str(e)}")
            messagebox.showerror("设置错误", f"应用设置时出错:\n{str(e)}")