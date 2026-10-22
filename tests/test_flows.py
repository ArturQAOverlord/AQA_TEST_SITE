import pytest
from playwright.sync_api import Page, expect


def assert_passed(page: Page):
    expect(page.get_by_test_id("mission-status")).to_have_attribute("data-status", "success")


def test_login_flow(page: Page):
    def login(username: str, password: str):
        page.get_by_label("Логин").fill(username)
        page.get_by_label("Пароль").fill(password)
        page.get_by_role("button", name="Войти").click()

    page.goto("/play/login-flow")
    error = page.get_by_role("alert")

    login("", "")
    expect(error).to_have_text("Введите логин")

    login("admin", "wrong")
    expect(error).to_have_text("Неверный логин или пароль")

    login("admin", "secret")
    # exact=True: без него имя сравнивается без учёта регистра и «Admin!» тоже подойдёт
    expect(page.get_by_role("heading", name="Добро пожаловать, admin!", exact=True)).to_be_visible()

    page.get_by_role("button", name="Выйти").click()
    expect(page.get_by_role("heading", name="Вход в систему")).to_be_visible()
    expect(page.get_by_label("Пароль")).to_be_empty()
    assert_passed(page)


def test_e2e_purchase(page: Page):
    page.goto("/play/e2e-purchase")

    phone = page.get_by_role("listitem").filter(has=page.get_by_text("iPhone 17", exact=True))
    phone.get_by_role("button", name="В корзину").click()
    page.get_by_role("button", name="Корзина (1)").click()

    page.get_by_label("Количество").fill("2")
    expect(page.get_by_text("Итого: 199980 ₽")).to_be_visible()
    page.get_by_role("button", name="Оформить заказ").click()

    page.get_by_label("Имя получателя").fill("Тест Тестов")
    page.get_by_label("Адрес доставки").fill("Казань, ул. Баумана, 1")
    page.get_by_label("Картой онлайн").check()
    page.get_by_role("button", name="Подтвердить заказ").click()

    expect(page.get_by_role("heading", name="Спасибо за заказ!")).to_be_visible()
    expect(page.get_by_role("listitem")).to_have_text(["iPhone 17 × 2"])
    assert_passed(page)


def test_conditional_form(page: Page):
    page.goto("/play/conditional-form")
    inn = page.get_by_label("ИНН")
    expect(inn).to_be_hidden()

    page.get_by_label("Тип клиента").select_option(label="Юридическое лицо")
    expect(inn).to_be_visible()
    page.get_by_label("Название компании").fill("ООО Тестировщики")
    inn.fill("12345")

    page.get_by_label("Нужна доставка").check()
    page.get_by_label("Адрес доставки").fill("Москва, Тверская, 7")

    submit = page.get_by_role("button", name="Отправить заявку")
    submit.click()
    expect(page.get_by_role("alert")).to_have_text("ИНН должен содержать 10 цифр")

    inn.fill("7701234567")
    submit.click()
    expect(page.get_by_text("Заявка принята")).to_be_visible()
    assert_passed(page)


def test_wizard(page: Page):
    page.goto("/play/wizard")
    title = page.get_by_role("heading")
    next_button = page.get_by_role("button", name="Далее")

    expect(title).to_have_text("Шаг 1 из 3")
    page.get_by_label("Имя").fill("Анна")
    page.get_by_label("Email").fill("anna@aqa.lab")
    next_button.click()

    expect(title).to_have_text("Шаг 2 из 3")
    page.get_by_label("Pro").check()
    page.get_by_role("button", name="Назад").click()

    expect(title).to_have_text("Шаг 1 из 3")
    expect(page.get_by_label("Имя")).to_have_value("Анна")
    expect(page.get_by_label("Email")).to_have_value("anna@aqa.lab")
    next_button.click()

    expect(page.get_by_label("Pro")).to_be_checked()
    next_button.click()

    expect(title).to_have_text("Шаг 3 из 3")
    summary = page.get_by_role("definition")
    expect(summary).to_have_text(["Анна", "anna@aqa.lab", "Pro"])
    page.get_by_label("Согласен с условиями").check()
    page.get_by_role("button", name="Завершить").click()
    assert_passed(page)


@pytest.mark.parametrize(
    ("password", "message"),
    [
        ("Ab1!", "Минимум 8 символов"),
        ("Abc def1!", "Пароль не должен содержать пробелы"),
        ("Abcdefg!", "Нужна хотя бы одна цифра"),
        ("abcdefg1!", "Нужна заглавная буква"),
        ("Abcdefg1", "Нужен спецсимвол"),
        ("Abcdefg1!", "Аккаунт создан"),
    ],
    ids=["short", "spaces", "no-digit", "no-upper", "no-special", "valid"],
)
def test_parametrize(page: Page, password: str, message: str):
    page.goto("/play/parametrize")
    page.get_by_label("Пароль").fill(password)
    page.get_by_role("button", name="Создать аккаунт").click()
    expect(page.get_by_role("alert")).to_have_text(message)
    assert_passed(page)


def test_crud_table(page: Page):
    def row(name: str):
        return page.get_by_role("row").filter(has=page.get_by_role("cell", name=name, exact=True))

    page.goto("/play/crud-table")
    dialog = page.get_by_role("dialog")

    page.get_by_role("button", name="Добавить").click()
    dialog.get_by_label("Имя").fill("Глеб")
    dialog.get_by_label("Телефон").fill("+7 999 000-00-04")
    dialog.get_by_role("button", name="Сохранить").click()
    expect(dialog).to_be_hidden()

    row("Борис").get_by_role("button", name="Изменить").click()
    dialog.get_by_label("Телефон").fill("+7 999 111-11-11")
    dialog.get_by_role("button", name="Сохранить").click()

    page.once("dialog", lambda native_dialog: native_dialog.accept())
    row("Вера").get_by_role("button", name="Удалить").click()

    expect(page.get_by_test_id("contact-name")).to_have_text(["Алиса", "Борис", "Глеб"])
    expect(row("Борис").get_by_test_id("contact-phone")).to_have_text("+7 999 111-11-11")
    page.get_by_role("button", name="Сохранить изменения").click()
    assert_passed(page)
