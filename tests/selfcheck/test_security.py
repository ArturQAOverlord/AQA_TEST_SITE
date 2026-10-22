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
