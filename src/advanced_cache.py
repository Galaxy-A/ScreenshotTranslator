# advanced_cache.py - 高级缓存系统
import os
import json
import pickle
import hashlib
import logging
import time
from typing import Any, Dict, Optional, Union, List
from pathlib import Path
import threading

class AdvancedCache:
    """高级缓存系统 - 支持多种缓存策略和智能管理"""
    
    def __init__(self, cache_dir: str = "cache", max_size_mb: int = 200):
        self.logger = logging.getLogger("AdvancedCache")
        self.cache_dir = Path(cache_dir)
        self.max_size_mb = max_size_mb
        self.cache_index = {}
        self.access_times = {}
        self.cache_stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "total_requests": 0
        }
        self.lock = threading.RLock()
        
        # 创建缓存目录
        self.cache_dir.mkdir(exist_ok=True)
        
        # 加载缓存索引
        self._load_cache_index()
        
        # 启动清理线程
        self._start_cleanup_thread()
        
        self.logger.info(f"高级缓存系统初始化完成: {self.cache_dir}")
    
    def _load_cache_index(self):
        """加载缓存索引"""
        index_file = self.cache_dir / "index.json"
        if index_file.exists():
            try:
                with open(index_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.cache_index = data.get('index', {})
                    self.cache_stats = data.get('stats', self.cache_stats)
                self.logger.info(f"加载缓存索引: {len(self.cache_index)} 项")
            except Exception as e:
                self.logger.error(f"加载缓存索引失败: {str(e)}")
                self.cache_index = {}
    
    def _save_cache_index(self):
        """保存缓存索引"""
        index_file = self.cache_dir / "index.json"
        try:
            with self.lock:
                data = {
                    'index': self.cache_index,
                    'stats': self.cache_stats,
                    'timestamp': time.time()
                }
                with open(index_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"保存缓存索引失败: {str(e)}")
    
    def _get_cache_key(self, key: str, category: str = "default") -> str:
        """生成缓存键"""
        return f"{category}_{hashlib.md5(key.encode()).hexdigest()}"
    
    def _get_cache_path(self, cache_key: str) -> Path:
        """获取缓存文件路径"""
        return self.cache_dir / f"{cache_key}.cache"
    
    def set(self, key: str, value: Any, category: str = "default", 
            ttl: int = 3600, priority: int = 0, compress: bool = False):
        """设置缓存"""
        with self.lock:
            cache_key = self._get_cache_key(key, category)
            cache_path = self._get_cache_path(cache_key)
            
            try:
                # 序列化数据
                data = {
                    'value': value,
                    'metadata': {
                        'created': time.time(),
                        'ttl': ttl,
                        'priority': priority,
                        'compress': compress,
                        'category': category,
                        'key': key
                    }
                }
                
                with open(cache_path, 'wb') as f:
                    pickle.dump(data, f)
                
                # 更新索引
                self.cache_index[cache_key] = {
                    'key': key,
                    'category': category,
                    'size': cache_path.stat().st_size,
                    'created': time.time(),
                    'ttl': ttl,
                    'priority': priority,
                    'access_count': 0,
                    'last_access': time.time()
                }
                
                # 更新访问时间
                self.access_times[cache_key] = time.time()
                
                # 保存索引
                self._save_cache_index()
                
                self.logger.debug(f"缓存已设置: {key} ({category})")
                
                # 检查缓存大小
                self._check_cache_size()
                
            except Exception as e:
                self.logger.error(f"设置缓存失败: {key}, {str(e)}")
    
    def get(self, key: str, category: str = "default", default: Any = None) -> Any:
        """获取缓存"""
        with self.lock:
            cache_key = self._get_cache_key(key, category)
            cache_path = self._get_cache_path(cache_key)
            
            self.cache_stats["total_requests"] += 1
            
            if cache_key not in self.cache_index:
                self.cache_stats["misses"] += 1
                return default
            
            try:
                # 检查TTL
                cache_info = self.cache_index[cache_key]
                if time.time() - cache_info['created'] > cache_info['ttl']:
                    self.delete(key, category)
                    self.cache_stats["misses"] += 1
                    return default
                
                # 检查文件是否存在
                if not cache_path.exists():
                    del self.cache_index[cache_key]
                    self.cache_stats["misses"] += 1
                    return default
                
                # 读取缓存
                with open(cache_path, 'rb') as f:
                    data = pickle.load(f)
                
                # 更新访问信息
                current_time = time.time()
                self.access_times[cache_key] = current_time
                self.cache_index[cache_key]['access_count'] += 1
                self.cache_index[cache_key]['last_access'] = current_time
                
                self.cache_stats["hits"] += 1
                self.logger.debug(f"缓存命中: {key} ({category})")
                return data['value']
                
            except Exception as e:
                self.logger.error(f"获取缓存失败: {key}, {str(e)}")
                self.cache_stats["misses"] += 1
                return default
    
    def delete(self, key: str, category: str = "default") -> bool:
        """删除缓存"""
        with self.lock:
            cache_key = self._get_cache_key(key, category)
            cache_path = self._get_cache_path(cache_key)
            
            try:
                # 删除文件
                if cache_path.exists():
                    cache_path.unlink()
                
                # 删除索引
                if cache_key in self.cache_index:
                    del self.cache_index[cache_key]
                
                if cache_key in self.access_times:
                    del self.access_times[cache_key]
                
                # 保存索引
                self._save_cache_index()
                
                self.logger.debug(f"缓存已删除: {key} ({category})")
                return True
                
            except Exception as e:
                self.logger.error(f"删除缓存失败: {key}, {str(e)}")
                return False
    
    def clear(self, category: Optional[str] = None):
        """清空缓存"""
        with self.lock:
            try:
                if category:
                    # 清空指定分类
                    keys_to_delete = [
                        key for key, info in self.cache_index.items()
                        if info['category'] == category
                    ]
                else:
                    # 清空所有缓存
                    keys_to_delete = list(self.cache_index.keys())
                
                for cache_key in keys_to_delete:
                    cache_path = self._get_cache_path(cache_key)
                    if cache_path.exists():
                        cache_path.unlink()
                
                # 清空索引
                if category:
                    self.cache_index = {
                        key: info for key, info in self.cache_index.items()
                        if info['category'] != category
                    }
                else:
                    self.cache_index = {}
                
                self.access_times = {}
                
                # 保存索引
                self._save_cache_index()
                
                self.logger.info(f"缓存已清空: {category or '全部'}")
                
            except Exception as e:
                self.logger.error(f"清空缓存失败: {str(e)}")
    
    def _check_cache_size(self):
        """检查缓存大小"""
        total_size = sum(info['size'] for info in self.cache_index.values())
        total_size_mb = total_size / (1024 * 1024)
        
        if total_size_mb > self.max_size_mb:
            self.logger.info(f"缓存大小超限: {total_size_mb:.2f}MB > {self.max_size_mb}MB")
            self._evict_cache()
    
    def _evict_cache(self):
        """缓存淘汰策略 - LRU + 优先级"""
        # 按优先级和访问时间排序
        sorted_items = sorted(
            self.cache_index.items(),
            key=lambda x: (x[1]['priority'], x[1]['last_access'])
        )
        
        # 删除最旧的缓存直到大小合适
        for cache_key, cache_info in sorted_items:
            self.delete(cache_info['key'], cache_info['category'])
            self.cache_stats["evictions"] += 1
            
            # 重新计算大小
            total_size = sum(info['size'] for info in self.cache_index.values())
            total_size_mb = total_size / (1024 * 1024)
            
            if total_size_mb <= self.max_size_mb * 0.8:  # 留20%余量
                break
    
    def _start_cleanup_thread(self):
        """启动清理线程"""
        def cleanup_worker():
            while True:
                try:
                    time.sleep(300)  # 每5分钟清理一次
                    self._cleanup_expired()
                except Exception as e:
                    self.logger.error(f"清理线程错误: {str(e)}")
        
        cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        cleanup_thread.start()
        self.logger.info("缓存清理线程已启动")
    
    def _cleanup_expired(self):
        """清理过期缓存"""
        with self.lock:
            current_time = time.time()
            expired_keys = []
            
            for cache_key, info in self.cache_index.items():
                if current_time - info['created'] > info['ttl']:
                    expired_keys.append(cache_key)
            
            for cache_key in expired_keys:
                cache_info = self.cache_index[cache_key]
                self.delete(cache_info['key'], cache_info['category'])
            
            if expired_keys:
                self.logger.info(f"清理了 {len(expired_keys)} 个过期缓存")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        with self.lock:
            total_size = sum(info['size'] for info in self.cache_index.values())
            total_size_mb = total_size / (1024 * 1024)
            
            hit_rate = 0
            if self.cache_stats["total_requests"] > 0:
                hit_rate = self.cache_stats["hits"] / self.cache_stats["total_requests"] * 100
            
            categories = {}
            for info in self.cache_index.values():
                category = info['category']
                if category not in categories:
                    categories[category] = {'count': 0, 'size': 0}
                categories[category]['count'] += 1
                categories[category]['size'] += info['size']
            
            return {
                'total_items': len(self.cache_index),
                'total_size_mb': total_size_mb,
                'max_size_mb': self.max_size_mb,
                'hit_rate': hit_rate,
                'categories': categories,
                'cache_dir': str(self.cache_dir),
                'stats': self.cache_stats.copy()
            }
    
    def optimize(self):
        """优化缓存"""
        with self.lock:
            # 重新计算文件大小
            for cache_key, info in self.cache_index.items():
                cache_path = self._get_cache_path(cache_key)
                if cache_path.exists():
                    info['size'] = cache_path.stat().st_size
                else:
                    # 文件不存在，删除索引
                    del self.cache_index[cache_key]
            
            # 保存索引
            self._save_cache_index()
            
            # 清理过期缓存
            self._cleanup_expired()
            
            self.logger.info("缓存优化完成")
    
    def export_cache(self, export_path: str, category: Optional[str] = None):
        """导出缓存"""
        try:
            export_data = {}
            
            for cache_key, info in self.cache_index.items():
                if category and info['category'] != category:
                    continue
                
                cache_path = self._get_cache_path(cache_key)
                if cache_path.exists():
                    with open(cache_path, 'rb') as f:
                        data = pickle.load(f)
                    export_data[cache_key] = {
                        'data': data,
                        'info': info
                    }
            
            with open(export_path, 'wb') as f:
                pickle.dump(export_data, f)
            
            self.logger.info(f"缓存已导出到: {export_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"导出缓存失败: {str(e)}")
            return False
    
    def cleanup(self):
        """清理缓存管理器"""
        self.logger.info("正在清理缓存管理器...")
        
        # 清理过期缓存
        current_time = time.time()
        expired_keys = []
        
        for cache_key, info in self.cache_index.items():
            if current_time - info['created'] > info['ttl']:
                expired_keys.append(cache_key)
        
        for cache_key in expired_keys:
            cache_info = self.cache_index[cache_key]
            self.delete(cache_info['key'], cache_info['category'])
        
        # 保存索引
        self._save_cache_index()
        
        self.logger.info("缓存管理器清理完成")
