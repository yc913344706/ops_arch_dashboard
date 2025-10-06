# http://testingpai.com/article/1646638660220

import os
from datetime import timedelta

from celery import Celery
from celery.schedules import crontab

from backend.settings import config_data, set_color_logger_level

set_color_logger_level(config_data.get('LOG_LEVEL', "DEBUG"))

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

# 设置 Django 的默认环境变量
redis_url = 'redis://:{}@{}:{}/'.format(
    config_data['REDIS']['PASSWORD'],
    config_data['REDIS']['HOST'],
    config_data['REDIS']['PORT'],
)

app = Celery('backend',
    broker=redis_url + str(config_data['REDIS']['DB']['CELERY_BROKER']),
    backend=redis_url + str(config_data['REDIS']['DB']['CELERY']),
)


app.conf.update(broker_connection_retry_on_startup=True)

# 配置序列化
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Shanghai',
    enable_utc=True,
)

app.autodiscover_tasks()

# 添加定时任务配置
app.conf.update(
    imports=(
        'apps.demo.tasks',
        'apps.monitor.tasks',
    ),
    beat_schedule={
        # 每30秒 测试任务
        'say-hello': {
            'task': 'apps.demo.tasks.say_hello',
            'schedule': timedelta(seconds=30),
        },
        # 每5分钟检查所有节点健康状态
        'check-all-nodes-health': {
            'task': 'apps.monitor.tasks.check_all_nodes',
            'schedule': timedelta(minutes=5),
        },
        # 每天凌晨2点清理过期的健康记录
        'cleanup-health-records': {
            'task': 'apps.monitor.tasks.cleanup_health_records',
            'schedule': crontab(hour=2, minute=0),  # 每天凌晨2点执行
        }
    }
)


