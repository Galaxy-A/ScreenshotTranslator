# config.py - 增强配置管理模块
import json
import os
import logging
import shutil
from typing import Dict, Any, Optional
from datetime import datetime

class Config:
    """增强的配置管理类"""
    
    # 默认配置
    DEFAULT_SETTINGS = {
        "ocr_config": {
            "language": "chi_sim+eng",
            "psm": "3",
            "oem": "3"
        },
        "offset": {
            "horizontal": 0,
            "vertical": 0
        },
        "tesseract_path": r'C:\Program Files\Tesseract-OCR\tesseract.exe',
        "tessdata_path": r'C:\Program Files\Tesseract-OCR\tessdata',
        "api_provider": "openai",  # "openai" 或 "deepseek"
        "api_key": "",
        "api_model": "gpt-3.5-turbo",
        "preprocessing": {
            "grayscale": True,
            "invert": False,
            "threshold": 0
        },
        "hide_window_on_capture": False,
        "hotkey": "ctrl+alt+s"
    }
    
    def __init__(self, config_file: str = "settings.json"):
        self.logger = logging.getLogger("Config")
        self.config_file = config_file
        self._settings = self._load_settings()
    
    def _load_settings(self) -> Dict[str, Any]:
        """加载配置文件"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                # 合并默认设置，确保所有键都存在
                merged_settings = self.DEFAULT_SETTINGS.copy()
                merged_settings.update(settings)
                self.logger.info("配置文件已加载")
                return merged_settings
            except Exception as e:
                self.logger.error(f"加载配置文件失败: {str(e)}, 使用默认设置")
                return self.DEFAULT_SETTINGS.copy()
        
        self.logger.info("未找到配置文件，使用默认设置")
        return self.DEFAULT_SETTINGS.copy()
    
    def save_settings(self) -> bool:
        """保存配置到文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self._settings, f, indent=2, ensure_ascii=False)
            self.logger.info("配置已保存")
            return True
        except Exception as e:
            self.logger.error(f"保存配置失败: {str(e)}")
            return False
    
    def get(self, key: str, default=None):
        """获取配置值"""
        keys = key.split('.')
        value = self._settings
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value: Any):
        """设置配置值"""
        keys = key.split('.')
        settings = self._settings
        for k in keys[:-1]:
            if k not in settings:
                settings[k] = {}
            settings = settings[k]
        settings[keys[-1]] = value
        self.logger.debug(f"配置已更新: {key} = {value}")
    
    def get_all(self) -> Dict[str, Any]:
        """获取所有配置"""
        return self._settings.copy()
    
    def update(self, new_settings: Dict[str, Any]):
        """批量更新配置"""
        self._settings.update(new_settings)
        self.logger.info("配置已批量更新")
    
    def backup_config(self, backup_dir: str = "backups") -> bool:
        """备份配置文件"""
        try:
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = os.path.join(backup_dir, f"settings_backup_{timestamp}.json")
            
            if os.path.exists(self.config_file):
                shutil.copy2(self.config_file, backup_file)
                self.logger.info(f"配置已备份到: {backup_file}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"备份配置失败: {str(e)}")
            return False
    
    def restore_config(self, backup_file: str) -> bool:
        """从备份恢复配置"""
        try:
            if not os.path.exists(backup_file):
                self.logger.error(f"备份文件不存在: {backup_file}")
                return False
            
            shutil.copy2(backup_file, self.config_file)
            self._settings = self._load_settings()
            self.logger.info(f"配置已从备份恢复: {backup_file}")
            return True
        except Exception as e:
            self.logger.error(f"恢复配置失败: {str(e)}")
            return False
    
    def validate_config(self) -> Dict[str, Any]:
        """验证配置有效性"""
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        # 检查Tesseract路径
        tesseract_path = self.get("tesseract_path")
        if not tesseract_path or not os.path.exists(tesseract_path):
            validation_result["errors"].append(f"Tesseract路径无效: {tesseract_path}")
            validation_result["valid"] = False
        
        # 检查语言包路径
        tessdata_path = self.get("tessdata_path")
        if not tessdata_path or not os.path.exists(tessdata_path):
            validation_result["warnings"].append(f"语言包路径无效: {tessdata_path}")
        
        # 检查API密钥
        api_key = self.get("api_key")
        provider = self.get("api_provider", "openai")
        provider_name = "DeepSeek" if provider == "deepseek" else "OpenAI"
        if not api_key or api_key.strip() == "":
            validation_result["warnings"].append(f"{provider_name} API密钥未设置")
        
        # 检查快捷键格式
        hotkey = self.get("hotkey")
        if not hotkey or not isinstance(hotkey, str):
            validation_result["errors"].append("快捷键格式无效")
            validation_result["valid"] = False
        
        return validation_result
    
    def get_config_info(self) -> Dict[str, Any]:
        """获取配置信息摘要"""
        return {
            "config_file": self.config_file,
            "last_modified": datetime.fromtimestamp(os.path.getmtime(self.config_file)).isoformat() if os.path.exists(self.config_file) else None,
            "total_keys": len(self._settings),
            "validation": self.validate_config()
        }
    
    def export_config(self, export_path: str) -> bool:
        """导出配置到文件"""
        try:
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(self._settings, f, indent=2, ensure_ascii=False)
            self.logger.info(f"配置已导出到: {export_path}")
            return True
        except Exception as e:
            self.logger.error(f"导出配置失败: {str(e)}")
            return False
    
    def import_config(self, import_path: str) -> bool:
        """从文件导入配置"""
        try:
            with open(import_path, 'r', encoding='utf-8') as f:
                imported_settings = json.load(f)
            
            # 合并配置
            merged_settings = self.DEFAULT_SETTINGS.copy()
            merged_settings.update(imported_settings)
            
            self._settings = merged_settings
            self.save_settings()
            self.logger.info(f"配置已从文件导入: {import_path}")
            return True
        except Exception as e:
            self.logger.error(f"导入配置失败: {str(e)}")
            return False
    
    def reset_to_defaults(self) -> bool:
        """重置为默认配置"""
        try:
            self._settings = self.DEFAULT_SETTINGS.copy()
            self.save_settings()
            self.logger.info("配置已重置为默认值")
            return True
        except Exception as e:
            self.logger.error(f"重置配置失败: {str(e)}")
            return False
    
    def get_config_diff(self, other_config: Dict[str, Any]) -> Dict[str, Any]:
        """比较配置差异"""
        diff = {
            "added": {},
            "modified": {},
            "removed": {}
        }
        
        # 检查新增和修改的配置
        for key, value in other_config.items():
            if key not in self._settings:
                diff["added"][key] = value
            elif self._settings[key] != value:
                diff["modified"][key] = {
                    "old": self._settings[key],
                    "new": value
                }
        
        # 检查删除的配置
        for key in self._settings:
            if key not in other_config:
                diff["removed"][key] = self._settings[key]
        
        return diff
