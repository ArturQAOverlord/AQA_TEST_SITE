"""Здесь пишутся твои решения.

Скопируй стартовый шаблон со страницы миссии, допиши код и запусти:
    pytest exercises --headed

Можно создавать сколько угодно файлов test_*.py в этой папке —
например, по одному на раздел (test_my_locators.py, test_my_network.py…).
Только не называй их так же, как файлы в tests/.
"""

import re

from playwright.sync_api import Page, expect


def test_first_click(page: Page):
    page.goto("/play/first-click")

    # TODO: найди кнопку «Начать» по роли и нажми её

    expect(page.get_by_test_id("mission-status")).to_have_attribute("data-status", "success")
