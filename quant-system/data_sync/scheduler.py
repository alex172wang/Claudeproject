"""
定时任务调度器

使用 Django Q 或 threading 实现简单的定时任务调度
"""

import logging
import threading
import time
from typing import Callable, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class ScheduledTask:
    """定时任务"""

    def __init__(
        self,
        func: Callable,
        interval_seconds: int,
        name: Optional[str] = None,
        immediate: bool = False,
    ):
        self.func = func
        self.interval_seconds = interval_seconds
        self.name = name or func.__name__
        self.immediate = immediate
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_run: Optional[datetime] = None
        self._next_run: Optional[datetime] = None

    def _run(self):
        """任务执行循环"""
        if self.immediate:
            self._execute_task()

        while self._running:
            try:
                now = datetime.now()
                wait_time = (self._next_run - now).total_seconds() if self._next_run else self.interval_seconds

                if wait_time > 0:
                    time.sleep(min(wait_time, 1))
                    continue

                self._execute_task()

            except Exception as e:
                logger.error(f"[ScheduledTask] 任务 {self.name} 执行异常: {e}")
                time.sleep(self.interval_seconds)

    def _execute_task(self):
        """执行任务"""
        try:
            self._last_run = datetime.now()
            self._next_run = self._last_run + timedelta(seconds=self.interval_seconds)

            logger.info(f"[ScheduledTask] 执行任务 {self.name}")
            self.func()

        except Exception as e:
            logger.error(f"[ScheduledTask] 任务 {self.name} 执行失败: {e}")

    def start(self):
        """启动任务"""
        if self._running:
            logger.warning(f"[ScheduledTask] 任务 {self.name} 已在运行中")
            return

        self._running = True
        self._next_run = datetime.now() + timedelta(seconds=self.interval_seconds)
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

        logger.info(f"[ScheduledTask] 任务 {self.name} 已启动，间隔 {self.interval_seconds} 秒")

    def stop(self):
        """停止任务"""
        if not self._running:
            logger.warning(f"[ScheduledTask] 任务 {self.name} 未在运行")
            return

        self._running = False
        if self._thread:
            self._thread.join(timeout=5)

        logger.info(f"[ScheduledTask] 任务 {self.name} 已停止")

    def status(self) -> dict:
        """获取任务状态"""
        return {
            'name': self.name,
            'running': self._running,
            'interval_seconds': self.interval_seconds,
            'last_run': self._last_run.isoformat() if self._last_run else None,
            'next_run': self._next_run.isoformat() if self._next_run else None,
        }


class DataSyncScheduler:
    """数据同步调度器"""

    def __init__(self):
        self._tasks: dict[str, ScheduledTask] = {}
        self._initialized = False

    def initialize(self):
        """初始化调度器"""
        if self._initialized:
            return

        # 从配置读取间隔
        from django.conf import settings
        sync_config = settings.QUANT_SYSTEM.get('data_sync', {})
        quote_interval = sync_config.get('quote_interval', 5)
        cleanup_interval = sync_config.get('cache_cleanup_interval', 3600)

        # 注册定时任务
        from data_sync.tasks import sync_realtime_quotes, cleanup_expired_cache

        # 实时行情同步
        self.add_task(
            name='sync_quotes',
            func=lambda: sync_realtime_quotes(),
            interval_seconds=quote_interval,
            immediate=True,
        )

        # 缓存清理
        self.add_task(
            name='cleanup_cache',
            func=cleanup_expired_cache,
            interval_seconds=cleanup_interval,
            immediate=False,
        )

        self._initialized = True
        logger.info("[DataSyncScheduler] 调度器已初始化")

    def add_task(
        self,
        name: str,
        func: Callable,
        interval_seconds: int,
        immediate: bool = False,
    ):
        """添加任务"""
        if name in self._tasks:
            logger.warning(f"[DataSyncScheduler] 任务 {name} 已存在，将被覆盖")
            self.stop_task(name)

        task = ScheduledTask(
            func=func,
            interval_seconds=interval_seconds,
            name=name,
            immediate=immediate,
        )
        self._tasks[name] = task

        logger.info(f"[DataSyncScheduler] 任务 {name} 已添加，间隔 {interval_seconds} 秒")

    def start_task(self, name: str):
        """启动指定任务"""
        if name not in self._tasks:
            raise ValueError(f"任务 {name} 不存在")

        self._tasks[name].start()

    def stop_task(self, name: str):
        """停止指定任务"""
        if name not in self._tasks:
            raise ValueError(f"任务 {name} 不存在")

        self._tasks[name].stop()

    def start_all(self):
        """启动所有任务"""
        for name in self._tasks:
            try:
                self.start_task(name)
            except Exception as e:
                logger.error(f"[DataSyncScheduler] 启动任务 {name} 失败: {e}")

        logger.info("[DataSyncScheduler] 所有任务已启动")

    def stop_all(self):
        """停止所有任务"""
        for name in self._tasks:
            try:
                self.stop_task(name)
            except Exception as e:
                logger.error(f"[DataSyncScheduler] 停止任务 {name} 失败: {e}")

        logger.info("[DataSyncScheduler] 所有任务已停止")

    def get_status(self) -> dict:
        """获取所有任务状态"""
        return {
            name: task.status()
            for name, task in self._tasks.items()
        }


# 全局调度器实例
_scheduler: Optional[DataSyncScheduler] = None


def get_scheduler() -> DataSyncScheduler:
    """获取全局调度器实例"""
    global _scheduler
    if _scheduler is None:
        _scheduler = DataSyncScheduler()
        _scheduler.initialize()
    return _scheduler
