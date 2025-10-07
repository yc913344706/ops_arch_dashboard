import yaml
import os
from typing import Dict, Any, List
from lib.log import color_logger
from backend.settings import BASE_DIR


class AlertRule:
    """告警规则类"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.enabled = config.get('enabled', True)
        self.description = config.get('description', '')
        self.condition = config.get('condition', '')
        self.duration = config.get('duration', '1m')
        self.severity = config.get('severity', 'MEDIUM')
        self.message = config.get('message', '')
        self.check_interval = config.get('check_interval', '5m')
        self.data_source = config.get('data_source', 'node_health')
        self.aggregation = config.get('aggregation', 'avg')
        self.time_window = config.get('time_window', '5m')


class AlertConfigParser:
    """告警配置解析器"""
    
    def __init__(self, config_file_path: str = None):
        if config_file_path is None:
            config_file_path = os.path.join(
                BASE_DIR, 
                'config', 
                'alert_rules.yaml'
            )
        self.config_file_path = config_file_path
        self.alert_rules = {}
        self.load_config()
    
    def load_config(self):
        """加载告警配置"""
        try:
            with open(self.config_file_path, 'r', encoding='utf-8') as file:
                config_data = yaml.safe_load(file)
                self.parse_alert_rules(config_data.get('alerts', {}))
        except FileNotFoundError:
            color_logger.warning(f"Alert config file not found: {self.config_file_path}")
            # 创建默认配置
            self.create_default_config()
        except yaml.YAMLError as e:
            color_logger.error(f"Error parsing alert config file: {e}")
            raise
        except Exception as e:
            color_logger.error(f"Unexpected error loading alert config: {e}")
            raise
    
    def parse_alert_rules(self, alerts_config: Dict[str, Any]):
        """解析告警规则"""
        for rule_name, rule_config in alerts_config.items():
            self.alert_rules[rule_name] = AlertRule(rule_name, rule_config)
    
    def get_enabled_rules(self) -> List[AlertRule]:
        """获取启用的告警规则"""
        return [rule for rule in self.alert_rules.values() if rule.enabled]
    
    def get_rule_by_name(self, name: str) -> AlertRule:
        """根据名称获取告警规则"""
        return self.alert_rules.get(name)
    
    def create_default_config(self):
        """创建默认配置"""
        default_config = {
            'alerts': {}
        }
        
        # 确保config目录存在
        config_dir = os.path.dirname(self.config_file_path)
        os.makedirs(config_dir, exist_ok=True)
        
        # 写入默认配置
        with open(self.config_file_path, 'w', encoding='utf-8') as file:
            yaml.dump(default_config, file, default_flow_style=False, allow_unicode=True)
        
        color_logger.info(f"Default alert config created: {self.config_file_path}")
        
        # 重新加载配置
        self.parse_alert_rules(default_config.get('alerts', {}))
    
    def get_alert_type_choices(self):
        """获取告警类型选择项，用于模型字段"""
        choices = []
        for rule_name in self.alert_rules.keys():
            # 将规则名称转换为大写格式
            choice_value = rule_name.upper().replace('-', '_')
            # 使用规则的描述作为显示标签，或生成默认标签
            rule = self.alert_rules[rule_name]
            choice_label = rule.description if rule.description else rule_name.replace('_', ' ').title()
            choices.append((choice_value, choice_label))
        return choices

    def get_alert_type_mapping(self):
        """获取告警类型中文映射，用于前端显示"""
        mapping = {}
        for rule_name, rule in self.alert_rules.items():
            # 将规则名称转换为大写格式
            alert_type = rule_name.upper().replace('-', '_')
            # 使用规则的描述或生成默认中文标签
            if rule.description:
                # 尝试从描述中获取中文名，否则使用默认的规则名中文映射
                mapping[alert_type] = rule.description
            else:
                mapping[alert_type] = "规则定义文件未找到description"
        return mapping

    def reload_config(self):
        """重新加载配置"""
        self.load_config()


def get_alert_choices():
    """
    获取告警类型的选项列表，用于Django模型字段choices
    NOTE: 这是动态获取的，但在Django模型中使用时，需要在运行时获取
    """
    return alert_config_parser.get_alert_type_choices()

def get_alert_type_mapping():
    """
    获取告警类型映射，用于前端显示
    """
    return alert_config_parser.get_alert_type_mapping()

# 全局配置解析器实例
alert_config_parser = AlertConfigParser()