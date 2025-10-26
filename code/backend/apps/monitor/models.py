from django.db import models
from lib.model_tools import BaseModel
from apps.user.models import User
from apps.monitor.enum import NODE_HEALTH_STATUS_CHOICES
from django.utils import timezone
import json


class Alert(BaseModel):
    """
    告警模型 - 记录系统监控告警信息
    """
    # 告警状态
    STATUS_CHOICES = [
        ('OPEN', 'Open'),
        ('CLOSED', 'Closed'),
        ('SILENCED', 'Silenced'),
    ]
    
    # 严重程度
    SEVERITY_CHOICES = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('CRITICAL', 'Critical'),
    ]
    
    # 唯一标识字段
    node_id = models.CharField(max_length=100, help_text="关联的节点ID")
    alert_type = models.CharField(max_length=50, help_text="告警类型")
    alert_subtype = models.CharField(max_length=100, blank=True, default="", help_text="告警子类型，用于更细化的分类")
    
    # 告警内容
    title = models.CharField(max_length=200, help_text="告警标题")
    description = models.TextField(help_text="告警详细描述")
    
    # 状态管理
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='OPEN', help_text="告警状态")
    severity = models.CharField(max_length=20, default='MEDIUM', choices=SEVERITY_CHOICES, help_text="告警严重程度")
    
    # 关联信息
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='created_alerts', 
        help_text="创建人"
    )
    silenced_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='silenced_alerts', 
        help_text="静默人"
    )
    
    # 时间字段
    first_occurred = models.DateTimeField(auto_now_add=True, help_text="首次发生时间")
    last_occurred = models.DateTimeField(auto_now=True, help_text="最后发生时间")
    resolved_at = models.DateTimeField(null=True, blank=True, help_text="解决时间")
    silenced_at = models.DateTimeField(null=True, blank=True, help_text="静默时间")
    silenced_until = models.DateTimeField(null=True, blank=True, help_text="静默结束时间")
    
    class Meta:
        db_table = 'alert'
        verbose_name = '告警'
        verbose_name_plural = verbose_name
        # 确保同一节点的相同类型告警不会重复（仅对未解决的告警）
        constraints = [
            models.UniqueConstraint(
                fields=['node_id', 'alert_type', 'alert_subtype', 'status'],
                condition=models.Q(status='OPEN'),
                name='unique_open_alert'
            ),
            models.UniqueConstraint(
                fields=['node_id', 'alert_type', 'alert_subtype', 'status'],
                condition=models.Q(status='SILENCED'),
                name='unique_silenced_alert'
            ),
        ]
        ordering = ['-first_occurred']

    def __str__(self):
        return f"{self.title} - {self.status}"

    # 静默相关字段
    silenced_reason = models.TextField(null=True, blank=True, help_text="静默原因")

    def is_currently_silenced(self):
        """
        检查告警是否正在被静默
        """
        if self.status == 'SILENCED' and self.silenced_until:
            return timezone.now() < self.silenced_until
        return False


class Link(BaseModel):
    """
    链路模型 - 定义一个完整的运维链路
    """
    name = models.CharField(max_length=200, verbose_name='链路名称')
    description = models.TextField(blank=True, null=True, verbose_name='链路描述')

    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    check_single_point = models.BooleanField(default=False, verbose_name='是否检测单点')
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


class BaseInfo(BaseModel):
    """
    基础信息模型 - 存储共享的服务信息（不与特定节点关联）
    """
    host = models.CharField(max_length=255, verbose_name='主机地址')
    port = models.IntegerField(null=True, blank=True, verbose_name='端口')
    is_ping_disabled = models.BooleanField(default=False, verbose_name='是否禁ping')
    # 新增字段：健康状态
    is_healthy = models.BooleanField(null=True, blank=True, verbose_name='健康状态')
    remarks = models.TextField(blank=True, null=True, verbose_name='备注')

    class Meta:
        verbose_name = '基础服务信息'
        verbose_name_plural = verbose_name
        ordering = ['-create_time']
        # 确保在整个系统中，host+port的组合是唯一的
        constraints = [
            models.UniqueConstraint(
                fields=['host', 'port'],
                name='unique_host_port_global'
            )
        ]

    def __str__(self):
        if self.port:
            return f"{self.host}:{self.port}"
        else:
            return f"{self.host}"


