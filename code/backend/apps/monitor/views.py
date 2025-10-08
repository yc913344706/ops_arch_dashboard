from django.views import View
from apps.monitor.tasks import check_node_health
from lib.time_tools import utc_obj_to_time_zone_str
from lib.request_tool import pub_bool_check, pub_get_request_body, pub_success_response, pub_error_response, get_request_param
from lib.paginator_tool import pub_paging_tool
from .models import Link, Node, NodeHealth, NodeConnection, Alert, SystemHealthStats
from lib.log import color_logger
from apps.myAuth.token_utils import TokenManager
from django.db.models import Q, Count, Case, When, IntegerField, Sum, F
from django.db.models.functions import RowNumber
from django.db.models.expressions import Window
from django.utils import timezone
from datetime import datetime, timedelta
from django.db.models.expressions import RawSQL

class LinkView(View):
    """架构图相关接口"""
    
    def get(self, request):
        """获取架构图列表"""
        try:
            body = pub_get_request_body(request)
            
            page = int(body.get('page', 1))
            page_size = int(body.get('page_size', 20))
            search = body.get('search', '')
            
            link_list = Link.objects.all()
            if body.get('is_active'):
                is_active = pub_bool_check(body.get('is_active', True))
                link_list = link_list.filter(is_active=is_active)
            
            # 添加搜索功能
            if search:
                link_list = link_list.filter(
                    Q(name__icontains=search) | Q(description__icontains=search)
                )
            
            # 分页查询
            has_next, next_page, page_list, all_num, result = pub_paging_tool(page, link_list, page_size)
            
            # 格式化返回数据
            result_data = []
            for link in result:
                result_data.append({
                    'uuid': str(link.uuid),
                    'name': link.name,
                    'description': link.description,
                    'is_active': link.is_active,
                    'created_by': {
                        'uuid': str(link.created_by.uuid) if link.created_by else None,
                        'username': link.created_by.username if link.created_by else None,
                        'nickname': link.created_by.nickname if link.created_by else None
                    } if link.created_by else None,
                    'create_time': utc_obj_to_time_zone_str(link.create_time),
                    'update_time': utc_obj_to_time_zone_str(link.update_time)
                })
            
            return pub_success_response({
                'has_next': has_next,
                'next_page': next_page,
                'all_num': all_num,
                'data': result_data
            })
            
        except Exception as e:
            color_logger.error(f"获取架构图列表失败: {e.args}")
            return pub_error_response(f"获取架构图列表失败: {e.args}")
    
    def post(self, request):
        """创建架构图"""
        try:
            body = pub_get_request_body(request)
            user_name = request.user_name
            
            create_keys = ['name', 'description', 'is_active']
            create_dict = {key: value for key, value in body.items() if key in create_keys}
            
            # 设置默认值
            create_dict['is_active'] = body.get('is_active', True)
            
            # 关联创建者（如果需要）
            from apps.user.models import User
            user = User.objects.filter(username=user_name).first()
            if user:
                create_dict['created_by'] = user
            
            link = Link.objects.create(**create_dict)
            
            return pub_success_response({
                'uuid': str(link.uuid),
                'name': link.name,
                'description': link.description,
                'is_active': link.is_active
            })
        except Exception as e:
            color_logger.error(f"创建架构图失败: {e.args}")
            return pub_error_response(f"创建架构图失败: {e.args}")
    
    def put(self, request):
        """更新架构图"""
        try:
            body = pub_get_request_body(request)
            
            uuid = body.get('uuid')
            assert uuid, 'uuid 不能为空'

            link = Link.objects.filter(uuid=uuid).first()
            assert link, '更新的架构图不存在'

            update_keys = ['name', 'description', 'is_active']
            update_dict = {key: value for key, value in body.items() if key in update_keys}
            
            for key, value in update_dict.items():
                setattr(link, key, value)
            link.save()

            return pub_success_response({
                'uuid': str(link.uuid),
                'name': link.name,
                'description': link.description,
                'is_active': link.is_active
            })
        except Exception as e:
            color_logger.error(f"更新架构图失败: {e.args}")
            return pub_error_response(f"更新架构图失败: {e.args}")
    
    def delete(self, request):
        """删除架构图"""
        try:
            body = pub_get_request_body(request)
            
            link = Link.objects.filter(uuid=body['uuid']).first()
            assert link, '删除的架构图不存在'
            link.delete()
            return pub_success_response()
        except Exception as e:
            color_logger.error(f"删除架构图失败: {e.args}")
            return pub_error_response(f"删除架构图失败: {e.args}")


class LinkDetailView(View):
    """单个架构图详情接口"""
    
    def get(self, request):
        """获取单个架构图详情"""
        try:
            body = pub_get_request_body(request)
            link_uuid = body.get('uuid')
            color_logger.debug(f"获取单个架构图详情: {link_uuid}")
            link = Link.objects.get(uuid=link_uuid)
            
            return pub_success_response({
                'uuid': str(link.uuid),
                'name': link.name,
                'description': link.description,
                'is_active': link.is_active,
                'create_time': link.create_time.isoformat() if link.create_time else None,
                'update_time': link.update_time.isoformat() if link.update_time else None
            })
        except Link.DoesNotExist:
            return pub_error_response("架构图不存在")
        except Exception as e:
            color_logger.error(f"获取架构图详情失败: {e.args}")
            return pub_error_response(f"获取架构图详情失败: {e.args}")


