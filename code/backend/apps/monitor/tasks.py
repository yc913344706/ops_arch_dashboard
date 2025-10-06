from celery import shared_task
from django.utils import timezone
from .models import Node, NodeHealth
from .probes.factory import get_probe_instance
from lib.log import color_logger

@shared_task
def check_node_health(node_uuid):
    """
    检查单个节点健康状态
    """
    try:
        color_logger.info(f"Start checking node health: {node_uuid}")
        node = Node.objects.get(uuid=node_uuid, is_active=True)
        
        # 检查节点是否有 basic_info_list
        if not node.basic_info_list or len(node.basic_info_list) == 0:
            # 没有基本信息，状态为未知
            node.healthy_status = 'unknown'
            node.last_check_time = timezone.now()
            node.save(update_fields=['healthy_status', 'last_check_time'])
            
            # 创建健康记录
            NodeHealth.objects.create(
                node=node,
                healthy_status='unknown',  # Since there's no basic info, we can't determine health
                response_time=None,
                probe_result={'details': node.basic_info_list},
                error_message='No basic info to check'
            )
            
            color_logger.info(f"Node {node.name} health check completed: unknown (no basic info)")
            return

        # 遍历节点的所有基础信息，执行探活，并更新 basic_info_list 中的 is_healthy 状态
        updated_basic_info_list = []
        healthy_count = 0
        total_response_time = 0
        probe_count = 0
        
        for basic_info in node.basic_info_list:
            host = basic_info.get('host')
            port = basic_info.get('port')
            
            # Create a copy of the basic_info to update
            updated_info = basic_info.copy()
            updated_info['is_healthy'] = True  # Assume healthy initially
            
            # Perform checks and update is_healthy status
            if host:
                # 执行Ping检测
                probe = get_probe_instance('ping', {})
                result = probe.check_with_host(node, host)
                if not result['is_healthy']:
                    updated_info['is_healthy'] = False
                if result.get('response_time'):
                    total_response_time += result['response_time']
                    probe_count += 1
                    
            if port and host:  # 如果有端口和主机，则执行端口检测
                probe = get_probe_instance('port', {'timeout': 3})
                result = probe.check_with_host_port(node, host, port)
                if not result['is_healthy']:
                    updated_info['is_healthy'] = False
                if result.get('response_time'):
                    total_response_time += result['response_time']
                    probe_count += 1
            elif port:  # 如果只有端口，使用节点的IP地址
                probe = get_probe_instance('port', {'timeout': 3})
                result = probe.check_with_host_port(node, node.link.name, port)  # 使用节点链接名作为主机名占位符
                if not result['is_healthy']:
                    updated_info['is_healthy'] = False
                if result.get('response_time'):
                    total_response_time += result['response_time']
                    probe_count += 1
            
            # Count total healthy items for status determination
            if updated_info['is_healthy']:
                healthy_count += 1
                
            updated_basic_info_list.append(updated_info)

        avg_response_time = total_response_time / probe_count if probe_count > 0 else None
        
        # Determine the overall healthy status based on the results
        total_count = len(updated_basic_info_list)
        if healthy_count == total_count:
            healthy_status = 'green'  # All healthy
        elif healthy_count == 0:
            healthy_status = 'red'  # All unhealthy
        else:
            healthy_status = 'yellow'  # Partially healthy
        
        # Update the node with the new basic_info_list and healthy_status
        node.basic_info_list = updated_basic_info_list
        node.healthy_status = healthy_status
        node.last_check_time = timezone.now()
        node.save(update_fields=['basic_info_list', 'healthy_status', 'last_check_time'])
        
        # Create health record
        NodeHealth.objects.create(
            node=node,
            healthy_status=healthy_status,
            response_time=avg_response_time,
            probe_result={'details': updated_basic_info_list},
            error_message=None if healthy_status == 'green' else 'One or more checks failed'
        )
        
        color_logger.info(f"Node {node.name} health check completed: {healthy_status}")
        
    except Node.DoesNotExist:
        color_logger.warning(f"Node with uuid {node_uuid} does not exist or is inactive")
    except Exception as e:
        color_logger.error(f"Error checking node health {node_uuid}: {str(e)}")

@shared_task
def check_all_nodes():
    """
    检查所有节点的健康状态
    """
    from django.conf import settings
    
    active_nodes = Node.objects.filter(is_active=True)
    
    # 限制并发任务数以防止资源耗尽
    max_concurrent_checks = getattr(settings, 'MAX_CONCURRENT_HEALTH_CHECKS', 10)  # 默认为10
    
    for index, node in enumerate(active_nodes):
        # 在分派任务之间添加小延迟，防止系统过载
        # 每处理 max_concurrent_checks 个任务后延迟1秒
        countdown = (index // max_concurrent_checks) * 1  # 每10个任务延迟1秒
        check_node_health.apply_async(args=[str(node.uuid)], countdown=countdown)

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
    
    color_logger.info(f"Cleaned up {deleted_count[0]} old health records")