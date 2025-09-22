# performance.py - 简单性能监控模块
import time
import logging
from typing import Dict, Any

class PerformanceMonitor:
    """简单的性能监控器"""
    
    def __init__(self):
        self.logger = logging.getLogger("PerformanceMonitor")
        self.operation_times = {}
        self.start_time = time.time()
        self.operation_history = []
    
    def start_timer(self, operation: str):
        """开始计时"""
        self.operation_times[operation] = time.time()
        # 开始计时
    
    def end_timer(self, operation: str) -> float:
        """结束计时并返回耗时"""
        if operation not in self.operation_times:
            self.logger.warning(f"未找到开始时间: {operation}")
            return 0.0
        
        elapsed = time.time() - self.operation_times[operation]
        del self.operation_times[operation]
        
        # 记录操作历史
        self.operation_history.append({
            "operation": operation,
            "duration": elapsed,
            "timestamp": time.time()
        })
        
        # 操作完成
        return elapsed
    
    def get_operation_stats(self) -> Dict[str, Any]:
        """获取操作统计信息"""
        return {
            "monitored_operations": list(self.operation_times.keys()),
            "active_operations": len(self.operation_times)
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """获取性能统计信息"""
        current_time = time.time()
        total_runtime = current_time - self.start_time
        
        # 计算操作统计
        total_operations = len(self.operation_history)
        if total_operations > 0:
            total_duration = sum(op["duration"] for op in self.operation_history)
            avg_duration = total_duration / total_operations
        else:
            total_duration = 0.0
            avg_duration = 0.0
        
        # 按操作类型分组统计
        operation_counts = {}
        operation_times = {}
        for op in self.operation_history:
            op_name = op["operation"]
            operation_counts[op_name] = operation_counts.get(op_name, 0) + 1
            operation_times[op_name] = operation_times.get(op_name, 0.0) + op["duration"]
        
        return {
            "total_runtime": total_runtime,
            "total_operations": total_operations,
            "total_duration": total_duration,
            "average_duration": avg_duration,
            "active_operations": len(self.operation_times),
            "operation_counts": operation_counts,
            "operation_times": operation_times,
            "start_time": self.start_time,
            "current_time": current_time
        }

def time_operation(operation_name: str):
    """性能监控装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            monitor = PerformanceMonitor()
            monitor.start_timer(operation_name)
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                monitor.end_timer(operation_name)
        return wrapper
    return decorator
