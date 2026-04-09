"""
数据同步应用配置

在 Django 启动时初始化数据同步调度器
"""

import logging
from django.apps import AppConfig
from django.conf import settings

logger = logging.getLogger(__name__)


class DataSyncConfig(AppConfig):
    """数据同步应用配置"""
    name = 'data_sync'
    verbose_name = '数据同步服务'

    def ready(self):
        """
        Django 应用就绪时调用

        在这里初始化并启动数据同步调度器
        """
        # 避免在运行管理命令时启动调度器（如 migrate、collectstatic 等）
        import sys
        is_manage_command = len(sys.argv) > 1 and sys.argv[1] in ['migrate', 'collectstatic', 'shell', 'test', 'dbshell', 'check']
        is_python_c = len(sys.argv) > 1 and sys.argv[1] == '-c'

        if is_manage_command or is_python_c:
            logger.info("[DataSync] 检测到管理命令或测试，跳过调度器启动")
            return

        # 只在 DEBUG 模式或显式配置时启动调度器
        auto_start = getattr(settings, 'QUANT_SYSTEM', {}).get('auto_start_sync', False)
        if not settings.DEBUG and not auto_start:
            logger.info("[DataSync] 非DEBUG模式且未配置自动启动，跳过调度器启动")
            return

        try:
            from data_sync.scheduler import get_scheduler

            logger.info("[DataSync] 正在初始化数据同步调度器...")

            # 获取调度器实例（会自动初始化）
            scheduler = get_scheduler()

            # 启动所有定时任务
            scheduler.start_all()

            logger.info("[DataSync] 数据同步调度器已启动")
            logger.info(f"[DataSync] 定时任务: {list(scheduler.get_status().keys())}")

        except Exception as e:
            logger.error(f"[DataSync] 调度器启动失败: {e}", exc_info=True)
