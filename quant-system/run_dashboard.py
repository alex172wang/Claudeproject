#!/usr/bin/env python3
"""
量化交易系统仪表板启动脚本

使用方法:
    python run_dashboard.py           # 默认启动，访问 http://localhost:8050
    python run_dashboard.py --port 8080  # 指定端口
    python run_dashboard.py --debug    # 调试模式
"""

import argparse
import sys
import os

# 添加项目路径
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='量化交易系统仪表板',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s                           # 默认启动
  %(prog)s --port 8080               # 使用8080端口
  %(prog)s --host 0.0.0.0            # 允许外部访问
  %(prog)s --debug                   # 调试模式
        """
    )

    parser.add_argument(
        '--host',
        default='0.0.0.0',
        help='主机地址 (默认: 0.0.0.0)'
    )

    parser.add_argument(
        '--port',
        type=int,
        default=8050,
        help='端口号 (默认: 8050)'
    )

    parser.add_argument(
        '--debug',
        action='store_true',
        help='启用调试模式'
    )

    args = parser.parse_args()

    # 导入并启动简化版仪表板
    print("=" * 60)
    print("量化交易系统 - 实时监控仪表板")
    print("=" * 60)
    print(f"正在启动服务...")
    print(f"地址: http://{args.host}:{args.port}")
    print(f"模式: {'调试' if args.debug else '生产'}")
    print("=" * 60)
    print()

    try:
        # 直接运行完整版 dashboard 模块
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'quant_system.settings')

        # 修改 sys.argv 传递参数给 dashboard
        sys.argv = [sys.argv[0]]

        from dashboard.main import app
        app.run(
            host=args.host,
            port=args.port,
            debug=args.debug,
        )
    except ImportError as e:
        print(f"错误: 无法导入仪表板模块: {e}")
        import traceback
        traceback.print_exc()
        print("\n请确保已安装依赖:")
        print("  pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"错误: 启动失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
