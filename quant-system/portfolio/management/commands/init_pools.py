"""
品种池初始化命令
根据多维量化指标体系文档初始化ETF品种池

使用方法:
    python manage.py init_pools [--clear]
"""

from django.core.management.base import BaseCommand, CommandError
from portfolio.models import ETF, Pool, PoolMember


# ETF品种定义（来自多维量化指标体系文档）
ETF_DEFINITIONS = [
    # === 核心宽基 ===
    {'code': '510300', 'name': '沪深300ETF', 'market': 'SH', 'category': 'equity', 'tracking_index': '沪深300指数', 'fund_manager': '华泰柏瑞'},
    {'code': '510050', 'name': '上证50ETF', 'market': 'SH', 'category': 'equity', 'tracking_index': '上证50指数', 'fund_manager': '华夏基金'},
    {'code': '510500', 'name': '中证500ETF', 'market': 'SH', 'category': 'equity', 'tracking_index': '中证500指数', 'fund_manager': '南方基金'},
    {'code': '159915', 'name': '创业板ETF', 'market': 'SZ', 'category': 'equity', 'tracking_index': '创业板指数', 'fund_manager': '易方达'},
    {'code': '159901', 'name': '深证100ETF', 'market': 'SZ', 'category': 'equity', 'tracking_index': '深证100指数', 'fund_manager': '易方达'},
    {'code': '588000', 'name': '科创50ETF', 'market': 'SH', 'category': 'equity', 'tracking_index': '科创50指数', 'fund_manager': '华夏基金'},

    # === 跨境/行业 ===
    {'code': '513500', 'name': '标普500ETF', 'market': 'SH', 'category': 'cross_border', 'tracking_index': '标普500指数', 'fund_manager': '博时基金'},
    {'code': '513100', 'name': '纳斯达克ETF', 'market': 'SH', 'category': 'cross_border', 'tracking_index': '纳斯达克100指数', 'fund_manager': '国泰基金'},
    {'code': '513050', 'name': '恒生科技ETF', 'market': 'SH', 'category': 'cross_border', 'tracking_index': '恒生科技指数', 'fund_manager': '易方达'},
    {'code': '510900', 'name': 'H股ETF', 'market': 'SH', 'category': 'cross_border', 'tracking_index': '恒生H股指数', 'fund_manager': '易方达'},
    {'code': '159920', 'name': '恒生ETF', 'market': 'SZ', 'category': 'cross_border', 'tracking_index': '恒生指数', 'fund_manager': '华夏基金'},

    # === 商品/债券/货币 ===
    {'code': '518880', 'name': '黄金ETF', 'market': 'SH', 'category': 'commodity', 'tracking_index': '上海黄金交易所AU99.99', 'fund_manager': '华安基金'},
    {'code': '159934', 'name': '黄金ETF基金', 'market': 'SZ', 'category': 'commodity', 'tracking_index': '上海黄金交易所AU99.99', 'fund_manager': '易方达'},
    {'code': '511010', 'name': '国债ETF', 'market': 'SH', 'category': 'bond', 'tracking_index': '上证5年期国债指数', 'fund_manager': '国泰基金'},
    {'code': '511220', 'name': '信用债ETF', 'market': 'SH', 'category': 'bond', 'tracking_index': '上证10年期信用债指数', 'fund_manager': '海富通'},
    {'code': '511880', 'name': '银华日利ETF', 'market': 'SH', 'category': 'money_market', 'tracking_index': '活期存款利率', 'fund_manager': '银华基金'},
    {'code': '511990', 'name': '华宝添益ETF', 'market': 'SH', 'category': 'money_market', 'tracking_index': '活期存款利率', 'fund_manager': '华宝基金'},

    # === 行业/主题ETF ===
    {'code': '515700', 'name': '新能源ETF', 'market': 'SH', 'category': 'sector', 'tracking_index': '中证新能源指数', 'fund_manager': '易方达'},
    {'code': '159995', 'name': '芯片ETF', 'market': 'SZ', 'category': 'sector', 'tracking_index': '国证芯片指数', 'fund_manager': '华夏基金'},
    {'code': '515050', 'name': '5GETF', 'market': 'SH', 'category': 'sector', 'tracking_index': '5G通信指数', 'fund_manager': '华夏基金'},
    {'code': '512480', 'name': '半导体ETF', 'market': 'SH', 'category': 'sector', 'tracking_index': '中证全指半导体指数', 'fund_manager': '国联安'},
    {'code': '159928', 'name': '消费ETF', 'market': 'SZ', 'category': 'sector', 'tracking_index': '中证主要消费指数', 'fund_manager': '汇添富'},
    {'code': '512010', 'name': '医药ETF', 'market': 'SH', 'category': 'sector', 'tracking_index': '中证医药卫生指数', 'fund_manager': '易方达'},
]


