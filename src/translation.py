# translation.py - 翻译功能模块
import requests
import threading
import time
import logging
import json

class TranslationEngine:
    """使用OpenAI兼容API处理文本翻译功能的类（支持OpenAI和DeepSeek）"""

    def __init__(self, api_key=None, model="gpt-3.5-turbo", provider="openai"):
        # 获取日志记录器
        self.logger = logging.getLogger("TranslationEngine")
        
        self.api_key = api_key
        self.model = model
        self.provider = provider  # "openai" 或 "deepseek"
        
        # 根据提供商设置API端点
        if provider == "deepseek":
            self.base_url = "https://api.deepseek.com"
        else:
            self.base_url = "https://api.openai.com/v1"
        
        self.timeout = 30  # 默认超时时间30秒
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}" if api_key else ""
        }
        
        # 初始化OpenAI SDK客户端
        self._init_openai_client()

    def _init_openai_client(self):
        """初始化OpenAI SDK客户端"""
        try:
            from openai import OpenAI
            self.openai_client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
            pass  # OpenAI SDK客户端初始化成功
        except ImportError:
            self.openai_client = None
        except Exception as e:
            self.logger.error(f"OpenAI SDK客户端初始化失败: {str(e)}")
            self.openai_client = None

    def set_api_key(self, api_key):
        """设置API密钥"""
        self.api_key = api_key
        self.headers["Authorization"] = f"Bearer {api_key}"
        # 重新初始化OpenAI客户端
        self._init_openai_client()

    def set_model(self, model):
        """设置AI模型"""
        self.model = model

    def set_provider(self, provider):
        """设置API提供商"""
        self.provider = provider
        
        # 根据提供商更新API端点
        if provider == "deepseek":
            self.base_url = "https://api.deepseek.com"
        else:
            self.base_url = "https://api.openai.com/v1"
        
        # 重新初始化OpenAI客户端
        self._init_openai_client()

    def translate_text(self, text, direction="en2zh", callback=None, stream_callback=None):
        """翻译文本（异步执行，支持流式输出）"""
        if not self.api_key:
            provider_name = "DeepSeek" if self.provider == "deepseek" else "OpenAI"
            error_msg = f"错误：未设置有效的{provider_name} API密钥"
            self.logger.error(error_msg)
            if callback:
                callback(error_msg)
            return

        # 记录翻译文本长度
        char_count = len(text)

        # 在单独的线程中执行翻译
        threading.Thread(
            target=self._perform_translation_with_retry,
            args=(text, direction, callback, stream_callback, 3),  # 重试3次
            daemon=True
        ).start()

    def _perform_translation_with_retry(self, text, direction, callback, stream_callback, retries):
        """带重试机制的翻译操作"""
        for attempt in range(retries):
            try:
                result = self._perform_translation(text, direction, callback, stream_callback)
                if callback:
                    callback(result)
                return result
            except Exception as e:
                error_msg = f"翻译请求失败: {str(e)}"

                if attempt < retries - 1:
                    wait_time = 2 ** attempt  # 指数退避策略
                    time.sleep(wait_time)
                else:
                    final_error = f"翻译失败: {str(e)}\n请检查网络连接和API密钥"
                    self.logger.error(final_error)
                    if callback:
                        callback(final_error)
                    return final_error

    def _detect_text_type(self, text):
        """检测文本类型以优化翻译策略"""
        text_lower = text.lower().strip()
        
        # 检测代码类型
        if any(keyword in text_lower for keyword in ['function', 'class', 'import', 'def', 'return', 'if', 'else', 'for', 'while']):
            return "code"
        
        # 检测日志类型
        if any(keyword in text_lower for keyword in ['error', 'warning', 'info', 'debug', 'exception', 'traceback']):
            return "log"
        
        # 检测命令类型
        if any(keyword in text_lower for keyword in ['cmd', 'command', 'run', 'execute', 'install', 'pip', 'npm']):
            return "command"
        
        # 检测技术文档
        if any(keyword in text_lower for keyword in ['api', 'config', 'setting', 'parameter', 'option']):
            return "technical"
        
        return "general"

    def _get_language_name(self, lang_code):
        """获取语言代码对应的语言名称"""
        lang_names = {
            "zh": "中文",
            "en": "英文", 
            "ja": "日文",
            "ko": "韩文",
            "fr": "法文",
            "de": "德文",
            "es": "西班牙文",
            "ru": "俄文",
            "ar": "阿拉伯文",
            "it": "意大利文",
            "pt": "葡萄牙文",
            "nl": "荷兰文",
            "sv": "瑞典文",
            "no": "挪威文",
            "da": "丹麦文",
            "fi": "芬兰文",
            "pl": "波兰文",
            "cs": "捷克文",
            "hu": "匈牙利文",
            "el": "希腊文",
            "tr": "土耳其文",
            "he": "希伯来文",
            "th": "泰文",
            "vi": "越南文",
            "id": "印尼文",
            "ms": "马来文",
            "hi": "印地文",
            "ur": "乌尔都文",
            "fa": "波斯文"
        }
        return lang_names.get(lang_code, lang_code)

    def _get_optimized_prompt(self, text, direction, text_type):
        """根据文本类型获取优化的提示词"""
        # 解析翻译方向
        if "2" in direction:
            source_code, target_code = direction.split("2", 1)
            source_lang = self._get_language_name(source_code)
            target_lang = self._get_language_name(target_code)
        else:
            # 兼容旧的翻译方向格式
            source_lang = "未知"
            target_lang = "中文"
        
        base_prompts = {
            "en2zh": {
                "code": f"""请将以下英文代码/技术文本翻译成中文：

原文：{text}

翻译要求：
1. 保持代码语法和格式不变
2. 翻译注释和字符串内容
3. 保持变量名、函数名等技术标识符不变
4. 如果是错误信息，请提供准确的中文描述
5. 保持代码的可读性和专业性

翻译结果：""",
                "log": f"""请将以下英文日志/错误信息翻译成中文：

原文：{text}

翻译要求：
1. 准确翻译错误类型和描述
2. 保持日志级别（ERROR、WARNING、INFO等）不变
3. 翻译时间戳和路径信息
4. 如果是技术错误，请提供专业的中文术语
5. 保持日志的格式和结构

翻译结果：""",
                "command": f"""请将以下英文命令/操作说明翻译成中文：

原文：{text}

翻译要求：
1. 保持命令语法和参数不变
2. 翻译命令说明和帮助信息
3. 保持文件路径和URL格式
4. 如果是安装或配置说明，请提供清晰的中文指导
5. 保持技术术语的准确性

翻译结果：""",
                "technical": f"""请将以下英文技术文档翻译成中文：

原文：{text}

翻译要求：
1. 保持专业术语的准确性
2. 翻译配置项和参数说明
3. 保持API接口和数据结构不变
4. 如果是设置说明，请提供清晰的中文描述
5. 保持技术文档的专业性

翻译结果：""",
                "general": f"""请将以下英文文本翻译成中文：

原文：{text}

翻译要求：
1. 保持原文的语气和风格
2. 如果遇到OCR识别错误，请根据上下文推测正确内容
3. 保持专业术语的准确性
4. 输出简洁自然的中文表达
5. 保持原文的格式和结构

翻译结果："""
            },
            "zh2en": {
                "code": f"""Please translate the following Chinese code/technical text into English:

原文：{text}

Translation requirements:
1. Keep code syntax and format unchanged
2. Translate comments and string content
3. Keep variable names, function names and technical identifiers unchanged
4. If it's an error message, provide accurate English description
5. Maintain code readability and professionalism

Translation:""",
                "log": f"""Please translate the following Chinese log/error message into English:

原文：{text}

Translation requirements:
1. Accurately translate error types and descriptions
2. Keep log levels (ERROR, WARNING, INFO, etc.) unchanged
3. Translate timestamps and path information
4. If it's a technical error, provide professional English terminology
5. Maintain log format and structure

Translation:""",
                "command": f"""Please translate the following Chinese command/operation instructions into English:

原文：{text}

Translation requirements:
1. Keep command syntax and parameters unchanged
2. Translate command descriptions and help information
3. Keep file paths and URL formats
4. If it's installation or configuration instructions, provide clear English guidance
5. Maintain accuracy of technical terms

Translation:""",
                "technical": f"""Please translate the following Chinese technical documentation into English:

原文：{text}

Translation requirements:
1. Maintain accuracy of professional terms
2. Translate configuration items and parameter descriptions
3. Keep API interfaces and data structures unchanged
4. If it's setting instructions, provide clear English descriptions
5. Maintain professionalism of technical documentation

Translation:""",
                "general": f"""Please translate the following Chinese text into English:

原文：{text}

Translation requirements:
1. Preserve the tone and style of the original text
2. If OCR recognition errors are detected, infer correct content from context
3. Maintain accuracy of professional terms
4. Provide concise and natural English expression
5. Keep original format and structure

Translation:"""
            },
            "other2zh": {
                "code": f"""请将以下代码/技术文本翻译成中文：

原文：{text}

翻译要求：
1. 保持代码语法和格式不变
2. 翻译注释和字符串内容
3. 保持变量名、函数名等技术标识符不变
4. 如果是错误信息，请提供准确的中文描述
5. 保持代码的可读性和专业性
6. 自动识别源语言（英文、日文、韩文、法文、德文、西班牙文等）

翻译结果：""",
                "log": f"""请将以下日志/错误信息翻译成中文：

原文：{text}

翻译要求：
1. 准确翻译错误类型和描述
2. 保持日志级别（ERROR、WARNING、INFO等）不变
3. 翻译时间戳和路径信息
4. 如果是技术错误，请提供专业的中文术语
5. 保持日志的格式和结构
6. 自动识别源语言（英文、日文、韩文、法文、德文、西班牙文等）

翻译结果：""",
                "command": f"""请将以下命令/操作说明翻译成中文：

原文：{text}

翻译要求：
1. 保持命令语法和参数不变
2. 翻译命令说明和帮助信息
3. 保持文件路径和URL格式
4. 如果是安装或配置说明，请提供清晰的中文指导
5. 保持技术术语的准确性
6. 自动识别源语言（英文、日文、韩文、法文、德文、西班牙文等）

翻译结果：""",
                "technical": f"""请将以下技术文档翻译成中文：

原文：{text}

翻译要求：
1. 保持专业术语的准确性
2. 翻译配置项和参数说明
3. 保持API接口和数据结构不变
4. 如果是设置说明，请提供清晰的中文描述
5. 保持技术文档的专业性
6. 自动识别源语言（英文、日文、韩文、法文、德文、西班牙文等）

翻译结果：""",
                "general": f"""请将以下文本翻译成中文：

原文：{text}

翻译要求：
1. 保持原文的语气和风格
2. 如果遇到OCR识别错误，请根据上下文推测正确内容
3. 保持专业术语的准确性
4. 输出简洁自然的中文表达
5. 保持原文的格式和结构
6. 自动识别源语言（英文、日文、韩文、法文、德文、西班牙文等）

翻译结果："""
            },
            # 英文转中文
            "en2zh": {
                "code": f"""请将以下英文代码/技术文本翻译成中文：

原文：{text}

翻译要求：
1. 保持代码语法和格式不变
2. 翻译注释和字符串内容
3. 保持变量名、函数名等技术标识符不变
4. 如果是错误信息，请提供准确的中文描述
5. 保持代码的可读性和专业性

翻译结果：""",
                "log": f"""请将以下英文日志/错误信息翻译成中文：

原文：{text}

翻译要求：
1. 准确翻译错误类型和描述
2. 保持日志级别（ERROR、WARNING、INFO等）不变
3. 翻译时间戳和路径信息
4. 如果是技术错误，请提供专业的中文术语
5. 保持日志的格式和结构

翻译结果：""",
                "command": f"""请将以下英文命令/操作说明翻译成中文：

原文：{text}

翻译要求：
1. 保持命令语法和参数不变
2. 翻译命令说明和帮助信息
3. 保持文件路径和URL格式
4. 如果是安装或配置说明，请提供清晰的中文指导
5. 保持技术术语的准确性

翻译结果：""",
                "technical": f"""请将以下英文技术文档翻译成中文：

原文：{text}

翻译要求：
1. 保持专业术语的准确性
2. 翻译配置项和参数说明
3. 保持API接口和数据结构不变
4. 如果是设置说明，请提供清晰的中文描述
5. 保持技术文档的专业性

翻译结果：""",
                "general": f"""请将以下英文文本翻译成中文：

原文：{text}

翻译要求：
1. 保持原文的语气和风格
2. 如果遇到OCR识别错误，请根据上下文推测正确内容
3. 保持专业术语的准确性
4. 输出简洁自然的中文表达
5. 保持原文的格式和结构

翻译结果："""
            },
            # 日文转中文
            "ja2zh": {
                "general": f"""请将以下日文文本翻译成中文：

原文：{text}

翻译要求：
1. 准确理解日文含义并翻译成自然的中文
2. 保持原文的语气和风格
3. 如果是技术术语，请使用标准的中文译法
4. 保持原文的格式和结构
5. 如果遇到OCR识别错误，请根据上下文推测正确内容

翻译结果："""
            },
            # 韩文转中文
            "ko2zh": {
                "general": f"""请将以下韩文文本翻译成中文：

原文：{text}

翻译要求：
1. 准确理解韩文含义并翻译成自然的中文
2. 保持原文的语气和风格
3. 如果是技术术语，请使用标准的中文译法
4. 保持原文的格式和结构
5. 如果遇到OCR识别错误，请根据上下文推测正确内容

翻译结果："""
            },
            # 法文转中文
            "fr2zh": {
                "general": f"""请将以下法文文本翻译成中文：

原文：{text}

翻译要求：
1. 准确理解法文含义并翻译成自然的中文
2. 保持原文的语气和风格
3. 如果是技术术语，请使用标准的中文译法
4. 保持原文的格式和结构
5. 如果遇到OCR识别错误，请根据上下文推测正确内容

翻译结果："""
            },
            # 德文转中文
            "de2zh": {
                "general": f"""请将以下德文文本翻译成中文：

原文：{text}

翻译要求：
1. 准确理解德文含义并翻译成自然的中文
2. 保持原文的语气和风格
3. 如果是技术术语，请使用标准的中文译法
4. 保持原文的格式和结构
5. 如果遇到OCR识别错误，请根据上下文推测正确内容

翻译结果："""
            },
            # 西班牙文转中文
            "es2zh": {
                "general": f"""请将以下西班牙文文本翻译成中文：

原文：{text}

翻译要求：
1. 准确理解西班牙文含义并翻译成自然的中文
2. 保持原文的语气和风格
3. 如果是技术术语，请使用标准的中文译法
4. 保持原文的格式和结构
5. 如果遇到OCR识别错误，请根据上下文推测正确内容

翻译结果："""
            },
            # 俄文转中文
            "ru2zh": {
                "general": f"""请将以下俄文文本翻译成中文：

原文：{text}

翻译要求：
1. 准确理解俄文含义并翻译成自然的中文
2. 保持原文的语气和风格
3. 如果是技术术语，请使用标准的中文译法
4. 保持原文的格式和结构
5. 如果遇到OCR识别错误，请根据上下文推测正确内容

翻译结果："""
            },
            # 阿拉伯文转中文
            "ar2zh": {
                "general": f"""请将以下阿拉伯文文本翻译成中文：

原文：{text}

翻译要求：
1. 准确理解阿拉伯文含义并翻译成自然的中文
2. 保持原文的语气和风格
3. 如果是技术术语，请使用标准的中文译法
4. 保持原文的格式和结构
5. 如果遇到OCR识别错误，请根据上下文推测正确内容

翻译结果："""
            },
            # 中文转日文
            "zh2ja": {
                "general": f"""Please translate the following Chinese text into Japanese:

原文：{text}

Translation requirements:
1. Accurately understand the Chinese meaning and translate into natural Japanese
2. Maintain the tone and style of the original text
3. Use standard Japanese terminology for technical terms
4. Keep the original format and structure
5. If OCR recognition errors are detected, infer correct content from context

Translation:"""
            },
            # 中文转韩文
            "zh2ko": {
                "general": f"""Please translate the following Chinese text into Korean:

原文：{text}

Translation requirements:
1. Accurately understand the Chinese meaning and translate into natural Korean
2. Maintain the tone and style of the original text
3. Use standard Korean terminology for technical terms
4. Keep the original format and structure
5. If OCR recognition errors are detected, infer correct content from context

Translation:"""
            },
            # 中文转法文
            "zh2fr": {
                "general": f"""Please translate the following Chinese text into French:

原文：{text}

Translation requirements:
1. Accurately understand the Chinese meaning and translate into natural French
2. Maintain the tone and style of the original text
3. Use standard French terminology for technical terms
4. Keep the original format and structure
5. If OCR recognition errors are detected, infer correct content from context

Translation:"""
            },
            # 中文转德文
            "zh2de": {
                "general": f"""Please translate the following Chinese text into German:

原文：{text}

Translation requirements:
1. Accurately understand the Chinese meaning and translate into natural German
2. Maintain the tone and style of the original text
3. Use standard German terminology for technical terms
4. Keep the original format and structure
5. If OCR recognition errors are detected, infer correct content from context

Translation:"""
            },
            # 中文转西班牙文
            "zh2es": {
                "general": f"""Please translate the following Chinese text into Spanish:

原文：{text}

Translation requirements:
1. Accurately understand the Chinese meaning and translate into natural Spanish
2. Maintain the tone and style of the original text
3. Use standard Spanish terminology for technical terms
4. Keep the original format and structure
5. If OCR recognition errors are detected, infer correct content from context

Translation:"""
            },
            # 中文转俄文
            "zh2ru": {
                "general": f"""Please translate the following Chinese text into Russian:

原文：{text}

Translation requirements:
1. Accurately understand the Chinese meaning and translate into natural Russian
2. Maintain the tone and style of the original text
3. Use standard Russian terminology for technical terms
4. Keep the original format and structure
5. If OCR recognition errors are detected, infer correct content from context

Translation:"""
            },
            # 中文转阿拉伯文
            "zh2ar": {
                "general": f"""Please translate the following Chinese text into Arabic:

原文：{text}

Translation requirements:
1. Accurately understand the Chinese meaning and translate into natural Arabic
2. Maintain the tone and style of the original text
3. Use standard Arabic terminology for technical terms
4. Keep the original format and structure
5. If OCR recognition errors are detected, infer correct content from context

Translation:"""
            }
        }
        
        # 如果找到特定的翻译方向提示词，使用它
        if direction in base_prompts and text_type in base_prompts[direction]:
            return base_prompts[direction][text_type]
        
        # 否则生成通用提示词
        return self._generate_generic_prompt(text, source_lang, target_lang, text_type)
    
    def _generate_generic_prompt(self, text, source_lang, target_lang, text_type):
        """生成通用的翻译提示词"""
        # 根据目标语言选择提示词语言
        if target_lang == "中文":
            prompt_lang = "中文"
            result_label = "翻译结果："
        else:
            prompt_lang = "英文"
            result_label = "Translation:"
        
        # 根据文本类型调整提示词
        if text_type == "code":
            if prompt_lang == "中文":
                return f"""请将以下{source_lang}代码/技术文本翻译成{target_lang}：

原文：{text}

翻译要求：
1. 保持代码语法和格式不变
2. 翻译注释和字符串内容
3. 保持变量名、函数名等技术标识符不变
4. 如果是错误信息，请提供准确的{target_lang}描述
5. 保持代码的可读性和专业性

{result_label}"""
            else:
                return f"""Please translate the following {source_lang} code/technical text into {target_lang}:

原文：{text}

Translation requirements:
1. Keep code syntax and format unchanged
2. Translate comments and string content
3. Keep variable names, function names and technical identifiers unchanged
4. If it's an error message, provide accurate {target_lang} description
5. Maintain code readability and professionalism

{result_label}"""
        
        elif text_type == "log":
            if prompt_lang == "中文":
                return f"""请将以下{source_lang}日志/错误信息翻译成{target_lang}：

原文：{text}

翻译要求：
1. 准确翻译错误类型和描述
2. 保持日志级别（ERROR、WARNING、INFO等）不变
3. 翻译时间戳和路径信息
4. 如果是技术错误，请提供专业的{target_lang}术语
5. 保持日志的格式和结构

{result_label}"""
            else:
                return f"""Please translate the following {source_lang} log/error message into {target_lang}:

原文：{text}

Translation requirements:
1. Accurately translate error types and descriptions
2. Keep log levels (ERROR, WARNING, INFO, etc.) unchanged
3. Translate timestamps and path information
4. If it's a technical error, provide professional {target_lang} terminology
5. Maintain log format and structure

{result_label}"""
        
        elif text_type == "command":
            if prompt_lang == "中文":
                return f"""请将以下{source_lang}命令/操作说明翻译成{target_lang}：

原文：{text}

翻译要求：
1. 保持命令语法和参数不变
2. 翻译命令说明和帮助信息
3. 保持文件路径和URL格式
4. 如果是安装或配置说明，请提供清晰的{target_lang}指导
5. 保持技术术语的准确性

{result_label}"""
            else:
                return f"""Please translate the following {source_lang} command/operation instructions into {target_lang}:

原文：{text}

Translation requirements:
1. Keep command syntax and parameters unchanged
2. Translate command descriptions and help information
3. Keep file paths and URL formats
4. If it's installation or configuration instructions, provide clear {target_lang} guidance
5. Maintain accuracy of technical terms

{result_label}"""
        
        elif text_type == "technical":
            if prompt_lang == "中文":
                return f"""请将以下{source_lang}技术文档翻译成{target_lang}：

原文：{text}

翻译要求：
1. 保持专业术语的准确性
2. 翻译配置项和参数说明
3. 保持API接口和数据结构不变
4. 如果是设置说明，请提供清晰的{target_lang}描述
5. 保持技术文档的专业性

{result_label}"""
            else:
                return f"""Please translate the following {source_lang} technical documentation into {target_lang}:

原文：{text}

Translation requirements:
1. Maintain accuracy of professional terms
2. Translate configuration items and parameter descriptions
3. Keep API interfaces and data structures unchanged
4. If it's setting instructions, provide clear {target_lang} descriptions
5. Maintain professionalism of technical documentation

{result_label}"""
        
        else:  # general
            if prompt_lang == "中文":
                return f"""请将以下{source_lang}文本翻译成{target_lang}：

原文：{text}

翻译要求：
1. 保持原文的语气和风格
2. 如果遇到OCR识别错误，请根据上下文推测正确内容
3. 保持专业术语的准确性
4. 输出简洁自然的{target_lang}表达
5. 保持原文的格式和结构

{result_label}"""
            else:
                return f"""Please translate the following {source_lang} text into {target_lang}:

原文：{text}

Translation requirements:
1. Preserve the tone and style of the original text
2. If OCR recognition errors are detected, infer correct content from context
3. Maintain accuracy of professional terms
4. Provide concise and natural {target_lang} expression
5. Keep original format and structure

{result_label}"""

    def _perform_translation(self, text, direction, callback, stream_callback):
        """使用OpenAI兼容API执行翻译（支持流式输出）"""
        # 检测文本类型并获取优化的提示词
        text_type = self._detect_text_type(text)
        user_content = self._get_optimized_prompt(text, direction, text_type)

        start_time = time.time()

        try:
            # 优先使用OpenAI SDK
            if self.openai_client:
                return self._perform_translation_with_sdk(user_content, stream_callback, start_time)
            else:
                # 回退到requests方式
                return self._perform_translation_with_requests(user_content, stream_callback, start_time)

        except Exception as e:
            self.logger.error(f"翻译请求错误: {str(e)}")
            raise Exception(f"翻译失败: {str(e)}")

    def _perform_translation_with_sdk(self, user_content, stream_callback, start_time):
        """使用OpenAI SDK执行翻译"""
        try:
            
            messages = [
                {"role": "system", "content": "你是一位专业的翻译专家，具有以下特点：\n1. 精通中英文互译，能够准确理解原文含义\n2. 翻译时保持原文的语气、风格和语境\n3. 对于技术术语、专业词汇会使用标准译法\n4. 对于OCR识别可能存在的错误，会结合上下文进行合理推测和修正\n5. 输出简洁明了，避免冗余表达\n6. 如果原文是代码、命令或特殊格式，会保持原有格式\n请提供准确、自然、流畅的翻译。"},
                {"role": "user", "content": user_content}
            ]

            if stream_callback:
                # 流式翻译
                full_text = ""
                stream = self.openai_client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.3,
                    max_tokens=4000,
                    stream=True
                )
                
                for chunk in stream:
                    if chunk.choices[0].delta.content is not None:
                        content = chunk.choices[0].delta.content
                        full_text += content
                        stream_callback(content)
                
                return full_text.strip()
            else:
                # 非流式翻译
                response = self.openai_client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.3,
                    max_tokens=4000,
                    stream=False
                )
                
                translated_text = response.choices[0].message.content.strip()
                
                return translated_text

        except Exception as e:
            self.logger.error(f"OpenAI SDK翻译失败: {str(e)}")
            raise Exception(f"SDK翻译失败: {str(e)}")

    def _perform_translation_with_requests(self, user_content, stream_callback, start_time):
        """使用requests执行翻译（回退方案）"""
        # 准备请求数据
        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "你是一位专业的翻译专家，具有以下特点：\n1. 精通中英文互译，能够准确理解原文含义\n2. 翻译时保持原文的语气、风格和语境\n3. 对于技术术语、专业词汇会使用标准译法\n4. 对于OCR识别可能存在的错误，会结合上下文进行合理推测和修正\n5. 输出简洁明了，避免冗余表达\n6. 如果原文是代码、命令或特殊格式，会保持原有格式\n请提供准确、自然、流畅的翻译。"},
                {"role": "user", "content": user_content}
            ],
            "temperature": 0.3,
            "max_tokens": 4000,
            "stream": stream_callback is not None
        }

        # 构建完整的API URL
        api_url = f"{self.base_url}/chat/completions"

        try:
            response = requests.post(
                api_url,
                headers=self.headers,
                json=data,
                timeout=self.timeout,
                stream=data["stream"]
            )

            # 检查响应状态
            if response.status_code != 200:
                error_msg = f"API请求失败: HTTP {response.status_code}"
                self.logger.error(f"{error_msg}, 响应: {response.text}")
                raise Exception(f"{error_msg}: {response.text}")

            if data["stream"]:
                # 处理流式响应
                return self._handle_stream_response(response, stream_callback, start_time)
            else:
                # 处理非流式响应
                return self._handle_normal_response(response, start_time)

        except requests.exceptions.Timeout:
            self.logger.error("API请求超时")
            raise Exception("API请求超时，请稍后重试")
        except requests.exceptions.ConnectionError:
            self.logger.error("网络连接错误")
            raise Exception("网络连接错误，请检查网络连接")
        except Exception as e:
            self.logger.error(f"requests翻译失败: {str(e)}")
            raise Exception(f"requests翻译失败: {str(e)}")

    def _handle_stream_response(self, response, stream_callback, start_time):
        """处理流式响应"""
        full_text = ""
        try:
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        data = line[6:]  # 移除 'data: ' 前缀
                        if data.strip() == '[DONE]':
                            break
                        
                        try:
                            json_data = json.loads(data)
                            if 'choices' in json_data and len(json_data['choices']) > 0:
                                delta = json_data['choices'][0].get('delta', {})
                                if 'content' in delta:
                                    content = delta['content']
                                    full_text += content
                                    # 调用流式回调
                                    if stream_callback:
                                        stream_callback(content)
                        except json.JSONDecodeError:
                            continue

            return full_text.strip()

        except Exception as e:
            self.logger.error(f"处理流式响应时出错: {str(e)}")
            raise Exception(f"流式翻译失败: {str(e)}")

    def _handle_normal_response(self, response, start_time):
        """处理非流式响应"""
        # 解析响应
        response_data = response.json()

        if "choices" not in response_data or len(response_data["choices"]) == 0:
            error_msg = "API响应格式异常"
            self.logger.error(f"{error_msg}: {response_data}")
            raise Exception(error_msg)

        # 提取翻译结果
        translated_text = response_data["choices"][0]["message"]["content"].strip()

        return translated_text

    def generate_dialogue(self, original_text, translated_text, sentence_count=3, callback=None, stream_callback=None):
        """根据翻译结果生成中英文对照对话（异步执行，支持流式输出）"""
        if not self.api_key:
            provider_name = "DeepSeek" if self.provider == "deepseek" else "OpenAI"
            error_msg = f"错误：未设置有效的{provider_name} API密钥"
            self.logger.error(error_msg)
            if callback:
                callback(error_msg)
            return

        # 记录对话生成请求

        # 在新线程中执行对话生成
        def _generate_dialogue_thread():
            try:
                result = self._perform_dialogue_generation_with_retry(
                    original_text, translated_text, sentence_count, stream_callback
                )
                if callback:
                    callback(result)
            except Exception as e:
                error_msg = f"对话生成失败: {str(e)}"
                self.logger.error(error_msg)
                if callback:
                    callback(error_msg)

        thread = threading.Thread(target=_generate_dialogue_thread, daemon=True)
        thread.start()

    def _perform_dialogue_generation_with_retry(self, original_text, translated_text, sentence_count, stream_callback=None):
        """执行对话生成（带重试机制）"""
        max_retries = 3
        retry_delay = 1

        for attempt in range(max_retries):
            try:
                return self._perform_dialogue_generation(original_text, translated_text, sentence_count, stream_callback)
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2  # 指数退避
                else:
                    raise e

    def _perform_dialogue_generation(self, original_text, translated_text, sentence_count, stream_callback=None):
        """执行对话生成"""
        start_time = time.time()

        # 构建对话生成提示词
        system_prompt = """你是一位专业的语言学习助手，擅长根据给定的中英文对照文本生成实用的对话练习。

请根据提供的原文和译文，生成{count}句自然、实用的中英文对照对话。要求：
1. 对话内容要与原文主题相关
2. 语言自然流畅，符合日常交流习惯
3. 难度适中，适合语言学习
4. 每句对话都要有中英文对照
5. 格式：中文 | English

请直接输出对话内容，不要添加其他说明。"""

        user_prompt = f"""原文：{original_text}

译文：{translated_text}

请生成{sentence_count}句中英文对照对话："""

        # 优先使用OpenAI SDK
        if self.openai_client:
            return self._perform_dialogue_generation_with_sdk(
                system_prompt.format(count=sentence_count),
                user_prompt,
                sentence_count,
                stream_callback
            )
        else:
            return self._perform_dialogue_generation_with_requests(
                system_prompt.format(count=sentence_count),
                user_prompt,
                sentence_count,
                stream_callback
            )

    def _perform_dialogue_generation_with_sdk(self, system_prompt, user_prompt, sentence_count, stream_callback=None):
        """使用OpenAI SDK生成对话"""
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]

            if stream_callback:
                # 流式生成
                response = self.openai_client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    stream=True,
                    temperature=0.7,
                    max_tokens=1000
                )

                full_content = ""
                for chunk in response:
                    if chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        full_content += content
                        stream_callback(content)

                return full_content
            else:
                # 非流式生成
                response = self.openai_client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=1000
                )

                return response.choices[0].message.content.strip()

        except Exception as e:
            self.logger.error(f"OpenAI SDK对话生成失败: {str(e)}")
            raise e

    def _perform_dialogue_generation_with_requests(self, system_prompt, user_prompt, sentence_count, stream_callback=None):
        """使用requests生成对话（备用方案）"""
        try:
            data = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 1000
            }

            if stream_callback:
                data["stream"] = True
                return self._handle_stream_dialogue_response(data, stream_callback)
            else:
                return self._handle_normal_dialogue_response(data)

        except Exception as e:
            self.logger.error(f"requests对话生成失败: {str(e)}")
            raise e

    def _handle_stream_dialogue_response(self, data, stream_callback):
        """处理流式对话响应"""
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=data,
                stream=True,
                timeout=self.timeout
            )
            response.raise_for_status()

            full_content = ""
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        data_str = line[6:]
                        if data_str.strip() == '[DONE]':
                            break
                        try:
                            chunk_data = json.loads(data_str)
                            if 'choices' in chunk_data and len(chunk_data['choices']) > 0:
                                delta = chunk_data['choices'][0].get('delta', {})
                                if 'content' in delta:
                                    content = delta['content']
                                    full_content += content
                                    stream_callback(content)
                        except json.JSONDecodeError:
                            continue

            return full_content

        except Exception as e:
            self.logger.error(f"流式对话响应处理失败: {str(e)}")
            raise e

    def _handle_normal_dialogue_response(self, data):
        """处理普通对话响应"""
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=data,
                timeout=self.timeout
            )
            response.raise_for_status()

            response_data = response.json()

            if "choices" not in response_data or len(response_data["choices"]) == 0:
                error_msg = "API响应格式异常"
                self.logger.error(f"{error_msg}: {response_data}")
                raise Exception(error_msg)

            return response_data["choices"][0]["message"]["content"].strip()

        except Exception as e:
            self.logger.error(f"普通对话响应处理失败: {str(e)}")
            raise e
