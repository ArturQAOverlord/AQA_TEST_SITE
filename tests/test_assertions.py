import re

from playwright.sync_api import Page, expect


def assert_passed(page: Page):
    expect(page.get_by_test_id("mission-status")).to_have_attribute("data-status", "success")


def test_text_assertions(page: Page):
    page.goto("/play/text-assertions")
    page.get_by_role("button", name="Оформить заказ").click()

    alert = page.get_by_role("alert")
    expect(alert).to_have_text(re.compile(r"^\s*Заказ №\d{5} успешно оформлен\s*$"))
    expect(alert).to_contain_text("успешно оформлен")
    expect(page.get_by_role("listitem")).to_have_text(
        ["Мы соберём заказ", "Курьер позвонит заранее", "Оплата при получении"]
    )
    assert_passed(page)


def test_count_assertions(page: Page):
    page.goto("/play/count-assertions")
    for product in ("Кружка", "Стикеры", "Рюкзак"):
        page.get_by_role("listitem").filter(has_text=product).get_by_role("button", name="Добавить").click()

    cart = page.get_by_role("list", name="Корзина").get_by_role("listitem")
    badge = page.get_by_test_id("cart-count")
    expect(cart).to_have_count(3)
    expect(badge).to_have_text("3")

    cart.first.get_by_role("button", name="Убрать").click()
    expect(cart).to_have_count(2)
    expect(badge).to_have_text("2")
    assert_passed(page)


def test_value_assertions(page: Page):
    page.goto("/play/value-assertions")
    page.get_by_label("Город").select_option("Казань")
    expect(page.get_by_label("Индекс")).to_have_value("420111")

    page.get_by_label("Телефон").fill("9991234567")
    expect(page.get_by_label("Телефон")).to_have_value("+7 (999) 123-45-67")
    expect(page.get_by_label("Комментарий")).to_be_empty()
    assert_passed(page)


def test_attribute_assertions(page: Page):
    page.goto("/play/attribute-assertions")
    switch = page.get_by_role("switch", name="Двухфакторная аутентификация")
    expect(switch).to_have_attribute("aria-checked", "false")

    switch.click()
    expect(switch).to_have_attribute("aria-checked", "true")
    expect(switch).to_have_class(re.compile(r"\bis-on\b"))
    expect(switch).to_be_checked()

    link = page.get_by_role("link", name="Подробнее о 2FA")
    expect(link).to_have_attribute("href", "/docs/2fa")
    expect(link).to_have_attribute("target", "_blank")
    assert_passed(page)


def test_state_assertions(page: Page):
    page.goto("/play/state-assertions")
    submit = page.get_by_role("button", name="Зарегистрироваться")
    terms = page.get_by_label("Принимаю условия")

    expect(submit).to_be_disabled()
    expect(terms).not_to_be_checked()
    expect(page.get_by_label("Логин")).not_to_be_editable()
    expect(page.get_by_label("Email")).to_be_editable()

    page.get_by_label("Email").fill("me@aqa.lab")
    terms.check()
    expect(terms).to_be_checked()
    expect(submit).to_be_enabled()
    submit.click()
    assert_passed(page)


def test_negative_assertions(page: Page):
    page.goto("/play/negative-assertions")
    error = page.get_by_role("alert")
    subscribe = page.get_by_role("button", name="Подписаться")
    expect(error).not_to_be_visible()

    page.get_by_label("Email").fill("not-an-email")
    subscribe.click()
    expect(error).to_have_text("Некорректный email")

    page.get_by_label("Email").fill("me@aqa.lab")
    subscribe.click()
    expect(error).to_be_hidden()
    expect(subscribe).not_to_be_attached()
    assert_passed(page)


def test_page_assertions(page: Page):
    page.goto("/play/page-assertions")
    expect(page).to_have_title("Профиль — Личный кабинет")

    page.get_by_role("tab", name="Настройки").click()
    expect(page).to_have_url(re.compile(r"\?tab=settings$"))
    expect(page).to_have_title("Настройки — Личный кабинет")
    assert_passed(page)


def test_css_assertions(page: Page):
    page.goto("/play/css-assertions")
    expect(page.get_by_role("button", name="Удалить аккаунт")).to_have_css("background-color", "rgb(207, 34, 46)")

    page.get_by_role("switch", name="Тёмная тема").check()
    panel = page.get_by_test_id("settings-panel")
    expect(panel).to_have_css("background-color", "rgb(31, 36, 48)")
    expect(panel).to_have_css("color", "rgb(230, 233, 239)")
    assert_passed(page)


def test_a11y_assertions(page: Page):
    page.goto("/play/a11y-assertions")
    expect(page.get_by_test_id("bell")).to_have_role("button")

    page.get_by_role("button", name="Открыть настройки").click()
    dialog = page.get_by_role("dialog")
    expect(dialog).to_have_accessible_name("Настройки профиля")
    expect(dialog.get_by_label("Новый пароль")).to_have_accessible_description("Не менее 8 символов")

    close = dialog.get_by_role("button", name="Закрыть", exact=True)
    expect(close).to_have_accessible_name("Закрыть")
    close.click()
    expect(dialog).to_be_hidden()
    assert_passed(page)


def test_api_assertions(page: Page):
    users = page.request.get("/api/users")
    expect(users).to_be_ok()
    data = users.json()
    assert len(data) == 3
    assert data[0]["name"] == "Алиса"

    response = page.request.post("/api/todos", data={"title": "Написать тест"})
    assert response.status == 201
    todo = response.json()
    assert todo["title"] == "Написать тест"
    assert todo["done"] is False
    assert isinstance(todo["id"], int)

    page.goto("/play/api-assertions")
    mine = page.get_by_role("listitem").filter(has_text="создана тобой")
    expect(mine).to_have_count(1)
    expect(mine).to_contain_text("Написать тест")
    assert_passed(page)


def test_aria_snapshot(page: Page):
    page.goto("/play/aria-snapshot")
    page.get_by_role("button", name="Войти").click()
    expect(page.get_by_role("navigation", name="Основное меню")).to_match_aria_snapshot("""
      - list:
        - listitem:
          - link "Главная"
        - listitem:
          - link "Курсы"
        - listitem:
          - link "Блог"
        - listitem:
          - link "Профиль"
        - listitem:
          - button "Выйти"
    """)
    assert_passed(page)
