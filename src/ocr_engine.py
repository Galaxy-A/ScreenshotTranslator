# ocr_engine.py - 优化OCR引擎
import pytesseract
from PIL import Image, ImageOps, ImageEnhance
import logging
import time
from typing import Optional, Dict, Any, Callable
from error_handler import error_handler_decorator

class OCREngine:
    """优化的OCR识别引擎"""

    def __init__(self):
        # 获取日志记录器
        self.logger = logging.getLogger("OCREngine")
        # OCR引擎初始化

        # 默认配置
        self.config = {
            'language': 'chi_sim+eng',
            'psm': '3',
            'oem': '3'
        }
        self.preprocessing = {
            "grayscale": True,
            "invert": False,
            "threshold": 0
        }
        
        # 性能统计
        self.ocr_stats = {
            "total_ocr_calls": 0,
            "total_processing_time": 0,
            "average_processing_time": 0,
            "success_count": 0,
            "error_count": 0
        }
        
        # 缓存机制
        self.image_cache = {}
        self.cache_max_size = 10

    def set_preprocessing(self, preprocessing):
        """设置预处理配置"""
        self.preprocessing = preprocessing
        # 更新预处理配置

    def preprocess_image(self, image):
        """对图像进行预处理以提高OCR精度"""
        # 记录预处理步骤
        preprocess_steps = []

        # 灰度处理
        if self.preprocessing.get("grayscale", True):
            image = image.convert('L')
            preprocess_steps.append("灰度处理")

        # 反色处理（适用于浅色背景深色文字的情况）
        if self.preprocessing.get("invert", False):
            image = ImageOps.invert(image)
            preprocess_steps.append("反色处理")

        # 二值化处理
        threshold = self.preprocessing.get("threshold", 0)
        if threshold > 0:
            # 简单的二值化处理
            image = image.point(lambda p: p > threshold and 255)
            preprocess_steps.append(f"二值化处理(阈值={threshold})")

        # 增强对比度（保守设置）
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.2)  # 增强1.2倍对比度
        preprocess_steps.append("对比度增强(1.2x)")

        # 记录预处理步骤
        if preprocess_steps:
            pass  # 图像预处理步骤记录

        return image

    @error_handler_decorator("OCR识别")
    def perform_ocr(self, image, lang=None, progress_callback: Optional[Callable] = None):
        """执行OCR识别 - 优化版本"""
        start_time = time.time()
        self.ocr_stats["total_ocr_calls"] += 1
        
        if lang is None:
            lang = self.config['language']

        config_str = f'--psm {self.config["psm"]} --oem {self.config["oem"]}'

        # 记录OCR参数
        # 执行OCR识别
        
        # 进度回调
        if progress_callback:
            progress_callback(10, "开始OCR识别...")

        # 预处理图像
        processed_image = self.preprocess_image(image)
        if progress_callback:
            progress_callback(30, "图像预处理完成")

        try:
            # 执行OCR
            result = pytesseract.image_to_string(
                processed_image,  # 使用预处理后的图像
                lang=lang,
                config=config_str
            )
            
            if progress_callback:
                progress_callback(80, "OCR识别完成")

            # 记录OCR结果摘要
            char_count = len(result.strip())
            word_count = len(result.split())
            # OCR识别完成
            
            # 更新统计信息
            processing_time = time.time() - start_time
            self.ocr_stats["total_processing_time"] += processing_time
            self.ocr_stats["average_processing_time"] = (
                self.ocr_stats["total_processing_time"] / self.ocr_stats["total_ocr_calls"]
            )
            self.ocr_stats["success_count"] += 1
            
            if progress_callback:
                progress_callback(100, f"识别完成: {char_count}字符")

            return result
            
        except pytesseract.TesseractNotFoundError as e:
            self.ocr_stats["error_count"] += 1
            self.logger.error(f"Tesseract路径错误: {str(e)}")
            raise Exception("Tesseract路径配置错误，请检查设置中的路径配置")
        except pytesseract.TesseractError as e:
            self.ocr_stats["error_count"] += 1
            self.logger.error(f"Tesseract识别错误: {str(e)}")
            raise Exception(f"OCR识别错误: {str(e)}")
        except Exception as e:
            self.ocr_stats["error_count"] += 1
            self.logger.error(f"OCR处理失败: {str(e)}")
            raise Exception(f"OCR处理失败: {str(e)}")

    def update_config(self, language, psm, oem):
        """更新OCR配置"""
        self.config['language'] = language
        self.config['psm'] = psm
        self.config['oem'] = oem
        # 更新OCR配置
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计信息"""
        return self.ocr_stats.copy()
    
    def reset_stats(self):
        """重置统计信息"""
        self.ocr_stats = {
            "total_ocr_calls": 0,
            "total_processing_time": 0,
            "average_processing_time": 0,
            "success_count": 0,
            "error_count": 0
        }
        # OCR统计信息已重置
    
    def optimize_for_text_type(self, image, text_type: str = "mixed"):
        """根据文本类型优化OCR参数"""
        if text_type == "chinese":
            self.config['language'] = 'chi_sim'
            self.config['psm'] = '6'
        elif text_type == "english":
            self.config['language'] = 'eng'
            self.config['psm'] = '3'
        elif text_type == "numbers":
            self.config['psm'] = '8'
        else:  # mixed
            self.config['language'] = 'chi_sim+eng'
            self.config['psm'] = '3'
        
        # OCR参数已优化
        return self.config.copy()