class LinkTopologyView(View):
    """架构图拓扑接口"""
    
    def get(self, request):
        """获取架构图拓扑"""
        try:
            body = pub_get_request_body(request)
            link_uuid = body.get('uuid')
            link = Link.objects.get(uuid=link_uuid)
            nodes = Node.objects.filter(link=link, is_active=True)
            connections = NodeConnection.objects.filter(link=link, is_active=True)

            # 构建节点数据
            nodes_data = []
            for node in nodes:
                nodes_data.append({
                    'uuid': str(node.uuid),
                    'name': node.name,
                    'basic_info_list': node.basic_info_list,
                    'healthy_status': node.healthy_status,
                    'position_x': node.position_x,
                    'position_y': node.position_y,
                    'create_time': node.create_time.isoformat() if node.create_time else None
                })

            # 构建连接数据
            connections_data = []
            for conn in connections:
                connections_data.append({
                    'uuid': str(conn.uuid),
                    'from_node': str(conn.from_node.uuid),
                    'to_node': str(conn.to_node.uuid),
                    'healthy_status': conn.from_node.healthy_status,
                })

            return pub_success_response({
                'uuid': str(link.uuid),
                'name': link.name,
                'nodes': nodes_data,
                'connections': connections_data
            })
        except Link.DoesNotExist:
            return pub_error_response("架构图不存在")
        except Exception as e:
            color_logger.error(f"获取架构图拓扑失败: {e.args}")
            return pub_error_response(f"获取架构图拓扑失败: {e.args}")


class NodeView(View):
    """节点相关接口"""
    
    def get(self, request):
        """获取节点列表"""

        try:
            body = pub_get_request_body(request)
            
            page = int(body.get('page', 1))
            page_size = int(body.get('page_size', 20))
            search = body.get('search', '')
            link_id = body.get('link_id', '')
            healthy_status = body.get('healthy_status', '')
            
            node_list = Node.objects.all()
            
            # 添加搜索功能 - 同时按节点名称和basic_info_list中的内容搜索
            if search:
                node_list = node_list.annotate(
                    hosts_str=RawSQL(
                        "JSON_UNQUOTE(JSON_EXTRACT(basic_info_list, '$[*].host'))", []
                    ),
                    port_str=RawSQL(
                        "JSON_UNQUOTE(JSON_EXTRACT(basic_info_list, '$[*].port'))", []
                    )
                ).filter(
                    Q(name__icontains=search) |
                    Q(hosts_str__icontains=search) |
                    Q(port_str__icontains=search)
                )
            
            # 按健康状态过滤
            if healthy_status:
                node_list = node_list.filter(healthy_status=healthy_status)
            
            # 按架构图过滤
            if link_id:
                node_list = node_list.filter(link_id=link_id)
            
            # 分页查询
            has_next, next_page, page_list, all_num, result = pub_paging_tool(page, node_list, page_size)
            
            # 格式化返回数据
            result_data = []
            for node in result:
                # 获取此节点的检查耗时统计
                from .models import SystemHealthStats
                duration_stat = SystemHealthStats.objects.filter(
                    key=f'node_check_duration_{node.uuid}'
                ).first()
                
                result_data.append({
                    'uuid': str(node.uuid),
                    'name': node.name,
                    'basic_info_list': node.basic_info_list,
                    'link': {
                        'uuid': str(node.link.uuid),
                        'name': node.link.name
                    },
                    'is_active': node.is_active,
                    'healthy_status': node.healthy_status,
                    'position_x': node.position_x,
                    'position_y': node.position_y,
                    'create_time': utc_obj_to_time_zone_str(node.create_time),
                    'update_time': utc_obj_to_time_zone_str(node.update_time),
                    'last_check_time': utc_obj_to_time_zone_str(node.last_check_time) if node.last_check_time else None,
                    'check_duration_ms': float(duration_stat.value) if duration_stat else None,
                })
            
            return pub_success_response({
                'has_next': has_next,
                'next_page': next_page,
                'all_num': all_num,
                'data': result_data
            })
            
        except Exception as e:
            color_logger.error(f"获取节点列表失败: {e.args}")
            return pub_error_response(f"获取节点列表失败: {e.args}")
    
    def post(self, request):
        """创建节点"""

        try:
            body = pub_get_request_body(request)
            
            create_keys = ['name', 'basic_info_list', 'link', 'is_active', 'position_x', 'position_y']
            create_dict = {key: value for key, value in body.items() if key in create_keys}
            
            # 设置默认值
            create_dict['is_active'] = body.get('is_active', True)
            create_dict['basic_info_list'] = body.get('basic_info_list', [])
            
            # 关联架构图
            from .models import Link
            link = Link.objects.filter(uuid=body.get('link')).first()
            if link:
                create_dict['link'] = link
            else:
                return pub_error_response("架构图不存在")
            
            node = Node.objects.create(**create_dict)
            
            return pub_success_response({
                'uuid': str(node.uuid),
                'name': node.name,
                'basic_info_list': node.basic_info_list,
                'link': str(node.link.uuid),
                'is_active': node.is_active
            })
        except Exception as e:
            color_logger.error(f"创建节点失败: {e.args}")
            return pub_error_response(f"创建节点失败: {e.args}")
    
    def put(self, request):
        """更新节点"""

        try:
            body = pub_get_request_body(request)
            
            uuid = body.get('uuid')
            assert uuid, 'uuid 不能为空'

            node = Node.objects.filter(uuid=uuid).first()
            assert node, '更新的节点不存在'

            update_keys = ['name', 'basic_info_list', 'is_active', 'position_x', 'position_y']
            update_dict = {key: value for key, value in body.items() if key in update_keys}
            
            # 处理basic_info_list
            if 'basic_info_list' in body:
                update_dict['basic_info_list'] = body['basic_info_list']
            
            for key, value in update_dict.items():
                setattr(node, key, value)
            node.save()
            
            # 尝试触发健康检查任务，但即使失败也不影响API响应
            try:
                check_node_health.delay(node.uuid)
            except Exception as e:
                color_logger.error(f"触发节点健康检查任务失败: {e.args}", exc_info=True)
                # 不中断主流程，只是记录错误

            return pub_success_response({
                'uuid': str(node.uuid),
                'name': node.name,
                'basic_info_list': node.basic_info_list,
                'is_active': node.is_active
            })
        except Exception as e:
            color_logger.error(f"更新节点失败: {e.args}", exc_info=True)
            return pub_error_response(f"更新节点失败: {e.args}")
    
    def delete(self, request):
        """删除节点"""

        try:
            body = pub_get_request_body(request)
            
            node = Node.objects.filter(uuid=body['uuid']).first()
            assert node, '删除的节点不存在'
            node.delete()
            return pub_success_response()
        except Exception as e:
            color_logger.error(f"删除节点失败: {e.args}")
            return pub_error_response(f"删除节点失败: {e.args}")