# 品种池定义（来自多维量化指标体系文档）
POOL_DEFINITIONS = [
    {
        'code': 'rotation_pool',
        'name': 'ETF周度轮动品种池',
        'purpose': 'rotation',
        'description': '核心宽基ETF池，用于周度轮动策略，包含沪深300、上证50、中证500、创业板等主要宽基指数ETF',
        'asset_classes': {
            'equity': 1.0,  # 纯权益类
        },
        'members': [
            # 核心宽基
            {'code': '510300', 'weight': 0.0, 'order': 1},  # 沪深300ETF
            {'code': '510050', 'weight': 0.0, 'order': 2},  # 上证50ETF
            {'code': '510500', 'weight': 0.0, 'order': 3},  # 中证500ETF
            {'code': '159915', 'weight': 0.0, 'order': 4},  # 创业板ETF
            {'code': '159901', 'weight': 0.0, 'order': 5},  # 深证100ETF
            {'code': '588000', 'weight': 0.0, 'order': 6},  # 科创50ETF
        ]
    },
    {
        'code': 'permanent_pool',
        'name': '永久组合品种池',
        'purpose': 'permanent',
        'description': '哈利·布朗永久组合实现池，包含权益、债券、黄金、现金四大类资产',
        'asset_classes': {
            'equity': 0.40,    # 权益40%
            'bond': 0.25,      # 债券25%
            'gold': 0.20,      # 黄金20%
            'cash': 0.15,      # 现金15%
        },
        'members': [
            # 权益
            {'code': '510300', 'weight': 0.20, 'order': 1},  # 沪深300ETF 20%
            {'code': '513500', 'weight': 0.20, 'order': 2},  # 标普500ETF 20%
            # 债券
            {'code': '511010', 'weight': 0.15, 'order': 3},  # 国债ETF 15%
            {'code': '511220', 'weight': 0.10, 'order': 4},  # 信用债ETF 10%
            # 黄金
            {'code': '518880', 'weight': 0.20, 'order': 5},  # 黄金ETF 20%
            # 现金
            {'code': '511880', 'weight': 0.15, 'order': 6},  # 银华日利ETF 15%
        ]
    },
    {
        'code': 'thematic_pool',
        'name': '主题仓位品种池',
        'purpose': 'thematic',
        'description': '主题/行业ETF池，用于主题仓位策略，包含新能源、芯片、5G、消费等主题',
        'asset_classes': {
            'equity': 1.0,
        },
        'members': [
            # 科技
            {'code': '159995', 'weight': 0.0, 'order': 1},  # 芯片ETF
            {'code': '515050', 'weight': 0.0, 'order': 2},  # 5GETF
            {'code': '512480', 'weight': 0.0, 'order': 3},  # 半导体ETF
            {'code': '588000', 'weight': 0.0, 'order': 4},  # 科创50ETF
            # 新能源
            {'code': '515700', 'weight': 0.0, 'order': 5},  # 新能源ETF
            # 消费
            {'code': '159928', 'weight': 0.0, 'order': 6},  # 消费ETF
            # 医药
            {'code': '512010', 'weight': 0.0, 'order': 7},  # 医药ETF
            # 跨境
            {'code': '513500', 'weight': 0.0, 'order': 8},  # 标普500ETF
            {'code': '513100', 'weight': 0.0, 'order': 9},  # 纳斯达克ETF
            {'code': '513050', 'weight': 0.0, 'order': 10}, # 恒生科技ETF
            # 商品
            {'code': '518880', 'weight': 0.0, 'order': 11}, # 黄金ETF
        ]
    },
    {
        'code': 'option_underlying_pool',
        'name': '期权标的池',
        'purpose': 'rotation',
        'description': '场内ETF期权标的池，包含50ETF和300ETF，用于L4缺口层指标计算',
        'asset_classes': {
            'equity': 1.0,
        },
        'members': [
            {'code': '510050', 'weight': 0.5, 'order': 1},  # 50ETF - 期权标的
            {'code': '510300', 'weight': 0.5, 'order': 2},  # 300ETF - 期权标的
        ]
    },
    {
        'code': 'money_market_pool',
        'name': '货币基金池',
        'purpose': 'permanent',
        'description': '货币市场基金ETF池，作为现金等价物，用于防御性配置',
        'asset_classes': {
            'cash': 1.0,
        },
        'members': [
            {'code': '511880', 'weight': 0.5, 'order': 1},  # 银华日利ETF
            {'code': '511990', 'weight': 0.5, 'order': 2},  # 华宝添益ETF
        ]
    },
]


