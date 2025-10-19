from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from django.conf import settings
from lib.log import color_logger
import os
import re


class InfluxDBManager:
    """
    InfluxDB管理器 - 用于存储和查询时序监控数据
    """
    
    def __init__(self):
        # 从环境变量或配置中获取连接信息
        # 先尝试从Django设置中获取，如果不存在则从环境变量获取，最后使用默认值
        self.url = getattr(settings, 'INFLUXDB_URL', 
                          os.getenv('INFLUXDB_URL', 
                          self._get_config_value('INFLUXDB', 'URL', 'http://localhost:8086')))
        self.token = getattr(settings, 'INFLUXDB_TOKEN', 
                            os.getenv('INFLUXDB_TOKEN', 
                            self._get_config_value('INFLUXDB', 'TOKEN', 'your-influxdb-token')))
        self.org = getattr(settings, 'INFLUXDB_ORG', 
                          os.getenv('INFLUXDB_ORG', 
                          self._get_config_value('INFLUXDB', 'ORG', 'ops_org')))
        self.bucket = getattr(settings, 'INFLUXDB_BUCKET', 
                             os.getenv('INFLUXDB_BUCKET', 
                             self._get_config_value('INFLUXDB', 'BUCKET', 'monitoring')))
        
        self.client = None
        self.write_api = None
        self.query_api = None
    
    def _get_config_value(self, section, key, default=None):
        """
        从YAML配置中获取值
        """
        try:
            from django.conf import settings as django_settings
            from yaml import safe_load
            config_file = f"{django_settings.BASE_DIR}/.{os.environ.get('OPS_ARCH_DASHBOARD_ENV', 'dev')}.yaml"
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = safe_load(f)
            return config_data.get(section, {}).get(key, default)
        except Exception:
            # 如果配置文件读取失败，返回默认值
            return default
    
    def connect(self):
        """连接到InfluxDB"""
        try:
            self.client = InfluxDBClient(
                url=self.url,
                token=self.token,
                org=self.org
            )
            # 测试连接
            # 尝试列出buckets来测试连接
            buckets_api = self.client.buckets_api()
            list(buckets_api.find_buckets().buckets)  # 尝试获取bucket列表
            
            self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
            self.query_api = self.client.query_api()
            color_logger.info("Successfully connected to InfluxDB with token")
        except Exception as e:
            color_logger.error(f"Failed to connect to InfluxDB with token: {str(e)}")
            raise
    
    def write_node_health_data(self, node_uuid, healthy_status, response_time=None, probe_result=None, error_message=None):
        """写入节点健康数据到InfluxDB"""
        try:
            if not self.write_api:
                self.connect()

            # 创建数据点
            point = Point("node_health") \
                .tag("node_id", str(node_uuid)) \
                .field("healthy_status", healthy_status) \
                .time(None, WritePrecision.NS)  # 使用当前时间

            # 添加可选字段
            if response_time is not None:
                point = point.field("response_time", float(response_time))

            if probe_result:
                # 将probe_result中的一些关键信息作为字段存储
                if isinstance(probe_result, dict) and 'details' in probe_result:
                    details = probe_result['details']
                    if isinstance(details, list) and len(details) > 0:
                        # 计算健康检测的统计信息
                        total_checks = len(details)
                        failed_checks = sum(1 for item in details if not item.get('is_healthy', True))
                        point = point.field("total_checks", total_checks) \
                          .field("failed_checks", failed_checks)

            if error_message:
                point = point.field("error_message", str(error_message))

            # 写入数据
            self.write_api.write(bucket=self.bucket, org=self.org, record=point)

        except Exception as e:
            color_logger.error(f"Failed to write node health data to InfluxDB: {str(e)}")
            # 记录错误但不抛出异常，以避免影响正常业务流程
    
    def query_node_health_data(self, node_uuid, start_time, end_time=None, limit=100):
        """查询节点健康数据"""
        try:
            if not self.query_api:
                self.connect()

            # 确保start_time和end_time格式正确，符合Flux查询语法
            # Flux中时间格式需要是RFC3339格式或者duration格式
            start_time_formatted = self._format_time_for_flux(start_time)
            end_time_formatted = self._format_time_for_flux(end_time) if end_time else "now()"

            # 构建查询语句
            query = f'''
            from(bucket: "{self.bucket}")
              |> range(start: {start_time_formatted}, stop: {end_time_formatted})
              |> filter(fn: (r) => r["_measurement"] == "node_health")
              |> filter(fn: (r) => r["node_id"] == "{node_uuid}")
              |> limit(n: {limit})
              |> sort(columns: ["_time"], desc: true)
            '''

            result = self.query_api.query(org=self.org, query=query)

            # 解析查询结果
            records = []
            for table in result:
                for record in table.records:
                    records.append({
                        'time': record.get_time(),
                        'node_id': record.values.get('node_id'),
                        'healthy_status': record.get_value(),
                        'response_time': record.values.get('response_time'),
                        'total_checks': record.values.get('total_checks'),
                        'failed_checks': record.values.get('failed_checks'),
                        'error_message': record.values.get('error_message')
                    })

            return records

        except Exception as e:
            color_logger.error(f"Failed to query node health data from InfluxDB: {str(e)}")
            return []

    def query_multiple_nodes_health(self, node_uuids, start_time, end_time=None, limit_per_node=50):
        """查询多个节点的健康数据"""
        try:
            if not self.query_api:
                self.connect()

            # 确保start_time和end_time格式正确
            start_time_formatted = self._format_time_for_flux(start_time)
            end_time_formatted = self._format_time_for_flux(end_time) if end_time else "now()"

            # 构建查询语句，查询多个节点
            node_filter = ' or '.join([f'r["node_id"] == "{node_id}"' for node_id in node_uuids])
            query = f'''
            from(bucket: "{self.bucket}")
              |> range(start: {start_time_formatted}, stop: {end_time_formatted})
              |> filter(fn: (r) => r["_measurement"] == "node_health")
              |> filter(fn: (r) => {node_filter})
              |> limit(n: {limit_per_node * len(node_uuids)})
              |> sort(columns: ["_time"], desc: true)
            '''

            result = self.query_api.query(org=self.org, query=query)

            # 解析查询结果
            records = {}
            for table in result:
                for record in table.records:
                    node_id = record.values.get('node_id')
                    if node_id not in records:
                        records[node_id] = []

                    records[node_id].append({
                        'time': record.get_time(),
                        'healthy_status': record.get_value(),
                        'response_time': record.values.get('response_time'),
                        'total_checks': record.values.get('total_checks'),
                        'failed_checks': record.values.get('failed_checks'),
                        'error_message': record.values.get('error_message')
                    })

            return records

        except Exception as e:
            color_logger.error(f"Failed to query multiple nodes health data from InfluxDB: {str(e)}")
            return {}

    def _format_time_for_flux(self, time_str):
        """格式化时间字符串以符合Flux查询语法"""
        if not time_str:
            return time_str
        
        # 检查是否已经是duration格式 (例如: -1h, 1d, etc.)
        if re.match(r'^[-+]?[0-9]+(u|µ|ms|s|m|h|d|w|mo|y)$', time_str):
            return time_str
        
        # 如果不是duration格式，则假定为RFC3339格式，用引号包围
        if not time_str.startswith('"') and not time_str.endswith('"'):
            return f'"{time_str}"'
        
        return time_str

    def close(self):
        """关闭连接"""
        if self.client:
            self.client.close()