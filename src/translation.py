# translation.py - 翻译功能模块
import requests
import json
import threading
from tkinter import messagebox

class TranslationEngine:
    """处理文本翻译功能的类"""

    def __init__(self, api_key=None, model="deepseek-chat"):
        self.api_key = api_key
        self.model = model  # 添加模型属性
        self.base_url = "https://api.deepseek.com/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def set_api_key(self, api_key):
        """设置API密钥"""
        self.api_key = api_key
        self.headers["Authorization"] = f"Bearer {api_key}"

    def set_model(self, model):
        """设置AI模型"""
        self.model = model

    def translate_text(self, text, direction="en2zh", callback=None):
        """翻译文本（异步执行）"""
        if not self.api_key:
            return "错误：未设置DeepSeek API密钥"

        # 在单独的线程中执行翻译
        threading.Thread(
            target=self._perform_translation,
            args=(text, direction, callback),
            daemon=True
        ).start()

    def _perform_translation(self, text, direction, callback):
        """执行翻译操作"""
        try:
            # 根据方向设置提示词
            if direction == "en2zh":
                prompt = f"请将以下英文文本翻译成中文：\n\n{text}"
            elif direction == "zh2en":
                prompt = f"请将以下中文文本翻译成英文：\n\n{text}"
            else:
                prompt = f"请翻译以下文本：\n\n{text}"

            payload = {
                "model": self.model,  # 使用配置的模型
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 2000,
                "stream": False
            }

            response = requests.post(
                self.base_url,
                headers=self.headers,
                data=json.dumps(payload),
                timeout=30
            )
            response.raise_for_status()

            result = response.json()
            translated_text = result['choices'][0]['message']['content'].strip()

            if callback:
                callback(translated_text)

            return translated_text

        except requests.exceptions.RequestException as e:
            error_msg = f"翻译请求失败: {str(e)}"
            if callback:
                callback(error_msg)
            return error_msg
        except (KeyError, IndexError) as e:
            error_msg = f"解析翻译结果失败: {str(e)}"
            if callback:
                callback(error_msg)
            return error_msg
        except Exception as e:
            error_msg = f"翻译过程中出错: {str(e)}"
            if callback:
                callback(error_msg)
            return error_msg