"""Общие настройки для tests/ (эталонные решения) и exercises/ (твои решения).

Если сайт ещё не запущен (python app.py), он поднимется автоматически
в фоне на время прогона тестов. При параллельном запуске (pytest -n 4)
сервер поднимает главный процесс pytest, а воркеры xdist им пользуются.
"""

import socket
import threading
from urllib.parse import urlparse

from werkzeug.serving import make_server

from app import create_app


def _port_is_open(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.3)
        return sock.connect_ex((host, port)) == 0


def pytest_configure(config):
    if hasattr(config, "workerinput"):
        return  # воркер xdist: сервер уже поднят главным процессом
    base_url = config.getoption("base_url", None) or config.getini("base_url")
    if not base_url:
        return
    url = urlparse(base_url)
    host, port = url.hostname, url.port or 80
    if _port_is_open(host, port):
        return
    server = make_server(host, port, create_app(), threaded=True)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    config._lab_server = server


def pytest_unconfigure(config):
    server = getattr(config, "_lab_server", None)
    if server:
        server.shutdown()
