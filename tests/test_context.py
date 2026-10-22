from datetime import datetime
from pathlib import Path

from playwright.sync_api import Browser, Page, expect


def assert_passed(page: Page):
    expect(page.get_by_test_id("mission-status")).to_have_attribute("data-status", "success")


def test_cookies(page: Page, base_url: str):
    page.context.add_cookies([{"name": "beta", "value": "on", "url": base_url}])
    page.goto("/play/cookies")
    page.get_by_role("button", name="Попробовать новый редактор").click()
    assert any(c["name"] == "beta" and c["value"] == "on" for c in page.context.cookies())
    assert_passed(page)


def test_local_storage(page: Page):
    page.goto("/play/local-storage")
    page.evaluate("localStorage.setItem('onboarding_done', 'true')")
    page.reload()
    expect(page.get_by_role("dialog", name="Знакомство")).to_be_hidden()
    page.get_by_role("button", name="Создать проект").click()
    assert_passed(page)


def test_mobile_viewport(page: Page):
    page.set_viewport_size({"width": 375, "height": 667})
    page.goto("/play/mobile-viewport")
    contacts = page.get_by_role("link", name="Контакты")
    expect(contacts).to_be_hidden()
    page.get_by_role("button", name="Меню").click()
    contacts.click()
    assert_passed(page)


def test_color_scheme(page: Page):
    page.emulate_media(color_scheme="dark")
    page.goto("/play/color-scheme")
    expect(page.get_by_test_id("card")).to_have_css("background-color", "rgb(13, 17, 23)")
    page.get_by_role("button", name="Сообщить о баге тёмной темы").click()
    assert_passed(page)


def test_init_script(page: Page):
    page.add_init_script("""
        window.__LAB_FLAGS__ = { newCheckout: true };
        Math.random = () => 0.42;
    """)
    page.goto("/play/init-script")
    expect(page.get_by_test_id("lucky")).to_have_text("42")
    page.get_by_role("button", name="Новое оформление заказа").click()
    assert_passed(page)


def test_geolocation(page: Page):
    page.context.grant_permissions(["geolocation"])
    page.context.set_geolocation({"latitude": 55.7961, "longitude": 49.1064})
    page.goto("/play/geolocation")
    page.get_by_role("button", name="Определить город").click()
    expect(page.get_by_text("Ваш город: Казань")).to_be_visible()
    page.get_by_role("button", name="Подтвердить").click()
    assert_passed(page)


def test_storage_state(page: Page, browser: Browser, browser_context_args: dict, tmp_path: Path):
    page.goto("/play/storage-state")
    page.get_by_label("Логин").fill("student")
    page.get_by_label("Пароль").fill("playwright123")
    page.get_by_role("button", name="Войти").click()
    expect(page.get_by_role("heading", name="Личный кабинет")).to_be_visible()

    state = tmp_path / "state.json"
    page.context.storage_state(path=state)

    # browser_context_args — те же настройки, что у фикстуры page (base_url и т.д.)
    context = browser.new_context(**browser_context_args, storage_state=state)
    new_page = context.new_page()
    new_page.goto("/play/storage-state")
    expect(new_page.get_by_role("heading", name="Личный кабинет")).to_be_visible()
    new_page.get_by_role("button", name="Мои курсы").click()
    expect(new_page.get_by_test_id("mission-status")).to_have_attribute("data-status", "success")
    context.close()


def test_clock(page: Page):
    page.clock.install(time=datetime(2026, 12, 31, 23, 58, 0))
    page.goto("/play/clock")
    page.clock.pause_at(datetime(2026, 12, 31, 23, 59, 0))
    expect(page.get_by_test_id("countdown")).to_have_text("До Нового года: 0д 0ч 1м 0с")

    page.clock.fast_forward("01:00")
    expect(page.get_by_role("heading")).to_contain_text("С Новым годом!")
    page.get_by_role("button", name="Получить подарок").click()
    assert_passed(page)
