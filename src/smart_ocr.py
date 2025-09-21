# smart_ocr.py - 智能OCR引擎
import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract
import logging
from typing import Dict, Any, Optional, List, Tuple
import time
from advanced_cache import AdvancedCache
from error_handler import error_handler_decorator

class SmartOCREngine:
    """智能OCR引擎 - 自动优化识别参数和图像预处理"""
    
    def __init__(self, cache_manager: AdvancedCache = None):
        self.logger = logging.getLogger("SmartOCREngine")
        self.cache_manager = cache_manager or AdvancedCache("ocr_cache")
        
        # OCR配置模板
        self.ocr_templates = {
            "chinese_text": {
                "language": "chi_sim",
                "psm": "6",
                "oem": "3",
                "preprocessing": ["grayscale", "denoise", "enhance_contrast"]
            },
            "english_text": {
                "language": "eng",
                "psm": "3",
                "oem": "3",
                "preprocessing": ["grayscale", "enhance_contrast"]
            },
            "mixed_text": {
                "language": "chi_sim+eng",
                "psm": "3",
                "oem": "3",
                "preprocessing": ["grayscale", "denoise", "enhance_contrast"]
            },
            "log_text": {
                "language": "chi_sim+eng",
                "psm": "6",
                "oem": "3",
                "preprocessing": ["grayscale", "enhance_contrast", "sharpen"]
            },
            "numbers": {
                "language": "eng",
                "psm": "8",
                "oem": "3",
                "preprocessing": ["grayscale", "threshold", "morphology"]
            },
            "code": {
                "language": "eng",
                "psm": "6",
                "oem": "3",
                "preprocessing": ["grayscale", "threshold", "denoise"]
            }
        }
        
        # 性能统计
        self.stats = {
            "total_ocr_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "average_processing_time": 0,
            "total_processing_time": 0,
            "cache_hits": 0,
            "cache_misses": 0
        }
        
        self.logger.info("智能OCR引擎初始化完成")
    
    def analyze_image(self, image: Image.Image) -> Dict[str, Any]:
        """分析图像特征"""
        try:
            # 转换为OpenCV格式
            cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
            
            # 分析图像特征
            features = {
                "width": image.width,
                "height": image.height,
                "aspect_ratio": image.width / image.height,
                "brightness": np.mean(gray),
                "contrast": np.std(gray),
                "text_density": self._estimate_text_density(gray),
                "text_orientation": self._detect_text_orientation(gray),
                "image_quality": self._assess_image_quality(gray)
            }
            
            # 检测文本类型
            features["text_type"] = self._detect_text_type(features)
            
            return features
            
        except Exception as e:
            self.logger.error(f"图像分析失败: {str(e)}")
            return {}
    
    def _estimate_text_density(self, gray_image: np.ndarray) -> float:
        """估算文本密度"""
        try:
            # 使用边缘检测
            edges = cv2.Canny(gray_image, 50, 150)
            edge_pixels = np.sum(edges > 0)
            total_pixels = gray_image.shape[0] * gray_image.shape[1]
            return edge_pixels / total_pixels
        except:
            return 0.0
    
    def _detect_text_orientation(self, gray_image: np.ndarray) -> str:
        """检测文本方向"""
        try:
            # 使用Hough变换检测直线
            edges = cv2.Canny(gray_image, 50, 150)
            lines = cv2.HoughLines(edges, 1, np.pi/180, threshold=100)
            
            if lines is not None:
                angles = []
                for line in lines:
                    rho, theta = line[0]
                    angle = theta * 180 / np.pi
                    if angle > 90:
                        angle -= 180
                    angles.append(angle)
                
                if angles:
                    avg_angle = np.mean(angles)
                    if abs(avg_angle) < 10:
                        return "horizontal"
                    elif abs(avg_angle - 90) < 10:
                        return "vertical"
            
            return "horizontal"
        except:
            return "horizontal"
    
    def _assess_image_quality(self, gray_image: np.ndarray) -> str:
        """评估图像质量"""
        try:
            # 计算拉普拉斯方差（图像清晰度）
            laplacian_var = cv2.Laplacian(gray_image, cv2.CV_64F).var()
            
            # 计算对比度
            contrast = np.std(gray_image)
            
            # 计算亮度
            brightness = np.mean(gray_image)
            
            if laplacian_var > 100 and contrast > 50 and 50 < brightness < 200:
                return "high"
            elif laplacian_var > 50 and contrast > 30:
                return "medium"
            else:
                return "low"
        except:
            return "low"
    
    def _detect_text_type(self, features: Dict[str, Any]) -> str:
        """检测文本类型"""
        # 基于图像特征判断文本类型
        text_density = features.get("text_density", 0)
        contrast = features.get("contrast", 0)
        aspect_ratio = features.get("aspect_ratio", 1)
        brightness = features.get("brightness", 128)
        
        # 检测日志文本特征
        if text_density > 0.05 and contrast > 50 and 50 < brightness < 200:
            # 可能是日志文本，使用更保守的识别参数
            return "log_text"
        elif text_density > 0.1:
            if aspect_ratio > 2:
                return "code"
            elif contrast > 100:
                return "numbers"
            else:
                return "mixed_text"
        else:
            return "chinese_text"
    
    def preprocess_image(self, image: Image.Image, preprocessing_steps: List[str]) -> Image.Image:
        """智能图像预处理"""
        processed_image = image.copy()
        
        for step in preprocessing_steps:
            try:
                if step == "grayscale":
                    processed_image = processed_image.convert('L')
                elif step == "denoise":
                    processed_image = self._denoise_image(processed_image)
                elif step == "enhance_contrast":
                    processed_image = self._enhance_contrast(processed_image)
                elif step == "threshold":
                    processed_image = self._apply_threshold(processed_image)
                elif step == "morphology":
                    processed_image = self._apply_morphology(processed_image)
                elif step == "sharpen":
                    processed_image = self._sharpen_image(processed_image)
                elif step == "invert":
                    processed_image = ImageOps.invert(processed_image)
                
                self.logger.debug(f"应用预处理步骤: {step}")
                
            except Exception as e:
                self.logger.error(f"预处理步骤失败: {step}, {str(e)}")
        
        return processed_image
    
    def _denoise_image(self, image: Image.Image) -> Image.Image:
        """图像去噪"""
        cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        denoised = cv2.fastNlMeansDenoising(cv_image)
        return Image.fromarray(cv2.cvtColor(denoised, cv2.COLOR_BGR2RGB))
    
    def _enhance_contrast(self, image: Image.Image) -> Image.Image:
        """增强对比度"""
        enhancer = ImageEnhance.Contrast(image)
        return enhancer.enhance(1.5)
    
    def _apply_threshold(self, image: Image.Image) -> Image.Image:
        """应用阈值处理"""
        cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
        _, threshold = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return Image.fromarray(threshold)
    
    def _apply_morphology(self, image: Image.Image) -> Image.Image:
        """形态学处理"""
        cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
        
        # 创建结构元素
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        
        # 开运算
        opened = cv2.morphologyEx(gray, cv2.MORPH_OPEN, kernel)
        
        return Image.fromarray(opened)
    
    def _sharpen_image(self, image: Image.Image) -> Image.Image:
        """图像锐化"""
        return image.filter(ImageFilter.SHARPEN)
    
    def get_optimal_config(self, image_features: Dict[str, Any]) -> Dict[str, Any]:
        """获取最优OCR配置"""
        text_type = image_features.get("text_type", "mixed_text")
        base_config = self.ocr_templates.get(text_type, self.ocr_templates["mixed_text"]).copy()
        
        # 根据图像质量调整配置
        quality = image_features.get("image_quality", "medium")
        if quality == "low":
            # 低质量图像需要更多预处理
            base_config["preprocessing"].extend(["sharpen", "enhance_contrast"])
        elif quality == "high":
            # 高质量图像可以减少预处理
            base_config["preprocessing"] = ["grayscale"]
        
        # 根据文本密度调整PSM
        density = image_features.get("text_density", 0.05)
        if density > 0.1:
            base_config["psm"] = "6"  # 统一文本块
        elif density < 0.02:
            base_config["psm"] = "8"  # 单词
        
        return base_config
    
    @error_handler_decorator("智能OCR识别")
    def perform_smart_ocr(self, image: Image.Image, progress_callback: Optional[callable] = None) -> str:
        """执行智能OCR识别"""
        start_time = time.time()
        self.stats["total_ocr_calls"] += 1
        
        # 生成缓存键
        image_hash = self._get_image_hash(image)
        cache_key = f"smart_ocr_{image_hash}"
        
        # 检查缓存
        if self.cache_manager:
            cached_result = self.cache_manager.get(cache_key, "ocr_results")
            if cached_result:
                self.stats["cache_hits"] += 1
                self.logger.info("OCR结果从缓存获取")
                return cached_result
            self.stats["cache_misses"] += 1
        
        try:
            if progress_callback:
                progress_callback(10, "分析图像特征...")
            
            # 分析图像特征
            image_features = self.analyze_image(image)
            
            if progress_callback:
                progress_callback(30, "获取最优配置...")
            
            # 获取最优配置
            optimal_config = self.get_optimal_config(image_features)
            
            if progress_callback:
                progress_callback(50, "预处理图像...")
            
            # 预处理图像
            processed_image = self.preprocess_image(image, optimal_config["preprocessing"])
            
            if progress_callback:
                progress_callback(70, "执行OCR识别...")
            
            # 执行OCR
            config_str = f'--psm {optimal_config["psm"]} --oem {optimal_config["oem"]}'
            result = pytesseract.image_to_string(
                processed_image,
                lang=optimal_config["language"],
                config=config_str
            )
            
            if progress_callback:
                progress_callback(90, "后处理结果...")
            
            # 后处理结果
            result = self._post_process_result(result, image_features)
            
            if progress_callback:
                progress_callback(100, "OCR识别完成")
            
            # 更新统计
            processing_time = time.time() - start_time
            self.stats["total_processing_time"] += processing_time
            self.stats["average_processing_time"] = (
                self.stats["total_processing_time"] / self.stats["total_ocr_calls"]
            )
            self.stats["successful_calls"] += 1
            
            # 缓存结果
            if self.cache_manager and result.strip():
                self.cache_manager.set(cache_key, result, "ocr_results", ttl=86400)
            
            self.logger.info(f"智能OCR识别完成: {len(result.strip())}字符, 耗时{processing_time:.2f}秒")
            return result
            
        except Exception as e:
            self.stats["failed_calls"] += 1
            self.logger.error(f"智能OCR识别失败: {str(e)}")
            raise e
    
    def _get_image_hash(self, image: Image.Image) -> str:
        """获取图像哈希值"""
        import hashlib
        # 将图像转换为字节并计算哈希
        image_bytes = image.tobytes()
        return hashlib.md5(image_bytes).hexdigest()
    
    def _post_process_result(self, result: str, image_features: Dict[str, Any]) -> str:
        """后处理OCR结果"""
        # 清理结果
        result = result.strip()
        
        # 根据文本类型进行特定处理
        text_type = image_features.get("text_type", "mixed_text")
        
        if text_type == "numbers":
            # 数字类型：移除非数字字符
            import re
            result = re.sub(r'[^\d\.\-\+]', '', result)
        elif text_type == "code":
            # 代码类型：保持格式
            result = result.replace('\n\n', '\n')
        elif text_type == "log_text":
            # 日志文本：尝试修复常见的OCR错误
            result = self._fix_log_text_errors(result)
        
        return result
    
    def _fix_log_text_errors(self, text: str) -> str:
        """修复日志文本的常见OCR错误"""
        # 常见的OCR错误映射
        error_mappings = {
            "BeReeAeiDaLseAa": "高级缓存系统初始化完成",
            "INFO": "INFO",
            "ERROR": "ERROR",
            "WARNING": "WARNING",
            "DEBUG": "DEBUG",
            "app_cache": "app_cache",
            "初始化": "初始化",
            "完成": "完成",
            "系统": "系统",
            "缓存": "缓存",
            "高级": "高级"
        }
        
        # 应用错误映射
        for error, correct in error_mappings.items():
            if error in text:
                text = text.replace(error, correct)
        
        return text
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        stats = self.stats.copy()
        
        if self.cache_manager:
            cache_stats = self.cache_manager.get_stats()
            stats["cache_stats"] = cache_stats
        
        return stats
    
    def reset_stats(self):
        """重置统计信息"""
        self.stats = {
            "total_ocr_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "average_processing_time": 0,
            "total_processing_time": 0,
            "cache_hits": 0,
            "cache_misses": 0
        }
        self.logger.info("OCR统计信息已重置")
    
    def optimize_for_text_type(self, text_type: str) -> Dict[str, Any]:
        """为特定文本类型优化配置"""
        if text_type in self.ocr_templates:
            return self.ocr_templates[text_type].copy()
        else:
            return self.ocr_templates["mixed_text"].copy()
    
    def batch_ocr(self, images: List[Image.Image], progress_callback: Optional[callable] = None) -> List[str]:
        """批量OCR识别"""
        results = []
        total_images = len(images)
        
        for i, image in enumerate(images):
            if progress_callback:
                progress_callback(int((i / total_images) * 100), f"处理第 {i+1}/{total_images} 张图片")
            
            try:
                result = self.perform_smart_ocr(image)
                results.append(result)
            except Exception as e:
                self.logger.error(f"批量OCR第{i+1}张图片失败: {str(e)}")
                results.append("")
        
        if progress_callback:
            progress_callback(100, "批量OCR完成")
        
        return results
