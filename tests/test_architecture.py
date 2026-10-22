import uuid

import pytest
from playwright.sync_api import Page, expect


def assert_passed(page: Page):
    expect(page.get_by_test_id("mission-status")).to_have_attribute("data-status", "success")


PRODUCTS = [
    ("Клавиатура", 4990, "Периферия"),
    ("Монитор", 19990, "Мониторы"),
    ("Мышь", 1990, "Периферия"),
]


class LoginPage:
    def __init__(self, page: Page):
        self.page = page
        self.username = page.get_by_label("Логин")
        self.password = page.get_by_label("Пароль")
        self.submit = page.get_by_role("button", name="Войти")

    def open(self) -> "LoginPage":
        self.page.goto("/play/page-object")
        return self

    def login(self, username: str, password: str) -> "ProductsPage":
        self.username.fill(username)
        self.password.fill(password)
        self.submit.click()
        return ProductsPage(self.page)


class ProductsPage:
    def __init__(self, page: Page):
        self.page = page
        self.heading = page.get_by_role("heading", name="Товары")
        self.add_button = page.get_by_role("button", name="Добавить товар")
        self.dialog = page.get_by_role("dialog", name="Новый товар")

    def add_product(self, name: str, price: int, category: str) -> None:
        self.add_button.click()
        self.dialog.get_by_label("Название").fill(name)
        self.dialog.get_by_label("Цена").fill(str(price))
        self.dialog.get_by_label("Категория").select_option(category)
        self.dialog.get_by_role("button", name="Сохранить").click()
        expect(self.dialog).to_be_hidden()

    def row(self, name: str):
        return self.page.get_by_role("row").filter(has=self.page.get_by_role("cell", name=name, exact=True))


@pytest.fixture
def logged_in_page(page: Page) -> Page:
    response = page.request.post("/api/login", data={"username": "student", "password": "playwright123"})
    expect(response).to_be_ok()
    return page


@pytest.mark.smoke
def test_markers(page: Page):
    page.goto("/play/markers")
    page.get_by_role("button", name="Проверить").click()
    expect(page.get_by_test_id("service-status")).to_have_text(["OK", "OK", "OK"])
    assert_passed(page)


def test_fixtures(logged_in_page: Page):
    page = logged_in_page
    page.goto("/play/fixtures")
    expect(page.get_by_role("heading", name="Мои курсы")).to_be_visible()
    page.get_by_role("button", name="Продолжить обучение").click()
    assert_passed(page)


def test_page_object(page: Page):
    products = LoginPage(page).open().login("student", "playwright123")
    expect(products.heading).to_be_visible()
    for name, price, category in PRODUCTS:
        products.add_product(name, price, category)
    for name, price, category in PRODUCTS:
        expect(products.row(name)).to_contain_text(f"{price}{category}")
    assert_passed(page)


def test_isolation(page: Page):
    title = f"Тест {uuid.uuid4().hex[:8]}"
    page.goto("/play/isolation")
    page.get_by_label("Название карточки").fill(title)
    page.get_by_role("button", name="Создать").click()

    card = page.get_by_role("listitem").filter(has=page.get_by_text(title, exact=True))
    expect(card).to_have_count(1)
    card.get_by_role("button", name="Удалить").click()
    expect(card).to_have_count(0)
    assert_passed(page)
