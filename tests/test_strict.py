from playwright.sync_api import Page, expect


def assert_passed(page: Page):
    expect(page.get_by_test_id("mission-status")).to_have_attribute("data-status", "success")


def test_strict_three_buttons(page: Page):
    page.goto("/play/strict-three-buttons")
    archived = page.get_by_role("article").filter(has_text="Архив")
    archived.get_by_role("button", name="Удалить").click()
    assert_passed(page)


def test_exact_match(page: Page):
    page.goto("/play/exact-match")
    page.get_by_role("button", name="Сохранить", exact=True).click()
    assert_passed(page)


def test_role_disambiguation(page: Page):
    page.goto("/play/role-disambiguation")
    page.get_by_role("button", name="Избранное").click()
    expect(page.get_by_role("complementary")).to_contain_text("Наушники Lab Pro")
    assert_passed(page)


def test_all_elements(page: Page):
    page.goto("/play/all-elements")
    checkboxes = page.get_by_role("checkbox")
    for checkbox in checkboxes.all():
        checkbox.check()
    expect(page.get_by_text(f"Отмечено {checkboxes.count()} из {checkboxes.count()}")).to_be_visible()
    page.get_by_role("button", name="Выпустить релиз").click()
    assert_passed(page)


def test_random_popup(page: Page):
    page.add_locator_handler(
        page.get_by_role("dialog", name="Специальное предложение"),
        lambda: page.get_by_role("button", name="Не сейчас").click(),
    )
    page.goto("/play/random-popup")
    for n in (1, 2, 3):
        page.get_by_role("button", name=f"Шаг {n}").click()
    assert_passed(page)