class Command(BaseCommand):
    help = '初始化ETF品种池数据'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='清除现有数据后重新初始化',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write(self.style.WARNING('正在清除现有数据...'))
            PoolMember.objects.all().delete()
            Pool.objects.all().delete()
            ETF.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('现有数据已清除'))

        self.stdout.write(self.style.HTTP_INFO('开始初始化ETF数据...'))
        etf_created, etf_updated = self.init_etfs()

        self.stdout.write(self.style.HTTP_INFO('开始初始化品种池...'))
        pool_created, member_count = self.init_pools()

        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('初始化完成！'))
        self.stdout.write('=' * 60)
        self.stdout.write(f'ETF: 创建 {etf_created} 条, 更新 {etf_updated} 条')
        self.stdout.write(f'品种池: 创建 {pool_created} 个')
        self.stdout.write(f'池成员: 创建 {member_count} 个')
        self.stdout.write('=' * 60)

    def init_etfs(self):
        """初始化ETF数据"""
        created_count = 0
        updated_count = 0

        for etf_data in ETF_DEFINITIONS:
            try:
                etf, created = ETF.objects.update_or_create(
                    code=etf_data['code'],
                    defaults={
                        'name': etf_data['name'],
                        'market': etf_data['market'],
                        'category': etf_data['category'],
                        'tracking_index': etf_data.get('tracking_index', ''),
                        'fund_manager': etf_data.get('fund_manager', ''),
                        'is_active': True,
                    }
                )
                if created:
                    created_count += 1
                    self.stdout.write(f"  创建ETF: {etf.code} - {etf.name}")
                else:
                    updated_count += 1
                    self.stdout.write(f"  更新ETF: {etf.code} - {etf.name}")
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  错误处理ETF {etf_data.get('code')}: {e}"))

        return created_count, updated_count

    def init_pools(self):
        """初始化品种池数据"""
        pool_created = 0
        member_count = 0

        for pool_data in POOL_DEFINITIONS:
            try:
                # 创建或更新品种池
                pool, created = Pool.objects.update_or_create(
                    code=pool_data['code'],
                    defaults={
                        'name': pool_data['name'],
                        'purpose': pool_data['purpose'],
                        'description': pool_data.get('description', ''),
                        'asset_classes': pool_data.get('asset_classes', {}),
                        'is_active': True,
                    }
                )

                if created:
                    pool_created += 1
                    self.stdout.write(f"\n  创建品种池: {pool.code} - {pool.name}")
                else:
                    self.stdout.write(f"\n  更新品种池: {pool.code} - {pool.name}")

                # 添加池成员
                for member_data in pool_data.get('members', []):
                    try:
                        etf = ETF.objects.get(code=member_data['code'])
                        member, member_created = PoolMember.objects.update_or_create(
                            pool=pool,
                            etf=etf,
                            defaults={
                                'weight': member_data.get('weight', 0),
                                'order': member_data.get('order', 0),
                                'is_active': True,
                            }
                        )
                        member_count += 1
                        if member_created:
                            self.stdout.write(f"    + 添加成员: {etf.code} - {etf.name}")
                    except ETF.DoesNotExist:
                        self.stdout.write(self.style.WARNING(f"    ! ETF不存在: {member_data['code']}"))
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"    ! 添加成员失败 {member_data['code']}: {e}"))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  错误处理品种池 {pool_data.get('code')}: {e}"))

        return pool_created, member_count
