"""
PushPlus 推送服务
实现与 PushPlus API 的集成，用于推送告警和其他通知消息
"""

import requests
import json
from typing import List, Dict, Optional
from lib.log import color_logger
from .models import PushPlusConfig, Alert
from django.utils import timezone
from django.db.models import Q


class PushPlusService:
    """
    PushPlus 推送服务类
    """
    API_URL = "http://www.pushplus.plus/send"

    def __init__(self):
        self.default_config = None

    def get_active_config(self) -> Optional[PushPlusConfig]:
        """
        获取启用的配置
        """
        if self.default_config is None:
            self.default_config = PushPlusConfig.objects.filter(enabled=True).first()
        return self.default_config

    def send_message(
        self,
        token: str,
        title: str = "",
        content: str = "",
        msg_type: str = "txt",
        topic_list: List[str] = None,
        webhook_list: List[str] = None,
        template: str = "html",
        channel: str = "wechat",
        callback_url: str = "",
        **kwargs
    ) -> Dict:
        """
        发送消息到 PushPlus
        
        Args:
            token: PushPlus Token
            title: 消息标题
            content: 消息内容
            msg_type: 消息类型 (txt, html, markdown, json)
            topic_list: 订阅组列表
            webhook_list: Webhook列表
            template: 模板类型
            channel: 推送渠道
            callback_url: 回调地址
            **kwargs: 其他参数
            
        Returns:
            Dict: 发送结果
        """
        try:
            # 构建请求数据
            data = {
                "token": token,
                "title": title,
                "content": content,
                "template": template,
                "channel": channel,
            }

            # 添加可选参数
            if msg_type:
                data["msgtype"] = msg_type
            if topic_list:
                data["topic"] = ",".join(topic_list)
            if webhook_list:
                data["webhook"] = ",".join(webhook_list)
            if callback_url:
                data["callbackUrl"] = callback_url

            # 添加额外参数
            data.update(kwargs)

            # 发送请求
            response = requests.post(
                self.API_URL,
                json=data,
                headers={"Content-Type": "application/json"},
                timeout=10
            )

            response.raise_for_status()
            result = response.json()

            # 检查响应状态
            if result.get("code") == 200:
                color_logger.info(f"PushPlus消息发送成功: {title}")
                return {
                    "success": True,
                    "message": "发送成功",
                    "data": result
                }
            else:
                color_logger.error(f"PushPlus消息发送失败: {result.get('msg', '未知错误')}")
                return {
                    "success": False,
                    "error": result.get("msg", "未知错误"),
                    "data": result
                }

        except requests.exceptions.RequestException as e:
            color_logger.error(f"PushPlus请求异常: {str(e)}")
            return {
                "success": False,
                "error": f"请求异常: {str(e)}"
            }
        except Exception as e:
            color_logger.error(f"PushPlus发送消息异常: {str(e)}")
            return {
                "success": False,
                "error": f"发送异常: {str(e)}"
            }

    def send_alert_message(self, alert: Alert) -> Dict:
        """
        根据告警信息发送 PushPlus 消息
        
        Args:
            alert: 告警对象
            
        Returns:
            Dict: 发送结果
        """
        try:
            # 获取配置
            config = self.get_active_config()
            if not config:
                color_logger.warning("没有启用的PushPlus配置，跳过消息发送")
                return {
                    "success": False,
                    "error": "没有启用的PushPlus配置"
                }

            # 检查告警级别是否符合推送条件
            if not config.apply_to_all_alerts:
                severity_filter = config.get_alert_severity_filter_list()
                if severity_filter and alert.severity not in severity_filter:
                    color_logger.info(f"告警严重程度 {alert.severity} 不在推送范围内，跳过发送")
                    return {
                        "success": False,
                        "error": f"告警严重程度 {alert.severity} 不在推送范围内"
                    }

            # 获取关联节点信息
            from .models import Node
            node = Node.objects.filter(uuid=alert.node_id).first()
            node_name = node.name if node else alert.node_id

            # 构建标题和内容
            title_prefix = config.title_prefix or ""
            title = f"{title_prefix}[{alert.severity}] {alert.title}"

            # 根据配置的模板类型处理内容
            if config.template_type == 'alert':
                # 告警消息模板
                content = self._format_alert_content(alert, node_name, config.content_template)
            elif config.template_type == 'notification':
                # 通知消息模板
                content = self._format_notification_content(alert, node_name, config.content_template)
            else:
                # 自定义消息模板
                content = self._format_custom_content(alert, node_name, config.content_template)

            # 发送消息
            result = self.send_message(
                token=config.token,
                title=title,
                content=content,
                msg_type=config.msg_type,
                topic_list=config.get_topic_list(),
                webhook_list=config.get_webhook_list()
            )

            return result

        except Exception as e:
            color_logger.error(f"发送告警消息到PushPlus异常: {str(e)}")
            return {
                "success": False,
                "error": f"发送告警消息异常: {str(e)}"
            }

    def _format_alert_content(self, alert: Alert, node_name: str, template: str = "") -> str:
        """
        格式化告警消息内容
        
        Args:
            alert: 告警对象
            node_name: 节点名称
            template: 内容模板
            
        Returns:
            str: 格式化后的内容
        """
        # 默认告警模板
        if not template or template.strip() == "":
            template = """告警类型: {alert_type}
告警子类型: {alert_subtype}
节点名称: {node_name}
严重程度: {severity}
标题: {title}
描述: {description}
首次发生时间: {first_occurred}
最后发生时间: {last_occurred}"""

        # 变量替换
        content = template.format(
            alert_type=alert.alert_type,
            alert_subtype=alert.alert_subtype,
            node_name=node_name,
            severity=alert.severity,
            title=alert.title,
            description=alert.description,
            first_occurred=alert.first_occurred.strftime("%Y-%m-%d %H:%M:%S") if alert.first_occurred else "",
            last_occurred=alert.last_occurred.strftime("%Y-%m-%d %H:%M:%S") if alert.last_occurred else ""
        )

        return content

    def _format_notification_content(self, alert: Alert, node_name: str, template: str = "") -> str:
        """
        格式化通知消息内容
        
        Args:
            alert: 告警对象
            node_name: 节点名称
            template: 内容模板
            
        Returns:
            str: 格式化后的内容
        """
        # 默认通知模板
        if not template or template.strip() == "":
            template = """系统通知
告警类型: {alert_type}
节点: {node_name}
严重程度: {severity}
标题: {title}
时间: {occurred_time}"""

        content = template.format(
            alert_type=alert.alert_type,
            node_name=node_name,
            severity=alert.severity,
            title=alert.title,
            occurred_time=alert.last_occurred.strftime("%Y-%m-%d %H:%M:%S") if alert.last_occurred else ""
        )

        return content

    def _format_custom_content(self, alert: Alert, node_name: str, template: str) -> str:
        """
        格式化自定义内容
        
        Args:
            alert: 告警对象
            node_name: 节点名称
            template: 内容模板
            
        Returns:
            str: 格式化后的内容
        """
        # 如果模板为空，使用默认模板
        if not template or template.strip() == "":
            template = "{title}\n\n{description}"

        # 替换常用变量
        content = template.format(
            alert_type=alert.alert_type,
            alert_subtype=alert.alert_subtype,
            node_id=alert.node_id,
            node_name=node_name,
            severity=alert.severity,
            title=alert.title,
            description=alert.description,
            first_occurred=alert.first_occurred.strftime("%Y-%m-%d %H:%M:%S") if alert.first_occurred else "",
            last_occurred=alert.last_occurred.strftime("%Y-%m-%d %H:%M:%S") if alert.last_occurred else "",
            status=alert.status
        )

        return content

    def test_config(self, config_data: Dict) -> Dict:
        """
        测试配置是否有效
        
        Args:
            config_data: 配置数据
            
        Returns:
            Dict: 测试结果
        """
        try:
            token = config_data.get('token')
            if not token:
                return {
                    "success": False,
                    "error": "配置中缺少token"
                }

            # 发送测试消息
            result = self.send_message(
                token=token,
                title="PushPlus配置测试",
                content="这是一条配置测试消息",
                msg_type=config_data.get('msg_type', 'txt')
            )

            return result

        except Exception as e:
            color_logger.error(f"测试PushPlus配置异常: {str(e)}")
            return {
                "success": False,
                "error": f"测试异常: {str(e)}"
            }

    def check_and_send_alert(self, alert: Alert) -> Dict:
        """
        检查告警是否需要发送，并发送到 PushPlus
        
        Args:
            alert: 告警对象
            
        Returns:
            Dict: 发送结果
        """
        try:
            # 获取配置
            config = self.get_active_config()
            if not config:
                return {
                    "success": False,
                    "error": "没有启用的PushPlus配置",
                    "skipped": True
                }

            # 检查告警状态，只有OPEN状态的告警才发送
            if alert.status != 'OPEN':
                return {
                    "success": False,
                    "error": f"告警状态不是OPEN，当前状态: {alert.status}",
                    "skipped": True
                }

            # 检查是否静默
            if alert.is_currently_silenced():
                return {
                    "success": False,
                    "error": "告警当前处于静默状态",
                    "skipped": True
                }

            # 检查是否需要推送（避免重复推送）
            # 使用Django缓存来记录最近推送的告警
            from django.core.cache import cache
            cache_key = f"pushplus_last_sent_{alert.uuid}"
            last_sent_info = cache.get(cache_key)
            
            # 如果已记录推送信息，检查是否需要再次推送
            if last_sent_info:
                last_sent_time = last_sent_info.get('last_occurred')
                last_sent_description = last_sent_info.get('description')
                
                # 如果最后一次发生时间和描述与缓存中的一致，说明已经推送过相同的告警信息
                if (alert.last_occurred and last_sent_time and 
                    last_sent_description == alert.description and
                    abs((alert.last_occurred - last_sent_time).total_seconds()) < 60):  # 60秒内视为相同时间
                    color_logger.info(f"告警 {alert.uuid} 已推送过相同内容，跳过本次推送")
                    return {
                        "success": False,
                        "error": "告警已推送过",
                        "skipped": True
                    }

            # 发送告警消息
            result = self.send_alert_message(alert)
            
            if result['success']:
                # 记录推送信息，包括最后发生时间和描述
                cache.set(cache_key, {
                    'last_occurred': alert.last_occurred,
                    'description': alert.description
                }, timeout=3600)  # 缓存1小时
            
            return result

        except Exception as e:
            color_logger.error(f"检查并发送告警消息异常: {str(e)}")
            return {
                "success": False,
                "error": f"检查并发送告警消息异常: {str(e)}"
            }