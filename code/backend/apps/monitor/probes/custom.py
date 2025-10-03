import time
import subprocess
from .base import BaseProbe


class CustomProbe(BaseProbe):
    """
    自定义探活实现
    """
    def check(self, node):
        try:
            start_time = time.time()
            
            script = self.params.get('script')
            if not script:
                return {
                    'is_healthy': False,
                    'response_time': 0,
                    'error_message': 'No script specified',
                    'details': {}
                }
            
            # 替换脚本中的占位符
            script = script.replace('{host}', node.host or '')
            script = script.replace('{ip}', node.ip_address or '')
            script = script.replace('{port}', str(node.port or ''))
            
            # 执行脚本
            result = subprocess.run(
                script,
                shell=True,
                capture_output=True,
                text=True,
                timeout=self.params.get('timeout', 10)
            )
            
            response_time = (time.time() - start_time) * 1000  # 转换为毫秒
            
            # 通常认为返回码为0表示成功
            is_healthy = result.returncode == 0
            
            return {
                'is_healthy': is_healthy,
                'response_time': response_time,
                'error_message': None if is_healthy else f'Script failed with return code: {result.returncode}',
                'details': {
                    'stdout': result.stdout,
                    'stderr': result.stderr,
                    'returncode': result.returncode
                }
            }
            
        except subprocess.TimeoutExpired:
            return {
                'is_healthy': False,
                'response_time': (time.time() - start_time) * 1000,
                'error_message': 'Script execution timeout',
                'details': {}
            }
        except Exception as e:
            return {
                'is_healthy': False,
                'response_time': (time.time() - start_time) * 1000,
                'error_message': str(e),
                'details': {}
            }