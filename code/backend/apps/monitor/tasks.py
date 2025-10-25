import uuid
from celery import shared_task
from django.utils import timezone
from django.db import transaction

from lib.time_tools import utc_obj_to_time_zone_str
from lib.redis_tool import get_redis_value, set_redis_value, delete_redis_value
from django_redis import get_redis_connection
from .models import Node, NodeHealth, Alert, SystemHealthStats
from .probes.factory import get_probe_instance
from lib.log import color_logger
from lib.influxdb_tool import InfluxDBManager
from .alert_config_parser import alert_config_parser, AlertRule
import operator
from datetime import timedelta

def deduplicate_basic_info_list(basic_info_list):
    """
    去除basic_info_list中的重复项
    """
    seen_combinations = set()
    unique_list = []
    
    for basic_info in basic_info_list:
        # 创建唯一标识符：host:port，若无端口则只使用host
        host = basic_info.get('host')
        port = basic_info.get('port')
        
        if host and port:
            identifier = f"{host}:{port}"
        elif host:
            identifier = f"{host}"
        else:
            # 如果既没有host也没有port，则保留原项
            unique_list.append(basic_info)
            continue
        
        if identifier not in seen_combinations:
            seen_combinations.add(identifier)
            # 添加一个去重后的标记，用于后续处理
            unique_item = basic_info.copy()
            unique_item['deduplicated_id'] = identifier
            unique_list.append(unique_item)
    
    return unique_list


def _record_node_health_check_duration(node_uuid, start_time, check_duration=None):
    node_uuid = str(node_uuid)
    if check_duration is None:
        # Calculate the total check duration for this node
        check_duration = (timezone.now() - start_time).total_seconds() * 1000  # Convert to milliseconds
        
    # 添加节点检查耗时到节点属性
    # 由于Node模型可能没有duration字段，我们使用AppSetting来存储
    SystemHealthStats.objects.update_or_create(
        key=f'node_check_duration_{node_uuid}',
        defaults={
            'value': str(check_duration),
            'meta_info': {
                'node_id': node_uuid, 
                'check_time': utc_obj_to_time_zone_str(start_time), 
                'duration_ms': check_duration}
        }
    )

