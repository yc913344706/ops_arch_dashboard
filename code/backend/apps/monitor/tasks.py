from celery import shared_task
from django.utils import timezone

from lib.time_tools import utc_obj_to_time_zone_str
from lib.redis_tool import get_redis_value, set_redis_value, delete_redis_value
from django_redis import get_redis_connection
from .models import Node, NodeHealth, Alert, SystemHealthStats
from .probes.factory import get_probe_instance
from lib.log import color_logger
from .alert_config_parser import alert_config_parser, AlertRule
import operator
from datetime import timedelta

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
def check_node_health(node_uuid, parent_task_lock_key=None):
    """
    检查单个节点健康状态
    """
    start_time = timezone.now()
    success = False  # 标记是否成功完成
    
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
            
            _record_node_health_check_duration(node_uuid, start_time)
            color_logger.info(f"Node {node.name} health check completed: unknown (no basic info)")
            success = True
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
        health_record = NodeHealth.objects.create(
            node=node,
            healthy_status=healthy_status,
            response_time=avg_response_time,
            probe_result={'details': updated_basic_info_list},
            error_message=None if healthy_status == 'green' else 'One or more checks failed',
            # 添加检查耗时到 probe_result
            create_time=timezone.now()  # 确保记录正确的创建时间
        )

        _record_node_health_check_duration(node_uuid, start_time)
        
        # 使用配置驱动的方式处理告警，而不是硬编码逻辑
        # 通过定期任务 check_all_alerts 来处理告警
        # 这样可以更灵活地管理告警规则
        
        color_logger.info(f"Node {node.name} health check completed: {healthy_status}")
        color_logger.info(f"Finish checking node health: {node_uuid}")
        success = True
        
    except Node.DoesNotExist:
        _record_node_health_check_duration(node_uuid, start_time, -1)
        color_logger.warning(f"Node with uuid {node_uuid} does not exist or is inactive")
        color_logger.info(f"Warn checking node health: {node_uuid}")
    except Exception as e:
        _record_node_health_check_duration(node_uuid, start_time, -2)
        color_logger.error(f"Error checking node health {node_uuid}: {str(e)}")
        color_logger.info(f"Error checking node health: {node_uuid}")
    finally:
        # 检查是否需要释放父任务的锁，无论成功与否都要从待处理集合中移除
        # 这样即使任务失败，也不会导致主锁永远无法释放
        if parent_task_lock_key:
            _check_and_release_parent_lock(parent_task_lock_key, node_uuid, success)

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
            # 所有节点都已完成，删除主锁和待处理集合
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
        
        # 使用 Redis 集合来管理待处理的节点 UUID
        redis_conn = get_redis_connection("default")
        
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
                # 传递锁键名到子任务，以便在子任务完成时检查是否需要释放锁
                kwargs={'parent_task_lock_key': redis_key}
            )
            scheduled_count += 1
        
        # 记录检查开始时间到一个全局位置
        SystemHealthStats.objects.update_or_create(
            key='last_node_check',
            defaults={
                'value': utc_obj_to_time_zone_str(start_time),
                'meta_info': {
                    'node_count': node_count, 
                    'start_time': utc_obj_to_time_zone_str(start_time),
                    'scheduled_count': scheduled_count,
                    'estimated_duration': estimated_duration
                }
            }
        )
        
        color_logger.info(f"Started checking {node_count} nodes health, scheduled {scheduled_count} subtasks with lock {redis_key} and pending nodes set {pending_nodes_key}, estimated duration: {estimated_duration}s")
        
        return f"Scheduled {scheduled_count} node health checks"
    
    except Exception as e:
        # 如果出错，清理 Redis 键，确保不会永久锁定
        try:
            redis_conn = get_redis_connection("default")
            redis_conn.delete(redis_key)
            pending_nodes_key = f"{redis_key}_pending_nodes"
            redis_conn.delete(pending_nodes_key)
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

        # 检查是否已存在相同告警
        existing_alert = Alert.objects.filter(
            node_id=str(node.uuid),
            alert_type=alert_type,
            alert_subtype=alert_subtype,
            status='OPEN'
        ).first()
        
        if existing_alert:
            # 更新已存在告警的最后发生时间
            existing_alert.last_occurred = timezone.now()
            existing_alert.description = description
            existing_alert.severity = severity
            existing_alert.save()
            color_logger.info(f"Updated existing alert for node {node.name}: {title}")
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
        filters = {
            'node_id': str(node.uuid),
            'status': 'OPEN'
        }
        if alert_type:
            filters['alert_type'] = alert_type
        if alert_subtype:
            filters['alert_subtype'] = alert_subtype
            
        open_alerts = Alert.objects.filter(**filters)
        
        for alert in open_alerts:
            alert.status = 'CLOSED'
            alert.resolved_at = timezone.now()
            alert.save()
            color_logger.info(f"Closed alert {alert.title} for node {node.name}")

        # 处理静默的告警，如果问题已解决，也要将静默的告警关闭
        silenced_filters = {
            'node_id': str(node.uuid),
            'status': 'SILENCED'
        }
        if alert_type:
            silenced_filters['alert_type'] = alert_type
        if alert_subtype:
            silenced_filters['alert_subtype'] = alert_subtype
            
        silenced_alerts = Alert.objects.filter(**silenced_filters)
        
        for alert in silenced_alerts:
            alert.status = 'CLOSED'
            alert.resolved_at = timezone.now()
            alert.silenced_until = timezone.now()  # 既然问题解决了，静默也应结束
            alert.save()
            color_logger.info(f"Closed silenced alert {alert.title} for node {node.name} as the issue is resolved")
            
    except Exception as e:
        color_logger.error(f"Error closing resolved alerts for node {node.name}: {str(e)}")


def check_alert_conditions(node, health_record, rule: AlertRule):
    """
    根据规则检查节点是否触发告警
    """
    try:
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


