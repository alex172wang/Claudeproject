"""
投资组合应用配置
"""

from django.apps import AppConfig


class PortfolioConfig(AppConfig):
    """投资组合应用配置"""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'portfolio'
    verbose_name = '投资组合管理'

    def ready(self):
        """应用就绪时的初始化"""
        pass
