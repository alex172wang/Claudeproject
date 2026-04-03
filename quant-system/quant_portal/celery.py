"""
Celery 配置文件
定义定时任务调度
"""

import os
from celery import Celery
from celery.schedules import crontab

# 设置 Django 环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'quant_portal.settings')

# 创建 Celery 应用
app = Celery('quant_portal')

# 从 Django 配置加载
app.config_from_object('django.conf:settings', namespace='CELERY')

# 自动发现任务
app.autodiscover_tasks()


# 定时任务调度
app.conf.beat_schedule = {
    # 盘中数据更新 - 每 10 分钟
    'intraday-data-update': {
        'task': 'monitor.tasks.update_intraday_data',
        'schedule': 600.0,  # 10 分钟
    },

    # 每日 14:45 信号计算
    'daily-signal-calculation': {
        'task': 'monitor.tasks.calculate_daily_signals',
        'schedule': crontab(hour=14, minute=45),
    },

    # 盘后数据更新 - 每日 15:30
    'post-market-data-update': {
        'task': 'monitor.tasks.update_post_market_data',
        'schedule': crontab(hour=15, minute=30),
    },

    # 系统健康检查 - 每 5 分钟
    'health-check': {
        'task': 'monitor.tasks.perform_health_check',
        'schedule': 300.0,  # 5 分钟
    },

    # 清理过期数据 - 每日凌晨 3:00
    'cleanup-old-data': {
        'task': 'monitor.tasks.cleanup_old_data',
        'schedule': crontab(hour=3, minute=0),
    },
}


# Celery 配置
app.conf.update(
    # 任务序列化
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',

    # 时区设置
    timezone='Asia/Shanghai',
    enable_utc=True,

    # 任务执行设置
    task_track_started=True,
    task_time_limit=3600,  # 任务硬超时 1 小时
    task_soft_time_limit=3000,  # 软超时 50 分钟

    # 结果后端设置
    result_expires=3600 * 24 * 7,  # 结果保留 7 天
    result_extended=True,

    # Worker 设置
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,

    # Broker 连接重试
    broker_connection_retry_on_startup=True,
    broker_connection_max_retries=10,
)
