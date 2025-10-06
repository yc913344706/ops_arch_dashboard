from django.urls import path
from . import views

urlpatterns = [
    # 架构图相关接口
    path('links/', views.LinkView.as_view(), name='link-list'),
    path('link/', views.LinkDetailView.as_view(), name='link-detail'),
    path('link/topology/', views.LinkTopologyView.as_view(), name='link-topology'),
    
    # 节点相关接口
    path('nodes/', views.NodeView.as_view(), name='node-list'),
    
    # 连接相关接口
    path('connections/', views.NodeConnectionView.as_view(), name='connection-list'),
    
    # 节点健康相关接口
    path('node/health/', views.NodeHealthView.as_view(), name='node-health'),
    
    # 告警相关接口
    path('alerts/', views.AlertView.as_view(), name='alert-list'),
    path('alert/', views.AlertDetailView.as_view(), name='alert-detail'),
    path('alert-types/', views.AlertTypesView.as_view(), name='alert-types'),
]