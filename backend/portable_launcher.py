"""Windows portable launcher for the B3 demo.

The PyInstaller build bundles Python, the backend dependencies, and the built
frontend. Users only need to double-click the executable (or START_B3.bat);
no Python/Node.js installation is required.
"""
from __future__ import annotations

import json
import logging
import os
import socket
import sys
import threading
import time
import traceback
import urllib.error
import urllib.request
import webbrowser

import uvicorn

from app.logging_setup import LOG_FILE
from app.main import app


HOST = "127.0.0.1"
DEFAULT_PORT = 8000
PORT_RANGE = range(DEFAULT_PORT, DEFAULT_PORT + 10)


def _health_url(port: int) -> str:
    return f"http://{HOST}:{port}/api/health"


def open_demo(url: str) -> None:
    if os.getenv("B3_NO_BROWSER") == "1":
        print(f"已禁用自动打开浏览器，请访问：{url}")
        return
    webbrowser.open(url)


def is_b3_running(port: int) -> bool:
    """Return True only when the B3 API is already answering on this port."""
    try:
        with urllib.request.urlopen(_health_url(port), timeout=0.8) as response:
            data = json.load(response)
        return response.status == 200 and str(data.get("app", "")).startswith("B3")
    except (OSError, ValueError, urllib.error.URLError):
        return False


def port_is_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((HOST, port))
        except OSError:
            return False
    return True


def choose_port() -> int | None:
    for port in PORT_RANGE:
        if is_b3_running(port):
            print(f"检测到 B3 演示已在运行：http://{HOST}:{port}")
            open_demo(f"http://{HOST}:{port}")
            return None
        if port_is_free(port):
            return port
    return -1


def open_browser_when_ready(port: int) -> None:
    for _ in range(80):
        if is_b3_running(port):
            open_demo(f"http://{HOST}:{port}")
            return
        time.sleep(0.5)
    print(f"浏览器未自动打开，请手动访问：http://{HOST}:{port}")


def main() -> int:
    port = choose_port()
    if port is None:
        time.sleep(1.5)
        return 0
    if port < 0:
        print("错误：8000-8009 端口均被占用，无法启动演示。")
        return 1

    url = f"http://{HOST}:{port}"
    print("=" * 64)
    print(" B3 高校师资/人才智能画像与辅助管理平台 - 便携演示版")
    print(f" 访问地址：{url}")
    print(f" 运行日志：{LOG_FILE}")
    print(" 数据均为模拟数据；关闭此窗口即停止服务。")
    print("=" * 64)
    logging.getLogger(__name__).info("Starting B3 portable demo at %s; log=%s", url, LOG_FILE)

    threading.Thread(target=open_browser_when_ready, args=(port,), daemon=True).start()
    # Keep the root console/file handlers configured in app.logging_setup so
    # Uvicorn startup, access and error logs all reach logs/b3.log.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access", "uvicorn.asgi"):
        uv_logger = logging.getLogger(name)
        uv_logger.handlers.clear()
        uv_logger.propagate = True
        uv_logger.setLevel(logging.INFO)
    config = uvicorn.Config(
        app,
        host=HOST,
        port=port,
        log_config=None,
        log_level="info",
        access_log=True,
    )
    server = uvicorn.Server(config)
    server.run()
    logging.getLogger(__name__).info("B3 portable demo stopped")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(0)
    except Exception as exc:  # keep the console open so a non-technical user can report it
        message = f"启动失败：{type(exc).__name__}: {exc}"
        print(f"\n{message}")
        try:
            LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
            with LOG_FILE.open("a", encoding="utf-8") as fh:
                fh.write("\n" + message + "\n")
                fh.write(traceback.format_exc())
            print(f"错误日志已保存：{LOG_FILE}")
        except OSError:
            pass
        try:
            input("按回车键退出...")
        except EOFError:
            pass
        raise SystemExit(1)
