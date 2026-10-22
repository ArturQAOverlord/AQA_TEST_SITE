import re

from playwright.sync_api import Page, Route, expect


def assert_passed(page: Page):
    expect(page.get_by_test_id("mission-status")).to_have_attribute("data-status", "success")


def test_block_requests(page: Page):
    page.route("**/api/analytics/**", lambda route: route.abort())
    page.route("**/ads/**", lambda route: route.abort())
    page.goto("/play/block-requests")

    expect(page.get_by_text("Аналитика: заблокирована")).to_be_visible()
    expect(page.get_by_text("Реклама: заблокирована")).to_be_visible()
    assert_passed(page)


def test_mock_500(page: Page):
    page.route("**/api/users", lambda route: route.fulfill(status=500, body="Internal Server Error"))
    page.goto("/play/mock-500")
    page.get_by_role("button", name="Загрузить пользователей").click()
    expect(page.get_by_role("alert")).to_have_text("Сервер недоступен (500)")

    page.unroute("**/api/users")
    page.get_by_role("button", name="Повторить").click()
    expect(page.get_by_role("listitem")).to_have_count(3)
    assert_passed(page)


def test_mock_data(page: Page):
    products = [
        {"id": 1, "name": "Кружка Playwright", "price": 990},
        {"id": 2, "name": "Футболка pytest", "price": 1990},
    ]
    page.route("**/api/products", lambda route: route.fulfill(json=products))
    page.goto("/play/mock-data")

    cards = page.get_by_role("list", name="Товары").get_by_role("listitem")
    expect(cards).to_have_count(2)
    expect(cards.first).to_contain_text("Кружка Playwright")
    expect(page.get_by_text("Итого: 2980 ₽")).to_be_visible()
    assert_passed(page)


def test_mock_empty(page: Page):
    page.route("**/api/orders", lambda route: route.fulfill(json=[]))
    page.goto("/play/mock-empty")
    page.get_by_role("button", name="Мои заказы").click()

    expect(page.get_by_text("У вас пока нет заказов")).to_be_visible()
    expect(page.get_by_role("link", name="Перейти в каталог")).to_be_visible()
    expect(page.get_by_role("table")).to_have_count(0)
    assert_passed(page)


def test_modify_response(page: Page):
    def make_premium(route: Route):
        response = route.fetch()
        data = response.json()
        data["plan"] = "premium"
        route.fulfill(response=response, json=data)

    page.route("**/api/profile", make_premium)
    page.goto("/play/modify-response")

    expect(page.get_by_role("region", name="Premium-функции")).to_be_visible()
    expect(page.get_by_role("heading", name="Гость")).to_be_visible()
    assert_passed(page)


def test_slow_network(page: Page):
    held: list[Route] = []
    page.route("**/api/search*", lambda route: held.append(route))
    page.goto("/play/slow-network")

    page.get_by_placeholder("Инструмент").fill("py")
    page.get_by_role("button", name="Найти").click()
    expect(page.get_by_text("Ищем…")).to_be_visible()

    page.wait_for_timeout(1500)
    held[0].continue_()

    expect(page.get_by_text("Ищем…")).to_be_hidden()
    expect(page.get_by_role("list", name="Результаты")).to_contain_text("pytest")
    assert_passed(page)


def test_auth_header(page: Page):
    def add_token(route: Route):
        route.continue_(headers={**route.request.headers, "authorization": "Bearer lab-token"})

    page.route("**/api/secret", add_token)
    page.goto("/play/auth-header")
    page.get_by_role("button", name="Загрузить секрет").click()
    expect(page.get_by_text(re.compile(r"Секретный код: LAB-[0-9A-F]{6}"))).to_be_visible()
    assert_passed(page)


def test_count_requests(page: Page):
    events = []

    def on_request(request):
        if "/api/analytics/track" in request.url:
            events.append(request.post_data_json["event"])

    page.on("request", on_request)
    page.goto("/play/count-requests")
    for name in ("Нравится", "В избранное", "Поделиться"):
        page.get_by_role("button", name=name).click()

    expect(page.get_by_test_id("sent")).to_have_text("Отправлено событий: 3")
    page.wait_for_timeout(1000)  # даём шанс проявиться лишним запросам
    assert events == ["like", "favorite", "share"]
    assert_passed(page)


def test_modify_request(page: Page):
    def swap_query(route: Route):
        route.continue_(url=route.request.url.replace("q=selenium", "q=playwright"))

    page.route("**/api/search*", swap_query)
    page.goto("/play/modify-request")
    page.get_by_role("button", name="Найти").click()
    expect(page.get_by_role("list", name="Результаты").get_by_role("listitem")).to_have_text(["Playwright"])
    assert_passed(page)
