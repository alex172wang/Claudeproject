"""
缓存管理器

提供统一的缓存接口，支持 Redis 和本地内存缓存
用于存储实时行情、计算结果等热点数据
"""

import json
import pickle
import hashlib
from typing import Optional, Any, Union, Dict, List
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class CacheError(Exception):
    """缓存错误"""
    pass


class BaseCache:
    """缓存基类"""

    def __init__(self, prefix: str = 'quant', default_timeout: int = 300):
        self.prefix = prefix
        self.default_timeout = default_timeout

    def _make_key(self, key: str) -> str:
        """生成完整的缓存键"""
        return f"{self.prefix}:{key}"

    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        raise NotImplementedError

    def set(self, key: str, value: Any, timeout: Optional[int] = None) -> bool:
        """设置缓存值"""
        raise NotImplementedError

    def delete(self, key: str) -> bool:
        """删除缓存"""
        raise NotImplementedError

    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        raise NotImplementedError

    def expire(self, key: str, timeout: int) -> bool:
        """设置过期时间"""
        raise NotImplementedError

    def clear(self) -> bool:
        """清空缓存"""
        raise NotImplementedError


class MemoryCache(BaseCache):
    """内存缓存（基于字典）"""

    def __init__(self, prefix: str = 'quant', default_timeout: int = 300):
        super().__init__(prefix, default_timeout)
        self._cache: Dict[str, Dict[str, Any]] = {}

    def _is_expired(self, key: str) -> bool:
        """检查是否过期"""
        if key not in self._cache:
            return True

        expire_at = self._cache[key].get('expire_at')
        if expire_at is None:
            return False

        return datetime.now() > expire_at

    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        full_key = self._make_key(key)

        if full_key not in self._cache:
            return None

        if self._is_expired(full_key):
            self.delete(key)
            return None

        return self._cache[full_key]['value']

    def set(self, key: str, value: Any, timeout: Optional[int] = None) -> bool:
        """设置缓存值"""
        full_key = self._make_key(key)
        timeout = timeout or self.default_timeout

        expire_at = datetime.now() + timedelta(seconds=timeout) if timeout > 0 else None

        self._cache[full_key] = {
            'value': value,
            'expire_at': expire_at,
            'created_at': datetime.now(),
        }

        return True

    def delete(self, key: str) -> bool:
        """删除缓存"""
        full_key = self._make_key(key)

        if full_key in self._cache:
            del self._cache[full_key]
            return True

        return False

    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        full_key = self._make_key(key)

        if full_key not in self._cache:
            return False

        if self._is_expired(full_key):
            self.delete(key)
            return False

        return True

    def expire(self, key: str, timeout: int) -> bool:
        """设置过期时间"""
        full_key = self._make_key(key)

        if full_key not in self._cache:
            return False

        expire_at = datetime.now() + timedelta(seconds=timeout)
        self._cache[full_key]['expire_at'] = expire_at

        return True

    def clear(self) -> bool:
        """清空缓存"""
        self._cache.clear()
        return True

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        total = len(self._cache)
        expired = sum(1 for k in list(self._cache.keys()) if self._is_expired(k))

        return {
            'total_keys': total,
            'expired_keys': expired,
            'valid_keys': total - expired,
        }


class RedisCache(BaseCache):
    """Redis 缓存"""

    def __init__(self, prefix: str = 'quant', default_timeout: int = 300,
                 host: str = 'localhost', port: int = 6379, db: int = 0,
                 password: Optional[str] = None):
        super().__init__(prefix, default_timeout)
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self._redis = None

    def _get_redis(self):
        """获取 Redis 连接"""
        if self._redis is None:
            try:
                import redis
                self._redis = redis.Redis(
                    host=self.host,
                    port=self.port,
                    db=self.db,
                    password=self.password,
                    decode_responses=True
                )
                # 测试连接
                self._redis.ping()
            except ImportError:
                raise CacheError("Redis 缓存需要安装 redis 包: pip install redis")
            except Exception as e:
                raise CacheError(f"无法连接到 Redis: {e}")

        return self._redis

    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        full_key = self._make_key(key)
        r = self._get_redis()

        data = r.get(full_key)
        if data is None:
            return None

        try:
            return pickle.loads(data.encode() if isinstance(data, str) else data)
        except Exception as e:
            logger.error(f"[RedisCache] 反序列化失败: {e}")
            return None

    def set(self, key: str, value: Any, timeout: Optional[int] = None) -> bool:
        """设置缓存值"""
        full_key = self._make_key(key)
        timeout = timeout or self.default_timeout
        r = self._get_redis()

        try:
            data = pickle.dumps(value)
            if timeout > 0:
                r.setex(full_key, timeout, data)
            else:
                r.set(full_key, data)
            return True
        except Exception as e:
            logger.error(f"[RedisCache] 设置缓存失败: {e}")
            return False

    def delete(self, key: str) -> bool:
        """删除缓存"""
        full_key = self._make_key(key)
        r = self._get_redis()

        return r.delete(full_key) > 0

    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        full_key = self._make_key(key)
        r = self._get_redis()

        return r.exists(full_key) > 0

    def expire(self, key: str, timeout: int) -> bool:
        """设置过期时间"""
        full_key = self._make_key(key)
        r = self._get_redis()

        return r.expire(full_key, timeout)

    def clear(self) -> bool:
        """清空缓存"""
        r = self._get_redis()
        pattern = f"{self.prefix}:*"
        keys = r.keys(pattern)
        if keys:
            r.delete(*keys)
        return True

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        r = self._get_redis()
        pattern = f"{self.prefix}:*"
        keys = r.keys(pattern)

        return {
            'total_keys': len(keys),
            'redis_version': r.info().get('redis_version'),
            'used_memory': r.info().get('used_memory_human'),
        }


