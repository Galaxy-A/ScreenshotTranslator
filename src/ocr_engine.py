# ocr_engine.py
import pytesseract
from PIL import Image, ImageOps, ImageEnhance

class OCREngine:
    """处理OCR识别相关功能的类"""

    def __init__(self):
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

    def preprocess_image(self, image):
        """对图像进行预处理以提高OCR精度"""
        # 灰度处理
        if self.preprocessing.get("grayscale", True):
            image = image.convert('L')

        # 反色处理（适用于浅色背景深色文字的情况）
        if self.preprocessing.get("invert", False):
            image = ImageOps.invert(image)

        # 二值化处理
        threshold = self.preprocessing.get("threshold", 0)
        if threshold > 0:
            # 简单的二值化处理
            image = image.point(lambda p: p > threshold and 255)

        # 增强对比度
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.5)  # 增强1.5倍对比度

        return image

    def perform_ocr(self, image, lang=None):
        """执行OCR识别"""
        if lang is None:
            lang = self.config['language']

        config_str = f'--psm {self.config["psm"]} --oem {self.config["oem"]}'

        # 预处理图像
        processed_image = self.preprocess_image(image)

        return pytesseract.image_to_string(
            processed_image,  # 使用预处理后的图像
            lang=lang,
            config=config_str
        )

    def update_config(self, language, psm, oem):
        """更新OCR配置"""
        self.config['language'] = language
        self.config['psm'] = psm
        self.config['oem'] = oem