class NodeConnectionView(View):
    """节点连接相关接口"""
    
    def get(self, request):
        """获取连接列表"""

        try:
            body = pub_get_request_body(request)
            
            page = int(body.get('page', 1))
            page_size = int(body.get('page_size', 20))
            link_id = body.get('link_id', '')
            from_node_id = body.get('from_node_id', '')
            to_node_id = body.get('to_node_id', '')
            
            connection_list = NodeConnection.objects.all()
            
            # 按架构图过滤
            if link_id:
                connection_list = connection_list.filter(link_id=link_id)
            
            # 按起始节点过滤
            if from_node_id:
                connection_list = connection_list.filter(from_node_id=from_node_id)
            
            # 按目标节点过滤
            if to_node_id:
                connection_list = connection_list.filter(to_node_id=to_node_id)
            
            # 分页查询
            has_next, next_page, page_list, all_num, result = pub_paging_tool(page, connection_list, page_size)
            
            # 格式化返回数据
            result_data = []
            for conn in result:
                result_data.append({
                    'uuid': str(conn.uuid),
                    'from_node': {
                        'uuid': str(conn.from_node.uuid),
                        'name': conn.from_node.name
                    },
                    'to_node': {
                        'uuid': str(conn.to_node.uuid),
                        'name': conn.to_node.name
                    },
                    'link': {
                        'uuid': str(conn.link.uuid),
                        'name': conn.link.name
                    },
                    'is_active': conn.is_active,
                    'create_time': conn.create_time.isoformat() if conn.create_time else None
                })
            
            return pub_success_response({
                'has_next': has_next,
                'next_page': next_page,
                'all_num': all_num,
                'data': result_data
            })
            
        except Exception as e:
            color_logger.error(f"获取连接列表失败: {e.args}")
            return pub_error_response(f"获取连接列表失败: {e.args}")
    
    def post(self, request):
        """创建连接"""

        try:
            body = pub_get_request_body(request)
            
            from_node_id = body.get('from_node')
            to_node_id = body.get('to_node')
            link_id = body.get('link')
            
            # 验证必填字段
            assert from_node_id, '起始节点不能为空'
            assert to_node_id, '目标节点不能为空'
            assert link_id, '架构图不能为空'
            
            # 验证节点和架构图是否存在
            from apps.user.models import User
            from_node = Node.objects.filter(uuid=from_node_id).first()
            to_node = Node.objects.filter(uuid=to_node_id).first()
            link = Link.objects.filter(uuid=link_id).first()
            
            assert from_node, '起始节点不存在'
            assert to_node, '目标节点不存在'
            assert link, '架构图不存在'
            
            # 创建连接
            connection = NodeConnection.objects.create(
                from_node=from_node,
                to_node=to_node,
                link=link
            )
            
            return pub_success_response({
                'uuid': str(connection.uuid),
                'from_node': str(connection.from_node.uuid),
                'to_node': str(connection.to_node.uuid),
                'link': str(connection.link.uuid)
            })
        except Exception as e:
            color_logger.error(f"创建连接失败: {e.args}")
            return pub_error_response(f"创建连接失败: {e.args}")
    
    def put(self, request):
        """更新连接"""

        try:
            body = pub_get_request_body(request)
            
            uuid = body.get('uuid')
            assert uuid, 'uuid 不能为空'

            connection = NodeConnection.objects.filter(uuid=uuid).first()
            assert connection, '更新的连接不存在'

            is_active = body.get('is_active')
            if is_active is not None:
                connection.is_active = is_active
                
            connection.save()

            return pub_success_response({
                'uuid': str(connection.uuid),
                'from_node': str(connection.from_node.uuid),
                'to_node': str(connection.to_node.uuid),
                'is_active': connection.is_active
            })
        except Exception as e:
            color_logger.error(f"更新连接失败: {e.args}")
            return pub_error_response(f"更新连接失败: {e.args}")
    
    def delete(self, request):
        """删除连接"""

        try:
            body = pub_get_request_body(request)
            
            connection = NodeConnection.objects.filter(uuid=body['uuid']).first()
            assert connection, '删除的连接不存在'
            connection.real_delete()
            return pub_success_response()
        except Exception as e:
            color_logger.error(f"删除连接失败: {e.args}")
            return pub_error_response(f"删除连接失败: {e.args}")


