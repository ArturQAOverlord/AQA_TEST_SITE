import json
import uuid
from pathlib import Path

from playwright.sync_api import Browser, Page, WebSocketRoute, expect


def assert_passed(page: Page):
    expect(page.get_by_test_id("mission-status")).to_have_attribute("data-status", "success")


def test_websocket_frames(page: Page):
    page.goto("/play/websocket-frames")
    with page.expect_websocket() as ws_info:
        page.get_by_role("button", name="Подписаться на PWRT").click()
    ws = ws_info.value

    with ws.expect_event("framereceived") as frame_info:
        pass  # просто дожидаемся следующего фрейма
    price = json.loads(frame_info.value)["price"]

    page.get_by_label("Цена из фрейма").fill(str(price))
    page.get_by_role("button", name="Проверить").click()
    assert_passed(page)


def test_virtual_list(page: Page):
    page.goto("/play/virtual-list")
    target = page.get_by_test_id("target").inner_text()
    number = int(target.removeprefix("Пользователь #"))

    users = page.get_by_role("list", name="Пользователи")
    users.evaluate("(el, top) => { el.scrollTop = top; }", (number - 1) * 32)
    row = users.get_by_role("listitem").filter(has=page.get_by_text(target, exact=True))
    row.get_by_role("button", name="Открыть").click()
    assert_passed(page)


def test_websocket_mock(page: Page):
    def fake_server(ws: WebSocketRoute):
        def on_message(message):
            if json.loads(message).get("subscribe") == "LAB":
                ws.send(json.dumps({"symbol": "LAB", "price": 1000}))
                ws.send(json.dumps({"symbol": "LAB", "price": 1100}))

        ws.on_message(on_message)

    page.route_web_socket("**/ws/quotes", fake_server)
    page.goto("/play/websocket-mock")
    page.get_by_role("button", name="Подписаться на LAB").click()
    expect(page.get_by_test_id("quote")).to_have_text("LAB: 1100 ₽ (+10.0%)")
    assert_passed(page)


def test_multi_user_chat(page: Page, browser: Browser, browser_context_args: dict):
    room = uuid.uuid4().hex

    def join(user_page: Page, name: str):
        user_page.goto(f"/play/multi-user-chat?room={room}")
        user_page.get_by_label("Ваше имя").fill(name)
        user_page.get_by_role("button", name="Войти в чат").click()

    def say(user_page: Page, text: str):
        user_page.get_by_label("Сообщение").fill(text)
        user_page.get_by_role("button", name="Отправить").click()

    bob_context = browser.new_context(**browser_context_args)
    bob = bob_context.new_page()
    join(page, "Алиса")
    join(bob, "Борис")

    say(page, "Привет, Борис!")
    expect(bob.get_by_role("log")).to_contain_text("Алиса: Привет, Борис!")
    say(bob, "Привет, Алиса!")
    expect(page.get_by_role("log")).to_contain_text("Борис: Привет, Алиса!")

    for user_page in (page, bob):
        expect(user_page.get_by_test_id("mission-status")).to_have_attribute("data-status", "success")
    bob_context.close()


def test_offline_sw(page: Page):
    page.goto("/play/offline-sw")
    expect(page.get_by_test_id("sw-state")).to_have_text("Офлайн-режим готов")

    page.context.set_offline(True)
    page.reload()
    offline_banner = page.get_by_role("alert")
    expect(offline_banner).to_have_text("Нет сети — показаны сохранённые статьи")
    expect(page.get_by_role("list", name="Статьи").get_by_role("listitem")).to_have_count(3)

    page.context.set_offline(False)
    expect(offline_banner).to_be_hidden()
    page.get_by_role("button", name="Синхронизировать").click()
    assert_passed(page)


def test_har_replay(page: Page, browser: Browser, browser_context_args: dict, tmp_path: Path):
    har = tmp_path / "forecast.har"

    record_context = browser.new_context(**browser_context_args)
    recorder = record_context.new_page()
    recorder.route_from_har(har, url="**/api/forecast", update=True)
    recorder.goto("/play/har-replay")
    recorder.get_by_role("button", name="Загрузить прогноз").click()
    expect(recorder.get_by_test_id("source")).to_have_text("Живые данные с сервера")
    recorded = recorder.get_by_test_id("forecast").inner_text()
    record_context.close()  # HAR записывается на диск при закрытии контекста

    page.route_from_har(har, url="**/api/forecast")
    page.goto("/play/har-replay")
    page.get_by_role("button", name="Загрузить прогноз").click()
    expect(page.get_by_test_id("forecast")).to_have_text(recorded)
    expect(page.get_by_test_id("source")).to_have_text("Данные из HAR")
    assert_passed(page)
