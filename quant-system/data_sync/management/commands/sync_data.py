"""
Django 管理命令：手动触发数据同步
"""

import logging
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError

from data_sync.tasks import (
    sync_etf_list,
    sync_realtime_quotes,
    sync_kline_history,
    cleanup_expired_cache,
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '数据同步管理命令'

    def add_arguments(self, parser):
        """添加命令行参数"""
        parser.add_argument(
            '--list',
            action='store_true',
            help='同步 ETF 列表',
        )
        parser.add_argument(
            '--quotes',
            action='store_true',
            help='同步实时行情',
        )
        parser.add_argument(
            '--kline',
            metavar='CODE',
            help='同步指定 ETF 的历史 K线',
        )
        parser.add_argument(
            '--days',
            type=int,
            default=365,
            help='K线数据天数（默认365天）',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='执行所有同步任务',
        )
        parser.add_argument(
            '--cleanup',
            action='store_true',
            help='清理过期缓存',
        )

    def handle(self, *args, **options):
        """执行命令"""
        start_time = datetime.now()
        self.stdout.write(self.style.SUCCESS(f'开始执行数据同步任务，时间：{start_time}'))

        try:
            if options['list'] or options['all']:
                self.stdout.write('正在同步 ETF 列表...')
                count = sync_etf_list()
                self.stdout.write(self.style.SUCCESS(f'ETF 列表同步完成，新增 {count} 个'))

            if options['quotes'] or options['all']:
                self.stdout.write('正在同步实时行情...')
                stats = sync_realtime_quotes()
                self.stdout.write(self.style.SUCCESS(
                    f'实时行情同步完成：成功 {stats["success"]}/{stats["total"]}，失败 {stats["failed"]}'
                ))

            if options['kline']:
                code = options['kline']
                days = options['days']
                self.stdout.write(f'正在同步 {code} 的历史 K线，{days} 天...')
                success = sync_kline_history(code, days)
                if success:
                    self.stdout.write(self.style.SUCCESS(f'{code} 历史 K线同步成功'))
                else:
                    self.stdout.write(self.style.WARNING(f'{code} 历史 K线同步失败'))

            if options['cleanup'] or options['all']:
                self.stdout.write('正在清理过期缓存...')
                cleared = cleanup_expired_cache()
                self.stdout.write(self.style.SUCCESS(f'过期缓存清理完成，清理了 {cleared} 个键'))

            if not any([
                options['list'],
                options['quotes'],
                options['kline'],
                options['all'],
                options['cleanup'],
            ]):
                self.stdout.write(self.style.WARNING('请指定至少一个操作：'))
                self.stdout.write('  --list       同步 ETF 列表')
                self.stdout.write('  --quotes     同步实时行情')
                self.stdout.write('  --kline CODE 同步指定 ETF 的历史 K线')
                self.stdout.write('  --all        执行所有同步任务')
                self.stdout.write('  --cleanup    清理过期缓存')

        except Exception as e:
            logger.error(f'数据同步失败: {e}')
            raise CommandError(f'数据同步失败: {e}')

        end_time = datetime.now()
        duration = end_time - start_time
        self.stdout.write(self.style.SUCCESS(f'所有任务完成，耗时：{duration}'))
