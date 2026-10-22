import re

from playwright.sync_api import Page, expect


def assert_passed(page: Page):
    expect(page.get_by_test_id("mission-status")).to_have_attribute("data-status", "success")


def test_first_click(page: Page):
    page.goto("/play/first-click")
    page.get_by_role("button", name="Начать").click()
    assert_passed(page)


def test_by_text(page: Page):
    page.goto("/play/by-text")
    page.get_by_text("Пингвин", exact=True).click()
    assert_passed(page)


def test_by_label(page: Page):
    page.goto("/play/by-label")
    page.get_by_label("Имя").fill("Иван")
    page.get_by_label("Фамилия").fill("Петров")
    page.get_by_label("Email").fill("ivan@test.ru")
    page.get_by_label("Согласен на обработку данных").check()
    page.get_by_role("button", name="Отправить").click()
    assert_passed(page)


def test_by_placeholder(page: Page):
    page.goto("/play/by-placeholder")
    search = page.get_by_placeholder("Поиск по каталогу")
    search.fill("наушники")
    search.press("Enter")
    assert_passed(page)


def test_test_id(page: Page):
    page.goto("/play/test-id")
    page.get_by_test_id("plan-pro").click()
    assert_passed(page)


def test_alt_title(page: Page):
    page.goto("/play/alt-title")
    page.get_by_alt_text("Море").click()
    page.get_by_title("Добавить в избранное").click()
    assert_passed(page)


def test_filter_has_text(page: Page):
    page.goto("/play/filter-has-text")
    product = page.get_by_role("listitem").filter(has_text="Скидка")
    product.get_by_role("button", name="В корзину").click()
    assert_passed(page)


def test_filter_has(page: Page):
    page.goto("/play/filter-has")
    pinned = page.get_by_role("listitem").filter(has=page.get_by_test_id("icon-pinned"))
    pinned.get_by_role("button", name="Выполнить").click()
    assert_passed(page)


def test_nth_first_last(page: Page):
    page.goto("/play/nth-first-last")
    buttons = page.get_by_role("button", name="Прочитано")
    buttons.first.click()
    buttons.nth(2).click()
    buttons.last.click()
    assert_passed(page)


def test_chaining(page: Page):
    page.goto("/play/chaining")
    letter = (
        page.get_by_role("region", name="Отправленные")
        .get_by_role("listitem")
        .filter(has=page.get_by_text("Отчёт за квартал", exact=True))
    )
    letter.get_by_role("button", name="Открыть").click()
    assert_passed(page)


def test_shadow_dom(page: Page):
    page.goto("/play/shadow-dom")
    page.get_by_label("Никнейм").fill("neo")
    page.get_by_role("button", name="Сохранить").click()
    assert_passed(page)


def test_dynamic_ids(page: Page):
    page.goto("/play/dynamic-ids")
    page.get_by_label("Код из SMS").fill("4242")
    page.get_by_role("button", name="Подтвердить").click()
    assert_passed(page)


def test_table(page: Page):
    page.goto("/play/table")
    row = (
        page.get_by_role("row")
        .filter(has_text="Анна Смирнова")
        .filter(has=page.get_by_role("cell", name="QA", exact=True))
    )
    row.get_by_role("button", name="Изменить").click()
    assert_passed(page)


def test_iframe(page: Page):
    page.goto("/play/iframe")
    frame = page.frame_locator('iframe[title="Подписка на рассылку"]')
    frame.get_by_placeholder("Ваш email").fill("student@aqa.lab")
    frame.get_by_role("button", name="Подписаться").click()
    assert_passed(page)


def test_css_xpath(page: Page):
    page.goto("/play/css-xpath")
    page.locator(
        "xpath=//span[text()='#A-1042']/ancestor::div[contains(@class,'order-row')]//div[@data-action='archive']"
    ).click()
    assert_passed(page)


def test_accordion(page: Page):
    page.goto("/play/accordion")
    question = page.get_by_role("button", name="Как вернуть товар?")
    question.click()
    expect(question).to_have_attribute("aria-expanded", "true")
    expect(page.get_by_role("region", name="Как вернуть товар?")).to_contain_text("14 дней")
    assert_passed(page)


def test_and_or(page: Page):
    page.goto("/play/and-or")
    page.get_by_role("button", name="Подтвердить").and_(page.get_by_title("Подтвердить оплату")).click()
    page.get_by_role("button", name="Принять cookies").or_(page.get_by_role("button", name="Согласен")).click()
    assert_passed(page)


def test_cheapest_product(page: Page):
    page.goto("/play/cheapest-product")
    cards = page.get_by_role("listitem")
    expect(cards).to_have_count(8)
    prices = [int(re.sub(r"\D", "", text)) for text in page.get_by_test_id("price").all_inner_texts()]
    cards.nth(prices.index(min(prices))).get_by_role("button", name="Купить").click()
    assert_passed(page)


def test_bad_markup(page: Page):
    def field(name: str):
        return page.locator(".form-row").filter(has=page.get_by_text(name, exact=True)).locator("input")

    page.goto("/play/bad-markup")
    field("Номер карты").fill("4242 4242 4242 4242")
    field("Срок действия").fill("12/30")
    page.locator("xpath=//span[text()='CVC']/following-sibling::input").fill("123")
    field("Имя на карте").fill("IVAN PETROV")
    page.get_by_role("button", name="Оплатить").click()
    assert_passed(page)


def test_nested_shadow(page: Page):
    page.goto("/play/nested-shadow")
    switch = page.get_by_role("switch", name="Push-уведомления", exact=True)
    switch.click()
    expect(switch).to_have_attribute("aria-checked", "true")
    assert_passed(page)


def test_pagination(page: Page):
    page.goto("/play/pagination")
    row = page.get_by_role("row").filter(has_text="Зоя Кузнецова")
    info = page.get_by_test_id("page-info")
    number = 1
    expect(info).to_have_text(f"Страница {number} из 5")
    while row.count() == 0:
        page.get_by_role("button", name="Вперёд").click()
        number += 1
        expect(info).to_have_text(f"Страница {number} из 5")
    row.get_by_role("button", name="Написать").click()
    assert_passed(page)


def test_nested_iframes(page: Page):
    page.goto("/play/nested-iframes")
    widget = page.frame_locator('iframe[title="Платёжный виджет"]')
    card = widget.frame_locator('iframe[title="Ввод карты"]')
    card.get_by_label("Номер карты").fill("4242 4242 4242 4242")
    widget.get_by_role("button", name="Оплатить 990 ₽").click()
    assert_passed(page)
