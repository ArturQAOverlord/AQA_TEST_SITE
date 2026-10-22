"""Общие настройки для tests/ (эталонные решения) и exercises/ (твои решения).

Если сайт ещё не запущен (python app.py), он поднимется автоматически
в фоне на время прогона тестов. При параллельном запуске (pytest -n 4)
сервер поднимает главный процесс pytest, а воркеры xdist им пользуются.
"""

import socket
import threading
import urllib.error
import urllib.request
from urllib.parse import urlparse

from werkzeug.serving import make_server

from app import create_app


def _lab_is_running(base_url: str) -> bool:
    """True, только если на адресе отвечает именно наша лаборатория.

    Просто «порт открыт» недостаточно: на этом порту может сидеть чужой сервис
    (на macOS, например, 5000 занимает AirPlay). Проверяем заголовок-маркер.
    """
    try:
        with urllib.request.urlopen(f"{base_url.rstrip('/')}/api/progress", timeout=1) as resp:
            return resp.headers.get("X-Lab") == "1"
    except (urllib.error.URLError, socket.timeout, ConnectionError):
        return False


def pytest_configure(config):
    if hasattr(config, "workerinput"):
        return  # воркер xdist: сервер уже поднят главным процессом
    if config.getoption("collectonly"):
        return  # при --collect-only тесты не запускаются — сервер не нужен
    base_url = config.getoption("base_url", None) or config.getini("base_url")
    if not base_url:
        return
    if _lab_is_running(base_url):
        return  # лаборатория уже запущена (python app.py или главный процесс pytest)
    url = urlparse(base_url)
    server = make_server(url.hostname, url.port or 80, create_app(), threaded=True)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    config._lab_server = server


def pytest_unconfigure(config):
    server = getattr(config, "_lab_server", None)
    if server:
        server.shutdown()
