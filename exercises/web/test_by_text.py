import re

from playwright.sync_api import Page, expect


def test_by_text(page: Page):
    page.goto("/play/by-text")

    # TODO: твой код здесь
    page.get_by_text('Пингвин', exact=True).click()
    expect(page.get_by_test_id("mission-status")).to_have_attribute("data-status", "success")
    