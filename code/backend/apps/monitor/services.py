from celery import current_app
from .tasks import check_all_nodes, cleanup_health_records


class ProbeService:
    """
    探活服务管理
    """
    @staticmethod
    def start_scheduled_tasks():
        """
        启动定时任务
        """
        # 重载任务调度配置
        current_app.conf.beat_schedule.update({
            'check-all-nodes': {
                'task': 'apps.monitor.tasks.check_all_nodes',
                'schedule': current_app.conf.get('PROBE_INTERVAL', 60),
            },
            'cleanup-health-records': {
                'task': 'apps.monitor.tasks.cleanup_health_records',
                'schedule': 3600,  # 每小时
            }
        })
        current_app.conf.timezone = 'UTC'
    
    @staticmethod
    def manual_check_node(node_uuid):
        """
        手动检查单个节点
        """
        from .tasks import check_node_health
        result = check_node_health.delay(node_uuid)
        return result
    
    @staticmethod
    def manual_check_all_nodes():
        """
        手动检查所有节点
        """
        result = check_all_nodes.delay()
        return result