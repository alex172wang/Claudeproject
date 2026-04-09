"""
API 路由配置
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from . import views, views_v2, ai_manager


# 创建路由器
router = DefaultRouter()

# 注册视图集
router.register(r'portfolio/etfs', views.ETFViewSet, basename='etf')
router.register(r'backtest/tasks', views.BacktestViewSet, basename='backtest-task')


@api_view(['GET'])
@permission_classes([AllowAny])
def api_root(request):
    """API 根路径"""
    return Response({
        'name': '量化交易系统 API',
        'version': '1.0.0',
        'endpoints': {
            'portfolio': {
                'etfs': '/api/portfolio/etfs/',
                'summary': '/api/portfolio/summary/',
                'positions': '/api/portfolio/positions/',
                'equity_curve': '/api/portfolio/equity_curve/',
            },
            'market': {
                'price': '/api/portfolio/etfs/{code}/price/',
                'kline': '/api/portfolio/etfs/{code}/kline/',
            },
            'backtest': {
                'tasks': '/api/backtest/tasks/',
                'run': '/api/backtest/run/',
            },
            'monitor': {
                'signals': '/api/monitor/signals/',
                'alerts': '/api/monitor/alerts/',
                'system_status': '/api/monitor/system_status/',
            },
            'journal': {
                'decisions': '/api/journal/decisions/',
                'deviations': '/api/journal/deviations/',
            },
        }
    })


# URL 配置
urlpatterns = [
    # API 根路径
    path('', api_root, name='api-root'),

    # 路由器生成的 URL
    path('', include(router.urls)),

    # Portfolio 额外端点
    path('portfolio/summary/', views.PortfolioViewSet.as_view({'get': 'summary'}), name='portfolio-summary'),
    path('portfolio/positions/', views.PortfolioViewSet.as_view({'get': 'positions'}), name='portfolio-positions'),
    path('portfolio/equity_curve/', views.PortfolioViewSet.as_view({'get': 'equity_curve'}), name='portfolio-equity-curve'),

    # Backtest 额外端点
    path('backtest/run/', views.BacktestViewSet.as_view({'post': 'run'}), name='backtest-run'),

    # Monitor 端点
    path('monitor/signals/', views.MonitorViewSet.as_view({'get': 'signals'}), name='monitor-signals'),
    path('monitor/alerts/', views.MonitorViewSet.as_view({'get': 'alerts'}), name='monitor-alerts'),
    path('monitor/system_status/', views.MonitorViewSet.as_view({'get': 'system_status'}), name='monitor-system-status'),

    # Journal 端点
    path('journal/decisions/', views.JournalViewSet.as_view({'get': 'decisions'}), name='journal-decisions'),
    path('journal/deviations/', views.JournalViewSet.as_view({'get': 'deviations'}), name='journal-deviations'),
    path('journal/log_decision/', views.JournalViewSet.as_view({'post': 'log_decision'}), name='journal-log-decision'),

    # AI 品种管理器端点
    path('ai/manager/', ai_manager.ai_manager, name='ai-manager'),
    path('ai/manager/help/', ai_manager.ai_manager_help, name='ai-manager-help'),

    # Instruments 端点 (ETF和品种池管理)
    path('instruments/etfs/', views.InstrumentsETFViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='instruments-etfs'),
    path('instruments/etfs/<str:pk>/', views.InstrumentsETFViewSet.as_view({
        'delete': 'destroy'
    }), name='instruments-etf-detail'),
    path('instruments/pools/', views.InstrumentsPoolViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='instruments-pools'),
    path('instruments/pools/<str:pk>/', views.InstrumentsPoolViewSet.as_view({
        'delete': 'destroy'
    }), name='instruments-pool-detail'),
    path('instruments/pools/<str:pool_code>/members/', views.InstrumentsPoolMemberViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='instruments-pool-members'),
    path('instruments/pools/<str:pool_code>/members/<str:pk>/', views.InstrumentsPoolMemberViewSet.as_view({
        'delete': 'destroy'
    }), name='instruments-pool-member-detail'),
]
