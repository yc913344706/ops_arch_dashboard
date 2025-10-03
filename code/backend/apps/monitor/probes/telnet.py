import time
import telnetlib
from .base import BaseProbe


class TelnetProbe(BaseProbe):
    """
    Telnet探活实现
    """
    def check(self, node):
        if not node.ip_address and not node.host:
            return {
                'is_healthy': False,
                'response_time': 0,
                'error_message': 'No IP address or host specified',
                'details': {}
            }
        
        if not node.port:
            return {
                'is_healthy': False,
                'response_time': 0,
                'error_message': 'No port specified',
                'details': {}
            }
        
        try:
            start_time = time.time()
            
            hostname = node.ip_address or node.host
            port = node.port
            
            tn = telnetlib.Telnet(hostname, port, timeout=self.params.get('timeout', 5))
            response_time = (time.time() - start_time) * 1000  # 转换为毫秒
            
            tn.close()
            
            return {
                'is_healthy': True,
                'response_time': response_time,
                'error_message': None,
                'details': {}
            }
            
        except Exception as e:
            return {
                'is_healthy': False,
                'response_time': (time.time() - start_time) * 1000,
                'error_message': str(e),
                'details': {}
            }