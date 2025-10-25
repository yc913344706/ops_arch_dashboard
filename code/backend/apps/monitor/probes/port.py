import time
import socket
from .base import BaseProbe


class PortProbe(BaseProbe):
    """
    端口探活实现
    """
    def check(self, node):
        # 为了向前兼容，我们仍然保留访问 basic_info_list 的方式
        # 但在新架构中，我们会优先使用 BaseInfo 模型
        from apps.monitor.models import BaseInfo
        
        # 首先尝试使用新架构的 BaseInfo
        base_info_items = BaseInfo.objects.filter(node=node)
        if base_info_items.exists():
            for base_info in base_info_items:
                if base_info.port:  # 只有当端口存在时才进行端口检测
                    return self.check_with_host_port(node, base_info.host, base_info.port)
        
        # 如果BaseInfo不存在，则尝试使用旧的字段
        port = getattr(node, 'port', None)
        if port:
            host = getattr(node, 'host', None) or getattr(node, 'ip_address', None)
            if host:
                return self.check_with_host_port(node, host, port)
        
        # 如果以上都不行，则尝试使用旧的basic_info_list
        if hasattr(node, 'basic_info_list') and node.basic_info_list:
            for info in node.basic_info_list:
                host = info.get('host')
                port = info.get('port')
                if host and port:
                    return self.check_with_host_port(node, host, port)
        
        return {
            'is_healthy': False,
            'response_time': 0,
            'error_message': 'No host:port specified',
            'details': {}
        }
    
    def check_with_host_port(self, node, host, port):
        """
        通过指定主机和端口执行端口检测
        """
        try:
            start_time = time.time()
            
            timeout = self.params.get('timeout', 3)
            
            # 确保端口是整数类型
            try:
                port = int(port)
            except ValueError:
                return {
                    'is_healthy': False,
                    'response_time': 0,
                    'error_message': f'Invalid port value: {port}',
                    'details': {}
                }
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            
            result = sock.connect_ex((host, port))
            response_time = (time.time() - start_time) * 1000  # 转换为毫秒
            
            sock.close()
            
            if result == 0:
                return {
                    'is_healthy': True,
                    'response_time': response_time,
                    'error_message': None,
                    'details': {}
                }
            else:
                return {
                    'is_healthy': False,
                    'response_time': response_time,
                    'error_message': f'Port {port} is closed or filtered',
                    'details': {}
                }
                
        except socket.gaierror as e:
            return {
                'is_healthy': False,
                'response_time': (time.time() - start_time) * 1000,
                'error_message': f'Hostname resolution failed: {str(e)}',
                'details': {}
            }
        except Exception as e:
            return {
                'is_healthy': False,
                'response_time': (time.time() - start_time) * 1000,
                'error_message': str(e),
                'details': {}
            }