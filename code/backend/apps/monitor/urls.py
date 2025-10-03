from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'links', views.LinkViewSet)
router.register(r'nodes', views.NodeViewSet)
router.register(r'connections', views.NodeConnectionViewSet)

urlpatterns = [
    # 使用路由器的URL
    path('', include(router.urls)),
    
    # 链路拓扑
    path('links/<uuid:link_uuid>/topology/', views.LinkTopologyView.as_view(), name='link-topology'),
    
    # 节点健康状态
    path('nodes/<uuid:node_uuid>/health/', views.NodeHealthView.as_view(), name='node-health'),
    path('nodes/<uuid:node_uuid>/health_history/', views.NodeHealthHistoryView.as_view(), name='node-health-history'),
    path('nodes/batch_health/', views.BatchNodeHealthView.as_view(), name='batch-node-health'),
    
    # 探活配置
    path('probe_config/', views.ProbeConfigView.as_view(), name='probe-config'),
    
    # 搜索
    path('search/', views.GlobalSearchView.as_view(), name='global-search'),
]