class NodeBaseInfo(BaseModel):
    """
    节点基础信息关联表 - 关联节点和服务信息
    """
    node = models.ForeignKey(
        Node,
        on_delete=models.CASCADE,
        related_name='node_base_info_items',
        verbose_name='关联节点'
    )
    base_info = models.ForeignKey(
        BaseInfo,
        on_delete=models.CASCADE,
        related_name='node_associations',
        verbose_name='服务信息'
    )
    
    class Meta:
        verbose_name = '节点服务关联'
        verbose_name_plural = verbose_name
        ordering = ['-create_time']
        # 确保一个节点不能重复关联同一个服务信息
        unique_together = ['node', 'base_info']

    def __str__(self):
        return f"{self.node.name} -> {self.base_info}"


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


class SystemHealthStats(BaseModel):
    """
    系统健康统计信息
    用于存储全局健康检查统计数据
    """
    key = models.CharField(max_length=100, unique=True, help_text="统计项唯一键")
    value = models.TextField(help_text="统计值")
    meta_info = models.JSONField(null=True, blank=True, help_text="附加信息")

    class Meta:
        db_table = 'system_health_stats'
        verbose_name = '系统健康统计'
        verbose_name_plural = verbose_name


class PushPlusConfig(BaseModel):
    """
    PushPlus配置模型 - 存储PushPlus推送配置
    """
    # 配置类型
    CONFIG_TYPE_CHOICES = [
        ('GLOBAL', '全局配置'),
        ('DEFAULT', '默认配置'),
    ]
    
    # 消息类型
    MSG_TYPE_CHOICES = [
        ('txt', '文本消息'),
        ('html', 'HTML消息'),
        ('markdown', 'Markdown消息'),
        ('json', 'JSON消息'),
    ]
    
    # 消息模板类型
    TEMPLATE_CHOICES = [
        ('alert', '告警消息模板'),
        ('notification', '通知消息模板'),
        ('custom', '自定义消息模板'),
    ]
    
    config_type = models.CharField(
        max_length=20, 
        choices=CONFIG_TYPE_CHOICES, 
        default='GLOBAL', 
        help_text="配置类型"
    )
    name = models.CharField(max_length=100, unique=True, help_text="配置名称")
    token = models.CharField(max_length=100, help_text="PushPlus Token")
    title_prefix = models.CharField(max_length=100, blank=True, default="", help_text="标题前缀")
    enabled = models.BooleanField(default=True, help_text="是否启用")
    msg_type = models.CharField(max_length=20, choices=MSG_TYPE_CHOICES, default='txt', help_text="消息类型")
    template_type = models.CharField(max_length=20, choices=TEMPLATE_CHOICES, default='alert', help_text="模板类型")
    content_template = models.TextField(help_text="内容模板，支持变量替换")
    
    # 推送条件配置
    apply_to_all_alerts = models.BooleanField(default=True, help_text="是否应用于所有告警")
    alert_severity_filter = models.JSONField(
        default=list, 
        help_text="告警严重程度过滤器，例如['CRITICAL', 'HIGH']"
    )
    
    # 消息配置
    topic_list = models.JSONField(
        default=list, 
        help_text="订阅组列表，以英文逗号分隔"
    )
    webhook_list = models.JSONField(
        default=list, 
        help_text="Webhook列表"
    )
    
    # 额外配置
    extra_params = models.JSONField(
        default=dict, 
        help_text="额外参数，以JSON格式存储"
    )
    
    # 关联信息
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='created_pushplus_configs', 
        help_text="创建人"
    )
    updated_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='updated_pushplus_configs', 
        help_text="更新人"
    )

    class Meta:
        db_table = 'pushplus_config'
        verbose_name = 'PushPlus配置'
        verbose_name_plural = verbose_name
        ordering = ['-create_time']

    def __str__(self):
        return f"PushPlus配置 - {self.name}"

    @classmethod
    def get_active_config(cls):
        """
        获取启用的配置
        """
        return cls.objects.filter(enabled=True).first()
    
    def get_alert_severity_filter_list(self):
        """
        获取告警严重程度过滤器列表
        """
        if isinstance(self.alert_severity_filter, list):
            return self.alert_severity_filter
        try:
            return json.loads(self.alert_severity_filter)
        except:
            return []
    
    def get_topic_list(self):
        """
        获取订阅组列表
        """
        if isinstance(self.topic_list, list):
            return self.topic_list
        try:
            return json.loads(self.topic_list)
        except:
            return []
    
    def get_webhook_list(self):
        """
        获取Webhook列表
        """
        if isinstance(self.webhook_list, list):
            return self.webhook_list
        try:
            return json.loads(self.webhook_list)
        except:
            return []
