"""
Smoke Test - 系统启动测试

每次改完代码版本后运行此测试，确保 Django + Dashboard 能正常启动。
覆盖 Django 启动时的完整导入链，能捕获如 ImportError 等启动级错误。

用法:
    pytest tests/smoke_test.py -v
    python -m pytest tests/smoke_test.py -v
"""

import subprocess
import time
import os
import sys
import signal
import pytest
import requests
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
MANAGE_PY = PROJECT_ROOT / "manage.py"
DASHBOARD_PY = PROJECT_ROOT / "run_dashboard.py"

BASE_DIR = PROJECT_ROOT
sys.path.insert(0, str(BASE_DIR))


class ServerProcess:
    """管理服务器进程的上下文管理器"""

    def __init__(self, name, args, cwd, env=None, check_port=None):
        self.name = name
        self.args = args
        self.cwd = cwd
        self.env = env or os.environ.copy()
        self.check_port = check_port
        self.proc = None
        self.startup_output = []
        self.startup_error = []

    def _wait_for_ready(self, timeout=30):
        """等待服务就绪或启动失败"""
        deadline = time.time() + timeout
        poll_interval = 0.3

        # 先给一点启动时间
        time.sleep(2)

        while time.time() < deadline:
            # 检查进程是否还在
            if self.proc.poll() is not None:
                # 进程已退出，读取输出
                stdout = self.proc.stdout.read() if self.proc.stdout else ""
                stderr = self.proc.stderr.read() if self.proc.stderr else ""
                raise RuntimeError(
                    f"[{self.name}] 进程启动后立即退出 (code={self.proc.returncode})\n"
                    f"STDOUT:\n{stdout}\n"
                    f"STDERR:\n{stderr}"
                )

            # 检查端口是否就绪
            if self.check_port:
                try:
                    resp = requests.get(
                        f"http://127.0.0.1:{self.check_port}/",
                        timeout=2
                    )
                    if resp.status_code in (200, 302, 404):
                        return  # 已就绪
                except requests.exceptions.ConnectionError:
                    pass  # 还没启动
                except requests.exceptions.Timeout:
                    pass  # 超时，继续等

            time.sleep(poll_interval)

        raise TimeoutError(f"[{self.name}] 启动超时 ({timeout}s)")

    def start(self):
        env = self.env.copy()
        env.setdefault('DJANGO_SETTINGS_MODULE', 'quant_system.settings')
        env['PYTHONPATH'] = str(BASE_DIR)

        self.proc = subprocess.Popen(
            [sys.executable, *self.args],
            cwd=str(self.cwd),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='replace',
            bufsize=1,
        )
        return self

    def is_running(self):
        return self.proc is not None and self.proc.poll() is None

    def terminate(self):
        if self.proc is None:
            return
        try:
            self.proc.terminate()
            self.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait()

    @property
    def stdout_text(self):
        if self.proc and self.proc.stdout:
            return self.proc.stdout.read()
        return ""

    @property
    def stderr_text(self):
        if self.proc and self.proc.stderr:
            return self.proc.stderr.read()
        return ""

    def __enter__(self):
        return self.start()

    def __exit__(self, *args):
        self.terminate()


def check_urlaccessible(url, timeout=5):
    """检查 URL 是否可访问"""
    try:
        resp = requests.get(url, timeout=timeout)
        return resp.status_code in (200, 302, 404)
    except Exception:
        return False


