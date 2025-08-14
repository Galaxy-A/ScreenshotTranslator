# ocr_engine.py
import pytesseract
from PIL import Image, ImageOps, ImageEnhance
import logging

class OCREngine:
    """处理OCR识别相关功能的类"""

    def __init__(self):
        # 获取日志记录器
        self.logger = logging.getLogger("OCREngine")
        self.logger.info("OCR引擎初始化")

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

    def set_preprocessing(self, preprocessing):
        """设置预处理配置"""
        self.preprocessing = preprocessing
        self.logger.info(f"更新预处理配置: {preprocessing}")

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

        # 增强对比度
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.5)  # 增强1.5倍对比度
        preprocess_steps.append("对比度增强(1.5x)")

        # 记录预处理步骤
        if preprocess_steps:
            self.logger.debug(f"图像预处理步骤: {' -> '.join(preprocess_steps)}")

        return image

    def perform_ocr(self, image, lang=None):
        """执行OCR识别"""
        if lang is None:
            lang = self.config['language']

        config_str = f'--psm {self.config["psm"]} --oem {self.config["oem"]}'

        # 记录OCR参数
        self.logger.info(f"执行OCR识别: 语言={lang}, PSM={self.config['psm']}, OEM={self.config['oem']}")

        # 预处理图像
        processed_image = self.preprocess_image(image)

        try:
            # 执行OCR
            result = pytesseract.image_to_string(
                processed_image,  # 使用预处理后的图像
                lang=lang,
                config=config_str
            )

            # 记录OCR结果摘要
            char_count = len(result.strip())
            word_count = len(result.split())
            self.logger.info(f"OCR识别完成: {char_count}字符, {word_count}单词")

            return result
        except pytesseract.TesseractNotFoundError as e:
            self.logger.error(f"Tesseract路径错误: {str(e)}")
            raise Exception("Tesseract路径配置错误，请检查设置中的路径配置")
        except pytesseract.TesseractError as e:
            self.logger.error(f"Tesseract识别错误: {str(e)}")
            raise Exception(f"OCR识别错误: {str(e)}")
        except Exception as e:
            self.logger.error(f"OCR处理失败: {str(e)}")
            raise Exception(f"OCR处理失败: {str(e)}")

    def update_config(self, language, psm, oem):
        """更新OCR配置"""
        self.config['language'] = language
        self.config['psm'] = psm
        self.config['oem'] = oem
        self.logger.info(f"更新OCR配置: 语言={language}, PSM={psm}, OEM={oem}")