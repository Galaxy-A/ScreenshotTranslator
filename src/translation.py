# translation.py - 翻译功能模块
import requests
import threading
import time
import logging
import json

class TranslationEngine:
    """使用DeepSeek API处理文本翻译功能的类"""

    def __init__(self, api_key=None, model="deepseek-chat"):
        # 获取日志记录器
        self.logger = logging.getLogger("TranslationEngine")
        self.logger.info("初始化DeepSeek翻译引擎")

        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.deepseek.com/chat/completions"  # 使用官方API端点
        self.timeout = 30  # 默认超时时间30秒
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}" if api_key else ""
        }

    def set_api_key(self, api_key):
        """设置API密钥"""
        self.logger.info("设置API密钥")
        self.api_key = api_key
        self.headers["Authorization"] = f"Bearer {api_key}"

    def set_model(self, model):
        """设置AI模型"""
        self.logger.info(f"设置AI模型: {model}")
        self.model = model

    def translate_text(self, text, direction="en2zh", callback=None):
        """翻译文本（异步执行）"""
        if not self.api_key:
            error_msg = "错误：未设置有效的DeepSeek API密钥"
            self.logger.error(error_msg)
            if callback:
                callback(error_msg)
            return

        # 记录翻译文本长度
        char_count = len(text)
        self.logger.info(f"开始翻译: 方向={direction}, 字符数={char_count}")

        # 在单独的线程中执行翻译
        threading.Thread(
            target=self._perform_translation_with_retry,
            args=(text, direction, callback, 3),  # 重试3次
            daemon=True
        ).start()

    def _perform_translation_with_retry(self, text, direction, callback, retries):
        """带重试机制的翻译操作"""
        for attempt in range(retries):
            try:
                self.logger.info(f"翻译尝试 #{attempt+1}/{retries}")
                result = self._perform_translation(text, direction, callback)
                if callback:
                    callback(result)
                return result
            except Exception as e:
                error_msg = f"翻译请求失败: {str(e)}"
                self.logger.error(error_msg)

                if attempt < retries - 1:
                    wait_time = 2 ** attempt  # 指数退避策略
                    self.logger.info(f"请求失败，{wait_time}秒后重试...")
                    time.sleep(wait_time)
                else:
                    final_error = f"翻译失败: {str(e)}\n请检查网络连接和API密钥"
                    self.logger.error(final_error)
                    if callback:
                        callback(final_error)
                    return final_error

    def _perform_translation(self, text, direction, callback):
        """使用DeepSeek API执行翻译"""
        # 根据方向设置提示词
        if direction == "en2zh":
            user_content = f"请将以下英文文本准确翻译成中文：\n\n{text}"
            self.logger.debug("英译中提示词")
        elif direction == "zh2en":
            user_content = f"请将以下中文文本准确翻译成英文：\n\n{text}"
            self.logger.debug("中译英提示词")
        else:
            user_content = f"请准确翻译以下文本：\n\n{text}"
            self.logger.debug("自动检测翻译提示词")

        self.logger.debug(f"完整提示词: {user_content[:100]}...")  # 只记录前100个字符

        # 准备请求数据 - 使用官方格式
        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "你是一个专业的翻译助手"},
                {"role": "user", "content": user_content}
            ],
            "temperature": 1.3,
            "max_tokens": 4000,
            "stream": False
        }

        start_time = time.time()

        try:
            # 发送请求到DeepSeek API
            self.logger.debug("发送翻译请求到DeepSeek API")
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json=data,
                timeout=self.timeout
            )

            # 检查响应状态
            if response.status_code != 200:
                error_msg = f"API请求失败: HTTP {response.status_code}"
                self.logger.error(f"{error_msg}, 响应: {response.text}")
                raise Exception(f"{error_msg}: {response.text}")

            # 解析响应
            response_data = response.json()
            self.logger.debug(f"API响应: {json.dumps(response_data)}")

            if "choices" not in response_data or len(response_data["choices"]) == 0:
                error_msg = "API响应格式异常"
                self.logger.error(f"{error_msg}: {response_data}")
                raise Exception(error_msg)

            # 提取翻译结果
            translated_text = response_data["choices"][0]["message"]["content"].strip()

            # 记录性能指标
            elapsed_time = time.time() - start_time
            char_count = len(translated_text)
            self.logger.info(f"翻译完成: 字符数={char_count}, 耗时={elapsed_time:.2f}秒")

            return translated_text

        except requests.exceptions.Timeout:
            self.logger.error("API请求超时")
            raise Exception("API请求超时，请稍后重试")
        except requests.exceptions.ConnectionError:
            self.logger.error("网络连接错误")
            raise Exception("网络连接错误，请检查网络连接")
        except Exception as e:
            self.logger.error(f"翻译请求错误: {str(e)}")
            raise Exception(f"翻译失败: {str(e)}")