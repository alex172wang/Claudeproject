#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
量化交易系统主入口

多维量化指标体系驱动，覆盖 ETF轮动 / 永久组合 / 主题仓位 三个策略层。

Usage:
    python main.py --strategy etf_rotation --start 2020-01-01 --end 2024-12-31
    python main.py --strategy permanent_portfolio --mode live
    python main.py --backtest-only
"""

import os
import sys
import argparse
import logging
from datetime import datetime
from pathlib import Path

# 添加项目根目录到 Python 路径
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# 导入配置
from config.settings import PROJECT_CONFIG, LOGGING_CONFIG

# 配置日志
def setup_logging():
    """配置日志系统"""
    log_dir = PROJECT_ROOT / "logs"
    log_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"quant_system_{timestamp}.log"

    logging.basicConfig(
        level=LOGGING_CONFIG.get("level", logging.INFO),
        format=LOGGING_CONFIG.get(
            "format",
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        ),
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout)
        ]
    )

    return logging.getLogger(__name__)


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="多维量化交易系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 运行ETF轮动策略回测
  python main.py --strategy etf_rotation --start 2020-01-01 --end 2024-12-31

  # 运行永久组合实时模式
  python main.py --strategy permanent_portfolio --mode live

  # 仅运行回测，不生成信号
  python main.py --backtest-only
        """
    )

    parser.add_argument(
        "--strategy",
        type=str,
        choices=["etf_rotation", "permanent_portfolio", "thematic_position", "all"],
        default="all",
        help="选择要运行的策略 (默认: all)"
    )

    parser.add_argument(
        "--mode",
        type=str,
        choices=["backtest", "live", "paper"],
        default="backtest",
        help="运行模式: backtest(回测)/live(实盘)/paper(模拟盘) (默认: backtest)"
    )

    parser.add_argument(
        "--start",
        type=str,
        default="2020-01-01",
        help="回测开始日期 (格式: YYYY-MM-DD, 默认: 2020-01-01)"
    )

    parser.add_argument(
        "--end",
        type=str,
        default=None,
        help=f"回测结束日期 (格式: YYYY-MM-DD, 默认: 今天)"
    )

    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="自定义配置文件路径"
    )

    parser.add_argument(
        "--backtest-only",
        action="store_true",
        help="仅运行回测，不生成交易信号"
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="显示详细日志"
    )

    return parser.parse_args()


def main():
    """主函数"""
    # 解析参数
    args = parse_arguments()

    # 设置日志
    logger = setup_logging()
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # 记录启动信息
    logger.info("=" * 60)
    logger.info("多维量化交易系统启动")
    logger.info("=" * 60)
    logger.info(f"策略: {args.strategy}")
    logger.info(f"模式: {args.mode}")
    logger.info(f"时间范围: {args.start} ~ {args.end or '今天'}")
    logger.info("=" * 60)

    # TODO: 根据参数执行相应策略
    # 这里将在后续开发中实现

    logger.info("系统初始化完成，等待进一步开发...")

    return 0


if __name__ == "__main__":
    sys.exit(main())
