from celery import current_app
from .tasks import check_all_nodes, cleanup_health_records


class ProbeService:
    """
    探活服务管理
    """
    
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