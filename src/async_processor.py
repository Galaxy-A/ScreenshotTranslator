# async_processor.py - 异步处理模块
import threading
import time
import logging
from typing import Callable, Any, Optional, Dict
from concurrent.futures import ThreadPoolExecutor, Future
import queue

class AsyncProcessor:
    """异步处理器"""
    
    def __init__(self, max_workers: int = 4):
        self.logger = logging.getLogger("AsyncProcessor")
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.running_tasks = {}
        self.task_queue = queue.Queue()
        self.callbacks = {}
        
    def submit_task(self, task_id: str, func: Callable, *args, callback: Optional[Callable] = None, **kwargs) -> str:
        """提交异步任务"""
        if task_id in self.running_tasks:
            self.logger.warning(f"任务 {task_id} 已在运行")
            return task_id
        
        future = self.executor.submit(func, *args, **kwargs)
        self.running_tasks[task_id] = future
        
        if callback:
            self.callbacks[task_id] = callback
        
        # 启动结果监听线程
        threading.Thread(
            target=self._monitor_task,
            args=(task_id, future),
            daemon=True
        ).start()
        
        self.logger.info(f"任务已提交: {task_id}")
        return task_id
    
    def _monitor_task(self, task_id: str, future: Future):
        """监控任务执行"""
        try:
            result = future.result()
            self.logger.info(f"任务完成: {task_id}")
            
            # 调用回调函数
            if task_id in self.callbacks:
                try:
                    self.callbacks[task_id](result, None)
                except Exception as e:
                    self.logger.error(f"回调函数执行失败: {str(e)}")
                finally:
                    del self.callbacks[task_id]
            
        except Exception as e:
            self.logger.error(f"任务执行失败 {task_id}: {str(e)}")
            
            # 调用错误回调
            if task_id in self.callbacks:
                try:
                    self.callbacks[task_id](None, e)
                except Exception as callback_error:
                    self.logger.error(f"错误回调执行失败: {str(callback_error)}")
                finally:
                    del self.callbacks[task_id]
        
        finally:
            # 清理任务记录
            if task_id in self.running_tasks:
                del self.running_tasks[task_id]
    
    def is_task_running(self, task_id: str) -> bool:
        """检查任务是否在运行"""
        return task_id in self.running_tasks
    
    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        if task_id in self.running_tasks:
            future = self.running_tasks[task_id]
            cancelled = future.cancel()
            if cancelled:
                del self.running_tasks[task_id]
                if task_id in self.callbacks:
                    del self.callbacks[task_id]
                self.logger.info(f"任务已取消: {task_id}")
            return cancelled
        return False
    
    def get_task_status(self) -> Dict[str, Any]:
        """获取任务状态"""
        return {
            "running_tasks": list(self.running_tasks.keys()),
            "total_running": len(self.running_tasks),
            "pending_callbacks": len(self.callbacks)
        }
    
    def shutdown(self, wait: bool = True):
        """关闭异步处理器"""
        self.logger.info("正在关闭异步处理器...")
        self.executor.shutdown(wait=wait)
        self.logger.info("异步处理器已关闭")

class ProgressTracker:
    """进度跟踪器"""
    
    def __init__(self):
        self.logger = logging.getLogger("ProgressTracker")
        self.progress_data = {}
        self.progress_callbacks = {}
    
    def start_progress(self, task_id: str, total_steps: int, description: str = ""):
        """开始进度跟踪"""
        self.progress_data[task_id] = {
            "total_steps": total_steps,
            "current_step": 0,
            "description": description,
            "start_time": time.time(),
            "status": "running"
        }
        self.logger.info(f"开始进度跟踪: {task_id} ({description})")
    
    def update_progress(self, task_id: str, step: int, description: str = ""):
        """更新进度"""
        if task_id not in self.progress_data:
            return
        
        self.progress_data[task_id]["current_step"] = step
        if description:
            self.progress_data[task_id]["description"] = description
        
        # 计算进度百分比
        total = self.progress_data[task_id]["total_steps"]
        percentage = (step / total * 100) if total > 0 else 0
        
        self.logger.debug(f"进度更新: {task_id} - {percentage:.1f}% ({description})")
        
        # 调用进度回调
        if task_id in self.progress_callbacks:
            try:
                self.progress_callbacks[task_id](percentage, description)
            except Exception as e:
                self.logger.error(f"进度回调执行失败: {str(e)}")
    
    def complete_progress(self, task_id: str, description: str = "完成"):
        """完成进度跟踪"""
        if task_id not in self.progress_data:
            return
        
        self.progress_data[task_id]["status"] = "completed"
        self.progress_data[task_id]["description"] = description
        self.progress_data[task_id]["end_time"] = time.time()
        
        elapsed_time = self.progress_data[task_id]["end_time"] - self.progress_data[task_id]["start_time"]
        self.logger.info(f"进度完成: {task_id} - 耗时 {elapsed_time:.2f}秒")
        
        # 调用完成回调
        if task_id in self.progress_callbacks:
            try:
                self.progress_callbacks[task_id](100, description)
            except Exception as e:
                self.logger.error(f"完成回调执行失败: {str(e)}")
    
    def add_progress_callback(self, task_id: str, callback: Callable):
        """添加进度回调函数"""
        self.progress_callbacks[task_id] = callback
    
    def remove_progress_callback(self, task_id: str):
        """移除进度回调函数"""
        if task_id in self.progress_callbacks:
            del self.progress_callbacks[task_id]
    
    def get_progress(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取进度信息"""
        return self.progress_data.get(task_id)
    
    def clear_progress(self, task_id: str):
        """清除进度数据"""
        if task_id in self.progress_data:
            del self.progress_data[task_id]
        if task_id in self.progress_callbacks:
            del self.progress_callbacks[task_id]