class NodeHealthView(View):
    """节点健康状态接口"""
    
    def get(self, request):
        """获取节点健康状态"""
        try:
            body = pub_get_request_body(request)
            node_uuid = body.get('uuid')
            node = Node.objects.get(uuid=node_uuid)
            latest_health = node.health_records.first()  # 获取最新健康记录

            # 获取此节点的检查耗时统计
            from .models import SystemHealthStats
            duration_stat = SystemHealthStats.objects.filter(
                key=f'node_check_duration_{node_uuid}'
            ).first()

            if latest_health:
                data = {
                    'uuid': str(node.uuid),
                    'name': node.name,
                    'healthy_status': latest_health.healthy_status,
                    'response_time': latest_health.response_time,
                    'last_check_time': latest_health.create_time.isoformat() if latest_health.create_time else None,
                    'probe_result': latest_health.probe_result,
                    'error_message': latest_health.error_message,
                    'check_duration_ms': float(duration_stat.value) if duration_stat else None,
                    'check_duration_info': duration_stat.meta_info if duration_stat else None
                }
            else:
                # 如果没有健康记录，使用节点的当前状态
                data = {
                    'uuid': str(node.uuid),
                    'name': node.name,
                    'healthy_status': node.healthy_status,
                    'response_time': None,
                    'last_check_time': node.last_check_time.isoformat() if node.last_check_time else None,
                    'probe_result': {},
                    'error_message': None,
                    'check_duration_ms': float(duration_stat.value) if duration_stat else None,
                    'check_duration_info': duration_stat.meta_info if duration_stat else None
                }

            return pub_success_response(data)
        except Node.DoesNotExist:
            return pub_error_response("节点不存在")
        except Exception as e:
            color_logger.error(f"获取节点健康状态失败: {e.args}")
            return pub_error_response(f"获取节点健康状态失败: {e.args}")


class AlertView(View):
    """告警相关接口"""
    
    def get(self, request):
        """获取告警列表"""
        try:
            body = pub_get_request_body(request)
            
            page = int(body.get('page', 1))
            page_size = int(body.get('page_size', 20))
            search = body.get('search', '')
            status = body.get('status', '')
            severity = body.get('severity', '')
            node_id = body.get('node_id', '')
            alert_type = body.get('alert_type', '')
            
            alert_list = Alert.objects.all()
            
            # 添加搜索功能
            if search:
                alert_list = alert_list.filter(
                    Q(title__icontains=search) | Q(description__icontains=search)
                )
            
            # 按状态过滤
            if status:
                alert_list = alert_list.filter(status=status)
            
            # 按严重程度过滤
            if severity:
                alert_list = alert_list.filter(severity=severity)
            
            # 按节点ID过滤
            if node_id:
                alert_list = alert_list.filter(node_id=node_id)
            
            # 按告警类型过滤
            if alert_type:
                alert_list = alert_list.filter(alert_type=alert_type)
            
            # 分页查询
            has_next, next_page, page_list, all_num, result = pub_paging_tool(page, alert_list, page_size)
            
            # 格式化返回数据
            result_data = []
            for alert in result:
                node = Node.objects.filter(uuid=alert.node_id).first()
                result_data.append({
                    'uuid': str(alert.uuid),
                    'node_id': alert.node_id,
                    'node_name': node.name if node else None,
                    'alert_type': alert.alert_type,
                    'alert_subtype': alert.alert_subtype,
                    'title': alert.title,
                    'description': alert.description,
                    'status': alert.status,
                    'severity': alert.severity,
                    'first_occurred': utc_obj_to_time_zone_str(alert.first_occurred),
                    'last_occurred': utc_obj_to_time_zone_str(alert.last_occurred),
                    'resolved_at': utc_obj_to_time_zone_str(alert.resolved_at) if alert.resolved_at else None,
                    'silenced_at': utc_obj_to_time_zone_str(alert.silenced_at) if alert.silenced_at else None,
                    'silenced_until': utc_obj_to_time_zone_str(alert.silenced_until) if alert.silenced_until else None,
                    'silenced_reason': alert.silenced_reason,
                    'created_by': {
                        'uuid': str(alert.created_by.uuid) if alert.created_by else None,
                        'username': alert.created_by.username if alert.created_by else None,
                        'nickname': alert.created_by.nickname if alert.created_by else None
                    } if alert.created_by else None,
                    'silenced_by': {
                        'uuid': str(alert.silenced_by.uuid) if alert.silenced_by else None,
                        'username': alert.silenced_by.username if alert.silenced_by else None,
                        'nickname': alert.silenced_by.nickname if alert.silenced_by else None
                    } if alert.silenced_by else None
                })
            
            return pub_success_response({
                'has_next': has_next,
                'next_page': next_page,
                'all_num': all_num,
                'data': result_data
            })
            
        except Exception as e:
            color_logger.error(f"获取告警列表失败: {e.args}")
            return pub_error_response(f"获取告警列表失败: {e.args}")
    
    def post(self, request):
        """创建或更新告警（如果相同的告警已存在则更新）"""
        try:
            body = pub_get_request_body(request)
            
            # 检查是否已存在相同告警
            existing_alert = Alert.objects.filter(
                node_id=body.get('node_id'),
                alert_type=body.get('alert_type', ''),
                alert_subtype=body.get('alert_subtype', ''),
                status='OPEN'
            ).first()
            
            if existing_alert:
                # 更新已存在告警的最后发生时间
                existing_alert.last_occurred = timezone.now()
                existing_alert.description = body.get('description', existing_alert.description)
                existing_alert.severity = body.get('severity', existing_alert.severity)
                existing_alert.save()
                
                return pub_success_response({
                    'uuid': str(existing_alert.uuid),
                    'node_id': existing_alert.node_id,
                    'alert_type': existing_alert.alert_type,
                    'alert_subtype': existing_alert.alert_subtype,
                    'title': existing_alert.title,
                    'description': existing_alert.description,
                    'status': existing_alert.status,
                    'severity': existing_alert.severity,
                    'first_occurred': utc_obj_to_time_zone_str(existing_alert.first_occurred),
                    'last_occurred': utc_obj_to_time_zone_str(existing_alert.last_occurred)
                })
            else:
                # 创建新告警
                create_keys = ['node_id', 'alert_type', 'alert_subtype', 'title', 'description', 'severity']
                create_dict = {key: value for key, value in body.items() if key in create_keys}
                
                # 设置默认值
                create_dict['severity'] = body.get('severity', 'MEDIUM')
                create_dict['status'] = 'OPEN'
                
                # 关联创建者（如果需要）
                user_name = getattr(request, 'user_name', None)
                if user_name:
                    from apps.user.models import User
                    user = User.objects.filter(username=user_name).first()
                    if user:
                        create_dict['created_by'] = user
                
                alert = Alert.objects.create(**create_dict)
                
                return pub_success_response({
                    'uuid': str(alert.uuid),
                    'node_id': alert.node_id,
                    'alert_type': alert.alert_type,
                    'alert_subtype': alert.alert_subtype,
                    'title': alert.title,
                    'description': alert.description,
                    'status': alert.status,
                    'severity': alert.severity
                })
        except Exception as e:
            color_logger.error(f"创建告警失败: {e.args}")
            return pub_error_response(f"创建告警失败: {e.args}")
    
    def put(self, request):
        """更新告警状态（关闭或静默）"""
        try:
            body = pub_get_request_body(request)
            
            uuid = body.get('uuid')
            assert uuid, 'uuid 不能为空'

            alert = Alert.objects.filter(uuid=uuid).first()
            assert alert, '告警不存在'

            # 更新状态
            new_status = body.get('status')
            if new_status in ['CLOSED', 'SILENCED']:
                if new_status == 'CLOSED':
                    alert.status = 'CLOSED'
                    alert.resolved_at = timezone.now()
                elif new_status == 'SILENCED':
                    # 静默操作需要静默时长和原因
                    silence_duration = body.get('silence_duration')
                    silence_reason = body.get('silence_reason')
                    assert silence_duration is not None, '静默时长不能为空'
                    assert silence_reason is not None and silence_reason.strip() != '', '静默原因不能为空'
                    
                    alert.status = 'SILENCED'
                    alert.silenced_at = timezone.now()
                    # 根据静默时长计算结束时间 (静默时长单位为秒)
                    alert.silenced_until = timezone.now() + timedelta(seconds=int(silence_duration))
                    alert.silenced_reason = silence_reason
                    
                    # 关联静默人
                    user_name = getattr(request, 'user_name', None)
                    if user_name:
                        from apps.user.models import User
                        user = User.objects.filter(username=user_name).first()
                        if user:
                            alert.silenced_by = user

                alert.save()

            return pub_success_response({
                'uuid': str(alert.uuid),
                'status': alert.status
            })
        except AssertionError as e:
            return pub_error_response(str(e))
        except Exception as e:
            color_logger.error(f"更新告警失败: {e.args}")
            return pub_error_response(f"更新告警失败: {e.args}")
    
    def delete(self, request):
        """删除告警"""
        try:
            body = pub_get_request_body(request)
            
            alert = Alert.objects.filter(uuid=body['uuid']).first()
            assert alert, '告警不存在'
            alert.delete()
            return pub_success_response()
        except Exception as e:
            color_logger.error(f"删除告警失败: {e.args}")
            return pub_error_response(f"删除告警失败: {e.args}")


