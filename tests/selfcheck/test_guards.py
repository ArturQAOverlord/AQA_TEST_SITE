"""Самопроверка защиты песочниц: обходные пути должны приводить к провалу миссии.

Это не решения миссий, а тесты самого сайта — поэтому они лежат в отдельной
папке и не показываются на страницах миссий.
"""

from playwright.sync_api import Page, expect


def status(page: Page):
    return page.get_by_test_id("mission-status")


def assert_failed(page: Page, reason: str = ""):
    expect(status(page)).to_have_attribute("data-status", "fail")
    if reason:
        expect(status(page)).to_contain_text(reason)


def test_dispatch_event_is_rejected(page: Page):
    page.goto("/play/first-click")
    page.get_by_role("button", name="Начать").dispatch_event("click")
    assert_failed(page, "синтетическое событие")


def test_js_click_is_rejected(page: Page):
    page.goto("/play/first-click")
    page.evaluate("document.getElementById('start').click()")
    assert_failed(page, "синтетическое событие")


def test_status_tampering_is_rejected(page: Page):
    page.goto("/play/first-click")
    page.evaluate("document.getElementById('mission-status').dataset.status = 'success'")
    assert_failed(page, "изменён вручную")


def test_failure_is_final(page: Page):
    page.goto("/play/by-text")
    page.get_by_text("Котик").click()
    page.get_by_text("Пингвин", exact=True).click()
    assert_failed(page)


def test_success_page_requires_payment(page: Page):
    page.goto("/play/wait-url/success?order=12345")
    assert_failed(page, "напрямую")


def test_direct_tab_url_does_not_count(page: Page):
    page.goto("/play/page-assertions?tab=settings")
    page.wait_for_timeout(500)
    expect(status(page)).to_have_attribute("data-status", "pending")


def test_force_click_is_rejected(page: Page):
    page.goto("/play/actionability")
    page.wait_for_timeout(3200)  # оверлей уже убран, кнопка ещё едет
    page.get_by_role("button", name="Отправить заявку").click(force=True)
    assert_failed(page, "force=True")


def test_fill_does_not_trigger_autocomplete(page: Page):
    page.goto("/play/press-sequentially")
    page.get_by_placeholder("Найти пакет").fill("pytest")
    page.wait_for_timeout(500)
    expect(page.get_by_role("option")).to_have_count(0)


def test_click_before_hydration_is_rejected(page: Page):
    page.goto("/play/wait-for-function")
    page.get_by_role("button", name="Продолжить").click()
    assert_failed(page, "гидратации")


def test_failed_mission_is_not_counted(page: Page):
    page.goto("/play/test-id")
    page.get_by_test_id("plan-basic").click()
    page.get_by_test_id("plan-pro").click()
    assert_failed(page)
    progress = page.request.get("/api/progress").json()
    assert "test-id" not in progress
