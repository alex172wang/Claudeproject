"""
API 视图集

提供数据集中化的 RESTful API 服务
"""

import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.utils import timezone
from datetime import datetime, timedelta

from portfolio.models import ETF
from backtest.models import BacktestTask, BacktestResult
from journal.models import DecisionLog, DeviationLog


from .serializers import (
    ETFSerializer, ETFPriceSerializer, KlineDataSerializer,
    PortfolioSummarySerializer, PositionSerializer,
    BacktestTaskSerializer, BacktestResultSerializer,
    DecisionLogSerializer, DeviationLogSerializer
)

logger = logging.getLogger(__name__)


class ETFViewSet(viewsets.ReadOnlyModelViewSet):
    """ETF 品种 API"""
    queryset = ETF.objects.filter(is_active=True)
    serializer_class = ETFSerializer
    permission_classes = [AllowAny]
    lookup_field = 'code'

    @action(detail=True, methods=['get'])
    def price(self, request, code=None):
        """获取实时价格"""
        etf = self.get_object()

        # 尝试从缓存获取
        try:
            from data_sync.cache_manager import cache_manager
            cache_key = f'quote:{etf.code}'
            cached_quote = cache_manager.get(cache_key)

            if cached_quote:
                logger.info(f"[ETFViewSet] 从缓存获取 {etf.code} 价格")
                change_percent = (cached_quote.get('change', 0) / cached_quote.get('prev_close', 1)) * 100 if cached_quote.get('prev_close', 0) != 0 else 0
                data = {
                    'code': etf.code,
                    'name': etf.name,
                    'current_price': cached_quote.get('price', 0),
                    'change': cached_quote.get('change', 0),
                    'change_percent': round(change_percent, 2),
                    'volume': cached_quote.get('volume', 0),
                    'turnover': cached_quote.get('amount', 0),
                    'update_time': timezone.now()
                }
                serializer = ETFPriceSerializer(data)
                return Response(serializer.data)
        except Exception as e:
            logger.warning(f"[ETFViewSet] 缓存获取失败: {e}")

        # 尝试从 data_sync 获取真实数据
        try:
            from data_sync.tasks import get_realtime_quote
            quote = get_realtime_quote(etf.code)
            if quote:
                change_percent = (quote.get('change', 0) / quote.get('prev_close', 1)) * 100 if quote.get('prev_close', 0) != 0 else 0
                data = {
                    'code': etf.code,
                    'name': etf.name,
                    'current_price': quote.get('price', 0),
                    'change': quote.get('change', 0),
                    'change_percent': round(change_percent, 2),
                    'volume': quote.get('volume', 0),
                    'turnover': quote.get('amount', 0),
                    'update_time': timezone.now()
                }
                serializer = ETFPriceSerializer(data)
                return Response(serializer.data)
        except Exception as e:
            logger.error(f"[ETFViewSet] 获取 {etf.code} 实时价格失败: {e}")

        return Response({'detail': '无法获取实时价格'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    @action(detail=True, methods=['get'])
    def kline(self, request, code=None):
        """获取 K 线数据"""
        etf = self.get_object()

        # 获取参数
        period = request.query_params.get('period', 'day')
        days = int(request.query_params.get('days', 60))

        # 尝试从缓存获取
        try:
            from data_sync.cache_manager import cache_manager
            cache_key = f'kline:{etf.code}:{period}:{days}'
            cached_df = cache_manager.get(cache_key)

            if cached_df is not None and not cached_df.empty:
                logger.info(f"[ETFViewSet] 从缓存获取 {etf.code} K线")
                data = []
                for _, row in cached_df.iterrows():
                    data.append({
                        'date': row.get('date') if 'date' in row else row.name,
                        'open': float(row.get('open', 0)),
                        'high': float(row.get('high', 0)),
                        'low': float(row.get('low', 0)),
                        'close': float(row.get('close', 0)),
                        'volume': int(row.get('volume', 0)),
                        'amount': float(row.get('amount', 0)),
                    })
                serializer = KlineDataSerializer(data, many=True)
                return Response(serializer.data)
        except Exception as e:
            logger.warning(f"[ETFViewSet] 缓存获取K线失败: {e}")

        # 尝试获取真实数据
        try:
            from data_sync.sync_service import data_sync_service
            from datetime import datetime, timedelta
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days+10)

            df = data_sync_service.sync_historical_kline(
                etf.code,
                start_date.strftime('%Y-%m-%d'),
                end_date.strftime('%Y-%m-%d'),
                period
            )
            if df is not None and not df.empty:
                # 存入缓存
                from data_sync.cache_manager import cache_manager
                cache_key = f'kline:{etf.code}:{period}:{days}'
                cache_manager.set(cache_key, df, timeout=3600)

                # 转换格式
                data = []
                for _, row in df.iterrows():
                    data.append({
                        'date': row.get('date') if 'date' in row else row.name,
                        'open': float(row.get('open', 0)),
                        'high': float(row.get('high', 0)),
                        'low': float(row.get('low', 0)),
                        'close': float(row.get('close', 0)),
                        'volume': int(row.get('volume', 0)),
                        'amount': float(row.get('amount', 0)),
                    })

                serializer = KlineDataSerializer(data, many=True)
                return Response(serializer.data)
        except Exception as e:
            logger.error(f"[ETFViewSet] 获取 {etf.code} K线失败: {e}")

        return Response({'detail': '无法获取K线数据'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    @action(detail=False, methods=['get'])
    def categories(self, request):
        """获取 ETF 分类列表"""
        categories = dict(ETF.CATEGORY_CHOICES)
        return Response(categories)


class PortfolioViewSet(viewsets.ViewSet):
    """投资组合 API"""
    permission_classes = [AllowAny]

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """获取投资组合汇总"""
        data = {
            'total_assets': 0.0,
            'total_return': 0.0,
            'sharpe_ratio': 0.0,
            'max_drawdown': 0.0,
            'update_time': timezone.now()
        }
        serializer = PortfolioSummarySerializer(data)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def positions(self, request):
        """获取当前持仓"""
        positions = []
        serializer = PositionSerializer(positions, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def equity_curve(self, request):
        """获取权益曲线"""
        return Response([])


class BacktestViewSet(viewsets.ReadOnlyModelViewSet):
    """回测任务 API"""
    queryset = BacktestTask.objects.all().order_by('-created_at')
    serializer_class = BacktestTaskSerializer
    permission_classes = [AllowAny]

    @action(detail=True, methods=['get'])
    def result(self, request, pk=None):
        """获取回测结果"""
        task = self.get_object()
        try:
            result = BacktestResult.objects.get(task=task)
            serializer = BacktestResultSerializer(result)
            return Response(serializer.data)
        except BacktestResult.DoesNotExist:
            return Response(
                {'detail': '回测结果不存在'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['post'])
    def run(self, request):
        """启动回测任务"""
        return Response(
            {'detail': '回测任务已启动', 'task_id': 123},
            status=status.HTTP_202_ACCEPTED
        )


class MonitorViewSet(viewsets.ViewSet):
    """监控 API"""
    permission_classes = [AllowAny]

    @action(detail=False, methods=['get'])
    def signals(self, request):
        """获取当前信号"""
        return Response([])

    @action(detail=False, methods=['get'])
    def alerts(self, request):
        """获取预警列表"""
        return Response([])

    @action(detail=False, methods=['get'])
    def system_status(self, request):
        """获取系统状态"""
        from django.db import connection
        from django.utils import timezone

        # 检查数据库连接
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            db_status = 'connected'
        except Exception as e:
            db_status = f'error: {str(e)}'

        return Response({
            'status': 'running',
            'database': db_status,
            'timestamp': timezone.now(),
            'version': '1.0.0'
        })


class JournalViewSet(viewsets.ViewSet):
    """交易日志 API"""
    permission_classes = [AllowAny]

    @action(detail=False, methods=['get'])
    def decisions(self, request):
        """获取决策日志"""
        logs = DecisionLog.objects.all().order_by('-created_at')[:50]
        serializer = DecisionLogSerializer(logs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def deviations(self, request):
        """获取偏差日志"""
        logs = DeviationLog.objects.all().order_by('-created_at')[:50]
        serializer = DeviationLogSerializer(logs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def log_decision(self, request):
        """记录决策"""
        return Response(
            {'detail': '决策已记录'},
            status=status.HTTP_201_CREATED
        )


# ============ Instruments API ============

from portfolio.models import Pool, PoolMember


class InstrumentsETFViewSet(viewsets.ViewSet):
    """ETF 品种管理 API"""
    permission_classes = [AllowAny]

    def list(self, request):
        """获取所有 ETF"""
        etfs = ETF.objects.filter(is_active=True).order_by('code')
        data = [{
            'code': etf.code,
            'name': etf.name,
            'market': etf.market,
            'category': etf.category,
            'category_display': etf.category_display,
            'tracking_index': etf.tracking_index,
            'fund_manager': etf.fund_manager,
            'is_active': etf.is_active,
            'list_date': etf.list_date.strftime('%Y-%m-%d') if etf.list_date else None,
        } for etf in etfs]
        return Response({'success': True, 'data': data})

    def create(self, request):
        """创建 ETF"""
        code = request.data.get('code', '').strip()
        name = request.data.get('name', f'ETF{code}')
        market = request.data.get('market', 'SH')
        category = request.data.get('category', 'equity')

        if not code or len(code) != 6:
            return Response({'success': False, 'error': 'ETF代码必须为6位数字'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            etf, created = ETF.objects.get_or_create(
                code=code,
                defaults={
                    'name': name,
                    'market': market,
                    'category': category,
                    'is_active': True,
                }
            )
            if not created:
                return Response({'success': False, 'error': f'ETF {code} 已存在'}, status=status.HTTP_400_BAD_REQUEST)

            return Response({
                'success': True,
                'data': {
                    'code': etf.code,
                    'name': etf.name,
                    'market': etf.market,
                    'category': etf.category,
                }
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def destroy(self, request, pk=None):
        """删除 ETF（软删除）"""
        if not pk:
            return Response({'success': False, 'error': '缺少ETF代码'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            etf = ETF.objects.get(code=pk)
            etf.is_active = False
            etf.save()
            return Response({'success': True, 'message': f'ETF {pk} 已停用'})
        except ETF.DoesNotExist:
            return Response({'success': False, 'error': f'ETF {pk} 不存在'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class InstrumentsPoolViewSet(viewsets.ViewSet):
    """品种池管理 API"""
    permission_classes = [AllowAny]

    def list(self, request):
        """获取所有品种池"""
        pools = Pool.objects.filter(is_active=True).order_by('code')
        data = [{
            'code': pool.code,
            'name': pool.name,
            'purpose': pool.purpose,
            'purpose_display': pool.purpose_display,
            'description': pool.description,
            'member_count': pool.member_count,
            'is_active': pool.is_active,
            'created_at': pool.created_at.isoformat() if pool.created_at else None,
        } for pool in pools]
        return Response({'success': True, 'data': data})

    def create(self, request):
        """创建品种池"""
        code = request.data.get('code', '').strip()
        name = request.data.get('name', '').strip()
        purpose = request.data.get('purpose', 'custom')
        description = request.data.get('description', '')

        if not code or not name:
            return Response({'success': False, 'error': '池代码和名称不能为空'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            pool, created = Pool.objects.get_or_create(
                code=code,
                defaults={
                    'name': name,
                    'purpose': purpose,
                    'description': description,
                    'is_active': True,
                }
            )
            if not created:
                return Response({'success': False, 'error': f'品种池 {code} 已存在'}, status=status.HTTP_400_BAD_REQUEST)

            return Response({
                'success': True,
                'data': {
                    'code': pool.code,
                    'name': pool.name,
                    'purpose': pool.purpose,
                }
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def destroy(self, request, pk=None):
        """删除品种池（软删除）"""
        if not pk:
            return Response({'success': False, 'error': '缺少池代码'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            pool = Pool.objects.get(code=pk)
            pool.is_active = False
            pool.save()
            return Response({'success': True, 'message': f'品种池 {pk} 已停用'})
        except Pool.DoesNotExist:
            return Response({'success': False, 'error': f'品种池 {pk} 不存在'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class InstrumentsPoolMemberViewSet(viewsets.ViewSet):
    """池成员管理 API"""
    permission_classes = [AllowAny]

    def list(self, request, pool_code=None):
        """获取池成员列表"""
        if not pool_code:
            return Response({'success': False, 'error': '缺少池代码'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            pool = Pool.objects.get(code=pool_code, is_active=True)
            members = PoolMember.objects.filter(pool=pool, is_active=True).order_by('order', 'etf__code')
            data = [{
                'etf_code': m.etf.code,
                'etf_name': m.etf.name,
                'weight': float(m.weight) if m.weight else 0,
                'is_active': m.is_active,
            } for m in members]
            return Response({'success': True, 'data': data})
        except Pool.DoesNotExist:
            return Response({'success': False, 'error': f'品种池 {pool_code} 不存在'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create(self, request, pool_code=None):
        """向池添加成员"""
        if not pool_code:
            return Response({'success': False, 'error': '缺少池代码'}, status=status.HTTP_400_BAD_REQUEST)

        etf_code = request.data.get('etf_code', '').strip()
        if not etf_code:
            return Response({'success': False, 'error': '缺少ETF代码'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            pool = Pool.objects.get(code=pool_code, is_active=True)
            etf = ETF.objects.get(code=etf_code, is_active=True)

            member, created = PoolMember.objects.get_or_create(
                pool=pool,
                etf=etf,
                defaults={'weight': 0.0, 'is_active': True}
            )

            if not created:
                return Response({'success': False, 'error': f'{etf_code} 已在池中'})

            return Response({
                'success': True,
                'message': f'已将 {etf_code} 加入 {pool_code}'
            }, status=status.HTTP_201_CREATED)
        except Pool.DoesNotExist:
            return Response({'success': False, 'error': f'品种池 {pool_code} 不存在'}, status=status.HTTP_404_NOT_FOUND)
        except ETF.DoesNotExist:
            return Response({'success': False, 'error': f'ETF {etf_code} 不存在'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def destroy(self, request, pool_code=None, pk=None):
        """从池移除成员"""
        if not pool_code or not pk:
            return Response({'success': False, 'error': '缺少参数'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            pool = Pool.objects.get(code=pool_code, is_active=True)
            member = PoolMember.objects.get(pool=pool, etf__code=pk)
            member.is_active = False
            member.save()
            return Response({'success': True, 'message': f'已从 {pool_code} 移除 {pk}'})
        except Pool.DoesNotExist:
            return Response({'success': False, 'error': f'品种池 {pool_code} 不存在'}, status=status.HTTP_404_NOT_FOUND)
        except PoolMember.DoesNotExist:
            return Response({'success': False, 'error': f'{pk} 不在池中'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
