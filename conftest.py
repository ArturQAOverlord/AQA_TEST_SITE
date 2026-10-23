"""Общие настройки для tests/ (эталонные решения) и exercises/ (твои решения).

Если сайт ещё не запущен (python app.py), он поднимется автоматически
в фоне на время прогона тестов. При параллельном запуске (pytest -n 4)
сервер поднимает главный процесс pytest, а воркеры xdist им пользуются.
"""

import base64
import os
import queue
import socket
import threading
import urllib.error
import urllib.request
from urllib.parse import urlparse

import pytest
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


class _LiveView:
    """Шлёт кадры экрана страницы теста на сайт — так их видно справа на странице миссии.

    Включается, только когда тест запущен кнопкой «Запустить» (сайт передаёт LAB_LIVE_URL и
    одноразовый LAB_LIVE_TOKEN). Кадры снимает Chromium (CDP screencast), отправляет фоновый
    поток: тест не ждёт сети, а если сайт не успевает, промежуточные кадры просто пропускаются.
    """

    def __init__(self, url: str, token: str):
        self.url, self.token = url, token
        self.frames: queue.Queue = queue.Queue(maxsize=1)
        threading.Thread(target=self._send_loop, daemon=True).start()

    def attach(self, page):
        try:
            cdp = page.context.new_cdp_session(page)
        except Exception:
            return  # не Chromium — показать вживую нечего, останется видео прогона

        def on_frame(event):
            try:
                cdp.send("Page.screencastFrameAck", {"sessionId": event["sessionId"]})
            except Exception:
                return
            frame = base64.b64decode(event["data"])
            try:
                self.frames.get_nowait()  # нужен только самый свежий кадр
            except queue.Empty:
                pass
            self.frames.put_nowait(frame)

        cdp.on("Page.screencastFrame", on_frame)
        cdp.send("Page.startScreencast", {"format": "jpeg", "quality": 70, "maxWidth": 1280, "maxHeight": 900})

    def _send_loop(self):
        while True:
            frame = self.frames.get()
            if frame is None:
                return
            req = urllib.request.Request(self.url, data=frame, method="POST",
                                         headers={"Content-Type": "image/jpeg", "X-Live-Token": self.token})
            try:
                urllib.request.urlopen(req, timeout=2).close()
            except (urllib.error.URLError, socket.timeout, ConnectionError):
                pass

    def flush(self):
        """Дождаться отправки последнего кадра, чтобы справа осталось финальное состояние страницы."""
        frame = None
        try:
            frame = self.frames.get_nowait()
        except queue.Empty:
            pass
        if frame is not None:
            req = urllib.request.Request(self.url, data=frame, method="POST",
                                         headers={"Content-Type": "image/jpeg", "X-Live-Token": self.token})
            try:
                urllib.request.urlopen(req, timeout=2).close()
            except (urllib.error.URLError, socket.timeout, ConnectionError):
                pass


@pytest.fixture(autouse=True)
def _lab_live_view(request):
    url, token = os.environ.get("LAB_LIVE_URL"), os.environ.get("LAB_LIVE_TOKEN")
    if not (url and token and "page" in request.fixturenames):
        yield
        return
    page = request.getfixturevalue("page")
    live = _LiveView(url, token)
    live.attach(page)
    page.context.on("page", live.attach)  # новые вкладки и всплывающие окна тоже показываем
    yield
    try:
        page.wait_for_timeout(300)  # последний кадр после финального действия
    except Exception:
        pass
    live.flush()
