from django.views import View
from apps.monitor.tasks import check_node_health, trigger_alert_notification
from lib.time_tools import utc_obj_to_time_zone_str
from lib.request_tool import pub_bool_check, pub_get_request_body, pub_success_response, pub_error_response, get_request_param
from lib.paginator_tool import pub_paging_tool
from .models import Link, Node, NodeHealth, NodeConnection, Alert, SystemHealthStats, PushPlusConfig
from lib.log import color_logger
from apps.myAuth.token_utils import TokenManager
from django.db.models import Q, Count, Case, When, IntegerField, Sum, F
from django.db.models.functions import RowNumber
from django.db.models.expressions import Window
from django.utils import timezone
from datetime import datetime, timedelta
from django.db.models.expressions import RawSQL
from lib.influxdb_tool import InfluxDBManager

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
                    'check_single_point': link.check_single_point,
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
            
            create_keys = ['name', 'description', 'is_active', 'check_single_point']
            create_dict = {key: value for key, value in body.items() if key in create_keys}
            
            # 设置默认值
            create_dict['is_active'] = body.get('is_active', True)
            create_dict['check_single_point'] = body.get('check_single_point', False)
            
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
                'is_active': link.is_active,
                'check_single_point': link.check_single_point
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

            update_keys = ['name', 'description', 'is_active', 'check_single_point']
            update_dict = {key: value for key, value in body.items() if key in update_keys}
            
            for key, value in update_dict.items():
                setattr(link, key, value)
            link.save()

            return pub_success_response({
                'uuid': str(link.uuid),
                'name': link.name,
                'description': link.description,
                'is_active': link.is_active,
                'check_single_point': link.check_single_point
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
                'check_single_point': link.check_single_point,
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
            from .models import BaseInfo, NodeBaseInfo
            nodes_data = []
            for node in nodes:
                # 优先使用 BaseInfo 表中存储的健康状态（通过 NodeBaseInfo 关联）
                node_base_info_items = NodeBaseInfo.objects.filter(node=node).select_related('base_info')
                base_info_list = []
                for node_base_info in node_base_info_items:
                    base_info = node_base_info.base_info
                    base_info_item = {
                        'uuid': str(base_info.uuid), 
                        'host': base_info.host, 
                        'port': base_info.port, 
                        'is_ping_disabled': node_base_info.is_ping_disabled,  # 使用节点特定配置
                        'is_healthy': base_info.is_healthy,  # 使用全局健康状态
                        'remarks': base_info.remarks  # 新增备注字段
                    }
                    base_info_list.append(base_info_item)
                
                nodes_data.append({
                    'uuid': str(node.uuid),
                    'name': node.name,
                    'base_info_list': base_info_list,    # 新格式数据
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
            
            # 添加搜索功能 - 按节点名称搜索
            # 注意：现在基本配置信息存储在BaseInfo模型中，需要通过关联查询来搜索
            if search:
                node_list = node_list.filter(
                    Q(name__icontains=search)
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
                
                # 优先使用 BaseInfo 表中存储的健康状态（通过 NodeBaseInfo 关联）
                from .models import BaseInfo, NodeBaseInfo
                node_base_info_items = NodeBaseInfo.objects.filter(node=node).select_related('base_info')
                base_info_list = []
                for node_base_info in node_base_info_items:
                    base_info = node_base_info.base_info
                    base_info_item = {
                        'uuid': str(base_info.uuid), 
                        'host': base_info.host, 
                        'port': base_info.port, 
                        'is_ping_disabled': node_base_info.is_ping_disabled,  # 使用节点特定配置
                        'is_healthy': base_info.is_healthy,  # 使用全局健康状态
                        'remarks': base_info.remarks  # 新增备注字段
                    }
                    base_info_list.append(base_info_item)
                
                result_data.append({
                    'uuid': str(node.uuid),
                    'name': node.name,
                    'base_info_list': base_info_list,    # 新格式数据
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
            
            create_keys = ['name', 'link', 'is_active', 'position_x', 'position_y']
            create_dict = {key: value for key, value in body.items() if key in create_keys}
            
            # 设置默认值
            create_dict['is_active'] = body.get('is_active', True)
            
            # 关联架构图
            from .models import Link
            link = Link.objects.filter(uuid=body.get('link')).first()
            if link:
                create_dict['link'] = link
            else:
                return pub_error_response("架构图不存在")
            
            node = Node.objects.create(**create_dict)
            
            # 如果提供了 base_info_list 参数，则创建或关联BaseInfo记录
            base_info_list = body.get('base_info_list', [])
            if base_info_list:
                from .models import BaseInfo, NodeBaseInfo
                for base_info_item in base_info_list:
                    host = base_info_item.get('host')
                    if host:
                        port = base_info_item.get('port')
                        is_ping_disabled = base_info_item.get('is_ping_disabled', False)
                        remarks = base_info_item.get('remarks', '')
                        
                        # 检查是否已存在相同 host:port 的基础信息
                        base_info, created = BaseInfo.objects.get_or_create(
                            host=host,
                            port=port,
                            defaults={
                                'is_ping_disabled': is_ping_disabled,
                                'is_healthy': None,  # 初始健康状态为未知
                                'remarks': remarks
                            }
                        )
                        
                        if created:
                            color_logger.info(f"Created new BaseInfo for {host}:{port}")
                        else:
                            color_logger.info(f"Reusing existing BaseInfo for {host}:{port}")
                            # 如果基础信息已存在，但备注不同，可以考虑更新备注
                            if remarks and not base_info.remarks:
                                base_info.remarks = remarks
                                base_info.save(update_fields=['remarks'])
                        
                        # 建立节点与基础信息的关联
                        NodeBaseInfo.objects.get_or_create(
                            node=node,
                            base_info=base_info,
                            defaults={
                                'is_ping_disabled': is_ping_disabled
                            }
                        )
            
            # 返回更新后的数据
            from .models import BaseInfo, NodeBaseInfo
            node_base_info_items = NodeBaseInfo.objects.filter(node=node).select_related('base_info')
            base_info_list = []
            for node_base_info in node_base_info_items:
                base_info = node_base_info.base_info
                base_info_item = {
                    'uuid': str(base_info.uuid), 
                    'host': base_info.host, 
                    'port': base_info.port, 
                    'is_ping_disabled': node_base_info.is_ping_disabled,  # 使用节点特定配置
                    'is_healthy': base_info.is_healthy,  # 使用全局健康状态
                    'remarks': base_info.remarks  # 新增备注字段
                }
                base_info_list.append(base_info_item)
            
            return pub_success_response({
                'uuid': str(node.uuid),
                'name': node.name,
                'base_info_list': base_info_list,
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

            update_keys = ['name', 'is_active', 'position_x', 'position_y']
            update_dict = {key: value for key, value in body.items() if key in update_keys}
            
            for key, value in update_dict.items():
                setattr(node, key, value)
            node.save()
            
            # 如果提供了 base_info_list 参数，则更新BaseInfo记录
            base_info_list = body.get('base_info_list', None)
            if base_info_list is not None:  # 如果提供了该参数（即使是空列表也表示要清空）
                # 删除现有的节点基础信息关联
                from .models import NodeBaseInfo
                NodeBaseInfo.objects.filter(node=node).delete()
                
                # 创建或关联新的基础信息
                from .models import BaseInfo, NodeBaseInfo
                for base_info_item in base_info_list:
                    host = base_info_item.get('host')
                    if host:
                        port = base_info_item.get('port')
                        is_ping_disabled = base_info_item.get('is_ping_disabled', False)
                        remarks = base_info_item.get('remarks', '')
                        
                        # 检查或创建基础信息
                        base_info, created = BaseInfo.objects.get_or_create(
                            host=host,
                            port=port,
                            defaults={
                                'is_ping_disabled': is_ping_disabled,
                                'is_healthy': None,  # 初始健康状态为未知
                                'remarks': remarks
                            }
                        )
                        
                        if created:
                            color_logger.info(f"Created new BaseInfo for {host}:{port}")
                        else:
                            color_logger.info(f"Reusing existing BaseInfo for {host}:{port}")
                            # 如果基础信息已存在，但备注不同，可以考虑更新备注
                            if remarks and not base_info.remarks:
                                base_info.remarks = remarks
                                base_info.save(update_fields=['remarks'])
                        
                        # 建立节点与基础信息的关联
                        NodeBaseInfo.objects.get_or_create(
                            node=node,
                            base_info=base_info,
                            defaults={
                                'is_ping_disabled': is_ping_disabled
                            }
                        )
            
            # 尝试触发健康检查任务，但即使失败也不影响API响应
            try:
                check_node_health.delay(node.uuid)
            except Exception as e:
                color_logger.error(f"触发节点健康检查任务失败: {e.args}", exc_info=True)
                # 不中断主流程，只是记录错误

            # 返回更新后的数据
            from .models import BaseInfo, NodeBaseInfo
            node_base_info_items = NodeBaseInfo.objects.filter(node=node).select_related('base_info')
            base_info_list = []
            for node_base_info in node_base_info_items:
                base_info = node_base_info.base_info
                base_info_item = {
                    'uuid': str(base_info.uuid), 
                    'host': base_info.host, 
                    'port': base_info.port, 
                    'is_ping_disabled': node_base_info.is_ping_disabled,  # 使用节点特定配置
                    'is_healthy': base_info.is_healthy,  # 使用全局健康状态
                    'remarks': base_info.remarks  # 新增备注字段
                }
                base_info_list.append(base_info_item)
            
            return pub_success_response({
                'uuid': str(node.uuid),
                'name': node.name,
                'base_info_list': base_info_list,
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
            
            # 从InfluxDB获取最新的健康数据
            influxdb_manager = InfluxDBManager()
            try:
                # 查询最近的健康记录
                from datetime import datetime, timedelta
                # 查询最近1小时的数据
                start_time = (timezone.now() - timedelta(hours=1)).isoformat()
                health_records = influxdb_manager.query_node_health_data(
                    node_uuid=node_uuid,
                    start_time=start_time,
                    limit=1
                )
                
                if health_records:
                    latest_record = health_records[0]  # 最新的一条记录
                    data = {
                        'uuid': str(node.uuid),
                        'name': node.name,
                        'healthy_status': latest_record.get('healthy_status'),
                        'response_time': latest_record.get('response_time'),
                        'last_check_time': latest_record.get('time').isoformat() if latest_record.get('time') else None,
                        'probe_result': {},  # InfluxDB中暂不存储完整probe_result，可以通过其他API获取
                        'error_message': latest_record.get('error_message'),
                        'total_checks': latest_record.get('total_checks'),
                        'failed_checks': latest_record.get('failed_checks')
                    }
                else:
                    # 如果InfluxDB没有数据，回退到节点状态
                    data = {
                        'uuid': str(node.uuid),
                        'name': node.name,
                        'healthy_status': node.healthy_status,
                        'response_time': None,
                        'last_check_time': node.last_check_time.isoformat() if node.last_check_time else None,
                        'probe_result': {},
                        'error_message': None,
                        'total_checks': None,
                        'failed_checks': None
                    }
            except Exception as influx_error:
                color_logger.error(f"从InfluxDB获取节点健康状态失败: {str(influx_error)}", exc_info=True)
                # 如果InfluxDB查询失败，回退到原来的MySQL查询
                latest_health = node.health_records.first()
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
                
                # 触发告警通知
                from .tasks import trigger_alert_notification
                result = trigger_alert_notification(alert)
                
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
                
                # 状态更改后触发告警通知处理
                # 在关闭或静默告警后，可以发送状态更新通知
                # 只有在告警状态变为CLOSED或SILENCED时才推送状态变更
                if new_status in ['CLOSED', 'SILENCED']:
                    from apps.monitor.pushplus_service import PushPlusService
                    pushplus_service = PushPlusService()
                    result = pushplus_service.check_and_send_alert(alert)
                    if result['success']:
                        color_logger.info(f"告警状态更改后推送成功: {alert.title}")
                    else:
                        if not result.get('skipped'):
                            color_logger.warning(f"告警状态更改后推送失败: {result.get('error', 'Unknown error')}")

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
                
                # 状态更改后触发告警通知处理
                # 在关闭或静默告警后，可以发送状态更新通知
                # 只有在告警状态变为CLOSED或SILENCED时才推送状态变更
                if new_status in ['CLOSED', 'SILENCED']:
                    from apps.monitor.pushplus_service import PushPlusService
                    pushplus_service = PushPlusService()
                    result = pushplus_service.check_and_send_alert(alert)
                    if result['success']:
                        color_logger.info(f"告警状态更改后推送成功: {alert.title}")
                    else:
                        if not result.get('skipped'):
                            color_logger.warning(f"告警状态更改后推送失败: {result.get('error', 'Unknown error')}")

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
            
            # 检查是否请求特定任务信息
            task_uuid = body.get('task_uuid')
            
            if task_uuid:
                # 获取特定任务的详细信息
                from .tasks import get_check_all_nodes_task_info
                task_info = get_check_all_nodes_task_info(task_uuid)
                
                if task_info:
                    return pub_success_response({
                        'task_uuid': task_uuid,
                        'task_info': task_info
                    })
                else:
                    return pub_error_response(f"任务不存在或已过期: {task_uuid}")
            
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
                # 检查是否请求任务列表
                get_tasks = body.get('get_tasks', False)
                if get_tasks:
                    from .tasks import get_recent_check_all_nodes_tasks
                    limit = int(body.get('limit', 10))
                    tasks_info = get_recent_check_all_nodes_tasks(limit)
                    
                    return pub_success_response({
                        'tasks': tasks_info,
                        'total_count': len(tasks_info)
                    })
                
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


class PushPlusConfigView(View):
    """PushPlus配置相关接口"""
    
    def get(self, request):
        """获取PushPlus配置列表"""
        try:
            body = pub_get_request_body(request)
            
            page = int(body.get('page', 1))
            page_size = int(body.get('page_size', 20))
            search = body.get('search', '')
            enabled = body.get('enabled')
            
            config_list = PushPlusConfig.objects.all()
            
            # 添加搜索功能
            if search:
                config_list = config_list.filter(
                    Q(name__icontains=search)
                )
            
            # 按启用状态过滤
            # color_logger.debug(f"enabled: {enabled}")
            if enabled is not None and enabled != '':
                # color_logger.debug(f"enabled is not None")
                enabled = pub_bool_check(enabled)
                config_list = config_list.filter(enabled=enabled)
            
            # 分页查询
            has_next, next_page, page_list, all_num, result = pub_paging_tool(page, config_list, page_size)
            
            # 格式化返回数据
            result_data = []
            for config in result:
                result_data.append({
                    'uuid': str(config.uuid),
                    'name': config.name,
                    'config_type': config.config_type,
                    'title_prefix': config.title_prefix,
                    'enabled': config.enabled,
                    'msg_type': config.msg_type,
                    'template_type': config.template_type,
                    'apply_to_all_alerts': config.apply_to_all_alerts,
                    'alert_severity_filter': config.alert_severity_filter,
                    'topic_list': config.topic_list,
                    'webhook_list': config.webhook_list,
                    'created_by': {
                        'uuid': str(config.created_by.uuid) if config.created_by else None,
                        'username': config.created_by.username if config.created_by else None,
                        'nickname': config.created_by.nickname if config.created_by else None
                    } if config.created_by else None,
                    'create_time': utc_obj_to_time_zone_str(config.create_time),
                    'update_time': utc_obj_to_time_zone_str(config.update_time)
                })
            
            return pub_success_response({
                'has_next': has_next,
                'next_page': next_page,
                'all_num': all_num,
                'data': result_data
            })
            
        except Exception as e:
            color_logger.error(f"获取PushPlus配置列表失败: {e.args}", exc_info=True)
            return pub_error_response(f"获取PushPlus配置列表失败: {e.args}")
    
    def post(self, request):
        """创建PushPlus配置"""
        try:
            body = pub_get_request_body(request)
            user_name = request.user_name
            
            # 验证必要字段
            required_fields = ['name', 'token']
            for field in required_fields:
                if field not in body:
                    return pub_error_response(f"缺少必要字段: {field}")
            
            # 检查配置名称是否已存在
            if PushPlusConfig.objects.filter(name=body.get('name')).exists():
                return pub_error_response("配置名称已存在")
            
            create_keys = [
                'name', 'token', 'title_prefix', 'enabled', 'msg_type', 
                'template_type', 'content_template', 'apply_to_all_alerts',
                'alert_severity_filter', 'topic_list', 'webhook_list', 'extra_params'
            ]
            create_dict = {key: value for key, value in body.items() if key in create_keys}
            
            # 设置默认值
            create_dict['enabled'] = body.get('enabled', True)
            create_dict['msg_type'] = body.get('msg_type', 'txt')
            create_dict['template_type'] = body.get('template_type', 'alert')
            create_dict['apply_to_all_alerts'] = body.get('apply_to_all_alerts', True)
            create_dict['alert_severity_filter'] = body.get('alert_severity_filter', [])
            create_dict['topic_list'] = body.get('topic_list', [])
            create_dict['webhook_list'] = body.get('webhook_list', [])
            create_dict['extra_params'] = body.get('extra_params', {})
            
            # 关联创建者
            from apps.user.models import User
            user = User.objects.filter(username=user_name).first()
            if user:
                create_dict['created_by'] = user
                create_dict['updated_by'] = user
            
            config = PushPlusConfig.objects.create(**create_dict)
            
            return pub_success_response({
                'uuid': str(config.uuid),
                'name': config.name,
                'enabled': config.enabled,
                'create_time': utc_obj_to_time_zone_str(config.create_time)
            })
        except Exception as e:
            color_logger.error(f"创建PushPlus配置失败: {e.args}")
            return pub_error_response(f"创建PushPlus配置失败: {e.args}")
    
    def put(self, request):
        """更新PushPlus配置"""
        try:
            body = pub_get_request_body(request)
            
            uuid = body.get('uuid')
            assert uuid, 'uuid 不能为空'

            config = PushPlusConfig.objects.filter(uuid=uuid).first()
            assert config, '更新的配置不存在'

            update_keys = [
                'name', 'token', 'title_prefix', 'enabled', 'msg_type', 
                'template_type', 'content_template', 'apply_to_all_alerts',
                'alert_severity_filter', 'topic_list', 'webhook_list', 'extra_params'
            ]
            update_dict = {key: value for key, value in body.items() if key in update_keys}
            
            # 更新关联用户
            user_name = getattr(request, 'user_name', None)
            if user_name:
                from apps.user.models import User
                user = User.objects.filter(username=user_name).first()
                if user:
                    update_dict['updated_by'] = user
            
            for key, value in update_dict.items():
                setattr(config, key, value)
            config.save()

            return pub_success_response({
                'uuid': str(config.uuid),
                'name': config.name,
                'enabled': config.enabled
            })
        except Exception as e:
            color_logger.error(f"更新PushPlus配置失败: {e.args}")
            return pub_error_response(f"更新PushPlus配置失败: {e.args}")
    
    def delete(self, request):
        """删除PushPlus配置"""
        try:
            body = pub_get_request_body(request)
            
            config = PushPlusConfig.objects.filter(uuid=body['uuid']).first()
            assert config, '删除的配置不存在'
            config.delete()
            return pub_success_response()
        except Exception as e:
            color_logger.error(f"删除PushPlus配置失败: {e.args}")
            return pub_error_response(f"删除PushPlus配置失败: {e.args}")


class PushPlusConfigDetailView(View):
    """单个PushPlus配置详情接口"""
    
    def get(self, request):
        """获取单个PushPlus配置详情"""
        try:
            body = pub_get_request_body(request)
            config_uuid = body.get('uuid')
            color_logger.debug(f"获取单个PushPlus配置详情: {config_uuid}")
            config = PushPlusConfig.objects.get(uuid=config_uuid)
            
            return pub_success_response({
                'uuid': str(config.uuid),
                'name': config.name,
                'config_type': config.config_type,
                'token': config.token,
                'title_prefix': config.title_prefix,
                'enabled': config.enabled,
                'msg_type': config.msg_type,
                'template_type': config.template_type,
                'content_template': config.content_template,
                'apply_to_all_alerts': config.apply_to_all_alerts,
                'alert_severity_filter': config.alert_severity_filter,
                'topic_list': config.topic_list,
                'webhook_list': config.webhook_list,
                'extra_params': config.extra_params,
                'created_by': {
                    'uuid': str(config.created_by.uuid) if config.created_by else None,
                    'username': config.created_by.username if config.created_by else None,
                    'nickname': config.created_by.nickname if config.created_by else None
                } if config.created_by else None,
                'updated_by': {
                    'uuid': str(config.updated_by.uuid) if config.updated_by else None,
                    'username': config.updated_by.username if config.updated_by else None,
                    'nickname': config.updated_by.nickname if config.updated_by else None
                } if config.updated_by else None,
                'create_time': config.create_time.isoformat() if config.create_time else None,
                'update_time': config.update_time.isoformat() if config.update_time else None
            })
        except PushPlusConfig.DoesNotExist:
            return pub_error_response("PushPlus配置不存在")
        except Exception as e:
            color_logger.error(f"获取PushPlus配置详情失败: {e.args}")
            return pub_error_response(f"获取PushPlus配置详情失败: {e.args}")
    
    def put(self, request):
        """更新单个PushPlus配置"""
        try:
            body = pub_get_request_body(request)
            
            uuid = body.get('uuid')
            assert uuid, 'uuid 不能为空'

            config = PushPlusConfig.objects.filter(uuid=uuid).first()
            assert config, '更新的配置不存在'

            update_keys = [
                'name', 'token', 'title_prefix', 'enabled', 'msg_type', 
                'template_type', 'content_template', 'apply_to_all_alerts',
                'alert_severity_filter', 'topic_list', 'webhook_list', 'extra_params'
            ]
            update_dict = {key: value for key, value in body.items() if key in update_keys}
            
            # 更新关联用户
            user_name = getattr(request, 'user_name', None)
            if user_name:
                from apps.user.models import User
                user = User.objects.filter(username=user_name).first()
                if user:
                    update_dict['updated_by'] = user
            
            for key, value in update_dict.items():
                setattr(config, key, value)
            config.save()

            return pub_success_response({
                'uuid': str(config.uuid),
                'name': config.name,
                'enabled': config.enabled
            })
        except Exception as e:
            color_logger.error(f"更新PushPlus配置失败: {e.args}")
            return pub_error_response(f"更新PushPlus配置失败: {e.args}")


class PushPlusTestView(View):
    """PushPlus测试接口"""
    
    def post(self, request):
        """测试PushPlus配置"""
        try:
            from apps.monitor.pushplus_service import PushPlusService
            body = pub_get_request_body(request)
            
            # 获取需要的参数
            token = body.get('token')
            title = body.get('title', 'PushPlus测试消息')
            content = body.get('content', '这是一条测试消息')
            msg_type = body.get('msg_type', 'txt')
            topic_list = body.get('topic_list', [])
            
            if not token:
                return pub_error_response("缺少token参数")
            
            # 创建服务实例并发送测试消息
            service = PushPlusService()
            result = service.send_message(
                token=token,
                title=title,
                content=content,
                msg_type=msg_type,
                topic_list=topic_list
            )
            
            if result['success']:
                return pub_success_response({
                    'message': '测试消息发送成功',
                    'result': result
                })
            else:
                return pub_error_response(f"测试消息发送失败: {result.get('error', '未知错误')}")
                
        except Exception as e:
            color_logger.error(f"测试PushPlus发送失败: {e.args}")
            return pub_error_response(f"测试PushPlus发送失败: {e.args}")


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
        """获取健康趋势数据（使用InfluxDB时序数据）"""
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

        try:
            # 使用InfluxDB获取健康趋势数据
            influxdb_manager = InfluxDBManager()
            
            # 获取所有活跃节点的UUID列表
            active_node_uuids = [str(node.uuid) for node in Node.objects.filter(is_active=True)]
            
            if not active_node_uuids:
                return {
                    'period': period,
                    'data': []
                }
            
            # 查询指定时间范围内的健康数据
            health_records = influxdb_manager.query_multiple_nodes_health(
                node_uuids=active_node_uuids,
                start_time=start_date.isoformat(),
                end_time=end_date.isoformat() if end_date else None
            )
            
            # 按时间段统计健康状态
            trend_data = []
            
            # 根据周期生成时间点
            time_points = []
            if period == 'day':
                # 按小时统计
                current_time = start_date.replace(minute=0, second=0, microsecond=0)
                end_time = end_date.replace(minute=0, second=0, microsecond=0)
                while current_time <= end_time:
                    if timezone.is_naive(current_time):
                        current_time = timezone.make_aware(current_time)
                    time_points.append(current_time)
                    current_time += timedelta(hours=1)
            elif period == 'week':
                # 按天统计
                current_date = start_date.date()
                end_date_obj = end_date.date()
                while current_date <= end_date_obj:
                    current_time = timezone.make_aware(datetime.combine(current_date, datetime.min.time()))
                    time_points.append(current_time)
                    current_date += timedelta(days=1)
            elif period == 'month':
                # 按天统计
                current_date = start_date.date()
                end_date_obj = end_date.date()
                while current_date <= end_date_obj:
                    current_time = timezone.make_aware(datetime.combine(current_date, datetime.min.time()))
                    time_points.append(current_time)
                    current_date += timedelta(days=1)
            elif period == 'quarter':
                # 按周统计
                current_date = start_date.date()
                end_date_obj = end_date.date()
                while current_date <= end_date_obj:
                    current_time = timezone.make_aware(datetime.combine(current_date, datetime.min.time()))
                    time_points.append(current_time)
                    current_date += timedelta(weeks=1)
            else:  # year
                # 按月统计
                current_date = start_date.date()
                end_date_obj = end_date.date()
                while current_date <= end_date_obj:
                    current_time = timezone.make_aware(datetime.combine(current_date, datetime.min.time()))
                    time_points.append(current_time)
                    if current_date.month == 12:
                        current_date = current_date.replace(year=current_date.year + 1, month=1)
                    else:
                        try:
                            current_date = current_date.replace(month=current_date.month + 1)
                        except ValueError:  # 处理月份天数问题
                            if current_date.month in [1, 3, 5, 7, 8, 10, 12]:
                                current_date = current_date.replace(day=30, month=current_date.month + 1)
                            else:
                                current_date = current_date.replace(day=28, month=current_date.month + 1)
            
            # 为每个时间段统计健康状态
            for i in range(len(time_points) - 1):
                period_start = time_points[i]
                period_end = time_points[i + 1]
                
                # 统计该时间段内的状态
                status_counts = {'green': 0, 'yellow': 0, 'red': 0, 'unknown': 0}
                
                # 遍历每个节点的数据
                for node_id, records in health_records.items():
                    # 确保时间范围是timezone-aware的
                    if timezone.is_naive(period_start):
                        period_start = timezone.make_aware(period_start)
                    if timezone.is_naive(period_end):
                        period_end = timezone.make_aware(period_end)
                    
                    # 找到该时间段内该节点的记录
                    period_records = []
                    for r in records:
                        record_time = r['time']
                        # 确保record_time是timezone-aware的
                        if timezone.is_naive(record_time):
                            record_time = timezone.make_aware(record_time)
                            
                        if period_start <= record_time < period_end:
                            period_records.append(r)
                    
                    if period_records:
                        # 以最新的记录为准
                        latest_record = max(period_records, key=lambda x: x['time'])
                        status = latest_record.get('healthy_status', 'unknown')
                        if status in status_counts:
                            status_counts[status] += 1
                    else:
                        # 如果该时间段内没有记录，使用节点当前状态
                        node = Node.objects.filter(uuid=node_id).first()
                        if node:
                            current_status = node.healthy_status
                            if current_status in status_counts:
                                status_counts[current_status] += 1
                
                trend_data.append({
                    'date': period_start.isoformat(),
                    'green_count': status_counts['green'],
                    'yellow_count': status_counts['yellow'],
                    'red_count': status_counts['red'],
                    'unknown_count': status_counts['unknown']
                })
            
            # 如果InfluxDB没有足够的数据，使用回退逻辑
            if not trend_data or all(
                item['green_count'] == 0 and item['yellow_count'] == 0 and 
                item['red_count'] == 0 and item['unknown_count'] == 0 
                for item in trend_data
            ):
                # 使用原有的基于MySQL的逻辑作为回退
                return self._get_health_trend_data_fallback(period, start_date, end_date)

            return {
                'period': period,
                'data': trend_data
            }
            
        except Exception as e:
            color_logger.error(f"从InfluxDB获取健康趋势数据失败: {str(e)}", exc_info=True)
            # 回退到原有逻辑
            return self._get_health_trend_data_fallback(period, start_date, end_date)
    
    def _get_health_trend_data_fallback(self, period, start_date, end_date):
        """回退到MySQL获取健康趋势数据"""
        # 原有逻辑...
        now = timezone.now()
        if not start_date or not end_date:
            if period == 'day':
                start_date = now - timedelta(days=1)
            elif period == 'week':
                start_date = now - timedelta(weeks=1)
            elif period == 'month':
                start_date = now - timedelta(days=30)
            elif period == 'quarter':
                start_date = now - timedelta(days=90)
            elif period == 'year':
                start_date = now - timedelta(days=365)
            else:
                start_date = now - timedelta(weeks=1)
            end_date = now

        time_points = []
        if period == 'day':
            start_hour_point = start_date.replace(minute=0, second=0, microsecond=0)
            end_hour_point = end_date.replace(minute=0, second=0, microsecond=0)
            current_hour = start_hour_point
            while current_hour <= end_hour_point:
                time_points.append(current_hour)
                current_hour += timedelta(hours=1)
        elif period in ['week', 'month']:
            current_date = start_date.date()
            end_date_date = end_date.date()
            while current_date <= end_date_date:
                time_points.append(timezone.make_aware(datetime.combine(current_date, datetime.min.time())))
                current_date += timedelta(days=1)

        trend_data = []
        for time_point in time_points:
            end_time = time_point + timedelta(days=1) if period in ['week', 'month'] else time_point + timedelta(hours=1)
            
            records_in_period = NodeHealth.objects.filter(
                create_time__gte=time_point,
                create_time__lt=end_time
            )
            
            node_highest_status = {}
            status_priority = {'red': 3, 'yellow': 2, 'unknown': 1, 'green': 0}
            
            for record in records_in_period:
                node_id = record.node_id
                current_status = record.healthy_status
                if (node_id not in node_highest_status or 
                    status_priority[current_status] > status_priority[node_highest_status[node_id]]):
                    node_highest_status[node_id] = current_status
            
            all_node_ids_in_records = set(node_highest_status.keys())
            nodes_without_records = Node.objects.filter(is_active=True).exclude(uuid__in=all_node_ids_in_records)
            
            for node in nodes_without_records:
                node_highest_status[node.uuid] = node.healthy_status
            
            from collections import Counter
            status_counts = Counter(node_highest_status.values())
            
            trend_data.append({
                'date': time_point.isoformat(),
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


class NodeHealthTSView(View):
    """节点健康时序数据接口 - 专门用于查询InfluxDB中的监控数据"""
    
    def get(self, request):
        """获取节点健康时序数据"""
        try:
            body = pub_get_request_body(request)
            node_uuid = body.get('uuid')
            if not node_uuid:
                return pub_error_response("缺少节点UUID参数")
                
            start_time = body.get('start_time', (timezone.now() - timedelta(hours=1)).isoformat())
            end_time = body.get('end_time')
            limit = int(body.get('limit', 100))
            
            # 从InfluxDB获取数据
            influxdb_manager = InfluxDBManager()
            health_records = influxdb_manager.query_node_health_data(
                node_uuid=node_uuid,
                start_time=start_time,
                end_time=end_time,
                limit=limit
            )
            
            # 格式化返回数据
            formatted_records = []
            for record in health_records:
                formatted_records.append({
                    'time': record['time'].isoformat() if record['time'] else None,
                    'healthy_status': record['healthy_status'],
                    'response_time': record.get('response_time'),
                    'total_checks': record.get('total_checks'),
                    'failed_checks': record.get('failed_checks'),
                    'error_message': record.get('error_message')
                })
            
            return pub_success_response({
                'node_uuid': node_uuid,
                'records': formatted_records,
                'count': len(formatted_records)
            })
            
        except Exception as e:
            color_logger.error(f"获取节点健康时序数据失败: {e.args}")
            return pub_error_response(f"获取节点健康时序数据失败: {e.args}")