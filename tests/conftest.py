import os

import pytest

from missions import MISSIONS_BY_SLUG


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    # Эталонные решения не должны засчитывать миссии в прогресс
    return {**browser_context_args, "extra_http_headers": {"X-Lab-Reference": "1"}}


def pytest_collection_modifyitems(config, items):
    """Эталонные тесты миссий «найди баг» падают на странице с багом — так и задумано.

    В обычном прогоне они помечаются как xfail. Не strict: у параметризованных тестов
    на баг падают не все случаи (граница снизу работает правильно). Что тест
    действительно ловит баг, проверяет verify.py (LAB_VERIFY=1 снимает пометку).
    """
    if os.environ.get("LAB_VERIFY"):
        return
    for item in items:
        slug = getattr(item, "originalname", item.name).removeprefix("test_").replace("_", "-")
        mission = MISSIONS_BY_SLUG.get(slug)
        if mission and mission.kind == "bug":
            item.add_marker(pytest.mark.xfail(reason="тест находит баг в песочнице"))
