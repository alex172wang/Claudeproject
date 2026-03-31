"""
信号监控模块

实时监控交易信号、指标状态、市场异常等情况。
提供告警机制，支持多渠道通知。
"""

import json
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set


class AlertLevel(Enum):
    """告警级别"""
    DEBUG = "debug"           # 调试信息
    INFO = "info"             # 一般信息
    WARNING = "warning"       # 警告
    ERROR = "error"           # 错误
    CRITICAL = "critical"     # 严重错误


class AlertType(Enum):
    """告警类型"""
    SIGNAL_GENERATED = "signal_generated"      # 信号生成
    SIGNAL_CHANGED = "signal_changed"            # 信号变化
    THRESHOLD_BREACH = "threshold_breach"     # 阈值突破
    INDICATOR_ERROR = "indicator_error"        # 指标计算错误
    DATA_SOURCE_ERROR = "data_source_error"    # 数据源错误
    CONNECTION_LOST = "connection_lost"        # 连接断开
    MARKET_ANOMALY = "market_anomaly"          # 市场异常


@dataclass
class SignalAlert:
    """
    信号告警对象

    保存单次告警的完整信息
    """
    alert_id: str                           # 告警ID
    timestamp: datetime                     # 告警时间
    level: AlertLevel                       # 告警级别
    alert_type: AlertType                   # 告警类型
    source: str                             # 告警来源（指标/模块）
    title: str                              # 告警标题
    message: str                            # 告警消息
    symbol: Optional[str] = None            # 相关品种
    value: Optional[float] = None           # 触发值
    threshold: Optional[float] = None     # 阈值
    metadata: Dict[str, Any] = field(default_factory=dict)  # 附加数据
    acknowledged: bool = False              # 是否已确认
    acknowledged_by: Optional[str] = None # 确认人
    acknowledged_time: Optional[datetime] = None  # 确认时间

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'alert_id': self.alert_id,
            'timestamp': self.timestamp.isoformat(),
            'level': self.level.value,
            'alert_type': self.alert_type.value,
            'source': self.source,
            'title': self.title,
            'message': self.message,
            'symbol': self.symbol,
            'value': self.value,
            'threshold': self.threshold,
            'metadata': self.metadata,
            'acknowledged': self.acknowledged,
        }

    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    def acknowledge(self, user: str) -> None:
        """确认告警"""
        self.acknowledged = True
        self.acknowledged_by = user
        self.acknowledged_time = datetime.now()


class NotificationChannel(ABC):
    """
    通知渠道基类

    所有通知渠道（邮件、短信、钉钉等）必须继承此类
    """

    @abstractmethod
    def send(self, alert: SignalAlert) -> bool:
        """发送通知"""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """检查渠道是否可用"""
        pass


class ConsoleNotificationChannel(NotificationChannel):
    """控制台通知渠道"""

    def send(self, alert: SignalAlert) -> bool:
        level_colors = {
            AlertLevel.DEBUG: "\033[90m",      # 灰色
            AlertLevel.INFO: "\033[94m",       # 蓝色
            AlertLevel.WARNING: "\033[93m",    # 黄色
            AlertLevel.ERROR: "\033[91m",      # 红色
            AlertLevel.CRITICAL: "\033[95m",   # 紫色
        }
        reset = "\033[0m"
        color = level_colors.get(alert.level, "")

        print(f"{color}[{alert.level.value.upper()}] {alert.timestamp.strftime('%H:%M:%S')} "
              f"{alert.source} - {alert.title}{reset}")
        print(f"  {alert.message}")
        if alert.symbol:
            print(f"  Symbol: {alert.symbol}, Value: {alert.value}")
        return True

    def is_available(self) -> bool:
        return True


