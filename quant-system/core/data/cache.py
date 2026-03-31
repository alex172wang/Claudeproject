"""
数据缓存模块
基于SQLite的本地缓存实现，支持TTL过期
"""

import sqlite3
import json
import pickle
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Any, Dict, List
import pandas as pd


class DataCache:
    """
    数据缓存管理器

    使用SQLite作为后端存储，支持：
    - 键值对缓存（字符串/JSON/二进制）
    - DataFrame缓存（序列化为pickle）
    - TTL过期机制
    - 自动清理过期数据
    """

    def __init__(
        self,
        db_path: str = "data/cache/market_data.db",
        default_ttl: Optional[int] = None
    ):
        """
        初始化缓存管理器

        Args:
            db_path: SQLite数据库文件路径
            default_ttl: 默认TTL（分钟），None表示永不过期
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.default_ttl = default_ttl

        # 初始化数据库
        self._init_db()

    def _init_db(self):
        """初始化数据库表结构"""
        with sqlite3.connect(self.db_path) as conn:
            # 键值对缓存表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS kv_cache (
                    key TEXT PRIMARY KEY,
                    value BLOB,
                    value_type TEXT DEFAULT 'pickle',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP
                )
            """)

            # DataFrame缓存表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS dataframe_cache (
                    key TEXT PRIMARY KEY,
                    data BLOB,
                    columns TEXT,
                    index_col TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP
                )
            """)

            # 缓存元数据表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache_meta (
                    key TEXT PRIMARY KEY,
                    access_count INTEGER DEFAULT 0,
                    last_accessed TIMESTAMP,
                    size_bytes INTEGER
                )
            """)

            # 创建索引
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_kv_expires
                ON kv_cache(expires_at)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_df_expires
                ON dataframe_cache(expires_at)
            """)

            conn.commit()

    def _generate_key(self, prefix: str, *args, **kwargs) -> str:
        """
        生成缓存键

        Args:
            prefix: 键前缀
            *args, **kwargs: 用于生成键的参数

        Returns:
            str: 生成的缓存键
        """
        key_parts = [prefix]
        key_parts.extend(map(str, args))
        for k, v in sorted(kwargs.items()):
            key_parts.append(f"{k}={v}")
        raw_key = "|".join(key_parts)

        # 使用MD5缩短键长度
        return hashlib.md5(raw_key.encode()).hexdigest()

    def _calculate_expiry(self, ttl_minutes: Optional[int] = None) -> Optional[datetime]:
        """
        计算过期时间

        Args:
            ttl_minutes: TTL（分钟），None表示使用默认值

        Returns:
            datetime: 过期时间，None表示永不过期
        """
        ttl = ttl_minutes if ttl_minutes is not None else self.default_ttl
        if ttl is None:
            return None
        return datetime.now() + timedelta(minutes=ttl)

    def set(
        self,
        key: str,
        value: Any,
        ttl_minutes: Optional[int] = None,
        value_type: str = 'pickle'
    ) -> bool:
        """
        存储键值对

        Args:
            key: 缓存键
            value: 要存储的值
            ttl_minutes: TTL（分钟）
            value_type: 值类型（'pickle', 'json', 'string'）

        Returns:
            bool: 是否成功
        """
        try:
            expires_at = self._calculate_expiry(ttl_minutes)

            # 序列化值
            if value_type == 'json':
                serialized = json.dumps(value).encode()
            elif value_type == 'string':
                serialized = str(value).encode()
            else:  # pickle
                serialized = pickle.dumps(value)

            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO kv_cache (key, value, value_type, expires_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (key, serialized, value_type, expires_at)
                )
                conn.commit()

            return True

        except Exception as e:
            print(f"[Cache] 存储失败: {e}")
            return False

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取键值对

        Args:
            key: 缓存键
            default: 默认值

        Returns:
            Any: 缓存值或默认值
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                row = conn.execute(
                    """
                    SELECT value, value_type, expires_at
                    FROM kv_cache
                    WHERE key = ?
                    """,
                    (key,)
                ).fetchone()

                if not row:
                    return default

                value, value_type, expires_at = row

                # 检查是否过期
                if expires_at and datetime.now() > datetime.fromisoformat(expires_at):
                    # 删除过期数据
                    conn.execute("DELETE FROM kv_cache WHERE key = ?", (key,))
                    conn.commit()
                    return default

                # 反序列化
                if value_type == 'json':
                    return json.loads(value)
                elif value_type == 'string':
                    return value.decode()
                else:  # pickle
                    return pickle.loads(value)

        except Exception as e:
            print(f"[Cache] 读取失败: {e}")
            return default

    def set_dataframe(
        self,
        key: str,
        df: pd.DataFrame,
        ttl_minutes: Optional[int] = None
    ) -> bool:
        """
        存储DataFrame

        Args:
            key: 缓存键
            df: DataFrame数据
            ttl_minutes: TTL（分钟）

        Returns:
            bool: 是否成功
        """
        try:
            expires_at = self._calculate_expiry(ttl_minutes)

            # 序列化DataFrame
            data = pickle.dumps(df)
            columns = json.dumps(list(df.columns))
            index_col = df.index.name or 'index'

            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO dataframe_cache
                    (key, data, columns, index_col, expires_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (key, data, columns, index_col, expires_at)
                )
                conn.commit()

            return True

        except Exception as e:
            print(f"[Cache] DataFrame存储失败: {e}")
            return False

    def get_dataframe(self, key: str) -> Optional[pd.DataFrame]:
        """
        获取DataFrame

        Args:
            key: 缓存键

        Returns:
            DataFrame或None
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                row = conn.execute(
                    """
                    SELECT data, expires_at
                    FROM dataframe_cache
                    WHERE key = ?
                    """,
                    (key,)
                ).fetchone()

                if not row:
                    return None

                data, expires_at = row

                # 检查是否过期
                if expires_at and datetime.now() > datetime.fromisoformat(expires_at):
                    conn.execute("DELETE FROM dataframe_cache WHERE key = ?", (key,))
                    conn.commit()
                    return None

                # 反序列化
                return pickle.loads(data)

        except Exception as e:
            print(f"[Cache] DataFrame读取失败: {e}")
            return None

    def delete(self, key: str) -> bool:
        """
        删除缓存

        Args:
            key: 缓存键

        Returns:
            bool: 是否成功
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM kv_cache WHERE key = ?", (key,))
                conn.execute("DELETE FROM dataframe_cache WHERE key = ?", (key,))
                conn.commit()
            return True
        except Exception as e:
            print(f"[Cache] 删除失败: {e}")
            return False

    def clear_expired(self) -> int:
        """
        清理过期缓存

        Returns:
            int: 清理的条目数
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                now = datetime.now().isoformat()

                # 清理kv_cache
                cursor1 = conn.execute(
                    "DELETE FROM kv_cache WHERE expires_at < ?",
                    (now,)
                )

                # 清理dataframe_cache
                cursor2 = conn.execute(
                    "DELETE FROM dataframe_cache WHERE expires_at < ?",
                    (now,)
                )

                conn.commit()
                return cursor1.rowcount + cursor2.rowcount

        except Exception as e:
            print(f"[Cache] 清理过期数据失败: {e}")
            return 0

    def get_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息

        Returns:
            dict: 统计信息
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                kv_count = conn.execute(
                    "SELECT COUNT(*) FROM kv_cache"
                ).fetchone()[0]

                df_count = conn.execute(
                    "SELECT COUNT(*) FROM dataframe_cache"
                ).fetchone()[0]

                expired_kv = conn.execute(
                    "SELECT COUNT(*) FROM kv_cache WHERE expires_at < ?",
                    (datetime.now().isoformat(),)
                ).fetchone()[0]

                expired_df = conn.execute(
                    "SELECT COUNT(*) FROM dataframe_cache WHERE expires_at < ?",
                    (datetime.now().isoformat(),)
                ).fetchone()[0]

                return {
                    'total_entries': kv_count + df_count,
                    'kv_entries': kv_count,
                    'df_entries': df_count,
                    'expired_entries': expired_kv + expired_df,
                    'db_path': str(self.db_path),
                }

        except Exception as e:
            print(f"[Cache] 获取统计信息失败: {e}")
            return {}
