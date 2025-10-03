from django.apps import AppConfig


class MonitorConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.monitor'
    
    def ready(self):
        # 启动探活服务
        from .services import ProbeService
        ProbeService.start_scheduled_tasks()