class SignalMonitor:
    """
    信号监控器

    监控系统中的信号、指标和异常情况，生成告警。
    支持多通知渠道和告警管理。

    功能：
    1. 监控指标阈值
    2. 监控信号变化
    3. 监控数据源状态
    4. 告警通知
    5. 告警历史管理

    示例：
        monitor = SignalMonitor()

        # 添加通知渠道
        monitor.add_channel(ConsoleNotificationChannel())

        # 监控指标
        monitor.watch_indicator('L101', threshold=50, direction='above')

        # 手动触发告警
        monitor.alert(
            level=AlertLevel.WARNING,
            alert_type=AlertType.SIGNAL_CHANGED,
            source='Strategy',
            title='Signal Changed',
            message='Buy signal generated for 510300'
        )
    """

    def __init__(self, max_history: int = 10000):
        """
        初始化监控器

        Args:
            max_history: 最大告警历史数量
        """
        self.max_history = max_history

        # 告警历史
        self._alerts: List[SignalAlert] = []
        self._alert_index: Dict[str, SignalAlert] = {}
        self._lock = threading.RLock()

        # 通知渠道
        self._channels: List[NotificationChannel] = []
        self._channel_filters: Dict[str, List[AlertLevel]] = {}

        # 监控规则
        self._indicator_watches: Dict[str, Dict] = {}
        self._signal_watches: Dict[str, Dict] = {}

        # 计数器
        self._alert_counter = 0

        # 默认添加控制台通知
        self.add_channel(ConsoleNotificationChannel())

    def add_channel(self, channel: NotificationChannel, name: Optional[str] = None,
                   filter_levels: Optional[List[AlertLevel]] = None) -> None:
        """
        添加通知渠道

        Args:
            channel: 通知渠道实例
            name: 渠道名称（用于后续管理）
            filter_levels: 过滤级别（只发送指定级别的告警）
        """
        self._channels.append(channel)
        if name:
            self._channel_filters[name] = filter_levels or []

    def remove_channel(self, channel: NotificationChannel) -> None:
        """移除通知渠道"""
        if channel in self._channels:
            self._channels.remove(channel)

    def alert(
        self,
        level: AlertLevel,
        alert_type: AlertType,
        source: str,
        title: str,
        message: str,
        symbol: Optional[str] = None,
        value: Optional[float] = None,
        threshold: Optional[float] = None,
        metadata: Optional[Dict] = None,
    ) -> SignalAlert:
        """
        触发告警

        Args:
            level: 告警级别
            alert_type: 告警类型
            source: 告警来源
            title: 告警标题
            message: 告警消息
            symbol: 相关品种
            value: 触发值
            threshold: 阈值
            metadata: 附加数据

        Returns:
            SignalAlert: 生成的告警对象
        """
        with self._lock:
            self._alert_counter += 1
            alert_id = f"ALT{datetime.now().strftime('%Y%m%d%H%M%S')}_{self._alert_counter:04d}"

            alert = SignalAlert(
                alert_id=alert_id,
                timestamp=datetime.now(),
                level=level,
                alert_type=alert_type,
                source=source,
                title=title,
                message=message,
                symbol=symbol,
                value=value,
                threshold=threshold,
                metadata=metadata or {},
            )

            # 保存到历史
            self._alerts.append(alert)
            self._alert_index[alert_id] = alert

            # 限制历史数量
            if len(self._alerts) > self.max_history:
                old_alert = self._alerts.pop(0)
                self._alert_index.pop(old_alert.alert_id, None)

        # 发送通知（在锁外）
        self._send_notifications(alert)

        return alert

    def _send_notifications(self, alert: SignalAlert) -> None:
        """发送通知到所有渠道"""
        for channel in self._channels:
            try:
                # 检查过滤条件
                if hasattr(channel, 'filter_levels'):
                    if alert.level not in channel.filter_levels:
                        continue

                if channel.is_available():
                    channel.send(alert)
            except Exception as e:
                print(f"[SignalMonitor] Channel error: {e}")

    def watch_indicator(
        self,
        indicator_id: str,
        threshold: float,
        direction: str = 'above',  # 'above', 'below', 'cross_up', 'cross_down'
        symbol: Optional[str] = None,
        level: AlertLevel = AlertLevel.WARNING,
    ) -> None:
        """
        监控指标阈值

        Args:
            indicator_id: 指标ID
            threshold: 阈值
            direction: 触发方向
            symbol: 关联品种
            level: 告警级别
        """
        self._indicator_watches[indicator_id] = {
            'threshold': threshold,
            'direction': direction,
            'symbol': symbol,
            'level': level,
        }
        print(f"[SignalMonitor] Watching indicator {indicator_id}: {direction} {threshold}")

    def check_indicator(
        self,
        indicator_id: str,
        value: float,
        symbol: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> Optional[SignalAlert]:
        """
        检查指标值是否触发告警

        Args:
            indicator_id: 指标ID
            value: 当前值
            symbol: 品种代码
            metadata: 附加数据

        Returns:
            SignalAlert: 如果触发告警则返回告警对象，否则None
        """
        if indicator_id not in self._indicator_watches:
            return None

        watch = self._indicator_watches[indicator_id]
        threshold = watch['threshold']
        direction = watch['direction']
        level = watch['level']

        triggered = False
        alert_type = AlertType.THRESHOLD_BREACH

        if direction == 'above' and value > threshold:
            triggered = True
        elif direction == 'below' and value < threshold:
            triggered = True
        elif direction in ['cross_up', 'cross_down']:
            # 需要历史数据判断穿越，这里简化处理
            pass

        if triggered:
            return self.alert(
                level=level,
                alert_type=alert_type,
                source=indicator_id,
                title=f"指标阈值触发: {indicator_id}",
                message=f"当前值 {value:.4f} {direction} 阈值 {threshold:.4f}",
                symbol=symbol or watch.get('symbol'),
                value=value,
                threshold=threshold,
                metadata=metadata,
            )

        return None

    def get_alert_history(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        level: Optional[AlertLevel] = None,
        alert_type: Optional[AlertType] = None,
        limit: int = 100,
    ) -> List[SignalAlert]:
        """
        获取告警历史

        Args:
            start_time: 开始时间
            end_time: 结束时间
            level: 告警级别过滤
            alert_type: 告警类型过滤
            limit: 返回数量限制

        Returns:
            List[SignalAlert]: 告警列表
        """
        with self._lock:
            alerts = self._alerts.copy()

        # 过滤
        if start_time:
            alerts = [a for a in alerts if a.timestamp >= start_time]
        if end_time:
            alerts = [a for a in alerts if a.timestamp <= end_time]
        if level:
            alerts = [a for a in alerts if a.level == level]
        if alert_type:
            alerts = [a for a in alerts if a.alert_type == alert_type]

        # 排序（时间倒序）并限制
        alerts = sorted(alerts, key=lambda a: a.timestamp, reverse=True)
        return alerts[:limit]

    def get_alert_by_id(self, alert_id: str) -> Optional[SignalAlert]:
        """根据ID获取告警"""
        with self._lock:
            return self._alert_index.get(alert_id)

    def acknowledge_alert(self, alert_id: str, user: str) -> bool:
        """确认告警"""
        alert = self.get_alert_by_id(alert_id)
        if alert:
            alert.acknowledge(user)
            return True
        return False

    def get_statistics(self) -> Dict[str, Any]:
        """获取告警统计"""
        with self._lock:
            alerts = self._alerts.copy()

        if not alerts:
            return {
                'total': 0,
                'by_level': {},
                'by_type': {},
                'unacknowledged': 0,
            }

        by_level = {}
        by_type = {}
        unacknowledged = 0

        for alert in alerts:
            # 按级别统计
            level = alert.level.value
            by_level[level] = by_level.get(level, 0) + 1

            # 按类型统计
            alert_type = alert.alert_type.value
            by_type[alert_type] = by_type.get(alert_type, 0) + 1

            # 未确认
            if not alert.acknowledged:
                unacknowledged += 1

        return {
            'total': len(alerts),
            'by_level': by_level,
            'by_type': by_type,
            'unacknowledged': unacknowledged,
        }

    def clear_history(self, before: Optional[datetime] = None) -> int:
        """
        清除历史告警

        Args:
            before: 清除此时间之前的告警，None则清除所有

        Returns:
            int: 清除的告警数量
        """
        with self._lock:
            if before is None:
                count = len(self._alerts)
                self._alerts.clear()
                self._alert_index.clear()
            else:
                to_remove = [a for a in self._alerts if a.timestamp < before]
                count = len(to_remove)
                for alert in to_remove:
                    self._alerts.remove(alert)
                    self._alert_index.pop(alert.alert_id, None)

            return count
