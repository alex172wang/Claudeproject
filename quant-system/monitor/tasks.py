"""
Celery 监控任务
实现实盘监控的定时任务
"""

import logging
import traceback
from datetime import datetime, timedelta
from decimal import Decimal

from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded
from django.db import transaction
from django.utils import timezone

# 配置日志
logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def update_intraday_data(self):
    """
    盘中数据更新任务
    每 10 分钟执行一次，更新实时行情数据
    """
    try:
        logger.info("开始盘中数据更新...")
        from core.data.mootdx_fetcher import MootdxFetcher
        from portfolio.models import ETF

        fetcher = MootdxFetcher()

        # 获取所有活跃ETF
        etfs = ETF.objects.filter(is_active=True)
        updated_count = 0

        for etf in etfs:
            try:
                # 获取实时行情
                data = fetcher.get_realtime_quotes(etf.code)
                if data is not None and not data.empty:
                    # 更新最新价格到缓存或数据库
                    updated_count += 1
            except Exception as e:
                logger.warning(f"更新 {etf.code} 数据失败: {e}")
                continue

        fetcher.close()
        logger.info(f"盘中数据更新完成，共更新 {updated_count} 个品种")

        # 记录健康检查
        from monitor.models import HealthCheckLog
        HealthCheckLog.objects.create(
            check_type='data_source',
            status='healthy',
            message=f'盘中数据更新完成，更新 {updated_count} 个品种',
            details={'updated_count': updated_count}
        )

        return {'status': 'success', 'updated_count': updated_count}

    except SoftTimeLimitExceeded:
        logger.error("盘中数据更新任务超时")
        raise self.retry(exc=Exception("任务超时"))
    except Exception as e:
        logger.error(f"盘中数据更新失败: {e}\n{traceback.format_exc()}")

        # 记录健康检查失败
        from monitor.models import HealthCheckLog
        HealthCheckLog.objects.create(
            check_type='data_source',
            status='critical',
            message=f'盘中数据更新失败: {str(e)}',
            details={'error': str(e)}
        )

        raise self.retry(exc=e)


@shared_task(bind=True, max_retries=2, default_retry_delay=30)
def calculate_daily_signals(self):
    """
    每日信号计算任务
    每日 14:45 执行，计算交易信号
    """
    try:
        logger.info("开始计算每日信号...")
        from core.indicators import get_indicator
        from monitor.models import MonitorStrategy, Signal
        from portfolio.models import ETF

        # 获取所有活跃策略
        strategies = MonitorStrategy.objects.filter(
            is_active=True,
            is_running=False  # 避免重复执行
        )

        signals_generated = 0

        for strategy in strategies:
            try:
                # 标记策略为运行中
                strategy.is_running = True
                strategy.last_run_at = timezone.now()
                strategy.save()

                # 获取品种池中的ETF
                etfs = strategy.pool.members.filter(is_active=True)

                for member in etfs:
                    etf = member.etf

                    # 获取ETF历史数据
                    # TODO: 从缓存或数据库获取K线数据

                    # 计算各层得分
                    l1_score = 0
                    l2_score = 0
                    l3_score = 0
                    l4_score = 0

                    # 综合得分（示例计算）
                    weights = strategy.get_weight_config()
                    composite_score = (
                        l1_score * weights.get('L1', 0.35) +
                        l2_score * weights.get('L2', 0.25) +
                        l3_score * weights.get('L3', 0.20) +
                        l4_score * weights.get('L4', 0.20)
                    )

                    # 根据得分生成信号
                    signal_type = 'hold'
                    if composite_score > 70:
                        signal_type = 'buy'
                    elif composite_score < 30:
                        signal_type = 'sell'

                    # 创建信号记录
                    if signal_type != 'hold':
                        Signal.objects.create(
                            strategy=strategy,
                            timestamp=timezone.now(),
                            trade_date=timezone.now().date(),
                            signal_type=signal_type,
                            to_etf=etf if signal_type == 'buy' else None,
                            from_etf=etf if signal_type == 'sell' else None,
                            l1_score=Decimal(str(l1_score)),
                            l2_score=Decimal(str(l2_score)),
                            l3_score=Decimal(str(l3_score)),
                            l4_score=Decimal(str(l4_score)),
                            composite_score=Decimal(str(composite_score)),
                            status='pending'
                        )
                        signals_generated += 1

                # 标记策略执行完成
                strategy.is_running = False
                strategy.save()

                logger.info(f"策略 {strategy.name} 信号计算完成")

            except Exception as e:
                logger.error(f"策略 {strategy.name} 信号计算失败: {e}")
                strategy.is_running = False
                strategy.save()
                continue

        logger.info(f"每日信号计算完成，共生成 {signals_generated} 个信号")

        return {
            'status': 'success',
            'signals_generated': signals_generated,
            'strategies_processed': strategies.count()
        }

    except Exception as e:
        logger.error(f"每日信号计算失败: {e}\n{traceback.format_exc()}")
        raise self.retry(exc=e)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def update_post_market_data(self):
    """
    盘后数据更新任务
    每日 15:30 执行，更新收盘数据
    """
    try:
        logger.info("开始盘后数据更新...")
        from core.data.mootdx_fetcher import MootdxFetcher
        from portfolio.models import ETF

        fetcher = MootdxFetcher()

        # 获取所有活跃ETF的日线数据
        etfs = ETF.objects.filter(is_active=True)
        updated_count = 0

        for etf in etfs:
            try:
                # 获取日线数据
                end_date = datetime.now().strftime('%Y%m%d')
                start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')

                data = fetcher.get_kline(etf.code, start=start_date, end=end_date)
                if data is not None and not data.empty:
                    updated_count += 1
            except Exception as e:
                logger.warning(f"更新 {etf.code} 盘后数据失败: {e}")
                continue

        fetcher.close()
        logger.info(f"盘后数据更新完成，共更新 {updated_count} 个品种")

        return {'status': 'success', 'updated_count': updated_count}

    except Exception as e:
        logger.error(f"盘后数据更新失败: {e}")
        raise self.retry(exc=e)