class AlertDetailView(View):
    """单个告警详情接口"""
    
    def get(self, request):
        """获取单个告警详情"""
        try:
            body = pub_get_request_body(request)
            alert_uuid = body.get('uuid')
            color_logger.debug(f"获取单个告警详情: {alert_uuid}")
            alert = Alert.objects.get(uuid=alert_uuid)
            
            return pub_success_response({
                'uuid': str(alert.uuid),
                'node_id': alert.node_id,
                'alert_type': alert.alert_type,
                'alert_subtype': alert.alert_subtype,
                'title': alert.title,
                'description': alert.description,
                'status': alert.status,
                'severity': alert.severity,
                'first_occurred': alert.first_occurred.isoformat() if alert.first_occurred else None,
                'last_occurred': alert.last_occurred.isoformat() if alert.last_occurred else None,
                'resolved_at': alert.resolved_at.isoformat() if alert.resolved_at else None,
                'silenced_at': alert.silenced_at.isoformat() if alert.silenced_at else None,
                'silenced_until': alert.silenced_until.isoformat() if alert.silenced_until else None,
                'silenced_reason': alert.silenced_reason,
                'created_by': {
                    'uuid': str(alert.created_by.uuid) if alert.created_by else None,
                    'username': alert.created_by.username if alert.created_by else None,
                    'nickname': alert.created_by.nickname if alert.created_by else None
                } if alert.created_by else None,
                'silenced_by': {
                    'uuid': str(alert.silenced_by.uuid) if alert.silenced_by else None,
                    'username': alert.silenced_by.username if alert.silenced_by else None,
                    'nickname': alert.silenced_by.nickname if alert.silenced_by else None
                } if alert.silenced_by else None
            })
        except Alert.DoesNotExist:
            return pub_error_response("告警不存在")
        except Exception as e:
            color_logger.error(f"获取告警详情失败: {e.args}")
            return pub_error_response(f"获取告警详情失败: {e.args}")
    
    def put(self, request):
        """更新告警状态（关闭或静默）"""
        try:
            body = pub_get_request_body(request)
            
            uuid = body.get('uuid')
            assert uuid, 'uuid 不能为空'

            alert = Alert.objects.filter(uuid=uuid).first()
            assert alert, '告警不存在'

            # 更新状态
            new_status = body.get('status')
            if new_status in ['CLOSED', 'SILENCED']:
                if new_status == 'CLOSED':
                    alert.status = 'CLOSED'
                    alert.resolved_at = timezone.now()
                elif new_status == 'SILENCED':
                    # 静默操作需要静默时长和原因
                    silence_duration = body.get('silence_duration')
                    silence_reason = body.get('silence_reason')
                    assert silence_duration is not None, '静默时长不能为空'
                    assert silence_reason is not None and silence_reason.strip() != '', '静默原因不能为空'
                    
                    alert.status = 'SILENCED'
                    alert.silenced_at = timezone.now()
                    # 根据静默时长计算结束时间 (静默时长单位为秒)
                    alert.silenced_until = timezone.now() + timedelta(seconds=int(silence_duration))
                    alert.silenced_reason = silence_reason
                    
                    # 关联静默人
                    user_name = getattr(request, 'user_name', None)
                    if user_name:
                        from apps.user.models import User
                        user = User.objects.filter(username=user_name).first()
                        if user:
                            alert.silenced_by = user

                alert.save()

            return pub_success_response({
                'uuid': str(alert.uuid),
                'status': alert.status
            })
        except AssertionError as e:
            return pub_error_response(str(e))
        except Exception as e:
            color_logger.error(f"更新告警失败: {e.args}")
            return pub_error_response(f"更新告警失败: {e.args}")


