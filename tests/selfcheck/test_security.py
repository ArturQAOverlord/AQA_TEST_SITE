"""Проверки защиты эндпоинтов, выполняющих код (без браузера, через тестовый клиент)."""

import pytest

from app import create_app

LOCAL = {"REMOTE_ADDR": "127.0.0.1"}
JSON = {"Content-Type": "application/json"}


@pytest.fixture
def client():
    return create_app().test_client()


def test_run_rejects_cross_origin(client):
    r = client.post("/api/run/first-click", json={"code": "x"},
                    headers={"Origin": "http://evil.example"}, environ_base=LOCAL)
    assert r.status_code == 403


def test_run_rejects_foreign_host(client):
    r = client.post("/api/run/first-click", json={"code": "x"},
                    headers={"Host": "evil.example"}, environ_base=LOCAL)
    assert r.status_code == 403


def test_run_rejects_non_json_content_type(client):
    # Кросс-доменный «простой» запрос не может быть application/json без preflight.
    # Код 415 (а не 403) доказывает заодно, что локальный same-origin запрос проходит
    # проверку доступа и отсекается уже на этапе разбора тела.
    r = client.post("/api/run/first-click", data="code=x",
                    content_type="application/x-www-form-urlencoded", environ_base=LOCAL)
    assert r.status_code == 415


def test_run_rejects_remote_address(client):
    r = client.post("/api/run/first-click", json={"code": "x"},
                    environ_base={"REMOTE_ADDR": "192.168.1.50"})
    assert r.status_code == 403


def test_save_rejects_cross_origin(client):
    r = client.put("/api/solution/first-click", json={"code": "x"},
                   headers={"Origin": "http://evil.example"}, environ_base=LOCAL)
    assert r.status_code == 403


def test_verify_rejects_cross_origin(client):
    r = client.post("/api/verify/markers", json={},
                    headers={"Origin": "http://evil.example"}, environ_base=LOCAL)
    assert r.status_code == 403


def test_stored_xss_payload_is_not_executed_as_markup(client):
    # Сервер не обязан чистить title (это делает страница через textContent),
    # но и не должен падать на таком вводе
    r = client.post("/api/todos", json={"title": "<img src=x onerror=alert(1)>"})
    assert r.status_code == 201
    assert r.get_json()["title"] == "<img src=x onerror=alert(1)>"


def test_run_video_serves_only_recordings(client):
    # Отдаются только .webm из папки записей миссии — ни выхода за её пределы, ни других файлов
    assert client.get("/api/run/first-click/video/..%2F..%2Fapp.py").status_code == 404
    assert client.get("/api/run/first-click/video/../../progress.json").status_code == 404
    assert client.get("/api/run/first-click/video/notes.txt").status_code == 404
    assert client.get("/api/run/no-such-mission/video/video.webm").status_code == 404


def test_live_frames_need_run_token(client):
    # Кадры живого показа принимаются только от pytest, запущенного кнопкой «Запустить»
    frame = {"data": b"\xff\xd8jpeg", "content_type": "image/jpeg"}
    assert client.post("/api/live/first-click/frame", **frame).status_code == 403
    assert client.post("/api/live/first-click/frame", headers={"X-Live-Token": "guess"}, **frame).status_code == 403
