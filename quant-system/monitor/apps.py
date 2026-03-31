"""
监控应用配置
"""

from django.apps import AppConfig


class MonitorConfig(AppConfig):
    """监控应用配置"""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'monitor'
    verbose_name = '实盘监控'

    def ready(self):
        """应用就绪时的初始化"""
        pass
