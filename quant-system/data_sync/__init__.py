"""
数据同步服务模块

负责从外部数据源（mootdx、akshare 等）拉取数据，
并同步到本地数据库和缓存中。
"""

# 延迟导入以避免 Django AppRegistryNotReady 错误
# 使用时再导入：from data_sync.adapters import MootdxAdapter 等

__all__ = [
    # 模块会在需要时动态导入
]
