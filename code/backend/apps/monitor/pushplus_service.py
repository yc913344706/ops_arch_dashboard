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
            from .models import Node, Link, NodeBaseInfo, BaseInfo
            node = Node.objects.filter(uuid=alert.node_id).first()
            node_name = node.name if node else alert.node_id
            
            # 获取节点所属链路信息
            link_name = ""
            link_id = ""
            if node and node.link:
                link = node.link
                link_name = link.name
                link_id = str(link.uuid)
            else:
                # 尝试通过alert.node_id获取节点并查找链路
                node_by_id = Node.objects.filter(uuid=alert.node_id).first()
                if node_by_id and node_by_id.link:
                    link = node_by_id.link
                    link_name = link.name
                    link_id = str(link.uuid)

            # 获取节点的base_info详情
            base_info_list = []
            if node:
                # 获取节点关联的所有base_info
                node_base_info_items = NodeBaseInfo.objects.filter(node=node).select_related('base_info')
                for node_base_info in node_base_info_items:
                    base_info = node_base_info.base_info
                    base_info_item = {
                        'uuid': str(base_info.uuid),
                        'host': base_info.host,
                        'port': base_info.port,
                        'is_ping_disabled': base_info.is_ping_disabled,
                        'is_healthy': base_info.is_healthy,
                        'remarks': base_info.remarks
                    }
                    base_info_list.append(base_info_item)
            
            # 根据告警状态和消息类型决定标题和内容
            title_prefix = config.title_prefix or ""
            
            # 根据消息格式选择换行符
            line_break = "\n"  # 默认换行符
            if config.msg_type == 'html':
                line_break = "<br/>"
            elif config.msg_type == 'markdown':
                line_break = "  \n"  # Markdown 换行需要两个空格加换行
            
            # 如果告警状态是CLOSED，说明是恢复通知
            if alert.status == 'CLOSED':
                title = f"{title_prefix}[恢复通知] {alert.title} 已恢复"
                
                # 对于恢复通知，使用专门的格式
                if config.template_type == 'alert':
                    # 在告警模板基础上添加恢复说明
                    original_content = self._format_alert_content(alert, node_name, link_name, link_id, base_info_list, config.content_template)
                    if config.msg_type == 'html':
                        content = f"<strong>【问题已恢复】</strong>{line_break}{original_content}{line_break}{line_break}<em>恢复时间:</em> {alert.resolved_at.strftime('%Y-%m-%d %H:%M:%S') if alert.resolved_at else ''}"
                    elif config.msg_type == 'markdown':
                        content = f"**【问题已恢复】**{line_break}{original_content}{line_break}{line_break}*恢复时间:* {alert.resolved_at.strftime('%Y-%m-%d %H:%M:%S') if alert.resolved_at else ''}"
                    else:  # txt 或其他格式
                        content = f"【问题已恢复】{line_break}{original_content}{line_break}{line_break}恢复时间: {alert.resolved_at.strftime('%Y-%m-%d %H:%M:%S') if alert.resolved_at else ''}"
                elif config.template_type == 'notification':
                    # 通知模板的恢复格式
                    original_content = self._format_notification_content(alert, node_name, link_name, link_id, base_info_list, config.content_template)
                    if config.msg_type == 'html':
                        content = f"<strong>【系统通知 - 问题恢复】</strong>{line_break}{original_content}{line_break}{line_break}<em>问题已解决，恢复正常运行</em>"
                    elif config.msg_type == 'markdown':
                        content = f"**【系统通知 - 问题恢复】**{line_break}{original_content}{line_break}{line_break}*问题已解决，恢复正常运行*"
                    else:  # txt 或其他格式
                        content = f"【系统通知 - 问题恢复】{line_break}{original_content}{line_break}{line_break}问题已解决，恢复正常运行"
                else:  # custom template
                    # 自定义模板的恢复格式
                    original_content = self._format_custom_content(alert, node_name, link_name, link_id, base_info_list, config.content_template)
                    if config.msg_type == 'html':
                        content = f"<strong>【恢复通知】{alert.title} 已恢复</strong>{line_break}{original_content}{line_break}{line_break}<em>恢复时间:</em> {alert.resolved_at.strftime('%Y-%m-%d %H:%M:%S') if alert.resolved_at else ''}"
                    elif config.msg_type == 'markdown':
                        content = f"**【恢复通知】{alert.title} 已恢复**{line_break}{original_content}{line_break}{line_break}*恢复时间:* {alert.resolved_at.strftime('%Y-%m-%d %H:%M:%S') if alert.resolved_at else ''}"
                    else:  # txt 或其他格式
                        content = f"【恢复通知】{alert.title} 已恢复{line_break}{original_content}{line_break}{line_break}恢复时间: {alert.resolved_at.strftime('%Y-%m-%d %H:%M:%S') if alert.resolved_at else ''}"
            else:
                # 非关闭状态的正常告警处理
                title = f"{title_prefix}[{alert.severity}] {alert.title}"
                
                # 根据配置的模板类型处理内容
                if config.template_type == 'alert':
                    # 告警消息模板
                    content = self._format_alert_content(alert, node_name, link_name, link_id, base_info_list, config.content_template)
                    # 对于HTML和Markdown，应用基本格式
                    if config.msg_type == 'html':
                        content = content.replace('\n', '<br/>')
                    elif config.msg_type == 'markdown':
                        # Markdown 通常不需要特殊转换，但保留结构
                        pass
                elif config.template_type == 'notification':
                    # 通知消息模板
                    content = self._format_notification_content(alert, node_name, link_name, link_id, base_info_list, config.content_template)
                    # 对于HTML和Markdown，应用基本格式
                    if config.msg_type == 'html':
                        content = content.replace('\n', '<br/>')
                    elif config.msg_type == 'markdown':
                        # Markdown 通常不需要特殊转换，但保留结构
                        pass
                else:
                    # 自定义消息模板
                    content = self._format_custom_content(alert, node_name, link_name, link_id, base_info_list, config.content_template)
                    # 对于HTML和Markdown，应用基本格式
                    if config.msg_type == 'html':
                        content = content.replace('\n', '<br/>')
                    elif config.msg_type == 'markdown':
                        # Markdown 通常不需要特殊转换，但保留结构
                        pass

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

    def _format_alert_content(self, alert: Alert, node_name: str, link_name: str = "", link_id: str = "", base_info_list: list = None, template: str = "") -> str:
        """
        格式化告警消息内容
        
        Args:
            alert: 告警对象
            node_name: 节点名称
            link_name: 链路名称
            link_id: 链路ID
            base_info_list: 基础信息列表
            template: 内容模板
            
        Returns:
            str: 格式化后的内容
        """
        if base_info_list is None:
            base_info_list = []
        
        # 默认告警模板
        if not template or template.strip() == "":
            template = """告警类型: {alert_type}
告警子类型: {alert_subtype}
节点名称: {node_name}
所属链路: {link_name}
严重程度: {severity}
标题: {title}
描述: {description}
首次发生时间: {first_occurred}
最后发生时间: {last_occurred}
节点基础信息:
{base_info_list_formatted}"""

        # 格式化base_info_list为字符串
        base_info_formatted = ""
        if base_info_list:
            for i, info in enumerate(base_info_list, 1):
                base_info_formatted += f"  [{i}] 主机: {info.get('host', 'N/A')}, 端口: {info.get('port', 'N/A')}, " \
                                      f"禁ping: {info.get('is_ping_disabled', 'N/A')}, 健康状态: {info.get('is_healthy', 'N/A')}, " \
                                      f"备注: {info.get('remarks', 'N/A')}\n"
            # 去掉最后一个换行符
            base_info_formatted = base_info_formatted.rstrip('\n')
        else:
            base_info_formatted = "  无"

        # 变量替换
        content = template.format(
            alert_type=alert.alert_type,
            alert_subtype=alert.alert_subtype,
            node_name=node_name,
            link_name=link_name,
            link_id=link_id,
            severity=alert.severity,
            title=alert.title,
            description=alert.description,
            first_occurred=alert.first_occurred.strftime("%Y-%m-%d %H:%M:%S") if alert.first_occurred else "",
            last_occurred=alert.last_occurred.strftime("%Y-%m-%d %H:%M:%S") if alert.last_occurred else "",
            resolved_at=alert.resolved_at.strftime("%Y-%m-%d %H:%M:%S") if alert.resolved_at else "",
            silenced_at=alert.silenced_at.strftime("%Y-%m-%d %H:%M:%S") if alert.silenced_at else "",
            status=alert.status,
            base_info_list_formatted=base_info_formatted
        )

        return content

    def _format_notification_content(self, alert: Alert, node_name: str, link_name: str = "", link_id: str = "", base_info_list: list = None, template: str = "") -> str:
        """
        格式化通知消息内容
        
        Args:
            alert: 告警对象
            node_name: 节点名称
            link_name: 链路名称
            link_id: 链路ID
            base_info_list: 基础信息列表
            template: 内容模板
            
        Returns:
            str: 格式化后的内容
        """
        if base_info_list is None:
            base_info_list = []
        
        # 默认通知模板
        if not template or template.strip() == "":
            template = """系统通知
告警类型: {alert_type}
节点: {node_name}
所属链路: {link_name}
严重程度: {severity}
标题: {title}
时间: {occurred_time}
节点基础信息: {base_info_list_formatted}"""

        # 格式化base_info_list为字符串
        base_info_formatted = ""
        if base_info_list:
            for i, info in enumerate(base_info_list, 1):
                base_info_formatted += f"[{i}]主机:{info.get('host', 'N/A')},端口:{info.get('port', 'N/A')},"
            # 去掉最后一个逗号
            base_info_formatted = base_info_formatted.rstrip(',')
        else:
            base_info_formatted = "无"

        content = template.format(
            alert_type=alert.alert_type,
            node_name=node_name,
            link_name=link_name,
            link_id=link_id,
            severity=alert.severity,
            title=alert.title,
            occurred_time=alert.last_occurred.strftime("%Y-%m-%d %H:%M:%S") if alert.last_occurred else "",
            resolved_at=alert.resolved_at.strftime("%Y-%m-%d %H:%M:%S") if alert.resolved_at else "",
            silenced_at=alert.silenced_at.strftime("%Y-%m-%d %H:%M:%S") if alert.silenced_at else "",
            status=alert.status,
            base_info_list_formatted=base_info_formatted
        )

        return content

    def _format_custom_content(self, alert: Alert, node_name: str, link_name: str = "", link_id: str = "", base_info_list: list = None, template: str = "") -> str:
        """
        格式化自定义内容
        
        Args:
            alert: 告警对象
            node_name: 节点名称
            link_name: 链路名称
            link_id: 链路ID
            base_info_list: 基础信息列表
            template: 内容模板
            
        Returns:
            str: 格式化后的内容
        """
        if base_info_list is None:
            base_info_list = []
        
        # 如果模板为空，使用默认模板
        if not template or template.strip() == "":
            template = "{title}\n\n{description}"

        # 格式化base_info_list为字符串
        base_info_formatted = ""
        if base_info_list:
            for i, info in enumerate(base_info_list, 1):
                base_info_formatted += f"[{i}]主机:{info.get('host', 'N/A')},端口:{info.get('port', 'N/A')},"
            # 去掉最后一个逗号
            base_info_formatted = base_info_formatted.rstrip(',')
        else:
            base_info_formatted = "无"

        # 替换常用变量
        content = template.format(
            alert_type=alert.alert_type,
            alert_subtype=alert.alert_subtype,
            node_id=alert.node_id,
            node_name=node_name,
            link_name=link_name,
            link_id=link_id,
            severity=alert.severity,
            title=alert.title,
            description=alert.description,
            first_occurred=alert.first_occurred.strftime("%Y-%m-%d %H:%M:%S") if alert.first_occurred else "",
            last_occurred=alert.last_occurred.strftime("%Y-%m-%d %H:%M:%S") if alert.last_occurred else "",
            resolved_at=alert.resolved_at.strftime("%Y-%m-%d %H:%M:%S") if alert.resolved_at else "",
            silenced_at=alert.silenced_at.strftime("%Y-%m-%d %H:%M:%S") if alert.silenced_at else "",
            status=alert.status,
            base_info_list_formatted=base_info_formatted
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

            # 检查告警状态，只有OPEN和CLOSED状态的告警才发送
            # OPEN: 新告警或现有告警更新
            # CLOSED: 告警关闭（恢复通知）
            # SILENCED: 告警静默（通常由用户手动触发，不推送通知以避免骚扰）
            if alert.status not in ['OPEN', 'CLOSED']:
                return {
                    "success": False,
                    "error": f"告警状态不支持推送，当前状态: {alert.status}",
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
                last_sent_status = last_sent_info.get('status')
                
                # 如果是状态变更（如从OPEN变为CLOSED），则应该推送
                # 如果状态未变化且其他信息也未变化，则跳过推送
                is_status_change = (last_sent_status != alert.status)
                
                if not is_status_change:  # 只有在状态未变化时才检查重复
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
                # 记录推送信息，包括最后发生时间、描述和状态
                cache.set(cache_key, {
                    'last_occurred': alert.last_occurred,
                    'description': alert.description,
                    'status': alert.status
                }, timeout=3600)  # 缓存1小时
            
            return result

        except Exception as e:
            color_logger.error(f"检查并发送告警消息异常: {str(e)}")
            return {
                "success": False,
                "error": f"检查并发送告警消息异常: {str(e)}"
            }