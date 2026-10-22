import re

import pytest
from playwright.sync_api import Page, expect


def assert_passed(page: Page):
    expect(page.get_by_test_id("mission-status")).to_have_attribute("data-status", "success")


@pytest.mark.parametrize(("quantity", "total"), [(9, 2700), (10, 2550), (20, 5100)])
def test_bug_cart_total(page: Page, quantity: int, total: int):
    page.goto("/play/bug-cart-total")
    page.get_by_label("Количество").fill(str(quantity))
    expect(page.get_by_test_id("total")).to_have_text(f"Итого: {total} ₽")


@pytest.mark.parametrize(("length", "valid"), [(7, False), (8, True), (20, True), (21, False)])
def test_bug_boundary(page: Page, length: int, valid: bool):
    page.goto("/play/bug-boundary")
    page.get_by_label("Пароль").fill("a" * length)
    page.get_by_role("button", name="Проверить").click()
    expected = "Пароль подходит" if valid else "Длина пароля должна быть от 8 до 20 символов"
    expect(page.get_by_role("alert")).to_have_text(expected)


def test_bug_sorting(page: Page):
    page.goto("/play/bug-sorting")
    prices = page.get_by_test_id("price")
    values = [int(text.removesuffix(" ₽")) for text in prices.all_inner_texts()]
    sort_button = page.get_by_role("button", name="Цена")

    sort_button.click()
    expect(prices).to_have_text([f"{v} ₽" for v in sorted(values)])
    sort_button.click()
    expect(prices).to_have_text([f"{v} ₽" for v in sorted(values, reverse=True)])


def test_bug_pagination(page: Page):
    page.goto("/play/bug-pagination")
    next_button = page.get_by_role("button", name="Следующая")
    page_number = page.get_by_test_id("page-number")
    collected, number = [], 1
    while True:
        expect(page_number).to_have_text(re.compile(rf"^Страница {number} из"))
        collected += page.get_by_role("list", name="Каталог").get_by_role("listitem").all_inner_texts()
        if next_button.is_disabled():
            break
        next_button.click()
        number += 1
    assert collected == [f"Товар {i}" for i in range(1, 24)]


def test_fix_brittle_locators(page: Page):
    page.goto("/play/fix-brittle-locators")
    page.get_by_label("Имя").fill("Иван")
    page.get_by_label("Email").fill("ivan@test.ru")
    page.get_by_label("Тариф").select_option(label="Pro")
    page.get_by_role("button", name="Подписаться").click()
    assert_passed(page)


def test_fix_sleeps(page: Page):
    page.goto("/play/fix-sleeps")
    page.get_by_role("button", name="Сгенерировать").click()
    expect(page.get_by_text("Отчёт готов")).to_be_visible(timeout=10_000)
    page.get_by_role("button", name="Скачать").click()
    assert_passed(page)
