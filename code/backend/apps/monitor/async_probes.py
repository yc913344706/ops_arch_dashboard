import asyncio
import subprocess
from typing import List, Dict, Any
from lib.log import color_logger


class AsyncProbeManager:
    """
    异步探针管理器，支持并发执行ping和端口检测
    """
    
    def __init__(self, timeout: int = 3):
        self.timeout = timeout
    
    async def ping_async(self, host: str) -> Dict[str, Any]:
        """
        异步ping检测

        Return: 
        - {
            'host': 主机地址,
            'is_healthy': 是否健康,
            'response_time': 响应时间(毫秒),
            'error_message': 错误信息
        }
        """
        try:
            # 使用系统ping命令，更可靠
            process = await asyncio.create_subprocess_exec(
                'ping', '-c', '1', '-W', str(self.timeout), host,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=self.timeout + 1)
            
            is_healthy = process.returncode == 0
            response_time = None
            
            # 从ping输出中提取响应时间
            if is_healthy and stdout:
                output = stdout.decode()
                import re
                match = re.search(r'time=(\d+\.?\d*)', output)
                if match:
                    response_time = float(match.group(1))
            
            return {
                'host': host,
                'is_healthy': is_healthy,
                'response_time': response_time,
                'error_message': stderr.decode() if not is_healthy else None
            }
        except asyncio.TimeoutError:
            return {
                'host': host,
                'is_healthy': False,
                'response_time': None,
                'error_message': f'Ping timeout after {self.timeout}s'
            }
        except Exception as e:
            return {
                'host': host,
                'is_healthy': False,
                'response_time': None,
                'error_message': str(e)
            }

    async def port_check_async(self, host: str, port: int) -> Dict[str, Any]:
        """
        异步端口检测

        Return: 
        - {
            'host': 主机地址,
            'port': 端口号,
            'is_healthy': 是否健康,
            'response_time': 响应时间(毫秒),
            'error_message': 错误信息
        }
        """
        try:
            start_time = asyncio.get_event_loop().time()
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=self.timeout
            )
            end_time = asyncio.get_event_loop().time()
            
            writer.close()
            await writer.wait_closed()
            
            response_time = (end_time - start_time) * 1000  # 转换为毫秒
            
            return {
                'host': host,
                'port': port,
                'is_healthy': True,
                'response_time': response_time,
                'error_message': None
            }
        except asyncio.TimeoutError:
            return {
                'host': host,
                'port': port,
                'is_healthy': False,
                'response_time': None,
                'error_message': f'Port {port} timeout after {self.timeout}s'
            }
        except Exception as e:
            return {
                'host': host,
                'port': port,
                'is_healthy': False,
                'response_time': None,
                'error_message': str(e)
            }

    async def check_multiple_hosts(self, hosts: List[str]) -> List[Dict[str, Any]]:
        """
        并发执行多个主机的ping检测
        """
        tasks = [self.ping_async(host) for host in hosts]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常结果
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    'host': hosts[i],
                    'is_healthy': False,
                    'response_time': None,
                    'error_message': str(result)
                })
            else:
                processed_results.append(result)
        
        return processed_results

    async def check_multiple_ports(self, host_port_pairs: List[tuple]) -> List[Dict[str, Any]]:
        """
        并发执行多个主机+端口的检测
        """
        tasks = [self.port_check_async(host, port) for host, port in host_port_pairs]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常结果
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                host, port = host_port_pairs[i]
                processed_results.append({
                    'host': host,
                    'port': port,
                    'is_healthy': False,
                    'response_time': None,
                    'error_message': str(result)
                })
            else:
                processed_results.append(result)
        
        return processed_results