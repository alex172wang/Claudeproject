"""
数据同步任务模块

定义各种数据同步任务，供定时调度器调用
"""

import logging
from typing import List, Dict, Any
from datetime import datetime, timedelta

from django.utils import timezone

from portfolio.models import ETF
from .sync_service import data_sync_service
from .cache_manager import cache_manager

logger = logging.getLogger(__name__)

# 全局服务实例（使用简化的函数接口）
_service = data_sync_service
_cache = cache_manager


def get_realtime_quote(code: str) -> Dict[str, Any]:
    """获取实时行情（简化接口）"""
    return _service.get_realtime_quote(code)


def batch_sync_quotes(codes: List[str]) -> Dict[str, Any]:
    """批量同步行情（简化接口）"""
    return _service.batch_sync_quotes(codes)


def sync_historical_kline(code: str, start_date: str, end_date: str, frequency: str = 'day'):
    """同步历史K线（简化接口）"""
    return _service.sync_historical_kline(code, start_date, end_date, frequency)


class DataSyncTasks:
    """数据同步任务集合"""

    @staticmethod
    def sync_etf_list() -> int:
        """
        同步 ETF 列表

        Returns:
            新增的 ETF 数量
        """
        logger.info("[DataSyncTasks] 开始同步 ETF 列表")
        # 从配置文件读取 ETF 列表
        from django.conf import settings
        from portfolio.models import ETF
        etf_list = settings.QUANT_SYSTEM.get('etf_pool', [])
        count = 0
        from django.db import transaction
        with transaction.atomic():
            for etf_data in etf_list:
                obj, created = ETF.objects.update_or_create(
                    code=etf_data['code'],
                    defaults=etf_data
                )
                if created:
                    count += 1
        logger.info(f"[DataSyncTasks] ETF 列表同步完成，新增 {count} 个")
        return count

    @staticmethod
    def sync_realtime_quotes(codes: List[str] = None) -> Dict[str, Any]:
        """
        同步实时行情

        Args:
            codes: ETF 代码列表，为 None 则同步所有活跃的 ETF

        Returns:
            同步结果统计
        """
        if codes is None:
            codes = list(ETF.objects.filter(is_active=True).values_list('code', flat=True))

        logger.info(f"[DataSyncTasks] 开始同步 {len(codes)} 个 ETF 的实时行情")

        results = batch_sync_quotes(codes)

        # 更新缓存
        from django.conf import settings
        sync_config = settings.QUANT_SYSTEM.get('data_sync', {})
        quote_ttl = sync_config.get('quote_cache_ttl', 10)

        for code, data in results.items():
            cache_key = f'quote:{code}'
            _cache.set(cache_key, data, timeout=quote_ttl)

        stats = {
            'total': len(codes),
            'success': len(results),
            'failed': len(codes) - len(results),
            'timestamp': timezone.now().isoformat(),
        }

        logger.info(f"[DataSyncTasks] 实时行情同步完成: {stats}")
        return stats

    @staticmethod
    def sync_kline_history(code: str, days: int = 365) -> bool:
        """
        同步历史 K 线数据

        Args:
            code: ETF 代码
            days: 获取天数

        Returns:
            是否成功
        """
        logger.info(f"[DataSyncTasks] 开始同步 {code} 历史 K线，{days} 天")

        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        df = sync_historical_kline(
            code=code,
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d'),
            frequency='day'
        )

        if df is not None and not df.empty:
            # 存入缓存
            cache_key = f'kline:{code}:day:{days}'
            _cache.set(cache_key, df, timeout=3600)  # 1 小时过期

            logger.info(f"[DataSyncTasks] {code} 历史 K线同步完成，共 {len(df)} 条")
            return True
        else:
            logger.warning(f"[DataSyncTasks] {code} 历史 K线同步失败")
            return False

    @staticmethod
    def cleanup_expired_cache() -> int:
        """
        清理过期缓存

        Returns:
            清理的键数量
        """
        logger.info("[DataSyncTasks] 开始清理过期缓存")

        # 获取所有缓存键
        all_keys = _cache.keys('quote:*') + _cache.keys('kline:*')

        # 检查并删除过期的键
        cleared = 0
        for key in all_keys:
            if not _cache.exists(key):
                cleared += 1

        # 清理本地缓存
        _service.clear_expired_cache()

        logger.info(f"[DataSyncTasks] 过期缓存清理完成，共 {cleared} 个")
        return cleared


# 任务快捷函数
def sync_etf_list() -> int:
    """同步 ETF 列表"""
    return DataSyncTasks.sync_etf_list()


def sync_realtime_quotes(codes: List[str] = None) -> Dict[str, Any]:
    """同步实时行情"""
    return DataSyncTasks.sync_realtime_quotes(codes)


def sync_kline_history(code: str, days: int = 365) -> bool:
    """同步历史 K 线"""
    return DataSyncTasks.sync_kline_history(code, days)


def cleanup_expired_cache() -> int:
    """清理过期缓存"""
    return DataSyncTasks.cleanup_expired_cache()


# tasks 兼容对象（供 views_v2.py 使用）
class _TasksCompat:
    """tasks 兼容封装，暴露 service 属性"""
    service = _service

    def get_realtime_quote(self, code):
        return _service.get_realtime_quote(code)

    def get_kline(self, code, frequency='day', limit=60):
        return _service.sync_historical_kline(code, '', '', frequency)

    def batch_sync_quotes(self, codes):
        return _service.batch_sync_quotes(codes)


tasks = _TasksCompat()
