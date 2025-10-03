import time
import requests
from .base import BaseProbe


class HttpProbe(BaseProbe):
    """
    HTTP探活实现
    """
    def check(self, node):
        try:
            start_time = time.time()
            
            # 构建URL
            protocol = self.params.get('protocol', 'http')
            path = self.params.get('path', '/')
            port = node.port or self.params.get('port', 80 if protocol == 'http' else 443)
            
            if node.ip_address:
                url = f"{protocol}://{node.ip_address}:{port}{path}"
            elif node.host:
                url = f"{protocol}://{node.host}:{port}{path}"
            else:
                return {
                    'is_healthy': False,
                    'response_time': 0,
                    'error_message': 'No IP address or host specified'
                }
            
            # 准备请求参数
            timeout = self.params.get('timeout', 5)
            method = self.params.get('method', 'GET').upper()
            
            req_kwargs = {
                'timeout': timeout,
                'verify': self.params.get('verify_ssl', True),
            }
            
            if self.params.get('headers'):
                req_kwargs['headers'] = self.params['headers']
            
            if self.params.get('auth'):
                req_kwargs['auth'] = tuple(self.params['auth'])
            
            # 发送请求
            response = requests.request(method, url, **req_kwargs)
            response_time = (time.time() - start_time) * 1000  # 转换为毫秒
            
            # 检查状态码
            expected_codes = self.params.get('expected_codes', [200])
            is_healthy = response.status_code in expected_codes
            
            # 检查响应内容
            if is_healthy and 'expected_content' in self.params:
                expected = self.params['expected_content']
                if expected not in response.text:
                    is_healthy = False
                    response_time = (time.time() - start_time) * 1000
            
            error_message = None if is_healthy else f"HTTP {response.status_code}"
            
            return {
                'is_healthy': is_healthy,
                'response_time': response_time,
                'error_message': error_message,
                'details': {
                    'status_code': response.status_code,
                    'headers': dict(response.headers),
                    'content_length': len(response.text)
                }
            }
            
        except requests.exceptions.Timeout:
            return {
                'is_healthy': False,
                'response_time': (time.time() - start_time) * 1000,
                'error_message': 'HTTP request timeout',
                'details': {}
            }
        except requests.exceptions.RequestException as e:
            return {
                'is_healthy': False,
                'response_time': (time.time() - start_time) * 1000,
                'error_message': str(e),
                'details': {}
            }
        except Exception as e:
            return {
                'is_healthy': False,
                'response_time': 0,
                'error_message': str(e),
                'details': {}
            }