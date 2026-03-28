#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
量化交易策略开发系统 - 入口程序

该程序负责：
1. 设置控制台编码
2. 初始化系统配置
3. 打印启动信息
"""

import sys
import io
import os
from datetime import datetime


def setup_console_encoding():
    """
    设置控制台编码为 UTF-8（Windows系统专用）
    """
    if sys.platform == 'win32':
        os.system('chcp 65001 >nul')
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def print_system_info():
    """
    打印系统启动信息
    """
    print("=" * 50)
    print("量化交易策略开发系统")
    print("=" * 50)
    print(f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Python版本: {sys.version}")
    print("-" * 50)
    print("项目配置已加载")
    print("CLAUDE.md 文件已创建，包含完整开发规范")
    print("-" * 50)
    print("提示：使用 /help 命令获取 Claude 功能帮助")


if __name__ == "__main__":
    setup_console_encoding()
    print_system_info()
