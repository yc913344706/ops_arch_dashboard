import time
import subprocess
from .base import BaseProbe


class PingProbe(BaseProbe):
    """
    Ping探活实现
    """
    def check(self, node):
        # 使用 BaseInfo 模型
        from apps.monitor.models import BaseInfo
        
        # 尝试使用 BaseInfo
        base_info_items = BaseInfo.objects.filter(node=node)
        if base_info_items.exists():
            for base_info in base_info_items:
                # 检查是否禁ping
                if base_info.is_ping_disabled:
                    # 如果禁ping，则跳过ping检测
                    continue
                return self.check_with_host(node, base_info.host)
        
        # 如果没有BaseInfo记录，返回错误
        return {
            'is_healthy': False,
            'response_time': 0,
            'error_message': 'No host specified in BaseInfo',
            'details': {}
        }
    
    def check_with_host(self, node, host):
        """
        通过指定主机执行Ping检测
        """
        try:
            start_time = time.time()
            
            # 使用系统ping命令
            timeout = self.params.get('timeout', 3)
            cmd = ['ping', '-c', '1', '-W', str(timeout), host]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout+1)
            
            response_time = (time.time() - start_time) * 1000  # 转换为毫秒
            
            if result.returncode == 0:
                return {
                    'is_healthy': True,
                    'response_time': response_time,
                    'error_message': None,
                    'details': {'output': result.stdout}
                }
            else:
                return {
                    'is_healthy': False,
                    'response_time': response_time,
                    'error_message': f'Ping failed: {result.stderr}',
                    'details': {'output': result.stderr}
                }
                
        except subprocess.TimeoutExpired:
            return {
                'is_healthy': False,
                'response_time': (time.time() - start_time) * 1000,
                'error_message': 'Ping timeout',
                'details': {}
            }
        except Exception as e:
            return {
                'is_healthy': False,
                'response_time': 0,
                'error_message': str(e),
                'details': {}
            }