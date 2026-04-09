"""
AI 品种管理器

基于意图识别的智能品种管理 API
识别用户意图并执行相应的 ETF 品种、品种池管理操作
"""

import re
import logging
from typing import Dict, List, Any, Optional, Tuple
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.db import transaction

from portfolio.models import ETF, Pool, PoolMember

logger = logging.getLogger(__name__)


class IntentRecognizer:
    """意图识别器"""

    # 意图模式定义
    INTENT_PATTERNS = {
        'list_etfs': [
            r'.*列出.*ETF.*',
            r'.*查看.*ETF.*',
            r'.*ETF.*列表.*',
            r'.*有哪些.*ETF.*',
            r'.*显示.*ETF.*',
        ],
        'add_etf': [
            r'.*添加.*ETF.*',
            r'.*新增.*ETF.*',
            r'.*加入.*ETF.*',
        ],
        'remove_etf': [
            r'.*删除.*ETF.*',
            r'.*移除.*ETF.*',
            r'.*取消.*ETF.*',
        ],
        'list_pools': [
            r'.*列出.*(品种)?[池p].*',
            r'.*(品种)?[池p].*列表.*',
            r'.*有哪些.*(品种)?[池p].*',
            r'.*[池p].*有哪些.*',
        ],
        'add_pool': [
            r'.*创建.*品种池.*',
            r'.*新建.*品种池.*',
            r'.*添加.*品种池.*',
        ],
        'remove_pool': [
            r'.*删除.*(品种)?[池p].*',
            r'.*移除.*(品种)?[池p].*',
        ],
        'list_pool_members': [
            r'.*查看.*[池p].*的?成[员].*',
            r'.*[池p].*包含.*ETF.*',
            r'.*[池p].*有.*哪些.*ETF.*',
            r'.*有哪些.*ETF.*在.*[池p].*',
        ],
        'add_pool_member': [
            r'.*向.*[池p].*添加.*',
            r'.*[池p].*加入.*',
            r'.*把.*加入.*[池p].*',
            r'.*添加.*到.*[池p].*',
        ],
        'remove_pool_member': [
            r'.*从.*[池p].*移除.*',
            r'.*[池p].*删除.*',
            r'.*把.*从.*[池p].*移除.*',
            r'.*移除.*[池p].*成[员].*',
        ],
        'clear_pool': [
            r'.*清空.*[池p].*',
            r'.*重置.*[池p].*',
            r'.*[池p].*清空.*',
        ],
        'clear_all_pools': [
            r'.*清空所有.*[池p].*',
            r'.*所有.*[池p].*清空.*',
        ],
        'help': [
            r'.*帮助.*',
            r'.*怎么用.*',
            r'.*能做什么.*',
            r'.*功能.*',
        ],
    }

    @classmethod
    def recognize(cls, text: str) -> Tuple[Optional[str], Dict[str, Any]]:
        """
        识别用户意图并提取参数

        Args:
            text: 用户输入文本

        Returns:
            (意图类型, 参数字典)
        """
        text = text.strip()

        for intent, patterns in cls.INTENT_PATTERNS.items():
            for pattern in patterns:
                if re.match(pattern, text, re.IGNORECASE):
                    params = cls._extract_params(text, intent)
                    return intent, params

        return 'unknown', {}

    @classmethod
    def _extract_params(cls, text: str, intent: str) -> Dict[str, Any]:
        """从文本中提取参数"""
        params = {}

        # ETF 代码提取 (6位数字)
        etf_codes = re.findall(r'\b(\d{6})\b', text)
        if etf_codes:
            params['etf_codes'] = etf_codes

        # 品种池代码提取 - 匹配 "rotation_pool", "permanent_pool", "池" 等
        pool_code_patterns = [
            r'([a-zA-Z_]+_pool)\b',  # rotation_pool, permanent_pool
            r'(?:池|pool)[:：]?([a-zA-Z_]+)',  # 池:rotation 或 pool:rotation
            r'(轮动|永久|主题|期权|货币)[池]',  # 轮动池, 永久池
            r'([a-zA-Z]+_pool)',  # fallback
        ]
        for pattern in pool_code_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                pool_code = match.group(1)
                # 标准化池代码
                pool_code_lower = pool_code.lower()
                # 中文池名称映射
                chinese_pool_map = {
                    '轮动': 'rotation_pool',
                    '永久': 'permanent_pool',
                    '主题': 'thematic_pool',
                    '期权': 'option_underlying_pool',
                    '货币': 'money_market_pool',
                }
                if pool_code_lower in chinese_pool_map:
                    params['pool_code'] = chinese_pool_map[pool_code_lower]
                elif 'rotation' in pool_code_lower:
                    params['pool_code'] = 'rotation_pool'
                elif 'permanent' in pool_code_lower:
                    params['pool_code'] = 'permanent_pool'
                elif 'thematic' in pool_code_lower:
                    params['pool_code'] = 'thematic_pool'
                elif 'option' in pool_code_lower:
                    params['pool_code'] = 'option_underlying_pool'
                elif 'money' in pool_code_lower:
                    params['pool_code'] = 'money_market_pool'
                else:
                    params['pool_code'] = pool_code_lower
                break

        # 品种池名称提取
        pool_names = re.findall(r'叫[名为]?["\']?([^"\'的]+)["\']?(?:的?品种池|池)', text)
        if pool_names:
            params['pool_name'] = pool_names[0].strip()

        return params


