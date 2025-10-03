from celery import shared_task
from django.utils import timezone
from .models import Node, NodeHealth
from .probes.factory import get_probe_instance
import logging

logger = logging.getLogger(__name__)

@shared_task
def check_node_health(node_uuid):
    """
    检查单个节点健康状态
    """
    try:
        node = Node.objects.get(uuid=node_uuid, is_active=True)
        
        # 遍历节点的所有基础信息，执行探活
        all_healthy = True
        total_response_time = 0
        probe_count = 0
        
        for basic_info in node.basic_info_list:
            host = basic_info.get('host')
            port = basic_info.get('port')
            
            if host:
                # 执行Ping检测
                probe = get_probe_instance('ping', {})
                result = probe.check_with_host(node, host)
                if not result['is_healthy']:
                    all_healthy = False
                if result.get('response_time'):
                    total_response_time += result['response_time']
                    probe_count += 1
                    
            if port and host:  # 如果有端口和主机，则执行端口检测
                probe = get_probe_instance('port', {'timeout': 3})
                result = probe.check_with_host_port(node, host, port)
                if not result['is_healthy']:
                    all_healthy = False
                if result.get('response_time'):
                    total_response_time += result['response_time']
                    probe_count += 1
            elif port:  # 如果只有端口，使用节点的IP地址
                probe = get_probe_instance('port', {'timeout': 3})
                result = probe.check_with_host_port(node, node.link.name, port)  # 使用节点链接名作为主机名占位符
                if not result['is_healthy']:
                    all_healthy = False
                if result.get('response_time'):
                    total_response_time += result['response_time']
                    probe_count += 1
        
        avg_response_time = total_response_time / probe_count if probe_count > 0 else None
        
        # 创建健康记录
        NodeHealth.objects.create(
            node=node,
            is_healthy=all_healthy,
            response_time=avg_response_time,
            probe_result={'details': node.basic_info_list},
            error_message=None if all_healthy else 'One or more checks failed'
        )
        
        # 更新节点最新状态
        node.is_healthy = all_healthy
        node.last_check_time = timezone.now()
        node.save(update_fields=['is_healthy', 'last_check_time'])
        
        logger.info(f"Node {node.name} health check completed: {all_healthy}")
        
    except Node.DoesNotExist:
        logger.warning(f"Node with uuid {node_uuid} does not exist or is inactive")
    except Exception as e:
        logger.error(f"Error checking node health {node_uuid}: {str(e)}")

@shared_task
def check_all_nodes():
    """
    检查所有节点的健康状态
    """
    active_nodes = Node.objects.filter(is_active=True)
    
    for node in active_nodes:
        # 异步调度每个节点的健康检查
        check_node_health.delay(str(node.uuid))

@shared_task
def cleanup_health_records():
    """
    清理过期的健康记录
    """
    from datetime import timedelta
    from django.utils import timezone
    
    # 删除30天前的健康记录
    cutoff_time = timezone.now() - timedelta(days=30)
    deleted_count = NodeHealth.objects.filter(create_time__lt=cutoff_time).delete()
    
    logger.info(f"Cleaned up {deleted_count[0]} old health records")