"""
回测应用配置
"""

from django.apps import AppConfig


class BacktestConfig(AppConfig):
    """回测应用配置"""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'backtest'
    verbose_name = '回测管理'

    def ready(self):
        """应用就绪时的初始化"""
        pass
