# translation.py - 翻译功能模块
import openai
import threading
import time
import logging
from openai import OpenAI
import sys
import os
import json

class TranslationEngine:
    """使用OpenAI SDK处理文本翻译功能的类"""

    def __init__(self, api_key=None, model="deepseek-chat"):
        # 获取日志记录器
        self.logger = logging.getLogger("TranslationEngine")
        self.logger.info("初始化翻译引擎")

        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.deepseek.com"  # DeepSeek API端点
        self.client = None
        self.timeout = 130  # 默认超时时间30秒

        # 如果提供了API密钥，立即初始化客户端
        if api_key:
            self.initialize_client()
        else:
            self.logger.warning("未提供API密钥")

    def initialize_client(self):
        """初始化OpenAI客户端"""
        try:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=self.timeout  # 设置全局超时
            )
            self.logger.info("OpenAI客户端初始化成功")
        except Exception as e:
            self.logger.error(f"OpenAI客户端初始化失败: {str(e)}")
            self.client = None

    def set_api_key(self, api_key):
        """设置API密钥并重新初始化客户端"""
        self.logger.info("设置API密钥")
        self.api_key = api_key
        self.initialize_client()

    def set_model(self, model):
        """设置AI模型"""
        self.logger.info(f"设置AI模型: {model}")
        self.model = model

    def translate_text(self, text, direction="en2zh", callback=None):
        """翻译文本（异步执行）"""
        if not self.api_key or not self.client:
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
                result = self._perform_streaming_translation(text, direction, callback)
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

    def _perform_streaming_translation(self, text, direction, callback):
        """使用OpenAI SDK的流式传输执行翻译"""
        # 根据方向设置提示词
        if direction == "en2zh":
            prompt = f"请将以下英文文本准确翻译成中文：\n\n{text}"
            self.logger.debug("英译中提示词")
        elif direction == "zh2en":
            prompt = f"请将以下中文文本准确翻译成英文：\n\n{text}"
            self.logger.debug("中译英提示词")
        else:
            prompt = f"请准确翻译以下文本：\n\n{text}"
            self.logger.debug("自动检测翻译提示词")

        self.logger.debug(f"完整提示词: {prompt[:100]}...")  # 只记录前100个字符

        # 初始化结果变量
        full_response = ""
        last_update_time = time.time()
        accumulated_text = ""
        start_time = time.time()
        received_chunks = 0
        timeout = 150  # 设置15秒超时

        # 显示初始状态
        if callback:
            callback("翻译中...")

        try:
            # 创建流式响应
            self.logger.debug("创建流式翻译请求")
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=4000,
                stream=True,
                timeout=timeout  # 设置请求超时
            )

            # 处理流式响应
            self.logger.debug("开始处理流式响应")
            for chunk in stream:
                # 检查超时
                if time.time() - start_time > timeout:
                    self.logger.warning(f"流式响应超时 ({timeout}秒)")
                    raise openai.APITimeoutError("流式响应超时")

                if chunk.choices[0].delta.content is not None:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    accumulated_text += content
                    received_chunks += 1

                    # 定期更新UI
                    current_time = time.time()
                    if current_time - last_update_time > 0.3:
                        if callback and accumulated_text:
                            callback(accumulated_text)
                        accumulated_text = ""
                        last_update_time = current_time

            # 处理剩余文本
            if accumulated_text and callback:
                callback(accumulated_text)

            # 记录性能指标
            elapsed_time = time.time() - start_time
            char_count = len(full_response.strip())
            self.logger.info(f"流式翻译完成: 接收块={received_chunks}, 字符数={char_count}, 耗时={elapsed_time:.2f}秒")

            return full_response.strip()

        except openai.APITimeoutError:
            # 超时异常处理
            self.logger.error("API请求超时")
            if full_response:
                self.logger.warning(f"返回部分翻译结果: {len(full_response)}字符")
                return full_response.strip() + "\n\n[翻译超时，返回部分结果]"
            else:
                raise Exception("API请求超时，请稍后重试")
        except openai.APIError as e:
            self.logger.error(f"API错误: {str(e)}")
            # 尝试获取更多错误信息
            try:
                error_data = e.response.json()
                self.logger.debug(f"API错误详情: {json.dumps(error_data)}")
                error_code = error_data.get('error', {}).get('code', 'unknown')
                error_msg = error_data.get('error', {}).get('message', str(e))
                raise Exception(f"API错误 ({error_code}): {error_msg}")
            except:
                raise Exception(f"API错误: {str(e)}")
        except Exception as e:
            self.logger.error(f"流式传输错误: {str(e)}")
            # 如果流式传输失败，尝试非流式传输
            self.logger.info("流式传输失败，尝试非流式传输")
            return self._perform_non_streaming_translation(text, direction, callback)

    def _perform_non_streaming_translation(self, text, direction, callback):
        """非流式传输的翻译操作"""
        self.logger.info("使用非流式传输进行翻译")
        try:
            # 根据方向设置提示词
            if direction == "en2zh":
                prompt = f"请将以下英文文本翻译成中文：\n\n{text}"
            elif direction == "zh2en":
                prompt = f"请将以下中文文本翻译成英文：\n\n{text}"
            else:
                prompt = f"请翻译以下文本：\n\n{text}"

            self.logger.debug(f"非流式提示词: {prompt[:100]}...")

            # 显示翻译中状态
            if callback:
                callback("正在翻译...")

            start_time = time.time()

            # 发送非流式请求
            self.logger.debug("发送非流式翻译请求")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=4000,
                stream=False,
                timeout=self.timeout  # 设置超时
            )

            # 提取翻译结果
            translated_text = response.choices[0].message.content.strip()

            # 记录性能指标
            elapsed_time = time.time() - start_time
            char_count = len(translated_text)
            self.logger.info(f"非流式翻译完成: 字符数={char_count}, 耗时={elapsed_time:.2f}秒")

            return translated_text
        except openai.APIError as e:
            self.logger.error(f"API错误: {str(e)}")
            # 尝试获取更多错误信息
            try:
                error_data = e.response.json()
                self.logger.debug(f"API错误详情: {json.dumps(error_data)}")
                error_code = error_data.get('error', {}).get('code', 'unknown')
                error_msg = error_data.get('error', {}).get('message', str(e))
                raise Exception(f"API错误 ({error_code}): {error_msg}")
            except:
                raise Exception(f"API错误: {str(e)}")
        except Exception as e:
            self.logger.error(f"非流式传输错误: {str(e)}")
            raise Exception(f"翻译失败: {str(e)}")