class AlertTypesView(View):
    """告警类型接口"""
    
    def get(self, request):
        """获取所有告警类型"""
        try:
            # 从配置文件获取所有告警类型
            from apps.monitor.alert_config_parser import alert_config_parser
            alert_types_with_desc = []
            
            # 使用配置解析器获取告警类型映射
            type_mapping = alert_config_parser.get_alert_type_mapping()
            for alert_type, description in type_mapping.items():
                alert_types_with_desc.append({
                    'value': alert_type,
                    'label': description
                })
            
            return pub_success_response({
                'alert_types': alert_types_with_desc
            })
        except Exception as e:
            color_logger.error(f"获取告警类型失败: {e.args}")
            return pub_error_response(f"获取告警类型失败: {e.args}")


class SystemHealthStatsView(View):
    """系统健康统计信息接口"""
    
    def get(self, request):
        """获取系统健康统计信息"""
        try:
            body = pub_get_request_body(request)
            
            # 获取指定键的统计信息，或者获取所有统计信息
            key = body.get('key')
            
            if key:
                # 获取特定键的统计信息
                try:
                    stat = SystemHealthStats.objects.get(key=key)
                    return pub_success_response({
                        'key': stat.key,
                        'value': stat.value,
                        'meta_info': stat.meta_info,
                        'create_time': utc_obj_to_time_zone_str(stat.create_time),
                        'update_time': utc_obj_to_time_zone_str(stat.update_time)
                    })
                except SystemHealthStats.DoesNotExist:
                    return pub_error_response(f"统计信息不存在: {key}")
            else:
                # 获取所有统计信息（按需获取特定类型的统计）
                stats = SystemHealthStats.objects.all()
                
                # 过滤出节点检查相关的统计
                last_check_stats = stats.filter(key='last_node_check').first()
                all_node_durations = stats.filter(key__startswith='node_check_duration_')
                
                result = {
                    'last_node_check': None,
                    'node_check_durations': [],
                    'total_nodes_checked': 0,
                    'total_check_duration': 0,  # 总耗时（毫秒）
                    'last_check_time': None
                }
                
                if last_check_stats:
                    result['last_node_check'] = {
                        'value': last_check_stats.value,
                        'meta_info': last_check_stats.meta_info,
                        'create_time': utc_obj_to_time_zone_str(last_check_stats.create_time),
                        'update_time': utc_obj_to_time_zone_str(last_check_stats.update_time)
                    }
                    # 从meta_info中获取时间
                    if last_check_stats.meta_info and 'start_time' in last_check_stats.meta_info:
                        result['last_check_time'] = last_check_stats.meta_info['start_time']
                
                # 计算所有节点检查的总耗时：取所有节点检查耗时的最大值，近似并行执行的总耗时
                if all_node_durations.exists():
                    max_duration = 0
                    node_durations = []
                    
                    for stat in all_node_durations:
                        try:
                            if stat.value:
                                duration = float(stat.value)
                                node_durations.append({
                                    'key': stat.key,
                                    'value': stat.value,
                                    'meta_info': stat.meta_info,
                                    'create_time': utc_obj_to_time_zone_str(stat.create_time),
                                    'update_time': utc_obj_to_time_zone_str(stat.update_time)
                                })
                                max_duration = max(max_duration, duration)
                        except ValueError:
                            pass  # 如果值不能转换为数字，跳过
                    
                    result['node_check_durations'] = node_durations
                    result['total_nodes_checked'] = len(node_durations)
                    
                    # 使用最大耗时作为并行执行的近似总耗时
                    result['total_check_duration'] = max_duration
                else:
                    result['total_nodes_checked'] = 0
                    result['total_check_duration'] = 0
                
                return pub_success_response(result)
                
        except Exception as e:
            color_logger.error(f"获取系统健康统计信息失败: {e.args}")
            return pub_error_response(f"获取系统健康统计信息失败: {e.args}")


