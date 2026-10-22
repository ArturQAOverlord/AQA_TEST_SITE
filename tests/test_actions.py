import re
from pathlib import Path

from playwright.sync_api import Page, expect


def assert_passed(page: Page):
    expect(page.get_by_test_id("mission-status")).to_have_attribute("data-status", "success")


def test_click_variants(page: Page):
    page.goto("/play/click-variants")
    page.get_by_text("Документы").dblclick()
    page.get_by_text("report.pdf").click(button="right")
    page.get_by_role("menuitem", name="Переименовать").click()
    assert_passed(page)


def test_login_form(page: Page):
    page.goto("/play/login-form")
    page.get_by_label("Логин").fill("student")
    page.get_by_label("Пароль").fill("playwright123")
    page.get_by_label("Запомнить меня").check()
    page.get_by_role("button", name="Войти").click()
    assert_passed(page)


def test_press_sequentially(page: Page):
    page.goto("/play/press-sequentially")
    page.get_by_placeholder("Найти пакет").press_sequentially("pytest", delay=100)
    page.get_by_role("option", name="pytest-playwright").click()
    assert_passed(page)


def test_keyboard(page: Page):
    page.goto("/play/keyboard")
    message = page.get_by_placeholder("Сообщение…")
    message.fill("Привет")
    message.press("Enter")

    page.get_by_role("button", name="Настройки").click()
    expect(page.get_by_role("dialog", name="Настройки")).to_be_visible()
    page.keyboard.press("Escape")
    expect(page.get_by_role("dialog", name="Настройки")).to_be_hidden()

    page.keyboard.press("Control+K")
    expect(page.get_by_role("dialog", name="Палитра команд")).to_be_visible()
    assert_passed(page)


def test_select_option(page: Page):
    page.goto("/play/select-option")
    page.get_by_label("Страна").select_option(label="Казахстан")
    page.get_by_label("Опыт").select_option("senior")
    page.get_by_label("Языки").select_option(["python", "js"])
    page.get_by_role("button", name="Сохранить").click()
    assert_passed(page)


def test_checkbox_radio(page: Page):
    page.goto("/play/checkbox-radio")
    page.get_by_label("Тёмная").check()
    page.get_by_label("Письма на email").uncheck()
    page.get_by_label("Push-уведомления").check()
    page.get_by_label("SMS").set_checked(False)
    page.get_by_role("button", name="Сохранить").click()
    assert_passed(page)


def test_drag_and_drop(page: Page):
    page.goto("/play/drag-and-drop")
    page.get_by_text("Написать автотесты").drag_to(page.get_by_test_id("column-done"))
    expect(page.get_by_test_id("column-done")).to_contain_text("Написать автотесты")
    assert_passed(page)


def test_date_picker(page: Page):
    months = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
              "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]
    target = (2027, 3)

    page.goto("/play/date-picker")
    page.get_by_label("Дата заезда").click()
    title = page.get_by_test_id("calendar-title")
    while True:
        month_name, year = title.inner_text().split()
        current = (int(year), months.index(month_name) + 1)
        if current == target:
            break
        direction = "Следующий месяц" if current < target else "Предыдущий месяц"
        page.get_by_role("button", name=direction).click()

    page.get_by_role("button", name="14", exact=True).click()
    expect(page.get_by_label("Дата заезда")).to_have_value("14.03.2027")
    page.get_by_role("button", name="Забронировать").click()
    assert_passed(page)


def test_hover_menu(page: Page):
    page.goto("/play/hover-menu")
    page.get_by_text("ⓘ").hover()
    expect(page.get_by_role("tooltip")).to_have_text("Версия API: v3.2.1")
    page.get_by_role("button", name="Продукты").hover()
    page.get_by_role("link", name="API для разработчиков").click()
    assert_passed(page)


def test_file_upload(page: Page):
    page.goto("/play/file-upload")
    page.get_by_label("Аватар").set_input_files(
        files=[{"name": "me.png", "mimeType": "image/png", "buffer": b"fake png"}]
    )
    with page.expect_file_chooser() as fc_info:
        page.get_by_role("button", name="Прикрепить отчёт").click()
    fc_info.value.set_files(
        files=[{"name": "report.csv", "mimeType": "text/csv", "buffer": b"id,result\n1,passed\n"}]
    )
    assert_passed(page)


