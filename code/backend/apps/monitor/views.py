from django.views import View
from apps.monitor.tasks import check_node_health
from lib.time_tools import utc_obj_to_time_zone_str
from lib.request_tool import pub_get_request_body, pub_success_response, pub_error_response, get_request_param
from lib.paginator_tool import pub_paging_tool
from .models import Link, Node, NodeHealth, NodeConnection
from lib.log import color_logger
from apps.myAuth.token_utils import TokenManager
from django.db.models import Q


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
            
            node_list = Node.objects.all()
            
            # 添加搜索功能
            if search:
                node_list = node_list.filter(name__icontains=search)
            
            # 按架构图过滤
            if link_id:
                node_list = node_list.filter(link_id=link_id)
            
            # 分页查询
            has_next, next_page, page_list, all_num, result = pub_paging_tool(page, node_list, page_size)
            
            # 格式化返回数据
            result_data = []
            for node in result:
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
                    'create_time': node.create_time.isoformat() if node.create_time else None,
                    'update_time': node.update_time.isoformat() if node.update_time else None
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
            check_node_health(node.uuid)

            return pub_success_response({
                'uuid': str(node.uuid),
                'name': node.name,
                'basic_info_list': node.basic_info_list,
                'is_active': node.is_active
            })
        except Exception as e:
            color_logger.error(f"更新节点失败: {e.args}")
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

            if latest_health:
                data = {
                    'uuid': str(node.uuid),
                    'name': node.name,
                    'healthy_status': latest_health.healthy_status,
                    'response_time': latest_health.response_time,
                    'last_check_time': latest_health.create_time.isoformat() if latest_health.create_time else None,
                    'probe_result': latest_health.probe_result,
                    'error_message': latest_health.error_message
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
                    'error_message': None
                }

            return pub_success_response(data)
        except Node.DoesNotExist:
            return pub_error_response("节点不存在")
        except Exception as e:
            color_logger.error(f"获取节点健康状态失败: {e.args}")
            return pub_error_response(f"获取节点健康状态失败: {e.args}")