class MonitorDashboardView(View):
    """监控仪表板统计信息接口"""
    
    def get(self, request):
        """获取监控仪表板统计信息"""
        try:
            body = pub_get_request_body(request)
            
            # 获取筛选参数
            period = body.get('period', 'week')  # 默认为周
            start_date = body.get('start_date')
            end_date = body.get('end_date')
            
            # 基础统计信息
            summary_data = self.get_summary_statistics()
            
            # 健康趋势数据
            health_trend_data = self.get_health_trend_data(period, start_date, end_date)
            
            # 最近告警数据
            recent_alerts = self.get_recent_alerts()
            
            return pub_success_response({
                'summary': summary_data,
                'health_trend': health_trend_data,
                'recent_alerts': recent_alerts
            })
        except Exception as e:
            color_logger.error(f"获取监控仪表板数据失败: {e.args}")
            return pub_error_response(f"获取监控仪表板数据失败: {e.args}")
    
    def get_summary_statistics(self):
        """获取概要统计信息"""
        # 链路统计
        total_links = Link.objects.count()
        # 假设健康链路是包含至少一个健康节点的链路
        links_with_healthy_nodes = Link.objects.filter(
            nodes__healthy_status='green',
            nodes__is_active=True
        ).distinct().count()
        
        # 节点统计
        total_nodes = Node.objects.count()
        healthy_nodes = Node.objects.filter(healthy_status='green', is_active=True).count()
        yellow_nodes = Node.objects.filter(healthy_status='yellow', is_active=True).count()  # 部分异常
        red_nodes = Node.objects.filter(healthy_status='red', is_active=True).count()  # 异常
        unknown_nodes = Node.objects.filter(healthy_status='unknown', is_active=True).count()  # 未知
        
        return {
            'total_links': total_links,
            'healthy_links': links_with_healthy_nodes,
            'total_nodes': total_nodes,
            'healthy_nodes': healthy_nodes,
            'yellow_nodes': yellow_nodes,  # 部分异常节点
            'red_nodes': red_nodes,  # 异常节点
            'unknown_nodes': unknown_nodes,  # 未知节点
            'unhealthy_nodes': yellow_nodes + red_nodes  # 不健康节点（黄色+红色）
        }
    
    def get_health_trend_data(self, period='week', start_date=None, end_date=None):
        """获取健康趋势数据"""
        # 根据周期参数确定时间范围
        now = timezone.now()
        if start_date and end_date:
            # 使用传入的日期范围
            start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            # 转换为本地时区时间
            start_date = timezone.localtime(timezone.make_aware(start_date)) if start_date.tzinfo is None else timezone.localtime(start_date)
            end_date = timezone.localtime(timezone.make_aware(end_date)) if end_date.tzinfo is None else timezone.localtime(end_date)
        else:
            # 根据周期参数确定时间范围
            if period == 'day':
                # 对于日周期，从24小时前开始到当前时间
                start_date = timezone.localtime(now) - timedelta(days=1)
            elif period == 'week':
                start_date = timezone.localtime(now) - timedelta(weeks=1)
            elif period == 'month':
                start_date = timezone.localtime(now) - timedelta(days=30)
            elif period == 'quarter':
                start_date = timezone.localtime(now) - timedelta(days=90)
            elif period == 'year':
                start_date = timezone.localtime(now) - timedelta(days=365)
            else:
                # 默认为周
                start_date = timezone.localtime(now) - timedelta(weeks=1)
            end_date = timezone.localtime(now)
        
        # 生成时间序列
        # 确定间隔以生成适当数量的数据点
        time_points = []
        if period == 'day':
            # 按小时统计，生成从24小时前到当前时间的整点时间点
            # 例如：如果现在是10月8日10:52，则时间点为昨天10月7日11:00 到 今天10月8日10:00
            # 计算开始整点（24小时前的整点）和结束整点（当前时间的整点）
            start_hour_point = start_date.replace(minute=0, second=0, microsecond=0)
            end_hour_point = end_date.replace(minute=0, second=0, microsecond=0)
            
            current_hour = start_hour_point
            while current_hour <= end_hour_point:
                time_points.append(current_hour)
                current_hour += timedelta(hours=1)
        elif period == 'week':
            # 按天统计
            current_date = start_date.date()
            end_date_date = end_date.date()
            while current_date <= end_date_date:
                time_point = timezone.make_aware(datetime.combine(current_date, datetime.min.time()))
                time_points.append(time_point.date())  # 保持原格式
                current_date += timedelta(days=1)
        elif period == 'month':
            # 按天统计
            current_date = start_date.date()
            end_date_date = end_date.date()
            while current_date <= end_date_date:
                time_points.append(current_date)
                current_date += timedelta(days=1)
        elif period == 'quarter':
            # 按周统计 - 从周一作为一周的开始
            current_date = start_date.date()
            # 将开始日期调整为当周的周一
            current_date = current_date - timedelta(days=current_date.weekday())
            end_date_date = end_date.date()
            while current_date <= end_date_date:
                time_points.append(current_date)
                current_date += timedelta(weeks=1)
        else:  # year
            # 按月统计
            current_date = start_date.date()
            end_date_date = end_date.date()
            while current_date <= end_date_date:
                time_points.append(current_date)
                # 移动到下个月 - 确保日期有效
                if current_date.month == 12:
                    current_date = current_date.replace(year=current_date.year + 1, month=1)
                else:
                    # 尝试简单递增月份
                    try:
                        current_date = current_date.replace(month=current_date.month + 1)
                    except ValueError:
                        # 处理像1月31日 -> 2月31日这样的无效日期
                        # 移动到下个月的最后一天
                        if current_date.month == 1:  # 跳过2月到3月
                            current_date = current_date.replace(day=28, month=2)
                        else:  # 其他月份
                            next_month = current_date.month + 1
                            if next_month in [4, 6, 9, 11]:  # 30天的月份
                                current_date = current_date.replace(day=30, month=next_month)
                            else:  # 31天的月份
                                current_date = current_date.replace(day=31, month=next_month)
        
        # 获取健康数据
        trend_data = []
        for i, time_point in enumerate(time_points):
            if period == 'day':
                # 按小时统计，时间段从当前整点开始，到下一个整点或实际结束时间
                start_time = time_point
                next_hour = time_point + timedelta(hours=1)
                
                # 如果下一整点超过实际的结束时间，使用实际结束时间
                if next_hour > end_date:
                    end_time = end_date
                else:
                    end_time = next_hour
            elif period == 'week':
                # 按天统计
                start_time = timezone.make_aware(datetime.combine(time_point, datetime.min.time()))
                end_time = start_time + timedelta(days=1)
            elif period == 'month':
                # 按天统计
                start_time = timezone.make_aware(datetime.combine(time_point, datetime.min.time()))
                end_time = start_time + timedelta(days=1)
            elif period == 'quarter':
                # 按周统计 - 从当前日期到下一周的同一天
                start_time = timezone.make_aware(datetime.combine(time_point, datetime.min.time()))
                end_time = start_time + timedelta(weeks=1)
            else:  # year, 按月统计
                # 对于月份，需要正确处理月份跨越
                start_time = timezone.make_aware(datetime.combine(time_point, datetime.min.time()))
                
                # 计算下一个月的对应日期
                if time_point.month == 12:
                    next_month_date = time_point.replace(year=time_point.year + 1, month=1)
                else:
                    try:
                        next_month_date = time_point.replace(month=time_point.month + 1)
                    except ValueError:  # 处理如1月31日到2月31日无效日期
                        # 将日期调整为下个月的最后一天
                        if time_point.month == 1:  # 跳到2月
                            if (time_point.year % 4 == 0 and time_point.year % 100 != 0) or time_point.year % 400 == 0:
                                next_month_date = time_point.replace(day=29, month=2)
                            else:
                                next_month_date = time_point.replace(day=28, month=2)
                        elif time_point.month in [3, 5, 8, 10]:  # 30天的月份 (原为4,6,9,11，但3/5/8/10月只有30天)
                            next_month_date = time_point.replace(day=30, month=time_point.month + 1)
                        else:  # 31天的月份，且该月份只有30天
                            next_month_date = time_point.replace(day=30, month=time_point.month + 1)
                
                end_time = timezone.make_aware(datetime.combine(next_month_date, datetime.min.time()))
            
            # 获取时间段内的所有健康记录
            records_in_period = NodeHealth.objects.filter(
                create_time__gte=start_time,
                create_time__lt=end_time
            )
            
            # 按节点ID分组，找出每个节点在时间段内的最高优先级状态
            node_highest_status = {}
            status_priority = {'red': 3, 'yellow': 2, 'unknown': 1, 'green': 0}
            
            for record in records_in_period:
                node_id = record.node_id
                current_status = record.healthy_status
                
                # 如果节点还没有记录，或者当前状态优先级更高，则更新
                if node_id not in node_highest_status or \
                   status_priority[current_status] > status_priority[node_highest_status[node_id]]:
                    node_highest_status[node_id] = current_status
            
            # 统计没有健康记录的活跃节点，使用节点的当前状态
            all_node_ids_in_records = set(node_highest_status.keys())
            nodes_without_records = Node.objects.filter(
                is_active=True
            ).exclude(uuid__in=all_node_ids_in_records)
            
            for node in nodes_without_records:
                node_highest_status[node.uuid] = node.healthy_status
            
            # 按状态统计数量
            from collections import Counter
            status_counts = Counter(node_highest_status.values())
            
            trend_data.append({
                'date': time_point.isoformat() if isinstance(time_point, datetime) else str(time_point),
                'green_count': status_counts['green'],
                'yellow_count': status_counts['yellow'],
                'red_count': status_counts['red'],
                'unknown_count': status_counts['unknown']
            })
        
        return {
            'period': period,
            'data': trend_data
        }
    
    def get_recent_alerts(self):
        """获取最近告警"""
        # 按状态和时间排序
        # 状态优先级：OPEN > SILENCED > CLOSED
        # 时间：新到老
        recent_alerts = Alert.objects.extra(
            select={
                'status_order': "CASE WHEN status='OPEN' THEN 3 WHEN status='SILENCED' THEN 2 WHEN status='CLOSED' THEN 1 ELSE 0 END"
            }
        ).order_by('-status_order', '-last_occurred')[:10]
        
        result = []
        for alert in recent_alerts:
            # 尝试获取关联的节点名称
            node = Node.objects.filter(uuid=alert.node_id).first()
            node_name = node.name if node else f'Node {alert.node_id}'
            
            result.append({
                'id': str(alert.uuid),
                'title': alert.title,
                'node_id': alert.node_id,
                'node_name': node_name,
                'link_name': node.link.name if node.link else 'Unknown',
                'level': alert.severity.lower() if alert.severity else 'medium',
                'time': utc_obj_to_time_zone_str(alert.last_occurred),
                # 'time': alert.last_occurred.isoformat() if alert.last_occurred else None,
                'status': alert.status,
                'severity': alert.severity,
                'description': alert.description
            })
        
        return result