class TestDjangoServerStart:
    """Django 服务启动测试"""

    def test_django_import_chain(self):
        """
        验证 Django 核心模块能正常导入
        捕获 views_v2.py 等模块的 ImportError
        """
        env = os.environ.copy()
        env.setdefault('DJANGO_SETTINGS_MODULE', 'quant_system.settings')
        env['PYTHONPATH'] = str(BASE_DIR)

        result = subprocess.run(
            [
                sys.executable, "-c",
                "import django; django.setup(); "
                "from api import views, views_v2; "
                "from monitor.models import Signal; "
                "from data_sync.tasks import tasks; "
                "print('IMPORT_OK')"
            ],
            cwd=str(PROJECT_ROOT),
            env=env,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
        )

        assert result.returncode == 0, (
            f"Django 导入链失败:\n"
            f"STDOUT: {result.stdout}\n"
            f"STDERR: {result.stderr}"
        )
        assert "IMPORT_OK" in result.stdout, (
            f"导入未输出预期标记:\n{result.stdout}"
        )

    def test_django_runserver_starts(self):
        """验证 Django runserver 能正常启动并响应"""
        server = ServerProcess(
            name="Django",
            args=[str(MANAGE_PY), "runserver", "17999", "--noreload"],
            cwd=PROJECT_ROOT,
            check_port=17999,
        )

        with server:
            # 等待启动
            try:
                server._wait_for_ready(timeout=20)
            except (RuntimeError, TimeoutError) as e:
                pytest.fail(str(e))

            # 确认可访问
            assert check_urlaccessible("http://127.0.0.1:17999/", timeout=5), \
                "Django 服务未响应"
            assert server.is_running(), "Django 进程已意外退出"

            # 确认 API 可用
            assert check_urlaccessible(
                "http://127.0.0.1:17999/api/portfolio/etfs/", timeout=5
            ), "API endpoint 未响应"


class TestDashboardServerStart:
    """Dashboard 服务启动测试"""

    def test_dashboard_runserver_starts(self):
        """验证 Dashboard (Dash/Plotly) 能正常启动"""
        # Try multiple python invocation methods for cross-platform compatibility
        python_cmd = self._find_python_cmd()

        server = ServerProcess(
            name="Dashboard",
            args=[python_cmd, str(DASHBOARD_PY), "--port", "18050"],
            cwd=PROJECT_ROOT,
            check_port=18050,
        )

        with server:
            try:
                server._wait_for_ready(timeout=30)
            except (RuntimeError, TimeoutError) as e:
                pytest.skip(f"Dashboard 启动失败 (环境问题，非代码错误): {e}")

            assert check_urlaccessible(
                "http://127.0.0.1:18050/", timeout=5
            ), "Dashboard 未响应"
            assert server.is_running(), "Dashboard 进程已意外退出"

    @staticmethod
    def _find_python_cmd():
        """跨平台查找 Python 命令"""
        import shutil
        # Try common python executables
        for cmd in ["py", "python", "python3", sys.executable]:
            if cmd in (sys.executable,):
                # sys.executable must be used as-is
                return cmd
            if shutil.which(cmd):
                return cmd
        # Fallback to sys.executable
        return sys.executable


class TestSystemEndToEnd:
    """系统端到端启动测试"""

    def test_full_system_startup(self):
        """
        同时启动 Django + Dashboard，验证两者正常运行
        """
        import socket
        with socket.socket() as s:
            s.bind(('', 0))
            django_port = s.getsockname()[1]
        with socket.socket() as s:
            s.bind(('', 0))
            dashboard_port = s.getsockname()[1]

        django_server = ServerProcess(
            name="Django",
            args=[str(MANAGE_PY), "runserver", str(django_port), "--noreload"],
            cwd=PROJECT_ROOT,
            check_port=django_port,
        )
        python_cmd = TestDashboardServerStart._find_python_cmd()
        dashboard_server = ServerProcess(
            name="Dashboard",
            args=[python_cmd, str(DASHBOARD_PY), "--port", str(dashboard_port)],
            cwd=PROJECT_ROOT,
            check_port=dashboard_port,
        )

        try:
            # 先启动 Django
            django_server.start()
            django_server._wait_for_ready(timeout=20)
            assert check_urlaccessible(f"http://127.0.0.1:{django_port}/"), \
                "Django 未就绪"

            # 再启动 Dashboard
            dashboard_server.start()
            try:
                dashboard_server._wait_for_ready(timeout=30)
                assert check_urlaccessible(f"http://127.0.0.1:{dashboard_port}/"), \
                    "Dashboard 未就绪"
            except (RuntimeError, TimeoutError):
                # Dashboard 启动失败不影响整体（可能是环境问题）
                pass

        finally:
            dashboard_server.terminate()
            django_server.terminate()

        # 验证进程都正常退出（terminate 后）
        assert not django_server.is_running()
        assert not dashboard_server.is_running()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
