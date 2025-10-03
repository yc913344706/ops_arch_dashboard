from .models import AppSetting


class ProbeConfig:
    """
    探活配置管理
    """
    @staticmethod
    def get_config(key, default=None):
        """
        获取探活配置
        """
        try:
            setting = AppSetting.objects.get(key=key)
            return setting.value
        except AppSetting.DoesNotExist:
            return default
    
    @staticmethod
    def set_config(key, value, description=""):
        """
        设置探活配置
        """
        AppSetting.objects.update_or_create(
            key=key,
            defaults={
                'value': value,
                'description': description
            }
        )
    
    @staticmethod
    def get_default_configs():
        """
        获取默认探活配置
        """
        return {
            'ping_timeout': 3,           # Ping超时时间（秒）
            'http_timeout': 5,           # HTTP请求超时时间（秒）
            'port_timeout': 3,           # 端口连接超时时间（秒）
            'probe_interval': 60,        # 探活间隔（秒）
            'max_concurrent_probes': 10, # 最大并发探活数
            'retry_count': 2,            # 重试次数
            'retry_delay': 1,            # 重试间隔（秒）
        }