class AIManager:
    """AI 品种管理器"""

    # 常用 ETF 参考数据
    COMMON_ETFS = {
        '510300': {'name': '沪深300ETF', 'category': 'equity', 'market': 'SH'},
        '510500': {'name': '中证500ETF', 'category': 'equity', 'market': 'SH'},
        '159915': {'name': '创业板ETF', 'category': 'equity', 'market': 'SZ'},
        '588000': {'name': '科创50ETF', 'category': 'equity', 'market': 'SH'},
        '518880': {'name': '黄金ETF', 'category': 'commodity', 'market': 'SH'},
        '513500': {'name': '标普500ETF', 'category': 'cross_border', 'market': 'SH'},
        '513100': {'name': '纳斯达克ETF', 'category': 'cross_border', 'market': 'SH'},
        '511010': {'name': '国债ETF', 'category': 'bond', 'market': 'SH'},
        '511220': {'name': '信用债ETF', 'category': 'bond', 'market': 'SH'},
        '512480': {'name': '半导体ETF', 'category': 'sector', 'market': 'SH'},
        '515700': {'name': '新能源ETF', 'category': 'sector', 'market': 'SH'},
    }

    # 用途映射
    PURPOSE_MAP = {
        '轮动': 'rotation',
        '永久': 'permanent',
        '主题': 'thematic',
        '自定义': 'custom',
    }

    @classmethod
    def handle(cls, intent: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理意图"""

        handlers = {
            'list_etfs': cls.list_etfs,
            'add_etf': cls.add_etf,
            'remove_etf': cls.remove_etf,
            'list_pools': cls.list_pools,
            'add_pool': cls.add_pool,
            'remove_pool': cls.remove_pool,
            'list_pool_members': cls.list_pool_members,
            'add_pool_member': cls.add_pool_member,
            'remove_pool_member': cls.remove_pool_member,
            'help': cls.get_help,
            'unknown': cls.unknown_intent,
        }

        handler = handlers.get(intent, cls.unknown_intent)
        return handler(params)

    @classmethod
    def list_etfs(cls, params: Dict[str, Any]) -> Dict[str, Any]:
        """列出所有 ETF"""
        try:
            etfs = ETF.objects.filter(is_active=True).order_by('code')
            data = [{
                'code': etf.code,
                'name': etf.name,
                'category': etf.category,
                'category_display': etf.category_display,
                'market': etf.market,
            } for etf in etfs]

            return {
                'success': True,
                'intent': 'list_etfs',
                'message': f'共找到 {len(data)} 个 ETF 品种',
                'data': data,
            }
        except Exception as e:
            logger.error(f"列出 ETF 失败: {e}")
            return {'success': False, 'error': str(e)}

    @classmethod
    def add_etf(cls, params: Dict[str, Any]) -> Dict[str, Any]:
        """添加 ETF"""
        try:
            # 从参数或文本中获取 ETF 代码
            etf_codes = params.get('etf_codes', [])

            if not etf_codes:
                return {
                    'success': False,
                    'error': '请提供 ETF 代码，例如：添加 ETF 510300'
                }

            results = []
            with transaction.atomic():
                for code in etf_codes:
                    code = code.strip()

                    # 如果数据库中没有，尝试用常用数据创建
                    etf, created = ETF.objects.get_or_create(
                        code=code,
                        defaults=cls.COMMON_ETFS.get(code, {
                            'name': f'ETF{code}',
                            'category': 'equity',
                            'market': 'SH' if code.startswith('51') else 'SZ',
                        })
                    )

                    if created:
                        results.append(f'成功添加 {code} {etf.name}')
                    else:
                        results.append(f'{code} {etf.name} 已存在')

            return {
                'success': True,
                'intent': 'add_etf',
                'message': '; '.join(results),
                'data': results,
            }
        except Exception as e:
            logger.error(f"添加 ETF 失败: {e}")
            return {'success': False, 'error': str(e)}

    @classmethod
    def remove_etf(cls, params: Dict[str, Any]) -> Dict[str, Any]:
        """删除 ETF（软删除）"""
        try:
            etf_codes = params.get('etf_codes', [])

            if not etf_codes:
                return {
                    'success': False,
                    'error': '请提供要删除的 ETF 代码'
                }

            results = []
            with transaction.atomic():
                for code in etf_codes:
                    code = code.strip()
                    try:
                        etf = ETF.objects.get(code=code)
                        etf.is_active = False
                        etf.save()
                        results.append(f'已停用 {code} {etf.name}')
                    except ETF.DoesNotExist:
                        results.append(f'{code} 不存在')

            return {
                'success': True,
                'intent': 'remove_etf',
                'message': '; '.join(results),
                'data': results,
            }
        except Exception as e:
            logger.error(f"删除 ETF 失败: {e}")
            return {'success': False, 'error': str(e)}

    @classmethod
    def list_pools(cls, params: Dict[str, Any]) -> Dict[str, Any]:
        """列出所有品种池"""
        try:
            pools = Pool.objects.filter(is_active=True).order_by('code')
            data = []
            for pool in pools:
                member_count = pool.members.filter(is_active=True).count()
                data.append({
                    'code': pool.code,
                    'name': pool.name,
                    'purpose': pool.purpose,
                    'purpose_display': pool.purpose_display,
                    'member_count': member_count,
                    'description': pool.description[:50] if pool.description else '',
                })

            return {
                'success': True,
                'intent': 'list_pools',
                'message': f'共找到 {len(data)} 个品种池',
                'data': data,
            }
        except Exception as e:
            logger.error(f"列出品种池失败: {e}")
            return {'success': False, 'error': str(e)}

    @classmethod
    def add_pool(cls, params: Dict[str, Any]) -> Dict[str, Any]:
        """创建品种池"""
        try:
            pool_code = params.get('pool_code', '')
            pool_name = params.get('pool_name', '')

            if not pool_name:
                return {
                    'success': False,
                    'error': '请提供品种池名称，例如：创建品种池叫"我的轮动池"'
                }

            # 生成代码
            if not pool_code:
                pool_code = f'pool_{pool_name[:4]}'

            # 确定用途
            purpose = 'custom'
            for name, p in cls.PURPOSE_MAP.items():
                if name in pool_name:
                    purpose = p
                    break

            pool, created = Pool.objects.get_or_create(
                code=pool_code,
                defaults={
                    'name': pool_name,
                    'purpose': purpose,
                    'description': f'由 AI 助手创建 - {pool_name}',
                }
            )

            if created:
                return {
                    'success': True,
                    'intent': 'add_pool',
                    'message': f'成功创建品种池 "{pool_name}" (代码: {pool_code})',
                    'data': {'code': pool.code, 'name': pool.name},
                }
            else:
                return {
                    'success': False,
                    'error': f'品种池 "{pool_name}" (代码: {pool_code}) 已存在',
                }
        except Exception as e:
            logger.error(f"创建品种池失败: {e}")
            return {'success': False, 'error': str(e)}

    @classmethod
    def remove_pool(cls, params: Dict[str, Any]) -> Dict[str, Any]:
        """删除品种池"""
        try:
            pool_code = params.get('pool_code', '')

            if not pool_code:
                return {
                    'success': False,
                    'error': '请提供要删除的品种池代码'
                }

            try:
                pool = Pool.objects.get(code=pool_code)
                pool.is_active = False
                pool.save()
                return {
                    'success': True,
                    'intent': 'remove_pool',
                    'message': f'已停用品种池 "{pool.name}" (代码: {pool_code})',
                }
            except Pool.DoesNotExist:
                return {
                    'success': False,
                    'error': f'品种池 {pool_code} 不存在',
                }
        except Exception as e:
            logger.error(f"删除品种池失败: {e}")
            return {'success': False, 'error': str(e)}

    @classmethod
    def list_pool_members(cls, params: Dict[str, Any]) -> Dict[str, Any]:
        """列出品种池成员"""
        try:
            pool_code = params.get('pool_code', '')

            if not pool_code:
                return {
                    'success': False,
                    'error': '请提供品种池代码，例如：查看 rotation_pool 的成员'
                }

            try:
                pool = Pool.objects.get(code=pool_code)
                members = pool.members.filter(is_active=True).order_by('order', 'etf__code')
                data = [{
                    'etf_code': m.etf.code,
                    'etf_name': m.etf.name,
                    'weight': float(m.weight) if m.weight else 0,
                    'is_active': m.is_active,
                } for m in members]

                return {
                    'success': True,
                    'intent': 'list_pool_members',
                    'message': f'品种池 "{pool.name}" 包含 {len(data)} 个成员',
                    'data': data,
                }
            except Pool.DoesNotExist:
                return {
                    'success': False,
                    'error': f'品种池 {pool_code} 不存在',
                }
        except Exception as e:
            logger.error(f"列出池成员失败: {e}")
            return {'success': False, 'error': str(e)}

    @classmethod
    def add_pool_member(cls, params: Dict[str, Any]) -> Dict[str, Any]:
        """向品种池添加成员"""
        try:
            pool_code = params.get('pool_code', '')
            etf_codes = params.get('etf_codes', [])

            if not pool_code:
                return {
                    'success': False,
                    'error': '请提供品种池代码'
                }
            if not etf_codes:
                return {
                    'success': False,
                    'error': '请提供要添加的 ETF 代码'
                }

            try:
                pool = Pool.objects.get(code=pool_code, is_active=True)
            except Pool.DoesNotExist:
                return {
                    'success': False,
                    'error': f'品种池 {pool_code} 不存在',
                }

            results = []
            with transaction.atomic():
                for code in etf_codes:
                    code = code.strip()
                    try:
                        etf = ETF.objects.get(code=code, is_active=True)
                    except ETF.DoesNotExist:
                        results.append(f'{code} 不存在或已停用')
                        continue

                    member, created = PoolMember.objects.get_or_create(
                        pool=pool,
                        etf=etf,
                        defaults={'weight': 0.0, 'is_active': True}
                    )

                    if created:
                        results.append(f'已将 {code} {etf.name} 加入 {pool.name}')
                    else:
                        results.append(f'{code} {etf.name} 已在 {pool.name} 中')

            return {
                'success': True,
                'intent': 'add_pool_member',
                'message': '; '.join(results),
                'data': results,
            }
        except Exception as e:
            logger.error(f"添加池成员失败: {e}")
            return {'success': False, 'error': str(e)}

    @classmethod
    def remove_pool_member(cls, params: Dict[str, Any]) -> Dict[str, Any]:
        """从品种池移除成员"""
        try:
            pool_code = params.get('pool_code', '')
            etf_codes = params.get('etf_codes', [])

            if not pool_code:
                return {
                    'success': False,
                    'error': '请提供品种池代码'
                }
            if not etf_codes:
                return {
                    'success': False,
                    'error': '请提供要移除的 ETF 代码'
                }

            try:
                pool = Pool.objects.get(code=pool_code, is_active=True)
            except Pool.DoesNotExist:
                return {
                    'success': False,
                    'error': f'品种池 {pool_code} 不存在',
                }

            results = []
            with transaction.atomic():
                for code in etf_codes:
                    code = code.strip()
                    try:
                        member = PoolMember.objects.get(pool=pool, etf__code=code)
                        member.is_active = False
                        member.save()
                        results.append(f'已从 {pool.name} 移除 {code}')
                    except PoolMember.DoesNotExist:
                        results.append(f'{code} 不在 {pool.name} 中')

            return {
                'success': True,
                'intent': 'remove_pool_member',
                'message': '; '.join(results),
                'data': results,
            }
        except Exception as e:
            logger.error(f"移除池成员失败: {e}")
            return {'success': False, 'error': str(e)}

    @classmethod
    def get_help(cls, params: Dict[str, Any]) -> Dict[str, Any]:
        """获取帮助信息"""
        help_text = """
## AI 品种管理器使用指南

### 可管理的对象
- **ETF 品种**: 沪深300ETF、中证500ETF 等
- **品种池**: 轮动池、永久组合池、主题池等
- **池成员**: 品种池中的具体 ETF

### 支持的操作

#### ETF 管理
- `列出所有 ETF` - 查看所有 ETF 品种
- `添加 ETF 510300` - 添加单个 ETF
- `删除 ETF 510500` - 停用某个 ETF

#### 品种池管理
- `列出所有品种池` - 查看所有品种池
- `创建品种池叫"我的轮动池"` - 创建新品种池
- `删除品种池 rotation_pool` - 停用品种池

#### 池成员管理
- `查看 rotation_pool 的成员` - 列出池中的 ETF
- `向 rotation_pool 添加 510300` - 向池中添加 ETF
- `从 permanent_pool 移除 518880` - 从池中移除 ETF

### 示例
- "添加 ETF 512480"
- "创建品种池叫科技主题池"
- "向轮动池添加 510300 和 510500"
"""
        return {
            'success': True,
            'intent': 'help',
            'message': '以下是 AI 品种管理器的使用指南',
            'data': {'help_text': help_text},
        }

    @classmethod
    def unknown_intent(cls, params: Dict[str, Any]) -> Dict[str, Any]:
        """未知意图"""
        return {
            'success': False,
            'intent': 'unknown',
            'error': '抱歉，我无法理解您的请求。请输入"帮助"查看支持的操作。',
        }


# API 视图
@api_view(['POST'])
@permission_classes([AllowAny])
def ai_manager(request):
    """
    AI 品种管理器 API

    POST /api/ai/manager/

    请求体:
    {
        "text": "添加 ETF 510300"
    }

    响应:
    {
        "success": true,
        "intent": "add_etf",
        "message": "成功添加 510300 沪深300ETF",
        "data": [...]
    }
    """
    text = request.data.get('text', '')

    if not text:
        return Response(
            {'success': False, 'error': '请提供 text 参数'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 识别意图
    intent, params = IntentRecognizer.recognize(text)
    logger.info(f"[AI Manager] 识别意图: {intent}, 参数: {params}")

    # 处理请求
    result = AIManager.handle(intent, params)

    return Response(result)


@api_view(['GET'])
@permission_classes([AllowAny])
def ai_manager_help(request):
    """获取 AI 品种管理器帮助"""
    result = AIManager.get_help({})
    return Response(result)