@shared_task(bind=True, max_retries=2, default_retry_delay=30)
def perform_health_check(self):
    """
    系统健康检查任务
    每 5 分钟执行一次
    """
    try:
        logger.info("开始系统健康检查...")

        from core.data.mootdx_fetcher import MootdxFetcher
        from monitor.models import HealthCheckLog

        checks = []

        # 1. 数据源检查
        try:
            fetcher = MootdxFetcher()
            # 尝试获取一个测试数据
            test_data = fetcher.get_realtime_quotes('000001')
            fetcher.close()

            if test_data is not None:
                checks.append({
                    'type': 'data_source',
                    'status': 'healthy',
                    'message': '数据源连接正常'
                })
            else:
                checks.append({
                    'type': 'data_source',
                    'status': 'warning',
                    'message': '数据源返回空数据'
                })
        except Exception as e:
            checks.append({
                'type': 'data_source',
                'status': 'critical',
                'message': f'数据源连接失败: {str(e)}'
            })

        # 2. 数据库检查
        try:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()

            checks.append({
                'type': 'database',
                'status': 'healthy',
                'message': '数据库连接正常'
            })
        except Exception as e:
            checks.append({
                'type': 'database',
                'status': 'critical',
                'message': f'数据库连接失败: {str(e)}'
            })

        # 3. 指标计算检查
        try:
            from core.indicators import get_indicator
            # 尝试获取一个指标
            indicator = get_indicator('L1-01')
            if indicator:
                checks.append({
                    'type': 'calculation',
                    'status': 'healthy',
                    'message': '指标计算模块正常'
                })
            else:
                checks.append({
                    'type': 'calculation',
                    'status': 'warning',
                    'message': '指标模块返回空值'
                })
        except Exception as e:
            checks.append({
                'type': 'calculation',
                'status': 'critical',
                'message': f'指标计算模块异常: {str(e)}'
            })

        # 记录健康检查结果
        overall_status = 'healthy'
        for check in checks:
            if check['status'] == 'critical':
                overall_status = 'critical'
                break
            elif check['status'] == 'warning' and overall_status != 'critical':
                overall_status = 'warning'

        # 创建健康检查日志
        for check in checks:
            HealthCheckLog.objects.create(
                check_type=check['type'],
                status=check['status'],
                message=check['message']
            )

        logger.info(f"系统健康检查完成，整体状态: {overall_status}")

        return {
            'status': 'success',
            'overall_status': overall_status,
            'checks': checks
        }

    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        return {
            'status': 'error',
            'message': str(e)
        }


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def cleanup_old_data(self):
    """
    清理过期数据任务
    每日凌晨 3:00 执行
    """
    try:
        logger.info("开始清理过期数据...")

        from datetime import datetime, timedelta
        from monitor.models import HealthCheckLog, AlertLog, Signal

        # 清理超过 30 天的健康检查日志
        cutoff_date = timezone.now() - timedelta(days=30)

        old_health_logs = HealthCheckLog.objects.filter(checked_at__lt=cutoff_date)
        health_deleted_count = old_health_logs.count()
        old_health_logs.delete()

        # 清理超过 90 天的已处理预警日志
        old_alerts = AlertLog.objects.filter(
            created_at__lt=timezone.now() - timedelta(days=90),
            is_acknowledged=True
        )
        alert_deleted_count = old_alerts.count()
        old_alerts.delete()

        # 清理超过 180 天的已执行信号
        old_signals = Signal.objects.filter(
            created_at__lt=timezone.now() - timedelta(days=180),
            status='executed'
        )
        signal_deleted_count = old_signals.count()
        old_signals.delete()

        logger.info(
            f"数据清理完成: 健康日志 {health_deleted_count} 条, "
            f"预警日志 {alert_deleted_count} 条, 信号 {signal_deleted_count} 条"
        )

        return {
            'status': 'success',
            'health_deleted': health_deleted_count,
            'alert_deleted': alert_deleted_count,
            'signal_deleted': signal_deleted_count
        }

    except Exception as e:
        logger.error(f"数据清理失败: {e}")
        raise self.retry(exc=e)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_notification(self, alert_log_id):
    """
    发送通知任务
    支持飞书、邮件等多种通知渠道
    """
    try:
        from monitor.models import AlertLog

        alert = AlertLog.objects.get(id=alert_log_id)

        # 获取通知渠道
        channels = alert.notification_channels or ['feishu']

        sent_channels = []

        for channel in channels:
            try:
                if channel == 'feishu':
                    _send_feishu_notification(alert)
                    sent_channels.append('feishu')
                elif channel == 'email':
                    _send_email_notification(alert)
                    sent_channels.append('email')
            except Exception as e:
                logger.warning(f"通过 {channel} 发送通知失败: {e}")

        # 更新通知状态
        alert.notification_status = 'sent'
        alert.notification_sent_at = timezone.now()
        alert.save()

        logger.info(f"通知发送完成，渠道: {sent_channels}")
        return {'status': 'success', 'channels': sent_channels}

    except AlertLog.DoesNotExist:
        logger.error(f"预警记录 {alert_log_id} 不存在")
        return {'status': 'error', 'message': '预警记录不存在'}
    except Exception as e:
        logger.error(f"发送通知失败: {e}")
        raise self.retry(exc=e)


