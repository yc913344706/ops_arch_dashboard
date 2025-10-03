import time
import paramiko
from .base import BaseProbe


class SshProbe(BaseProbe):
    """
    SSH探活实现
    """
    def check(self, node):
        if not node.ip_address and not node.host:
            return {
                'is_healthy': False,
                'response_time': 0,
                'error_message': 'No IP address or host specified',
                'details': {}
            }
        
        try:
            start_time = time.time()
            
            hostname = node.ip_address or node.host
            port = node.port or 22
            username = self.params.get('username', 'root')
            password = self.params.get('password')
            key_file = self.params.get('key_file')
            
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            if key_file:
                ssh.connect(
                    hostname=hostname,
                    port=port,
                    username=username,
                    key_filename=key_file,
                    timeout=self.params.get('timeout', 5)
                )
            else:
                ssh.connect(
                    hostname=hostname,
                    port=port,
                    username=username,
                    password=password,
                    timeout=self.params.get('timeout', 5)
                )
            
            response_time = (time.time() - start_time) * 1000  # 转换为毫秒
            
            ssh.close()
            
            return {
                'is_healthy': True,
                'response_time': response_time,
                'error_message': None,
                'details': {}
            }
            
        except paramiko.AuthenticationException:
            return {
                'is_healthy': False,
                'response_time': (time.time() - start_time) * 1000,
                'error_message': 'SSH authentication failed',
                'details': {}
            }
        except paramiko.SSHException as e:
            return {
                'is_healthy': False,
                'response_time': (time.time() - start_time) * 1000,
                'error_message': f'SSH connection error: {str(e)}',
                'details': {}
            }
        except Exception as e:
            return {
                'is_healthy': False,
                'response_time': (time.time() - start_time) * 1000,
                'error_message': str(e),
                'details': {}
            }