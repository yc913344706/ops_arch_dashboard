from django.urls import path
from . import views

urlpatterns = [
    # 架构图相关接口
    path('links/', views.LinkView.as_view(), name='link-list'),
    path('link/', views.LinkDetailView.as_view(), name='link-detail'),
    path('link/topology/', views.LinkTopologyView.as_view(), name='link-topology'),
    
    # 节点相关接口
    path('nodes/', views.NodeView.as_view(), name='node-list'),

    # baseinfo相关接口
    path('baseinfo/', views.BaseInfoView.as_view(), name='baseinfo-list'),
    
    # 连接相关接口
    path('connections/', views.NodeConnectionView.as_view(), name='connection-list'),
    
    # 节点健康相关接口
    path('node/health/', views.NodeHealthView.as_view(), name='node-health'),
    
    # 告警相关接口
    path('alerts/', views.AlertView.as_view(), name='alert-list'),
    path('alert/', views.AlertDetailView.as_view(), name='alert-detail'),
    path('alert-types/', views.AlertTypesView.as_view(), name='alert-types'),
    
    # PushPlus配置相关接口
    path('pushplus-configs/', views.PushPlusConfigView.as_view(), name='pushplus-config-list'),
    path('pushplus-config/', views.PushPlusConfigDetailView.as_view(), name='pushplus-config-detail'),
    path('pushplus-test/', views.PushPlusTestView.as_view(), name='pushplus-test'),
    
    # 监控仪表板统计接口
    path('dashboard/', views.MonitorDashboardView.as_view(), name='monitor-dashboard'),
    
    # 系统健康统计接口
    path('system_health_stats/', views.SystemHealthStatsView.as_view(), name='system-health-stats'),
    
    # 时序监控数据接口
    path('ts-data/node-health/', views.NodeHealthTSView.as_view(), name='node-health-ts'),
]