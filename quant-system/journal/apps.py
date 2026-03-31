"""
偏差日志应用配置
"""

from django.apps import AppConfig


class JournalConfig(AppConfig):
    """偏差日志应用配置"""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'journal'
    verbose_name = '偏差日志'

    def ready(self):
        """应用就绪时的初始化"""
        pass
