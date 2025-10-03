import time
import subprocess
from .base import BaseProbe


class PingProbe(BaseProbe):
    """
    Ping探活实现
    """
    def check(self, node):
        # 为了向前兼容，我们仍然保留这个方法
        # 在新架构中，我们会调用 check_with_host
        if hasattr(node, 'basic_info_list') and node.basic_info_list:
            # 如果节点有basic_info_list，则对第一个host进行ping
            for info in node.basic_info_list:
                host = info.get('host')
                if host:
                    return self.check_with_host(node, host)
        
        # 否则尝试使用旧的字段
        host = getattr(node, 'host', None) or getattr(node, 'ip_address', None)
        if host:
            return self.check_with_host(node, host)
        
        return {
            'is_healthy': False,
            'response_time': 0,
            'error_message': 'No host specified',
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