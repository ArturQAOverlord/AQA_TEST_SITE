import io
from pathlib import Path

import allure
from PIL import Image, ImageChops
from playwright.sync_api import Page, expect


def assert_passed(page: Page):
    expect(page.get_by_test_id("mission-status")).to_have_attribute("data-status", "success")


SNAPSHOTS = Path(__file__).parent / "__snapshots__"


def assert_matches_snapshot(image: bytes, name: str, max_diff_ratio: float = 0.001) -> None:
    """Сравнивает скриншот с эталоном; если эталона нет — сохраняет его."""
    baseline = SNAPSHOTS / name
    if not baseline.exists():
        SNAPSHOTS.mkdir(exist_ok=True)
        baseline.write_bytes(image)
        return
    expected = Image.open(baseline).convert("RGB")
    actual = Image.open(io.BytesIO(image)).convert("RGB")
    assert actual.size == expected.size, f"размер изменился: {expected.size} → {actual.size}"
    # Пиксель считается изменённым, если разница яркости больше 16 из 255 — так не мешает сглаживание
    diff = ImageChops.difference(expected, actual).convert("L").point(lambda v: 255 if v > 16 else 0)
    ratio = diff.histogram()[255] / (expected.width * expected.height)
    assert ratio <= max_diff_ratio, f"отличается {ratio:.2%} пикселей (допустимо {max_diff_ratio:.2%})"


def test_allure_steps(page: Page):
    with allure.step("Открыть страницу подписки"):
        page.goto("/play/allure-steps")
    with allure.step("Выбрать тариф Pro и указать email"):
        page.get_by_label("Pro").check()
        page.get_by_label("Email").fill("me@aqa.lab")
    with allure.step("Оформить подписку"):
        page.get_by_role("button", name="Оформить").click()
        expect(page.get_by_role("status")).to_have_text("Подписка Pro оформлена")
    allure.attach(page.screenshot(), name="Итог", attachment_type=allure.attachment_type.PNG)
    assert_passed(page)


def test_trace_debug(page: Page):
    # В trace: SALE10 истёк, действующий промокод — AUTUMN26
    page.goto("/play/trace-debug")
    page.get_by_placeholder("Промокод").fill("AUTUMN26")
    page.get_by_role("button", name="Применить").click()
    expect(page.get_by_test_id("total")).to_have_text("Итого: 8100 ₽")
    page.get_by_role("button", name="Оплатить").click()
    assert_passed(page)


def test_visual_regression(page: Page):
    page.goto("/play/visual-regression")
    page.get_by_role("button", name="Показать отчёт").click()
    chart = page.get_by_test_id("sales-chart")
    image = chart.screenshot(animations="disabled", mask=[page.get_by_test_id("updated-at")])
    assert_matches_snapshot(image, "visual-regression.png")
    assert_passed(page)