def test_dialogs(page: Page):
    page.goto("/play/dialogs")

    page.once("dialog", lambda dialog: dialog.accept())
    page.get_by_role("button", name="Удалить черновики").click()

    page.once("dialog", lambda dialog: dialog.dismiss())
    page.get_by_role("button", name="Удалить проект").click()

    page.once("dialog", lambda dialog: dialog.accept("Lab 2.0"))
    page.get_by_role("button", name="Переименовать").click()
    assert_passed(page)


def test_new_tab(page: Page):
    page.goto("/play/new-tab")
    with page.expect_popup() as popup_info:
        page.get_by_role("link", name="Открыть документацию").click()
    docs = popup_info.value
    code = docs.get_by_test_id("activation-code").inner_text()
    docs.close()

    page.get_by_label("Код активации").fill(code)
    page.get_by_role("button", name="Активировать").click()
    assert_passed(page)


def test_blur_validation(page: Page):
    page.goto("/play/blur-validation")
    email = page.get_by_label("Email")
    error = page.get_by_role("alert")
    save = page.get_by_role("button", name="Сохранить")

    email.fill("ivan@")
    email.blur()
    expect(error).to_have_text("Введите корректный email")
    expect(save).to_be_disabled()

    email.fill("ivan@aqa.lab")
    email.press("Tab")
    expect(error).to_be_hidden()
    expect(save).to_be_enabled()
    save.click()
    assert_passed(page)


def test_keyboard_listbox(page: Page):
    page.goto("/play/keyboard-listbox")
    combo = page.get_by_role("combobox", name="Основной язык")
    combo.focus()
    combo.press("ArrowDown")
    target = page.get_by_role("option", name="Python", selected=True)
    for _ in range(10):
        if target.count():
            break
        combo.press("ArrowDown")
    combo.press("Enter")
    expect(combo).to_have_text("Python")
    assert_passed(page)


def test_custom_slider(page: Page):
    page.goto("/play/custom-slider")
    slider = page.get_by_role("slider", name="Громкость")
    slider.press("Home")
    for _ in range(15):
        slider.press("ArrowRight")
    expect(slider).to_have_attribute("aria-valuenow", "75")
    page.get_by_role("button", name="Применить").click()
    assert_passed(page)


def test_contenteditable(page: Page):
    page.goto("/play/contenteditable")
    editor = page.get_by_role("textbox", name="Текст статьи")
    editor.fill("Playwright рулит")
    editor.press("Control+A")
    page.get_by_role("button", name="Жирный").click()
    expect(editor.locator("b, strong")).to_have_text("Playwright рулит")
    page.get_by_role("button", name="Опубликовать").click()
    assert_passed(page)


def test_infinite_scroll(page: Page):
    page.goto("/play/infinite-scroll")
    articles = page.get_by_role("article")
    card = articles.filter(has=page.get_by_role("heading", name="Статья №37", exact=True))
    sentinel = page.get_by_test_id("feed-sentinel")
    while card.count() == 0:
        loaded = articles.count()
        sentinel.scroll_into_view_if_needed()
        expect(articles).not_to_have_count(loaded)
    card.get_by_role("button", name="Читать").click()
    assert_passed(page)


def test_download(page: Page):
    page.goto("/play/download")
    with page.expect_download() as download_info:
        page.get_by_role("button", name="Скачать отчёт").click()
    download = download_info.value
    assert re.fullmatch(r"report-\d+\.csv", download.suggested_filename)

    text = Path(download.path()).read_text(encoding="utf-8")
    checksum = re.search(r"^checksum,(\w+)$", text, re.MULTILINE).group(1)
    page.get_by_label("Контрольная сумма").fill(checksum)
    page.get_by_role("button", name="Проверить").click()
    assert_passed(page)


def test_canvas_draw(page: Page):
    page.goto("/play/canvas-draw")
    box = page.get_by_test_id("signature").bounding_box()
    left, top, width, height = box["x"], box["y"], box["width"], box["height"]

    page.mouse.move(left + 20, top + height / 2)
    page.mouse.down()
    page.mouse.move(left + width / 2, top + 30, steps=15)
    page.mouse.move(left + width - 20, top + height - 30, steps=15)
    page.mouse.up()

    page.get_by_role("button", name="Подписать").click()
    assert_passed(page)