@shared_task
def check_node_health(node_uuid, parent_task_lock_key=None, task_uuid=None):
    """
    检查单个节点健康状态（异步优化版）
    """
    start_time = timezone.now()
    success = False
    
    try:
        color_logger.info(f"Start checking node health: {node_uuid}")
        node = Node.objects.get(uuid=node_uuid, is_active=True)
        
        # 获取BaseInfo数据，优先使用新架构
        from .models import BaseInfo
        base_info_items = BaseInfo.objects.filter(node=node).select_related('node')
        
        # 统计基础信息数量
        total_count = base_info_items.count()
        
        # 记录节点基本信息
        color_logger.info(f"Node {node.name} (UUID: {node_uuid}) - BaseInfo count: {total_count}")
        color_logger.info(f"Node {node.name} - link.check_single_point: {node.link.check_single_point}")
        
        # 检查是否有基础信息
        if total_count == 0:
            # 没有基础信息
            total_count = 0
            color_logger.info(f"Node {node.name} has no BaseInfo items, processing empty case")
            
            # 如果链路需要检测单点，即使没有基本配置信息，也要应用单点检测逻辑
            # 但不在此处创建告警，告警统一由 check_all_alerts 处理
            if node.link.check_single_point:
                # 应用单点检测逻辑 - 0个基础配置信息，应为red级别
                healthy_status = 'red'
                
                # 创建健康记录，包含单点检测相关信息
                probe_result_with_single_point = {
                    'details': node.basic_info_list, 
                    'single_point_status': 'missing',
                    'single_point_count': 0,
                    'base_info_details': []  # 由于没有BaseInfo，所以为空
                }
                NodeHealth.objects.create(
                    node=node,
                    healthy_status=healthy_status,
                    response_time=None,
                    probe_result=probe_result_with_single_point,
                    error_message='No base info to check for single point detection'
                )
                
                # 更新节点状态
                node.healthy_status = healthy_status
                node.last_check_time = timezone.now()
                node.save(update_fields=['healthy_status', 'last_check_time'])
                
                # 将健康记录写入InfluxDB（时序数据库）
                try:
                    influxdb_manager = InfluxDBManager()
                    influxdb_manager.write_node_health_data(
                        node_uuid=str(node.uuid),
                        healthy_status=healthy_status,
                        response_time=None,
                        probe_result=probe_result_with_single_point,
                        error_message='No base info to check for single point detection'
                    )
                    color_logger.info(f"Wrote node health data to InfluxDB for node {node.name}")
                except Exception as e:
                    color_logger.error(f"Failed to write to InfluxDB: {str(e)}", exc_info=True)
                    # 即使InfluxDB写入失败，也不影响主流程

                _record_node_health_check_duration(node_uuid, start_time)
                color_logger.info(f"Node {node.name} health check completed: {healthy_status} (single point detection data updated)")
                success = True
                return
            else:
                # 没有基本信息且不需要检测单点，状态为未知
                color_logger.info(f"Node {node.name} has no base info but not checking single point, setting to unknown")
                node.healthy_status = 'unknown'
                node.last_check_time = timezone.now()
                node.save(update_fields=['healthy_status', 'last_check_time'])
                
                # 创建健康记录
                probe_result = {
                    'details': node.basic_info_list,
                    'base_info_details': []
                }
                NodeHealth.objects.create(
                    node=node,
                    healthy_status='unknown',
                    response_time=None,
                    probe_result=probe_result,
                    error_message='No base info to check'
                )
                
                _record_node_health_check_duration(node_uuid, start_time)
                color_logger.info(f"Node {node.name} health check completed: unknown (no base info)")
                success = True
                return
        else:
            color_logger.info(f"Node {node.name} has {total_count} BaseInfo items, proceeding with normal check")
        
        # 使用异步探针管理器
        from .async_probes import AsyncProbeManager
        probe_manager = AsyncProbeManager(timeout=3)
        
        # 提取需要检测的主机和端口
        hosts_to_ping = []
        host_port_pairs = []
        
        for base_info in base_info_items:
            # 检查是否禁ping
            if not base_info.is_ping_disabled and base_info.host:
                hosts_to_ping.append((base_info.host, str(base_info.uuid)))  # 使用base_info的uuid作为唯一标识
            
            if base_info.host and base_info.port:
                host_port_pairs.append((base_info.host, base_info.port, str(base_info.uuid)))
        
        # 并发执行检测任务
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # 并发执行ping检测
            ping_tasks = []
            for host, base_info_uuid in hosts_to_ping:
                ping_tasks.append(probe_manager.ping_async(host))
            
            ping_results = loop.run_until_complete(
                asyncio.gather(*ping_tasks, return_exceptions=True)
            )
            
            # 并发执行端口检测
            port_tasks = []
            for host, port, base_info_uuid in host_port_pairs:
                port_tasks.append(probe_manager.port_check_async(host, port))
            
            port_results = loop.run_until_complete(
                asyncio.gather(*port_tasks, return_exceptions=True)
            )
        finally:
            loop.close()
        
        # 构建检测结果映射
        ping_result_map = {}
        for i, result in enumerate(ping_results):
            if not isinstance(result, Exception):
                ping_result_map[result['host']] = result
            else:
                host = hosts_to_ping[i][0]
                ping_result_map[host] = {
                    'host': host,
                    'is_healthy': False,
                    'response_time': None,
                    'error_message': str(result)
                }
        
        port_result_map = {}
        for i, result in enumerate(port_results):
            if not isinstance(result, Exception):
                port_result_map[f"{result['host']}:{result['port']}"] = result
            else:
                host, port = host_port_pairs[i][:2]
                port_result_map[f"{result['host']}:{result['port']}"] = {
                    'host': host,
                    'port': port,
                    'is_healthy': False,
                    'response_time': None,
                    'error_message': str(result)
                }
        
        # 更新 basic_info_list 中的健康状态（保持原始列表结构）
        # 同时构建新的 base_info_details
        updated_basic_info_list = []  # 保持向后兼容
        base_info_details = []        # 新的数据结构，包含BaseInfo的所有信息
        healthy_count = 0
        total_response_time = 0
        probe_count = 0
        
        # 首先处理basic_info_list以保持向后兼容
        for original_basic_info in node.basic_info_list:
            updated_info = original_basic_info.copy()
            host = original_basic_info.get('host')
            port = original_basic_info.get('port')
            
            # 假设初始健康
            updated_info['is_healthy'] = True

            # 检查ping结果
            if host:
                ping_result = ping_result_map.get(host)
                if ping_result and not ping_result['is_healthy']:
                    updated_info['is_healthy'] = False
                if ping_result and ping_result.get('response_time'):
                    total_response_time += ping_result['response_time']
                    probe_count += 1
            
            # 检查端口结果
            if host and port:
                port_key = f"{host}:{port}"
                port_result = port_result_map.get(port_key)
                if port_result and not port_result['is_healthy']:
                    updated_info['is_healthy'] = False
                if port_result and port_result.get('response_time'):
                    total_response_time += port_result['response_time']
                    probe_count += 1
            elif port:  # 只有端口的情况
                # 使用节点链接名作为主机名
                port_key = f"{node.link.name}:{port}"
                port_result = port_result_map.get(port_key)
                if port_result and not port_result['is_healthy']:
                    updated_info['is_healthy'] = False
                if port_result and port_result.get('response_time'):
                    total_response_time += port_result['response_time']
                    probe_count += 1
            
            if updated_info['is_healthy']:
                healthy_count += 1
            
            updated_basic_info_list.append(updated_info)
        
        # 然后处理BaseInfo数据
        for base_info in base_info_items:
            base_info_detail = {
                'uuid': str(base_info.uuid),
                'host': base_info.host,
                'port': base_info.port,
                'is_ping_disabled': base_info.is_ping_disabled,
                'is_healthy': True  # 假设初始健康
            }
            
            # 检查ping结果
            if not base_info.is_ping_disabled and base_info.host:
                ping_result = ping_result_map.get(base_info.host)
                if ping_result and not ping_result['is_healthy']:
                    base_info_detail['is_healthy'] = False
                if ping_result and ping_result.get('response_time'):
                    total_response_time += ping_result['response_time']
                    probe_count += 1
            
            # 检查端口结果
            if base_info.host and base_info.port:
                port_key = f"{base_info.host}:{base_info.port}"
                port_result = port_result_map.get(port_key)
                if port_result and not port_result['is_healthy']:
                    base_info_detail['is_healthy'] = False
                if port_result and port_result.get('response_time'):
                    total_response_time += port_result['response_time']
                    probe_count += 1
            
            # 如果base_info_detail不健康，则影响总体健康计数
            if base_info_detail['is_healthy']:
                healthy_count += 1
                
            base_info_details.append(base_info_detail)

        avg_response_time = total_response_time / probe_count if probe_count > 0 else None
        
        # 确定整体健康状态
        # 使用total_count（BaseInfo的数量）来计算总体健康状态
        total_checkable = len([bi for bi in base_info_details if bi['is_ping_disabled'] == False or bi['port'] is not None])
        if total_checkable > 0:
            healthy_percentage = healthy_count / total_checkable
            if healthy_percentage == 1.0:
                healthy_status = 'green'  # 全部健康
            elif healthy_percentage == 0.0:
                healthy_status = 'red'  # 全部不健康
            else:
                healthy_status = 'yellow'  # 部分健康
        else:
            # 如果没有任何可检查的项目，使用未知状态
            healthy_status = 'unknown'

        # 如果链路需要检测单点，则根据BaseInfo数量调整健康状态
        # 注意：对于0个BaseInfo的情况，已经在上面的早期检查中处理
        # 所以此处的total_count应始终基于非空列表（长度大于0）
        # 但告警处理统一由 check_all_alerts 完成，此处只更新节点状态和记录
        if node.link.check_single_point:
            if total_count == 1:
                # 只有1个基础配置信息，应为yellow级别
                healthy_status = 'yellow'
            # 注意：对于 total_count > 1 的情况，healthy_status 已经由之前的逻辑设置好了

        # 更新节点
        with transaction.atomic():
            node.basic_info_list = updated_basic_info_list  # 保持向后兼容
            node.healthy_status = healthy_status
            node.last_check_time = timezone.now()
            node.save(update_fields=['basic_info_list', 'healthy_status', 'last_check_time'])

        # 在probe_result中添加单点检测状态信息，供check_all_alerts使用
        single_point_status = 'normal'
        if node.link.check_single_point:
            if total_count == 0:
                single_point_status = 'missing'  # 这个情况应该不会到达这里，因为0的情况在上面就return了
            elif total_count == 1:
                single_point_status = 'warning'
            else:
                single_point_status = 'normal'

        probe_result_with_single_point = {
            'details': updated_basic_info_list, 
            'base_info_details': base_info_details,
            'single_point_status': single_point_status, 
            'single_point_count': total_count
        }

        # 将健康记录写入InfluxDB（时序数据库）
        try:
            influxdb_manager = InfluxDBManager()
            influxdb_manager.write_node_health_data(
                node_uuid=str(node.uuid),
                healthy_status=healthy_status,
                response_time=avg_response_time,
                probe_result=probe_result_with_single_point,
                error_message=None if healthy_status == 'green' else 'One or more checks failed'
            )
            color_logger.info(f"Wrote node health data to InfluxDB for node {node.name}")
        except Exception as e:
            color_logger.error(f"Failed to write to InfluxDB: {str(e)}", exc_info=True)
            # 即使InfluxDB写入失败，也不影响主流程

        _record_node_health_check_duration(node_uuid, start_time)
        
        color_logger.info(f"Node {node.name} health check completed: {healthy_status}")
        success = True
        
    except Node.DoesNotExist:
        _record_node_health_check_duration(node_uuid, start_time, -1)
        color_logger.warning(f"Node with uuid {node_uuid} does not exist or is inactive")
    except Exception as e:
        _record_node_health_check_duration(node_uuid, start_time, -2)
        color_logger.error(f"Error checking node health {node_uuid}: {str(e)}", exc_info=True)
    finally:
        # 如果有任务UUID，更新Redis中对应任务的结束时间
        if task_uuid:
            try:
                redis_conn = get_redis_connection("default")
                task_redis_key = f"check_all_nodes_task:{task_uuid}"
                
                # 设置当前时间作为最新的更新时间
                redis_conn.hset(task_redis_key, 'end_time', timezone.now().isoformat())
            except Exception as redis_error:
                color_logger.error(f"Error updating task end time for task_uuid {task_uuid}: {str(redis_error)}", exc_info=True)
        
        if parent_task_lock_key:
            _check_and_release_parent_lock(parent_task_lock_key, node_uuid, success)