class CacheManager:
    """缓存管理器"""

    def __init__(self):
        self._caches: Dict[str, BaseCache] = {}
        self._default_cache: Optional[str] = None

    def register(self, name: str, cache: BaseCache, default: bool = False):
        """注册缓存"""
        self._caches[name] = cache
        if default or self._default_cache is None:
            self._default_cache = name
        logger.info(f"[CacheManager] 注册缓存: {name}")

    def get_cache(self, name: Optional[str] = None) -> BaseCache:
        """获取缓存实例"""
        cache_name = name or self._default_cache
        if cache_name not in self._caches:
            raise CacheError(f"缓存 {cache_name} 不存在")
        return self._caches[cache_name]

    def get(self, key: str, cache_name: Optional[str] = None) -> Optional[Any]:
        """获取缓存值"""
        return self.get_cache(cache_name).get(key)

    def set(self, key: str, value: Any, timeout: Optional[int] = None,
            cache_name: Optional[str] = None) -> bool:
        """设置缓存值"""
        return self.get_cache(cache_name).set(key, value, timeout)

    def delete(self, key: str, cache_name: Optional[str] = None) -> bool:
        """删除缓存"""
        return self.get_cache(cache_name).delete(key)

    def clear(self, cache_name: Optional[str] = None) -> bool:
        """清空缓存"""
        return self.get_cache(cache_name).clear()

    def get_stats(self, cache_name: Optional[str] = None) -> Dict[str, Any]:
        """获取缓存统计"""
        if cache_name:
            return self.get_cache(cache_name).get_stats()

        stats = {}
        for name, cache in self._caches.items():
            stats[name] = cache.get_stats()
        return stats

    def keys(self, pattern: str, cache_name: Optional[str] = None) -> List[str]:
        """
        获取匹配的键列表"""
        cache = self.get_cache(cache_name)
        # 对于MemoryCache，我们直接检查内部缓存
        if hasattr(cache, '_cache'):
            pattern_parts = pattern.split(':')
            if len(pattern_parts) >= 2:
                search_prefix = f"{cache.prefix}:{pattern_parts[1]}"
                return [k.split(':', 2)[2] for k in cache._cache.keys() if k.startswith(search_prefix)]
        return []

    def exists(self, key: str, cache_name: Optional[str] = None) -> bool:
        """检查键是否存在"""
        return self.get_cache(cache_name).exists(key)

    def clear_expired(self, cache_name: Optional[str] = None):
        """清理过期键（MemoryCache专用）"""
        cache = self.get_cache(cache_name)
        if hasattr(cache, '_cache'):
            # 对于MemoryCache，遍历所有键检查过期
            cleaned = 0
            # 需要复制一份键列表，因为删除会改变字典
            all_keys = list(cache._cache.keys())
            for full_key in all_keys:
                if cache._is_expired(full_key):
                    del cache._cache[full_key]
                    cleaned += 1
            return cleaned


# 创建全局缓存管理器实例
cache_manager = CacheManager()

# 初始化默认内存缓存
_default_cache = MemoryCache(prefix='quant', default_timeout=300)
cache_manager.register('memory', _default_cache, default=True)

# 为了向后兼容，也创建一个CacheManager实例作为CacheManager
class CacheManagerCompat(CacheManager):
    """兼容层 - 保持与旧代码的兼容性"""
    def __init__(self):
        super().__init__()
        # 注册默认缓存
        self.register('default', _default_cache, default=True)


# 创建兼容实例
CacheManager = CacheManagerCompat
