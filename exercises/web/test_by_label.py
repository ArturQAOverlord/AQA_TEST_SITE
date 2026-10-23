import re

from playwright.sync_api import Page, expect


def test_by_label(page: Page):
    page.goto("/play/by-label")

    # TODO: твой код здесь
    page.get_by_label('Имя').fill('Иван')
    page.get_by_label('Фамилия ').fill('Петров')
    page.get_by_label('Email').fill('ivan@test.ru')
    page.get_by_label('Согласен на обработку данных ').check()
   
    expect(page.get_by_test_id("mission-status")).to_have_attribute("data-status", "success")