def get_check_all_nodes_task_info(task_uuid):
    """
    获取指定任务UUID的详细信息
    """
    redis_conn = get_redis_connection("default")
    task_redis_key = f"check_all_nodes_task:{task_uuid}"
    
    # 获取Redis哈希中的所有字段
    task_info = redis_conn.hgetall(task_redis_key)
    
    # 解码字节字符串为普通字符串（如果需要）
    decoded_task_info = {}
    for key, value in task_info.items():
        if isinstance(key, bytes):
            key = key.decode('utf-8')
        if isinstance(value, bytes):
            value = value.decode('utf-8')
        decoded_task_info[key] = value
    
    if decoded_task_info:
        # 计算任务耗时（如果已有开始和结束时间）
        start_time_str = decoded_task_info.get('start_time')
        end_time_str = decoded_task_info.get('final_end_time') or decoded_task_info.get('end_time')
        
        if start_time_str and end_time_str:
            try:
                from datetime import datetime
                import re
                # 处理ISO格式的时间字符串，兼容各种格式
                # 移除末尾的Z并处理时区信息
                start_time_str_clean = start_time_str.replace('Z', '+00:00') if start_time_str.endswith('Z') else start_time_str
                end_time_str_clean = end_time_str.replace('Z', '+00:00') if end_time_str.endswith('Z') else end_time_str
                
                # 如果时间字符串包含时区信息，直接解析；否则添加默认时区
                if '+' in start_time_str_clean or start_time_str_clean.endswith('-00:00'):
                    start_time = datetime.fromisoformat(start_time_str_clean)
                else:
                    # 如果没有时区信息，添加默认时区
                    if start_time_str_clean.count(':') == 2:  # YYYY-MM-DDTHH:MM:SS.ffffff 格式
                        start_time = datetime.fromisoformat(start_time_str_clean + '+00:00')
                    else:
                        start_time = datetime.fromisoformat(start_time_str_clean)
                
                if '+' in end_time_str_clean or end_time_str_clean.endswith('-00:00'):
                    end_time = datetime.fromisoformat(end_time_str_clean)
                else:
                    if end_time_str_clean.count(':') == 2:
                        end_time = datetime.fromisoformat(end_time_str_clean + '+00:00')
                    else:
                        end_time = datetime.fromisoformat(end_time_str_clean)
                
                duration = (end_time - start_time).total_seconds()
                decoded_task_info['duration_seconds'] = duration
                decoded_task_info['start_time'] = utc_obj_to_time_zone_str(start_time)
                decoded_task_info['end_time'] = utc_obj_to_time_zone_str(end_time)
            except Exception as e:
                color_logger.error(f"Error calculating duration for task {task_uuid}: {str(e)}")
    
    return decoded_task_info


