"""
数据同步服务

协调数据拉取、缓存更新和数据库写入
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import threading
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from .adapters import MootdxAdapter, DataSourceManager
from .cache_manager import cache_manager
from portfolio.models import ETF
from django.db import transaction

logger = logging.getLogger(__name__)


class SyncStatus(Enum):
    """同步状态"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class SyncTask:
    """同步任务"""
    id: str
    name: str
    task_type: str
    params: Dict[str, Any] = field(default_factory=dict)
    status: SyncStatus = SyncStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: int = 0  # 0-100

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'name': self.name,
            'task_type': self.task_type,
            'params': self.params,
            'status': self.status.value,
            'result': self.result,
            'error': self.error,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'progress': self.progress,
        }


class DataSyncService:
    """数据同步服务"""

    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._tasks: Dict[str, SyncTask] = {}
        self._lock = threading.Lock()
        self._running = False
        self._scheduler_thread: Optional[threading.Thread] = None

        # 初始化数据源管理器
        self._init_data_sources()

    def _init_data_sources(self):
        """初始化数据源"""
        # 注册 mootdx 适配器
        mootdx_adapter = MootdxAdapter(config={'market': 'std'})
        from .adapters import data_source_manager
        data_source_manager.register('mootdx', mootdx_adapter, primary=True)

        logger.info("[DataSyncService] 数据源初始化完成")

    # ========================================================================
    # 任务管理
    # ========================================================================

    def create_task(self, name: str, task_type: str,
                    params: Optional[Dict] = None) -> SyncTask:
        """创建同步任务"""
        import uuid

        task_id = str(uuid.uuid4())[:8]
        task = SyncTask(
            id=task_id,
            name=name,
            task_type=task_type,
            params=params or {},
        )

        with self._lock:
            self._tasks[task_id] = task

        logger.info(f"[DataSyncService] 创建任务: {task_id} - {name}")
        return task

    def get_task(self, task_id: str) -> Optional[SyncTask]:
        """获取任务"""
        return self._tasks.get(task_id)

    def list_tasks(self, status: Optional[SyncStatus] = None) -> List[SyncTask]:
        """列出任务"""
        tasks = list(self._tasks.values())
        if status:
            tasks = [t for t in tasks if t.status == status]
        return tasks

    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        task = self._tasks.get(task_id)
        if task and task.status in [SyncStatus.PENDING, SyncStatus.RUNNING]:
            task.status = SyncStatus.CANCELLED
            task.completed_at = datetime.now()
            logger.info(f"[DataSyncService] 取消任务: {task_id}")
            return True
        return False

    # ========================================================================
    # 同步操作
    # ========================================================================

    def sync_etf_list(self, force: bool = False) -> SyncTask:
        """同步 ETF 列表"""
        task = self.create_task(
            name="同步 ETF 列表",
            task_type="sync_etf_list",
            params={'force': force}
        )

        def _sync():
            try:
                task.status = SyncStatus.RUNNING
                task.started_at = datetime.now()

                # TODO: 从外部数据源获取 ETF 列表
                # 目前使用预设的 ETF 列表
                etf_list = [
                    {'code': '510300', 'name': '沪深300ETF', 'category': 'broad', 'exchange': 'SH'},
                    {'code': '510500', 'name': '中证500ETF', 'category': 'broad', 'exchange': 'SH'},
                    {'code': '512800', 'name': '银行ETF', 'category': 'sector', 'exchange': 'SH'},
                    {'code': '518880', 'name': '黄金ETF', 'category': 'commodity', 'exchange': 'SH'},
                ]

                # 更新或创建 ETF 记录
                with transaction.atomic():
                    for etf_data in etf_list:
                        ETF.objects.update_or_create(
                            code=etf_data['code'],
                            defaults={
                                'name': etf_data['name'],
                                'category': etf_data['category'],
                                'exchange': etf_data['exchange'],
                                'status': 'active',
                            }
                        )

                task.result = {'count': len(etf_list)}
                task.status = SyncStatus.SUCCESS
                task.progress = 100

            except Exception as e:
                task.status = SyncStatus.FAILED
                task.error = str(e)
                logger.error(f"[DataSyncService] 同步 ETF 列表失败: {e}")

            finally:
                task.completed_at = datetime.now()

        # 提交任务到线程池
        self._executor.submit(_sync)

        return task

    def sync_kline_data(self, code: str, period: str = 'day',
                        days: int = 365, force: bool = False) -> SyncTask:
        """同步 K 线数据"""
        task = self.create_task(
            name=f"同步 {code} {period} K 线数据",
            task_type="sync_kline",
            params={
                'code': code,
                'period': period,
                'days': days,
                'force': force
            }
        )

        def _sync():
            try:
                task.status = SyncStatus.RUNNING
                task.started_at = datetime.now()

                # 获取数据源适配器
                from .adapters import data_source_manager
                adapter = data_source_manager.get_adapter()

                if not adapter or not adapter.is_connected():
                    raise DataSourceError("数据源未连接")

                # 计算日期范围
                end_date = datetime.now()
                start_date = end_date - timedelta(days=days)

                # 拉取数据
                df = adapter.get_kline(
                    symbol=code,
                    period=period,
                    start_date=start_date,
                    end_date=end_date
                )

                if df.empty:
                    raise DataSourceError(f"获取 {code} K 线数据为空")

                # 保存到数据库
                # TODO: 实现 K 线数据模型和保存逻辑

                # 更新缓存
                cache_key = f"kline:{code}:{period}"
                cache_manager.set(cache_key, df, timeout=300)

                task.result = {
                    'code': code,
                    'period': period,
                    'count': len(df),
                    'start_date': df['date'].min() if 'date' in df.columns else None,
                    'end_date': df['date'].max() if 'date' in df.columns else None,
                }
                task.status = SyncStatus.SUCCESS
                task.progress = 100

            except Exception as e:
                task.status = SyncStatus.FAILED
                task.error = str(e)
                logger.error(f"[DataSyncService] 同步 K 线数据失败: {e}")

            finally:
                task.completed_at = datetime.now()

        # 提交任务到线程池
        self._executor.submit(_sync)

        return task

    def sync_all(self, force: bool = False) -> List[SyncTask]:
        """执行全量同步"""
        tasks = []

        # 1. 同步 ETF 列表
        tasks.append(self.sync_etf_list(force=force))

        # 2. 同步活跃 ETF 的 K 线数据
        active_etfs = ETF.objects.filter(status='active')
        for etf in active_etfs[:10]:  # 先同步前 10 个
            tasks.append(
                self.sync_kline_data(
                    code=etf.code,
                    period='day',
                    days=365,
                    force=force
                )
            )

        return tasks

    # ========================================================================
    # 调度器
    # ========================================================================

    def start_scheduler(self):
        """启动调度器"""
        if self._running:
            logger.warning("[DataSyncService] 调度器已在运行")
            return

        self._running = True
        self._scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self._scheduler_thread.start()

        logger.info("[DataSyncService] 调度器已启动")

    def stop_scheduler(self):
        """停止调度器"""
        self._running = False

        if self._scheduler_thread:
            self._scheduler_thread.join(timeout=5)

        # 关闭线程池
        self._executor.shutdown(wait=False)

        logger.info("[DataSyncService] 调度器已停止")

    def _scheduler_loop(self):
        """调度器主循环"""
        # 调度配置（秒）
        schedule_config = {
            'sync_etf_list': 3600,  # 每小时同步 ETF 列表
            'sync_realtime_quote': 5,  # 每 5 秒同步实时行情
            'sync_kline_daily': 86400,  # 每天同步 K 线
        }

        last_run = {key: 0 for key in schedule_config.keys()}

        while self._running:
            try:
                current_time = time.time()

                # 检查并执行任务
                for task_name, interval in schedule_config.items():
                    if current_time - last_run[task_name] >= interval:
                        self._execute_scheduled_task(task_name)
                        last_run[task_name] = current_time

                # 休眠 1 秒
                time.sleep(1)

            except Exception as e:
                logger.error(f"[DataSyncService] 调度器错误: {e}")
                time.sleep(5)

    def _execute_scheduled_task(self, task_name: str):
        """执行定时任务"""
        try:
            if task_name == 'sync_etf_list':
                self.sync_etf_list()

            elif task_name == 'sync_realtime_quote':
                # 同步活跃 ETF 的实时行情
                pass  # TODO: 实现实时行情同步

            elif task_name == 'sync_kline_daily':
                # 同步所有活跃 ETF 的日 K 线
                pass  # TODO: 实现日 K 线同步

        except Exception as e:
            logger.error(f"[DataSyncService] 执行定时任务 {task_name} 失败: {e}")


    # ========================================================================
    # 实时行情同步（供 tasks.py 调用）
    # ========================================================================

    def get_realtime_quote(self, code: str) -> Optional[Dict[str, Any]]:
        """
        获取单个ETF的实时行情

        Args:
            code: ETF代码

        Returns:
            实时行情数据字典
        """
        try:
            from .adapters import data_source_manager
            adapter = data_source_manager.get_adapter()

            if not adapter:
                logger.warning("[DataSyncService] 没有可用的数据源适配器")
                return None

            if not adapter.is_connected() and not adapter.connect():
                logger.warning("[DataSyncService] 数据源连接失败")
                return None

            quote = adapter.get_realtime_quote(code)
            if quote:
                # 标准化字段名供 tasks.py 使用
                return {
                    'code': quote.get('code', code),
                    'name': quote.get('name', code),
                    'price': quote.get('current_price', 0),
                    'current_price': quote.get('current_price', 0),
                    'open': quote.get('open', 0),
                    'high': quote.get('high', 0),
                    'low': quote.get('low', 0),
                    'change': quote.get('change', 0),
                    'change_percent': quote.get('change_percent', 0),
                    'prev_close': quote.get('prev_close', quote.get('current_price', 0)),
                    'volume': quote.get('volume', 0),
                    'amount': quote.get('amount', 0),
                    'timestamp': quote.get('timestamp', datetime.now().isoformat()),
                }
            return None

        except Exception as e:
            logger.error(f"[DataSyncService] 获取 {code} 实时行情失败: {e}")
            return None

    def batch_sync_quotes(self, codes: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        批量同步实时行情

        Args:
            codes: ETF代码列表

        Returns:
            {code: quote_data} 字典
        """
        results = {}

        for code in codes:
            try:
                quote = self.get_realtime_quote(code)
                if quote:
                    results[code] = quote
            except Exception as e:
                logger.error(f"[DataSyncService] 同步 {code} 行情失败: {e}")
                continue

        return results

    def sync_historical_kline(self, code: str, start_date: str, end_date: str,
                              frequency: str = 'day') -> Optional[pd.DataFrame]:
        """
        同步历史K线数据

        Args:
            code: ETF代码
            start_date: 开始日期 'YYYY-MM-DD'
            end_date: 结束日期 'YYYY-MM-DD'
            frequency: 周期 'day'|'week'|'month'

        Returns:
            K线数据DataFrame
        """
        try:
            from .adapters import data_source_manager
            adapter = data_source_manager.get_adapter()

            if not adapter:
                logger.warning("[DataSyncService] 没有可用的数据源适配器")
                return None

            if not adapter.is_connected() and not adapter.connect():
                logger.warning("[DataSyncService] 数据源连接失败")
                return None

            # 解析日期
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')

            df = adapter.get_kline(
                symbol=code,
                period=frequency,
                start_date=start_dt,
                end_date=end_dt
            )

            return df

        except Exception as e:
            logger.error(f"[DataSyncService] 同步 {code} 历史K线失败: {e}")
            return None

    def clear_expired_cache(self):
        """清理过期缓存"""
        try:
            from .cache_manager import cache_manager
            cache_manager.clear_expired()
        except Exception as e:
            logger.error(f"[DataSyncService] 清理过期缓存失败: {e}")


# 创建全局数据同步服务实例
data_sync_service = DataSyncService()