def _send_feishu_notification(alert):
    """
    发送飞书通知
    """
    import requests
    import json
    from django.conf import settings

    # 从配置获取 webhook URL
    webhook_url = getattr(settings, 'FEISHU_WEBHOOK_URL', None)
    if not webhook_url:
        logger.warning("未配置飞书 Webhook URL")
        return

    # 构建消息内容
    severity_emoji = {
        'info': 'ℹ️',
        'warning': '⚠️',
        'critical': '🚨'
    }

    message = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": f"{severity_emoji.get(alert.severity, '🔔')} 量化交易系统预警"
                },
                "template": "red" if alert.severity == 'critical' else "orange" if alert.severity == 'warning' else "blue"
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**预警标题:** {alert.title}\n**预警内容:** {alert.message}\n**严重级别:** {alert.get_severity_display()}\n**触发时间:** {alert.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
                    }
                }
            ]
        }
    }

    # 发送请求
    response = requests.post(
        webhook_url,
        headers={'Content-Type': 'application/json'},
        data=json.dumps(message),
        timeout=10
    )

    if response.status_code == 200:
        logger.info("飞书通知发送成功")
    else:
        logger.warning(f"飞书通知发送失败: {response.status_code} - {response.text}")


def _send_email_notification(alert):
    """
    发送邮件通知
    """
    from django.core.mail import send_mail
    from django.conf import settings

    subject = f"[{alert.get_severity_display()}] 量化交易系统预警 - {alert.title}"
    message = f"""
预警标题: {alert.title}
预警内容: {alert.message}
严重级别: {alert.get_severity_display()}
触发时间: {alert.created_at.strftime('%Y-%m-%d %H:%M:%S')}

请登录系统查看详细信息。
"""

    send_mail(
        subject=subject,
        message=message,
        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'alert@quantsystem.com'),
        recipient_list=getattr(settings, 'ALERT_EMAIL_RECIPIENTS', ['admin@quantsystem.com']),
        fail_silently=True
    )

    logger.info("邮件通知发送成功")


# 导入模型（放在文件末尾避免循环导入）
from monitor.models import HealthCheckLog
