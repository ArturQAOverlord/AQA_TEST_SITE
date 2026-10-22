import re

from playwright.sync_api import Page, expect


def assert_passed(page: Page):
    expect(page.get_by_test_id("mission-status")).to_have_attribute("data-status", "success")


def test_wait_appear(page: Page):
    page.goto("/play/wait-appear")
    page.get_by_role("button", name="Загрузить профиль").click()
    expect(page.get_by_text("Алиса Иванова")).to_be_visible()
    page.get_by_role("button", name="Написать сообщение").click()
    assert_passed(page)


def test_custom_timeout(page: Page):
    page.goto("/play/custom-timeout")
    page.get_by_role("button", name="Сформировать отчёт").click()
    expect(page.get_by_text("Отчёт готов")).to_be_visible(timeout=10_000)
    page.get_by_role("button", name="Скачать отчёт").click()
    assert_passed(page)


def test_actionability(page: Page):
    page.goto("/play/actionability")
    page.get_by_role("button", name="Отправить заявку").click()
    assert_passed(page)


def test_wait_url(page: Page):
    page.goto("/play/wait-url")
    page.get_by_role("button", name="Оплатить").click()
    expect(page).to_have_url(re.compile(r"/success\?order=\d+$"))
    expect(page.get_by_role("heading", name="Оплата прошла")).to_be_visible()
    assert_passed(page)


def test_wait_response(page: Page):
    page.goto("/play/wait-response")
    with page.expect_response("**/api/rates") as response_info:
        page.get_by_role("button", name="Обновить курс").click()
    rate = response_info.value.json()["rate"]

    page.get_by_label("Курс из ответа").fill(str(rate))
    page.get_by_role("button", name="Проверить").click()
    assert_passed(page)


def test_flaky_fix(page: Page):
    page.goto("/play/flaky-fix")
    page.get_by_role("button", name="Загрузить задачи").click()

    checkboxes = page.get_by_role("checkbox")
    expect(checkboxes).to_have_count(5)
    for checkbox in checkboxes.all():
        checkbox.check()

    page.get_by_role("button", name="Готово").click()
    assert_passed(page)


def test_networkidle(page: Page):
    page.goto("/play/networkidle")
    page.wait_for_load_state("networkidle")
    # Надёжнее ждать конкретный признак готовности:
    expect(page.locator('[data-testid="widget"][data-loaded="true"]')).to_have_count(4)
    page.get_by_role("button", name="Сохранить отчёт").click()
    assert_passed(page)


def test_wait_request(page: Page):
    page.goto("/play/wait-request")
    page.get_by_label("Оценка").select_option("5")
    page.get_by_label("Комментарий").fill("Отлично")
    with page.expect_request("**/api/feedback") as request_info:
        page.get_by_role("button", name="Отправить").click()
    request = request_info.value

    assert request.method == "POST"
    assert request.post_data_json == {"rating": 5, "comment": "Отлично", "source": "lab"}
    expect(page.get_by_text("Спасибо!")).to_be_visible()
    assert_passed(page)


def test_toast(page: Page):
    page.goto("/play/toast")
    page.get_by_role("button", name="Сохранить").click()
    toast = page.get_by_role("status")
    expect(toast).to_have_text("Изменения сохранены")
    expect(toast).to_be_hidden()
    assert_passed(page)


def test_stale_elements(page: Page):
    page.goto("/play/stale-elements")
    row = page.get_by_role("listitem").filter(has_text="Товар B")
    expect(row.get_by_test_id("price")).to_have_text(re.compile(r"^9\d\d ₽$"), timeout=15_000)
    row.get_by_role("button", name="Купить").click()
    assert_passed(page)


def test_wait_for_function(page: Page):
    page.goto("/play/wait-for-function")
    page.wait_for_function("() => window.app && window.app.ready")
    page.get_by_role("button", name="Продолжить").click()
    assert_passed(page)
