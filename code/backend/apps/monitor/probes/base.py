from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseProbe(ABC):
    """
    探活基类
    """
    def __init__(self, params: Dict[str, Any]):
        self.params = params or {}
    
    @abstractmethod
    def check(self, node):
        """
        执行探活检查
        返回: {
            'is_healthy': bool,
            'response_time': float,  # 响应时间（毫秒）
            'error_message': str,    # 错误信息
            'details': dict          # 详细结果
        }
        """
        pass