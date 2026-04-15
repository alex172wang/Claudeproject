"""
Pytest configuration for E2E tests
"""
import pytest
import os
import sys
import subprocess
import time
import socket
import threading
from pathlib import Path
from playwright.sync_api import sync_playwright

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def is_port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    """检查端口是否开放"""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False


def wait_for_server(host: str, port: int, timeout: float = 60.0) -> bool:
    """等待服务器启动并真正响应 HTTP 请求"""
    import urllib.request
    start_time = time.time()
    while time.time() - start_time < timeout:
        if is_port_open(host, port):
            try:
                urllib.request.urlopen(f'http://{host}:{port}/', timeout=3.0)
                return True
            except Exception:
                pass
        time.sleep(1.0)
    return False


def stream_output(process, prefix="[Dashboard]"):
    """在后台线程中流式读取进程输出"""
    def reader():
        try:
            for line in iter(process.stdout.readline, ''):
                if line:
                    print(f"{prefix} {line.rstrip()}")
        except Exception:
            pass
    thread = threading.Thread(target=reader, daemon=True)
    thread.start()
    return thread


@pytest.fixture(scope="session")
def django_setup():
    """Setup Django environment - 仅设置环境变量，不创建数据"""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'quant_system.settings')
    os.environ['DJANGO_ALLOW_ASYNC_UNSAFE'] = 'true'

    # 不初始化 Django ORM，避免 async 问题
    # 测试数据通过 init_test_data.py 单独初始化
    yield


@pytest.fixture(scope="session")
def browser(browser):
    """覆写 browser fixture，禁用 Chromium sandbox（Windows 本地测试需要）"""
    # pytest-playwright 已经提供了 browser fixture，我们在这里配置它
    # 实际通过 launch_persistent_context 或 BrowserType.launch 时的 args
    # 由于 browser fixture 由插件提供，这里我们只是引用它确保其被使用
    return browser


@pytest.fixture(scope="session")
def dashboard_server():
    """Start Dashboard server for testing - 使用真实的 run_dashboard.py"""
    # 确保使用测试端口
    port = 8052
    host = '127.0.0.1'

    # 先检查端口是否被占用
    if is_port_open(host, port):
        print(f"端口 {port} 已被占用，尝试终止占用进程...")
        try:
            if sys.platform == 'win32':
                result = subprocess.run(
                    ['netstat', '-ano', '|', 'findstr', f':{port}'],
                    capture_output=True, text=True, shell=True
                )
                if result.stdout:
                    for line in result.stdout.splitlines():
                        if f':{port}' in line and 'LISTENING' in line:
                            pid = line.split()[-1]
                            subprocess.run(['taskkill', '/F', '/PID', pid], shell=True)
            time.sleep(3)
        except Exception as e:
            print(f"清理端口失败: {e}")

    # Start the server in a subprocess - 使用真实的 run_dashboard.py
    env = os.environ.copy()
    env['PYTHONUNBUFFERED'] = '1'
    env['DJANGO_ALLOW_ASYNC_UNSAFE'] = 'true'

    proc = subprocess.Popen(
        [sys.executable, str(project_root / "run_dashboard.py"), "--port", str(port), "--host", host],
        cwd=str(project_root),
        stdout=subprocess.DEVNULL,  # 不捕获输出，避免管道阻塞
        stderr=subprocess.STDOUT,
        env=env
    )

    # Wait for server to start
    print(f"等待 Dashboard 服务器启动 (http://{host}:{port})...")
    server_ready = wait_for_server(host, port, timeout=90)

    if not server_ready:
        print("服务器启动超时")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        pytest.fail("Dashboard server failed to start")

    print(f"✓ Dashboard 服务器已启动: http://{host}:{port}")
    time.sleep(10)  # 额外等待确保完全就绪

    # 检查服务器是否还在运行
    if proc.poll() is not None:
        print(f"服务器进程已退出，返回码: {proc.returncode}")
        pytest.fail("Dashboard server exited prematurely")

    yield f"http://{host}:{port}"

    # Cleanup
    print("停止 Dashboard 服务器...")
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        print("强制终止服务器...")
        proc.kill()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            print("无法终止服务器")
