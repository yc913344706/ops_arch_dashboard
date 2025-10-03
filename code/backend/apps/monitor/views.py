from django.shortcuts import render
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from django.core.exceptions import ObjectDoesNotExist
from .models import Link, Node, NodeHealth, NodeConnection
from .tasks import check_node_health


class LinkViewSet(ModelViewSet):
    queryset = Link.objects.all()
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Link.objects.all()
        # 搜索
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(description__icontains=search)
            )
        # 过滤类型
        link_type = self.request.query_params.get('link_type', None)
        if link_type:
            queryset = queryset.filter(link_type=link_type)
        # 过滤激活状态
        is_active = self.request.query_params.get('is_active', None)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
            
        return queryset

    def get_serializer_class(self):
        from .serializers import LinkSerializer
        return LinkSerializer


class NodeViewSet(ModelViewSet):
    queryset = Node.objects.all()
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Node.objects.all()
        # 按架构图过滤
        link_id = self.request.query_params.get('link_id', None)
        if link_id:
            queryset = queryset.filter(link_id=link_id)
        # 过滤激活状态
        is_active = self.request.query_params.get('is_active', None)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
            
        return queryset

    def get_serializer_class(self):
        from .serializers import NodeSerializer
        return NodeSerializer


class NodeConnectionViewSet(ModelViewSet):
    queryset = NodeConnection.objects.all()
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = NodeConnection.objects.all()
        # 按架构图过滤
        link_id = self.request.query_params.get('link_id', None)
        if link_id:
            queryset = queryset.filter(link_id=link_id)
        # 按起始节点过滤
        from_node_id = self.request.query_params.get('from_node_id', None)
        if from_node_id:
            queryset = queryset.filter(from_node_id=from_node_id)
        # 按目标节点过滤
        to_node_id = self.request.query_params.get('to_node_id', None)
        if to_node_id:
            queryset = queryset.filter(to_node_id=to_node_id)
        # 过滤激活状态
        is_active = self.request.query_params.get('is_active', None)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
            
        return queryset

    def get_serializer_class(self):
        from .serializers import NodeConnectionSerializer
        return NodeConnectionSerializer


class LinkTopologyView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, link_uuid):
        try:
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
                    'is_healthy': node.is_healthy,
                    'position_x': node.position_x,
                    'position_y': node.position_y,
                    'create_time': node.create_time
                })

            # 构建连接数据
            connections_data = []
            for conn in connections:
                connections_data.append({
                    'uuid': str(conn.uuid),
                    'from_node': str(conn.from_node.uuid),
                    'to_node': str(conn.to_node.uuid),
                    'direction': conn.direction
                })

            return Response({
                'uuid': str(link.uuid),
                'name': link.name,
                'nodes': nodes_data,
                'connections': connections_data
            })
        except Link.DoesNotExist:
            return Response({'error': 'Architecture diagram not found'}, status=status.HTTP_404_NOT_FOUND)


class NodeHealthView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, node_uuid):
        try:
            node = Node.objects.get(uuid=node_uuid)
            latest_health = node.health_records.first()  # 获取最新健康记录

            if latest_health:
                data = {
                    'uuid': str(node.uuid),
                    'name': node.name,
                    'is_healthy': latest_health.is_healthy,
                    'response_time': latest_health.response_time,
                    'last_check_time': latest_health.create_time,
                    'probe_result': latest_health.probe_result,
                    'error_message': latest_health.error_message
                }
            else:
                # 如果没有健康记录，使用节点的当前状态
                data = {
                    'uuid': str(node.uuid),
                    'name': node.name,
                    'is_healthy': node.is_healthy,
                    'response_time': None,
                    'last_check_time': node.last_check_time,
                    'probe_result': {},
                    'error_message': None
                }

            return Response(data)
        except Node.DoesNotExist:
            return Response({'error': 'Node not found'}, status=status.HTTP_404_NOT_FOUND)


class NodeHealthHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, node_uuid):
        try:
            node = Node.objects.get(uuid=node_uuid)
            hours = int(request.query_params.get('hours', 24))
            
            from datetime import timedelta
            from django.utils import timezone
            
            start_time = timezone.now() - timedelta(hours=hours)
            health_records = node.health_records.filter(
                create_time__gte=start_time
            ).order_by('-create_time')
            
            data = []
            for record in health_records:
                data.append({
                    'create_time': record.create_time,
                    'is_healthy': record.is_healthy,
                    'response_time': record.response_time,
                    'probe_result': record.probe_result
                })
            
            return Response(data)
        except Node.DoesNotExist:
            return Response({'error': 'Node not found'}, status=status.HTTP_404_NOT_FOUND)
        except ValueError:
            return Response({'error': 'Invalid hours parameter'}, status=status.HTTP_400_BAD_REQUEST)


class BatchNodeHealthView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        node_uuids = request.data.get('node_uuids', [])
        if not node_uuids:
            return Response({'error': 'No node UUIDs provided'}, status=status.HTTP_400_BAD_REQUEST)

        nodes = Node.objects.filter(uuid__in=node_uuids)
        health_data = []

        for node in nodes:
            latest_health = node.health_records.first()
            if latest_health:
                health_data.append({
                    'node_uuid': str(node.uuid),
                    'name': node.name,
                    'is_healthy': latest_health.is_healthy,
                    'response_time': latest_health.response_time
                })
            else:
                health_data.append({
                    'node_uuid': str(node.uuid),
                    'name': node.name,
                    'is_healthy': node.is_healthy,
                    'response_time': None
                })

        return Response(health_data)


class ProbeConfigView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from .probe_config import ProbeConfig
        config = ProbeConfig.get_default_configs()
        for key in config:
            # 尝试从数据库获取配置，如果不存在则使用默认值
            from .models import AppSetting
            try:
                app_setting = AppSetting.objects.get(key=key)
                config[key] = app_setting.value
            except AppSetting.DoesNotExist:
                pass
                
        return Response(config)

    def put(self, request):
        from .probe_config import ProbeConfig
        for key, value in request.data.items():
            ProbeConfig.set_config(key, value)
        return Response({'message': 'Configuration updated successfully'})


class GlobalSearchView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = request.query_params.get('q', '')
        search_type = request.query_params.get('type', 'all')  # link, node, all

        if not query:
            return Response({'results': []})

        results = []
        
        if search_type in ['link', 'all']:
            links = Link.objects.filter(
                Q(name__icontains=query) | Q(description__icontains=query)
            )
            for link in links:
                results.append({
                    'type': 'link',
                    'uuid': str(link.uuid),
                    'name': link.name,
                    'description': link.description,
                    'link_type': link.link_type
                })

        if search_type in ['node', 'all']:
            nodes = Node.objects.filter(
                Q(name__icontains=query)
            )
            for node in nodes:
                results.append({
                    'type': 'node',
                    'uuid': str(node.uuid),
                    'name': node.name,
                    'link_name': node.link.name
                })

        return Response({'results': results})