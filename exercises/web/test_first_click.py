import re
from playwright.sync_api import Page, expect


def test_first_click(page: Page):
    page.goto("/play/first-click")

    # TODO: найди кнопку «Начать» по роли и нажми её
    page.get_by_role('button', name='Начать').click()
    expect(page.get_by_test_id("mission-status")).to_have_attribute("data-status", "success")