def get_recent_check_all_nodes_tasks(limit=10):
    """
    获取最近的check_all_nodes任务列表
    """
    redis_conn = get_redis_connection("default")
    
    # 查找所有check_all_nodes任务键
    task_keys = redis_conn.keys("check_all_nodes_task:*")
    
    # 提取任务UUID并获取任务信息
    tasks_info = []
    for task_key in task_keys:
        if isinstance(task_key, bytes):
            task_key = task_key.decode('utf-8')
        
        task_uuid = task_key.replace("check_all_nodes_task:", "")
        task_info = get_check_all_nodes_task_info(task_uuid)
        
        if task_info:  # 只添加存在的任务
            task_info['task_uuid'] = task_uuid
            tasks_info.append(task_info)
    
    # 按开始时间排序，返回最新的limit个任务
    tasks_info.sort(key=lambda x: x.get('start_time', ''), reverse=True)
    return tasks_info[:limit]


def _check_and_release_parent_lock(parent_task_lock_key, node_uuid, success=True):
    """
    检查父任务是否完成，如果完成则释放锁
    使用 Redis 集合来管理待处理的节点，每个节点完成时从集合中移除自己
    """
    try:
        # 获取Redis实例
        redis_conn = get_redis_connection("default")
        
        # 获取待处理节点集合的键名
        pending_nodes_key = f"{parent_task_lock_key}_pending_nodes"
        
        # 从待处理集合中移除当前完成的节点
        redis_conn.srem(pending_nodes_key, node_uuid)
        
        # 检查是否还有待处理的节点
        remaining_count = redis_conn.scard(pending_nodes_key)
        
        if remaining_count == 0:
            # 所有节点都已完成
            # 查找与这个锁关联的任务UUID
            # 从Redis hash中获取任务信息，其中可能包含task_uuid
            # 从锁键名中提取任务UUID
            # 锁键的格式是 "ops_arch_dashboard_check_all_nodes_lock"
            # 相应的Redis hash键格式是 "check_all_nodes_task:{task_uuid}"
            
            # 遍历所有可能的任务键，找到与当前锁相关的任务
            # 为了更精确地处理这个逻辑，我们采用另一种方法：
            # 从锁数据中解析出任务UUID，如果有的话
            # 或者在锁数据中存储任务UUID信息
            lock_data = get_redis_value('default', parent_task_lock_key)
            if lock_data:
                try:
                    # 锁数据格式为 "node_count:start_time"，但实际已存储在Redis hash中
                    # 我们需要通过某种方式找到相关的任务键
                    # 简单的方法是通过Redis键模式查找
                    task_keys = redis_conn.keys("check_all_nodes_task:*")
                    if task_keys:
                        # 找到最近的活动任务，通常是最相关的
                        for task_key in task_keys:
                            # 检查该任务键是否已经设置了结束时间
                            if not redis_conn.hexists(task_key, 'final_end_time'):
                                # 设置最终结束时间
                                redis_conn.hset(task_key, 'final_end_time', timezone.now().isoformat())
                                redis_conn.hset(task_key, 'status', 'completed')
                                # 保留这个键一段时间用于历史记录，不立即删除
                                redis_conn.expire(task_key, 3600)  # 1小时后过期
                                color_logger.info(f"Task {task_key} completed and final end time recorded")
                                break
            
                except Exception as task_error:
                    color_logger.error(f"Error updating final task end time: {str(task_error)}", exc_info=True)
            
            # 删除主锁和待处理集合
            redis_conn.delete(parent_task_lock_key)
            redis_conn.delete(pending_nodes_key)
            color_logger.info(f"All node health checks completed, lock {parent_task_lock_key} released")
        else:
            status_msg = "successfully" if success else "with failure"
            color_logger.debug(f"Node {node_uuid} completed {status_msg}, {remaining_count} nodes remaining")
            
        # 如果需要排错，可以查看还有哪些节点未完成
        if remaining_count > 0 and remaining_count < 10:  # 只在节点数不多时显示，避免日志过多
            remaining_nodes = redis_conn.smembers(pending_nodes_key)
            color_logger.info(f"Remaining nodes to check: {remaining_nodes}")
    except Exception as e:
        color_logger.error(f"Error checking and releasing parent lock: {str(e)}")

