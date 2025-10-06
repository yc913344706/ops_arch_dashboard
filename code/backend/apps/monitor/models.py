from django.db import models
from lib.model_tools import BaseModel
from apps.user.models import User
from apps.monitor.enum import NODE_HEALTH_STATUS_CHOICES


class Link(BaseModel):
    """
    链路模型 - 定义一个完整的运维链路
    """
    name = models.CharField(max_length=200, verbose_name='链路名称')
    description = models.TextField(blank=True, null=True, verbose_name='链路描述')
    link_type = models.CharField(
        max_length=50,
        choices=[
            ('domain', '域名链路'),
            ('network', '网络链路'),
            ('traffic', '流量链路'),
            ('application', '应用链路'),
            ('custom', '自定义链路')
        ],
        verbose_name='链路类型'
    )
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='创建者'
    )

    class Meta:
        verbose_name = '链路'
        verbose_name_plural = verbose_name
        ordering = ['-create_time']

    def __str__(self):
        return self.name


class Node(BaseModel):
    """
    节点模型 - 架构图中的一个节点
    """
    name = models.CharField(max_length=200, verbose_name='节点名称')
    basic_info_list = models.JSONField(
        default=list,
        verbose_name='基础信息列表'
    )  # 存储主机/端口信息列表，格式：[{'host': 'xxx', 'port': 80}, ...]
    link = models.ForeignKey(
        Link,
        on_delete=models.CASCADE,
        related_name='nodes',
        verbose_name='所属架构图'
    )
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    position_x = models.FloatField(null=True, blank=True, verbose_name='X坐标')
    position_y = models.FloatField(null=True, blank=True, verbose_name='Y坐标')
    healthy_status = models.CharField(
        max_length=20,
        choices=NODE_HEALTH_STATUS_CHOICES,
        default='unknown',
        verbose_name='健康状态'
    )
    last_check_time = models.DateTimeField(null=True, blank=True, verbose_name='最后检查时间')

    class Meta:
        verbose_name = '节点'
        verbose_name_plural = verbose_name
        ordering = ['-create_time']

    def __str__(self):
        return f"{self.link.name} - {self.name}"


class NodeConnection(BaseModel):
    """
    节点连接模型 - 定义节点之间的连接关系
    """
    # DIRECTIONS = [
    #     ('up', '上'),
    #     ('down', '下'),
    #     ('left', '左'),
    #     ('right', '右'),
    # ]

    from_node = models.ForeignKey(
        Node,
        on_delete=models.CASCADE,
        related_name='outgoing_connections',
        verbose_name='起始节点'
    )
    to_node = models.ForeignKey(
        Node,
        on_delete=models.CASCADE,
        related_name='incoming_connections',
        verbose_name='目标节点'
    )
    # direction = models.CharField(
    #     max_length=10,
    #     choices=DIRECTIONS,
    #     verbose_name='连接方向'
    # )
    link = models.ForeignKey(
        Link,
        on_delete=models.CASCADE,
        verbose_name='所属架构图'
    )
    is_active = models.BooleanField(default=True, verbose_name='是否启用')

    class Meta:
        verbose_name = '节点连接'
        verbose_name_plural = verbose_name
        unique_together = [['from_node', 'to_node', 'link', 'is_del']]  # 确保同一架构图内两个节点间只有一个连接

    def __str__(self):
        # return f"{self.from_node.name} -> {self.to_node.name} ({self.direction})"
        return f"{self.from_node.name} -> {self.to_node.name}"


class NodeHealth(BaseModel):
    """
    节点健康状态模型 - 记录节点健康状态历史
    """
    node = models.ForeignKey(
        Node,
        on_delete=models.CASCADE,
        related_name='health_records',
        verbose_name='节点'
    )
    healthy_status = models.CharField(
        max_length=20,
        choices=NODE_HEALTH_STATUS_CHOICES,
        verbose_name='健康状态',
        default='unknown'
    )
    response_time = models.FloatField(null=True, blank=True, verbose_name='响应时间(ms)')
    probe_result = models.JSONField(
        default=dict,
        verbose_name='探活结果'
    )  # 存储详细的探活结果
    error_message = models.TextField(null=True, blank=True, verbose_name='错误信息')

    class Meta:
        verbose_name = '节点健康状态'
        verbose_name_plural = verbose_name
        ordering = ['-create_time']

    def __str__(self):
        return f"{self.node.name} - {self.healthy_status}"


class AppSetting(BaseModel):
    """
    应用程序设置模型 - 存储监控相关全局配置
    """
    key = models.CharField(max_length=100, unique=True, verbose_name='配置键')
    value = models.TextField(verbose_name='配置值')
    description = models.TextField(null=True, blank=True, verbose_name='配置描述')

    class Meta:
        verbose_name = '应用设置'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.key