@shared_task
def check_all_nodes():
    """
    检查所有节点的健康状态
    """
    from django.conf import settings
    
    # 生成一个唯一任务ID
    task_uuid = str(uuid.uuid4())
    task_redis_key = f"check_all_nodes_task:{task_uuid}"
    
    # 使用 Redis 锁来防止重复运行
    redis_key = 'ops_arch_dashboard_check_all_nodes_lock'
    
    # 尝试获取锁，如果锁已存在则直接返回
    existing_lock = get_redis_value('default', redis_key)
    if existing_lock:
        color_logger.info("check_all_nodes task is already running, skipping this execution")
        return "Task already running, skipped"
    
    start_time = timezone.now()
    
    active_nodes = list(Node.objects.filter(is_active=True))
    node_count = len(active_nodes)
    
    if node_count == 0:
        color_logger.info("No active nodes to check, skipping task")
        return "No active nodes to check"
    
    try:
        # 设置锁，包含节点数量和开始时间
        lock_data = f"{node_count}:{start_time.isoformat()}"
        # 动态设置过期时间：基础30分钟 + 每个节点估算1分钟，最多2小时
        estimated_duration = min(7200, 1800 + node_count * 60)  # 30分钟基础 + 每个节点1分钟，上限2小时
        set_redis_value('default', redis_key, lock_data, set_expire=estimated_duration)
        
        # 使用 Redis 记录任务的开始时间
        redis_conn = get_redis_connection("default")
        task_info = {
            'start_time': start_time.isoformat(),
            'node_count': node_count,
            'estimated_duration': estimated_duration,
            'task_uuid': task_uuid
        }
        redis_conn.hset(task_redis_key, mapping=task_info)
        # 设置过期时间，与主锁相同的过期时间
        redis_conn.expire(task_redis_key, estimated_duration)
        
        # 使用 Redis 集合来管理待处理的节点 UUID
        pending_nodes_key = f"{redis_key}_pending_nodes"
        # 先删除可能存在的旧集合
        redis_conn.delete(pending_nodes_key)
        
        # 将所有待处理节点的 UUID 添加到集合中
        if active_nodes:
            node_uuids = [str(node.uuid) for node in active_nodes]
            redis_conn.sadd(pending_nodes_key, *node_uuids)
            # 设置过期时间，与锁相同的过期时间
            redis_conn.expire(pending_nodes_key, estimated_duration)
        
        # 限制并发任务数以防止资源耗尽
        max_concurrent_checks = getattr(settings, 'MAX_CONCURRENT_HEALTH_CHECKS', 10)  # 默认为10
        
        scheduled_count = 0
        for index, node in enumerate(active_nodes):
            # 在分派任务之间添加小延迟，防止系统过载
            # 每处理 max_concurrent_checks 个任务后延迟1秒
            countdown = (index // max_concurrent_checks) * 1  # 每10个任务延迟1秒
            check_node_health.apply_async(
                args=[str(node.uuid)], 
                countdown=countdown,
                # 传递锁键名和任务UUID到子任务
                kwargs={'parent_task_lock_key': redis_key, 'task_uuid': task_uuid}
            )
            scheduled_count += 1
        
        # 记录检查开始时间到一个全局位置
        SystemHealthStats.objects.update_or_create(
            key='last_node_check',
            defaults={
                'value': utc_obj_to_time_zone_str(start_time),
                'meta_info': {
                    'task_uuid': task_uuid,
                    'node_count': node_count, 
                    'start_time': utc_obj_to_time_zone_str(start_time),
                    'scheduled_count': scheduled_count,
                    'estimated_duration': estimated_duration
                }
            }
        )
        
        color_logger.info(f"Started checking {node_count} nodes health, scheduled {scheduled_count} subtasks with lock {redis_key} and pending nodes set {pending_nodes_key}, estimated duration: {estimated_duration}s, task_uuid: {task_uuid}")
        
        return f"Scheduled {scheduled_count} node health checks with task_uuid {task_uuid}"
    
    except Exception as e:
        # 如果出错，清理 Redis 键，确保不会永久锁定
        try:
            redis_conn = get_redis_connection("default")
            redis_conn.delete(redis_key)
            pending_nodes_key = f"{redis_key}_pending_nodes"
            redis_conn.delete(pending_nodes_key)
            # 清理任务相关键
            redis_conn.delete(task_redis_key)
            color_logger.error(f"Error in check_all_nodes, cleaned up locks: {str(e)}")
        except:
            pass  # 如果清理也失败，就不处理了
        raise  # 重新抛出异常，让 Celery 处理

@shared_task
def cleanup_health_records():
    """
    清理过期的健康记录
    """
    
    # 删除30天前的健康记录
    cutoff_time = timezone.now() - timedelta(days=30)
    deleted_count = NodeHealth.objects.filter(create_time__lt=cutoff_time).delete()
    
    color_logger.info(f"Cleaned up {deleted_count[0]} old health records")


def create_or_update_alert(node, alert_type, alert_subtype, title, description, severity='MEDIUM'):
    """
    创建或更新告警
    如果相同的告警已存在且为OPEN状态，则更新最后发生时间
    检查该告警是否被静默，如果是则不创建或更新
    """
    try:
        # 检查是否有静默的相同告警
        silenced_alert = Alert.objects.filter(
            node_id=str(node.uuid),
            alert_type=alert_type,
            alert_subtype=alert_subtype,
            status='SILENCED'
        ).first()
        
        # 如果存在静默状态的告警且仍在静默期内，则不创建或更新
        if silenced_alert and silenced_alert.is_currently_silenced():
            color_logger.info(f"Alert for node {node.name} is silenced until {silenced_alert.silenced_until}, skipping creation/update")
            return None

        # 使用事务确保操作的原子性，防止并发问题
        with transaction.atomic():
            # 检查是否已存在相同告警
            existing_alert = Alert.objects.select_for_update().filter(
                node_id=str(node.uuid),
                alert_type=alert_type,
                alert_subtype=alert_subtype,
                status='OPEN'
            ).first()
            
            if existing_alert:
                # 检查是否需要触发通知（只有在告警信息有实质性变化时才推送）
                # 比较当前告警的严重程度与更新后的严重程度，或者是否首次发生
                old_severity = existing_alert.severity
                needs_notification = (old_severity != severity)
                
                # 更新已存在告警的最后发生时间
                existing_alert.last_occurred = timezone.now()
                existing_alert.description = description
                existing_alert.severity = severity
                existing_alert.save()
                color_logger.info(f"Updated existing alert for node {node.name}: {title}")
                
                # 只有在告警严重程度变化时才触发通知，避免每分钟重复推送
                if needs_notification:
                    trigger_alert_notification(existing_alert)
                
                return existing_alert
            else:
                # 创建新告警
                alert = Alert.objects.create(
                    node_id=str(node.uuid),
                    alert_type=alert_type,
                    alert_subtype=alert_subtype,
                    title=title,
                    description=description,
                    severity=severity,
                    status='OPEN'
                )
                color_logger.info(f"Created new alert for node {node.name}: {title}")
                
                # 新创建的告警总是需要通知
                trigger_alert_notification(alert)
                
                return alert
    except Exception as e:
        color_logger.error(f"Error creating or updating alert for node {node.name}: {str(e)}", exc_info=True)


def evaluate_condition(condition_str: str, context: dict) -> bool:
    """
    评估告警条件表达式
    """
    try:
        # 使用更安全的条件评估方法
        # 定义安全的操作符
        ops = {
            '==': operator.eq,
            '!=': operator.ne,
            '<': operator.lt,
            '<=': operator.le,
            '>': operator.gt,
            '>=': operator.ge,
            'and': lambda x, y: x and y,
            'or': lambda x, y: x or y,
        }
        
        # 从条件字符串解析操作符和变量
        # 对于 "avg_response_time > 1000" 这样的条件
        if ' and ' in condition_str or ' or ' in condition_str:
            # 处理多个条件
            sub_conditions = []
            if ' and ' in condition_str:
                sub_conditions = condition_str.split(' and ')
                op_func = ops['and']
            elif ' or ' in condition_str:
                sub_conditions = condition_str.split(' or ')
                op_func = ops['or']
            
            results = []
            for sub_condition in sub_conditions:
                sub_result = evaluate_single_condition(sub_condition.strip(), context, ops)
                results.append(sub_result)
            
            # 对于 and 连接的条件，所有子条件都必须为真
            # 对于 or 连接的条件，至少一个子条件为真
            if ' and ' in condition_str:
                return all(results)
            else:
                return any(results)
        else:
            # 处理单个条件
            return evaluate_single_condition(condition_str, context, ops)
            
    except Exception as e:
        color_logger.error(f"Error evaluating condition '{condition_str}': {e}")
        return False


def evaluate_single_condition(condition_str: str, context: dict, ops: dict) -> bool:
    """
    评估单个条件表达式
    """
    import re
    
    # 支持的比较操作符
    operators = ['>=', '<=', '!=', '==', '>', '<']
    
    for op in operators:
        if op in condition_str:
            parts = condition_str.split(op, 1)  # 只分割第一个匹配的操作符
            if len(parts) == 2:
                left_expr = parts[0].strip()
                right_expr = parts[1].strip()
                
                # 解析左侧变量
                left_value = context.get(left_expr, 0)  # 如果变量不存在，默认为0
                
                # 解析右侧值（可能是数字或字符串）
                if right_expr.startswith("'") and right_expr.endswith("'"):
                    # 字符串比较
                    right_value = right_expr[1:-1]  # 去除引号
                elif right_expr.startswith('"') and right_expr.endswith('"'):
                    # 字符串比较
                    right_value = right_expr[1:-1]  # 去除引号
                else:
                    # 数值比较
                    try:
                        right_value = float(right_expr)
                    except ValueError:
                        # 如果不能转换为数值，则按字符串处理
                        right_value = right_expr
                
                # 执行比较
                op_func = ops[op]
                
                # 处理None值
                if left_value is None:
                    left_value = 0
                if right_value is None:
                    right_value = 0
                    
                return op_func(left_value, right_value)
    
    # 如果没有找到操作符，返回False
    color_logger.warning(f"No operator found in condition: {condition_str}")
    return False


def close_resolved_alerts(node, alert_type=None, alert_subtype=None):
    """
    关闭已解决的告警
    同时处理已静默的告警，如果告警条件已经解决，应结束静默状态
    """
    try:
        with transaction.atomic():
            filters = {
                'node_id': str(node.uuid),
                'status': 'OPEN'
            }
            if alert_type:
                filters['alert_type'] = alert_type
            if alert_subtype:
                filters['alert_subtype'] = alert_subtype
                
            # 使用 select_for_update 来防止并发问题
            open_alerts = Alert.objects.select_for_update().filter(**filters)
            
            for alert in open_alerts:
                alert.status = 'CLOSED'
                alert.resolved_at = timezone.now()
                alert.save()
                color_logger.info(f"Closed alert {alert.title} for node {node.name}")
                
                # 触发告警关闭通知
                trigger_alert_notification(alert)

            # 处理静默的告警，如果问题已解决，也要将静默的告警关闭
            silenced_filters = {
                'node_id': str(node.uuid),
                'status': 'SILENCED'
            }
            if alert_type:
                silenced_filters['alert_type'] = alert_type
            if alert_subtype:
                silenced_filters['alert_subtype'] = alert_subtype
                
            # 使用 select_for_update 来防止并发问题
            silenced_alerts = Alert.objects.select_for_update().filter(**silenced_filters)
            
            for alert in silenced_alerts:
                alert.status = 'CLOSED'
                alert.resolved_at = timezone.now()
                alert.silenced_until = timezone.now()  # 既然问题解决了，静默也应结束
                alert.save()
                color_logger.info(f"Closed silenced alert {alert.title} for node {node.name} as the issue is resolved")
                
                # 触发告警关闭通知
                trigger_alert_notification(alert)
                
    except Exception as e:
        color_logger.error(f"Error closing resolved alerts for node {node.name}: {str(e)}")


def check_alert_conditions(node, health_record, rule: AlertRule):
    """
    根据规则检查节点是否触发告警
    """
    try:
        # 处理单点检测相关的规则（single_point_missing, single_point_warning）
        # 现在由 check_all_alerts 统一处理，基于健康记录中的信息进行判断
        if rule.name in ['single_point_missing', 'single_point_warning']:
            # 检查节点的链路是否需要检测单点
            if not node.link.check_single_point:
                # 如果不需要检测单点，则关闭所有相关的单点检测告警
                if rule.name == 'single_point_missing':
                    close_resolved_alerts(
                        node=node,
                        alert_type='SINGLE_POINT_MISSING'
                    )
                elif rule.name == 'single_point_warning':
                    close_resolved_alerts(
                        node=node,
                        alert_type='SINGLE_POINT_WARNING'
                    )
                # 处理完单点检测规则后直接返回，不继续处理通用逻辑
                return

            # 获取最新的健康记录来判断单点状态
            if health_record:
                probe_result = health_record.probe_result or {}
                single_point_status = probe_result.get('single_point_status')
                single_point_count = probe_result.get('single_point_count', len(probe_result.get('details', [])) if 'details' in probe_result else 0)
                
                if rule.name == 'single_point_missing' and single_point_status == 'missing':
                    # basic_info_list 为空，触发 SINGLE_POINT_MISSING 告警
                    alert_description = rule.message.format(
                        node_name=node.name,
                        basic_info_count=0
                    )
                    
                    # 统一使用规则名称作为subtype，确保一致性
                    alert_subtype = 'NoBasicInfo'
                    
                    create_or_update_alert(
                        node=node,
                        alert_type=rule.name.upper().replace('-', '_'),
                        alert_subtype=alert_subtype,
                        title=f"节点{node.name}缺少基本配置信息",
                        description=f"节点{node.name}的basic_info_list为空，无法进行单点检测",
                        severity=rule.severity
                    )
                elif rule.name == 'single_point_warning' and single_point_status == 'warning':
                    # basic_info_list 只有1个，触发 SINGLE_POINT_WARNING 告警
                    alert_description = rule.message.format(
                        node_name=node.name,
                        single_point_count=single_point_count
                    )
                    
                    # 统一使用规则名称作为subtype，确保一致性
                    alert_subtype = 'SinglePoint'
                    
                    create_or_update_alert(
                        node=node,
                        alert_type=rule.name.upper().replace('-', '_'),
                        alert_subtype=alert_subtype,
                        title=f"节点{node.name}存在单点风险",
                        description=f"节点{node.name}的basic_info_list只有1个配置项，存在单点风险",
                        severity=rule.severity
                    )
                elif rule.name in ['single_point_missing', 'single_point_warning'] and single_point_status in ['normal', 'warning', 'missing']:
                    # 对于其他情况，检查是否需要关闭相应的告警
                    # 如果当前状态不是对应告警的状态，则关闭该类型的告警
                    if rule.name == 'single_point_missing' and single_point_status != 'missing':
                        # 关闭 SINGLE_POINT_MISSING 告警
                        close_resolved_alerts(
                            node=node,
                            alert_type='SINGLE_POINT_MISSING'
                        )
                    elif rule.name == 'single_point_warning' and single_point_status != 'warning':
                        # 关闭 SINGLE_POINT_WARNING 告警
                        close_resolved_alerts(
                            node=node,
                            alert_type='SINGLE_POINT_WARNING'
                        )
            else:
                # 没有健康记录，但basic_info_list可能为空
                basic_info_count = len(node.basic_info_list) if node.basic_info_list else 0
                if rule.name == 'single_point_missing' and basic_info_count == 0:
                    # basic_info_list 为空，触发 SINGLE_POINT_MISSING 告警
                    alert_description = rule.message.format(
                        node_name=node.name,
                        basic_info_count=0
                    )
                    
                    # 统一使用规则名称作为subtype，确保一致性
                    alert_subtype = 'NoBasicInfo'
                    
                    create_or_update_alert(
                        node=node,
                        alert_type=rule.name.upper().replace('-', '_'),
                        alert_subtype=alert_subtype,
                        title=f"节点{node.name}缺少基本配置信息",
                        description=f"节点{node.name}的basic_info_list为空，无法进行单点检测",
                        severity=rule.severity
                    )
            
            # 处理完单点检测规则后直接返回，不继续处理通用逻辑
            return

        # 如果规则需要聚合历史数据（如平均响应时间），则获取时间窗口内的数据
        if rule.aggregation and rule.time_window:
            # 解析时间窗口，例如 '5m', '10m', '1h', '1d' 等
            time_delta = parse_time_window(rule.time_window)
            if time_delta:
                # 获取时间窗口内的健康记录
                time_limit = timezone.now() - time_delta
                node_health_records = NodeHealth.objects.filter(
                    node=node,
                    create_time__gte=time_limit,
                    response_time__isnull=False  # 只计算有响应时间的记录
                ).order_by('-create_time')
                
                # 根据聚合方式计算
                if rule.aggregation == 'avg' and node_health_records.exists():
                    values = [record.response_time for record in node_health_records if record.response_time is not None]
                    if values:
                        aggregated_value = round(sum(values) / len(values), 2)
                    else:
                        aggregated_value = None
                elif rule.aggregation == 'max' and node_health_records.exists():
                    values = [record.response_time for record in node_health_records if record.response_time is not None]
                    aggregated_value = max(values) if values else None
                elif rule.aggregation == 'min' and node_health_records.exists():
                    values = [record.response_time for record in node_health_records if record.response_time is not None]
                    aggregated_value = min(values) if values else None
                else:
                    # 默认使用当前记录的值
                    aggregated_value = health_record.response_time if health_record else None
            else:
                # 时间窗口解析失败，使用当前记录的值
                aggregated_value = health_record.response_time if health_record else None
        else:
            # 不需要聚合，使用当前记录的值
            aggregated_value = health_record.response_time if health_record else None

        # 构建评估上下文
        # 从告警规则的条件中提取阈值（例如从 "avg_response_time > 1000" 提取 1000）
        threshold_value = extract_threshold_from_condition(rule.condition)
        
        # 初始化上下文
        context = {
            'node_name': node.name,
            'status': health_record.healthy_status if health_record else node.healthy_status,
            'avg_response_time': aggregated_value if aggregated_value is not None else 0,  # 使用聚合后的值，如果为None则设为0
            'current_response_time': health_record.response_time if health_record and health_record.response_time else 0,  # 当前响应时间
            'probe_result': health_record.probe_result if health_record else {},
            'error_message': health_record.error_message if health_record else None,
            'threshold': threshold_value,
            'probe_type': '',  # 默认值，从probe_result中提取
            'error_type': '',  # 默认值
            'status_code': 0,  # 默认值
        }
        
        # 从probe_result中提取更多数据
        probe_result = health_record.probe_result if health_record else {}
        if 'details' in probe_result:
            details = probe_result['details']
            
            # 计算健康检查失败数量
            total_checks = len(details)
            failed_checks = sum(1 for item in details if not item.get('is_healthy', True))
            context['failed_check_count'] = failed_checks
            context['total_check_count'] = total_checks
            context['failure_rate'] = failed_checks / total_checks if total_checks > 0 else 0
            
            # 提取probe相关的数据供条件判断使用
            for detail in details:
                # 根据探活类型设置probe_type
                host = detail.get('host')
                port = detail.get('port')
                
                if host and not port:
                    context['probe_type'] = 'ping'
                elif host and port:
                    context['probe_type'] = 'port'
                elif detail.get('url'):
                    context['probe_type'] = 'http'
                
                # 提取错误类型和状态码
                if not detail.get('is_healthy'):
                    if 'timeout' in (detail.get('error_message', '') or '').lower():
                        context['error_type'] = 'timeout'
                    if 'status_code' in detail:
                        context['status_code'] = detail['status_code']
        
        # 为健康状态检查提供额外上下文
        context['healthy_status'] = health_record.healthy_status if health_record else node.healthy_status
        
        # 评估告警条件
        condition_result = evaluate_condition(rule.condition, context)
        
        if condition_result:
            # 生成告警标题和描述
            # 尝试使用聚合值，如果不可用则使用当前值
            avg_time_value = aggregated_value if aggregated_value is not None else (health_record.response_time if health_record else 0)
            
            alert_description = rule.message.format(
                node_name=node.name,
                avg_response_time=avg_time_value,
                threshold=threshold_value  # 使用从条件中提取的阈值
            )
            
            alert_subtype = rule.name.replace('_', ' ').title().replace(' ', '')
            
            create_or_update_alert(
                node=node,
                alert_type=rule.name.upper().replace('-', '_'),
                alert_subtype=alert_subtype,
                title=f"节点{rule.description}",
                description=alert_description,
                severity=rule.severity
            )
        else:
            # 条件不满足，关闭对应的告警
            close_resolved_alerts(
                node=node, 
                alert_type=rule.name.upper().replace('-', '_')
            )
            
    except Exception as e:
        color_logger.error(f"Error checking alert condition for node {node.name}: {str(e)}")


def parse_time_window(time_window_str: str) -> timedelta:
    """
    解析时间窗口字符串，例如 '5m', '10m', '1h', '1d' 等
    """
    try:
        unit = time_window_str[-1]
        value = int(time_window_str[:-1])
        
        if unit == 's':  # 秒
            return timedelta(seconds=value)
        elif unit == 'm':  # 分钟
            return timedelta(minutes=value)
        elif unit == 'h':  # 小时
            return timedelta(hours=value)
        elif unit == 'd':  # 天
            return timedelta(days=value)
        else:
            color_logger.warning(f"Unknown time unit: {unit}, defaulting to 5 minutes")
            return timedelta(minutes=5)  # 默认5分钟
    except Exception:
        color_logger.warning(f"Invalid time window format: {time_window_str}, defaulting to 5 minutes")
        return timedelta(minutes=5)


def extract_threshold_from_condition(condition: str) -> float:
    """
    从告警条件中提取阈值，例如从 "avg_response_time > 1000" 提取 1000
    """
    import re
    
    # 支持的比较操作符
    operators = ['>', '>=', '<', '<=', '==', '!=']
    
    for op in operators:
        if op in condition:
            # 使用正则表达式匹配操作符后的数字
            pattern = rf'{re.escape(op)}\s*(\d+\.?\d*)'
            match = re.search(pattern, condition)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    pass  # 如果不能转换为数值，则继续尝试其他操作符
    
    # 如果没有找到阈值，返回默认值 1000
    return 1000.0


@shared_task
def check_all_alerts():
    """
    根据配置文件中的规则检查所有告警
    """
    from .models import Node, NodeHealth
    
    # 首先处理过期的静默告警
    expire_silenced_alerts()
    
    # 获取所有启用的告警规则
    enabled_rules = alert_config_parser.get_enabled_rules()
    
    if not enabled_rules:
        color_logger.info("No enabled alert rules found")
        return
    
    # 获取所有活跃节点
    active_nodes = Node.objects.filter(is_active=True).prefetch_related('health_records')
    
    for node in active_nodes:
        # 获取最近的健康记录
        recent_health = node.health_records.first()
        
        # 对每个启用的规则进行检查
        for rule in enabled_rules:
            if rule.data_source == 'node_health':
                # 只对健康数据类型的规则处理
                check_alert_conditions(node, recent_health, rule)
    
    color_logger.info(f"Completed alert check for {len(active_nodes)} nodes with {len(enabled_rules)} rules")


def expire_silenced_alerts():
    """
    自动处理过期的静默告警
    """
    
    try:
        # 查找所有静默状态且静默时间已过期的告警
        expired_silenced_alerts = Alert.objects.filter(
            status='SILENCED',
            silenced_until__lt=timezone.now()
        )
        
        for alert in expired_silenced_alerts:
            # 如果静默期已过，将告警状态改为开放（重新激活）
            alert.status = 'OPEN'
            alert.save()
            color_logger.info(f"Reactivated alert {alert.title} after silence period expired")
            
    except Exception as e:
        color_logger.error(f"Error processing expired silenced alerts: {str(e)}")


def trigger_alert_notification(alert):
    """
    触发告警通知，包括 PushPlus 推送
    """
    try:
        # 导入 PushPlus 服务
        from .pushplus_service import PushPlusService
        
        # 创建 PushPlus 服务实例并发送告警消息
        pushplus_service = PushPlusService()
        result = pushplus_service.check_and_send_alert(alert)
        
        if result['success']:
            color_logger.info(f"PushPlus告警推送成功: {alert.title}")
        else:
            if result.get('skipped'):
                color_logger.info(f"PushPlus告警推送已跳过: {result.get('error', 'Unknown reason')}")
            else:
                color_logger.error(f"PushPlus告警推送失败: {result.get('error', 'Unknown error')}")
                
        return result
        
    except ImportError:
        color_logger.warning("PushPlus服务模块不可用，跳过推送")
        return {"success": False, "error": "PushPlus服务模块不可用"}
    except Exception as e:
        color_logger.error(f"触发告警通知异常: {str(e)}")
        return {"success": False, "error": str(e)}


