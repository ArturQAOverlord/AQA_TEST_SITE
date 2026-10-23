"""Трек Manual QA: целостность банка вопросов, проверка ответов, прохождение теста
и правдивость практикумов — каждый ответ и каждый заявленный баг реально есть на стенде."""

import html
import re

from playwright.sync_api import Page, expect

from app import QA_PASS_RATIO, create_app
from qa_course import QUIZZES, QUIZZES_BY_SLUG, TOPICS_BY_ID, normalize
from qa_theory import THEORY

LEVELS = ("Easy", "Medium", "Hard")


def plain(option_html: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", option_html))


def answers_of(slug: str) -> list[str | None]:
    """Эталонные ответы текстовых вопросов теста по порядку (для остальных — None)."""
    return [q.answer[0] if q.kind == "text" else None for q in QUIZZES_BY_SLUG[slug].questions]


# ---------- банк вопросов ----------

def test_qa_bank_is_consistent():
    ids = [q.id for quiz in QUIZZES for q in quiz.questions]
    assert len(ids) == len(set(ids)), "id вопросов должны быть уникальны"
    levels = [LEVELS.index(quiz.level) for quiz in QUIZZES]
    assert levels == sorted(levels), "трек должен идти от простых тестов к сложным"
    for quiz in QUIZZES:
        assert quiz.topic in TOPICS_BY_ID
        assert len(quiz.questions) >= 5, quiz.slug
        for q in quiz.questions:
            assert q.explanation.strip(), q.id
            if q.kind == "single":
                assert 0 <= q.answer < len(q.options) and len(q.options) >= 3, q.id
            elif q.kind == "multi":
                assert q.answer and all(0 <= i < len(q.options) for i in q.answer), q.id
                assert len(q.answer) < len(q.options), f"{q.id}: в multi должны быть и неверные варианты"
            else:
                assert q.kind == "text" and q.answer and not q.options, q.id
            assert len({plain(o) for o in q.options}) == len(q.options), f"{q.id}: повторяются варианты"


def test_qa_every_quiz_has_theory():
    assert set(THEORY) == set(QUIZZES_BY_SLUG), "у каждого теста должна быть теория, и только у них"
    client = create_app().test_client()
    for quiz in QUIZZES:
        assert "<h3>" in THEORY[quiz.slug], quiz.slug
        data = client.get(f"/api/qa/{quiz.slug}/theory").get_json()
        assert data == {"title": quiz.title, "html": THEORY[quiz.slug]}
        # до завершения теста теории на странице нет — она приходит запросом после финиша
        assert THEORY[quiz.slug][:200] not in client.get(f"/qa/{quiz.slug}").get_data(as_text=True)
    assert client.get("/api/qa/no-such-quiz/theory").status_code == 404


def test_qa_check_grades_every_question():
    client = create_app().test_client()
    for quiz in QUIZZES:
        for q in quiz.questions:
            if q.kind == "single":
                right, wrong = q.answer, (q.answer + 1) % len(q.options)
            elif q.kind == "multi":
                right = sorted(q.answer)
                wrong = sorted(set(range(len(q.options))) - set(q.answer))[:1] + right
            else:
                right, wrong = f"  {q.answer[0].upper()} ", "совсем не то"
            ok = client.post(f"/api/qa/{quiz.slug}/check", json={"qid": q.id, "answer": right}).get_json()
            bad = client.post(f"/api/qa/{quiz.slug}/check", json={"qid": q.id, "answer": wrong}).get_json()
            assert ok["correct"] and not bad["correct"], q.id
            assert ok["explanation"] and ok["answer"]


def test_qa_text_answers_are_normalized():
    assert normalize(" 4 500,00 ₽ ") == normalize("4500.00")
    assert normalize("«QA-7731»") == normalize("qa-7731")


def test_qa_result_is_validated():
    client = create_app().test_client()
    assert client.post("/api/qa/qa-basics/result", json={"score": 99}).status_code == 422
    assert client.post("/api/qa/qa-basics/result", json={"score": "8"}).status_code == 422
    assert client.post("/api/qa/no-such-quiz/result", json={"score": 1}).status_code == 404


def test_qa_pages_render():
    client = create_app().test_client()
    assert client.get("/qa").status_code == 200
    for quiz in QUIZZES:
        page = client.get(f"/qa/{quiz.slug}")
        assert page.status_code == 200, quiz.slug
        # правильные ответы не должны попадать на страницу
        body = page.get_data(as_text=True)
        assert "explanation" not in body and '"answer"' not in body, quiz.slug
    for lab in ("devtools", "registration", "shop"):
        assert client.get(f"/qa/lab/{lab}").status_code == 200


# ---------- прохождение теста в браузере ----------

def answer_quiz(page: Page, slug: str, wrong: set[str] = frozenset()):
    for q in QUIZZES_BY_SLUG[slug].questions:
        if q.kind == "text":
            page.get_by_label("Ответ").fill("неверный ответ" if q.id in wrong else q.answer[0])
        else:
            if q.id in wrong:
                ids = [next(i for i in range(len(q.options)) if i not in
                            ({q.answer} if q.kind == "single" else q.answer))]
            else:
                ids = [q.answer] if q.kind == "single" else sorted(q.answer)
            for i in ids:
                page.get_by_label(plain(q.options[i]), exact=True).check()
        page.get_by_role("button", name="Ответить").click()
        expect(page.locator(".quiz-verdict")).to_have_text("❌ Неверно" if q.id in wrong else "✅ Верно")
        page.locator(".quiz-feedback").get_by_role("button").click()


def test_qa_quiz_all_correct(page: Page):
    quiz = QUIZZES_BY_SLUG["qa-basics"]
    page.goto("/qa/qa-basics")
    answer_quiz(page, "qa-basics")
    expect(page.locator(".quiz-score")).to_have_text(f"Результат: {len(quiz.questions)} из {len(quiz.questions)}")
    expect(page.get_by_text("Тест сдан")).to_be_visible()
    expect(page.get_by_text("Ни одной ошибки!")).to_be_visible()
    expect(page.locator("#quiz")).not_to_contain_text("null")

    # после теста сразу открывается теория; её можно закрыть и открыть снова
    theory = page.get_by_role("dialog", name=f"📖 Теория: {quiz.title}")
    expect(theory).to_be_visible()
    expect(theory).to_contain_text("7 принципов тестирования")
    theory.get_by_role("button", name="Понятно").click()
    expect(theory).to_be_hidden()
    page.get_by_role("button", name="📖 Теория по теме").click()
    expect(theory).to_be_visible()
    theory.get_by_role("button", name="Закрыть").click()
    expect(theory).to_be_hidden()


def test_qa_quiz_shows_mistakes(page: Page):
    quiz = QUIZZES_BY_SLUG["http"]
    total = len(quiz.questions)
    # Ровно столько ошибок, чтобы не дотянуть до порога сдачи
    misses = next(n for n in range(1, total + 1) if total - n < QA_PASS_RATIO * total)
    wrong = {q.id for q in quiz.questions[::2][:misses]}
    page.goto("/qa/http")
    answer_quiz(page, "http", wrong)
    expect(page.locator(".quiz-score")).to_have_text(f"Результат: {total - misses} из {total}")
    expect(page.get_by_text("Не сдан")).to_be_visible()
    expect(page.locator(".quiz-mistakes > li")).to_have_count(misses)


# ---------- практикумы: ответы и баги действительно есть на стендах ----------

def test_qa_devtools_lab_matches_answers(page: Page):
    a = answers_of("devtools-practice")
    errors = []
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    page.goto("/qa/lab/devtools")

    assert any(a[6] in text for text in errors)
    assert next(c["value"] for c in page.context.cookies() if c["name"] == "qa_session") == a[4]
    assert page.evaluate("localStorage.getItem('qa_theme')") == a[5]

    with page.expect_request("**/api/qa-lab/profile") as profile:
        page.get_by_role("button", name="Загрузить профиль").click()
    assert profile.value.response().json()["secret_code"] == a[0]
    assert profile.value.headers["x-request-source"] == a[8]

    with page.expect_response("**/api/qa-lab/order") as order:
        page.get_by_role("button", name="Оформить заказ").click()
    assert str(order.value.status) == a[1]
    assert order.value.json()["field"] == a[2]
    assert order.value.request.method == a[3]

    catalog = []
    page.on("request", lambda r: catalog.append(r.url) if "/api/qa-lab/catalog/" in r.url else None)
    page.get_by_role("button", name="Загрузить каталог").click()
    expect(page.get_by_role("status")).to_contain_text("Каталог загружен")
    assert str(len(catalog)) == a[7]

    promo = page.get_by_test_id("promo")
    expect(promo).to_be_hidden()
    assert a[9] in promo.text_content()


def register(page: Page, password="Abcdefg1", confirm=None, email="ivan@mail.ru", patronymic=""):
    page.goto("/qa/lab/registration")
    page.get_by_label("Имя *").fill("Иван")
    page.get_by_label("Фамилия *").fill("Петров")
    page.get_by_label("Отчество").fill(patronymic)
    page.get_by_label("Email *").fill(email)
    page.get_by_label("Пароль *", exact=True).fill(password)
    page.get_by_label("Подтверждение пароля *").fill(password if confirm is None else confirm)
    page.get_by_label("Принимаю").check()
    page.get_by_role("button", name="Зарегестрироваться").click()


def test_qa_registration_lab_bugs_are_real(page: Page):
    welcome = page.get_by_role("status")

    register(page, password="Abcdef1")  # 7 символов
    expect(welcome).to_have_text("Добро пожаловать, ivan@mail.ru!")  # и баг с email в приветствии
    register(page, email="user@mail")
    expect(welcome).not_to_be_empty()
    register(page, confirm="Different1")
    expect(welcome).not_to_be_empty()
    expect(page.get_by_label("Пароль *", exact=True)).to_have_attribute("type", "text")
    href = page.get_by_role("link", name="Условия использования").get_attribute("href")
    assert page.request.get(href).status == 404


def test_qa_registration_lab_decoys_follow_spec(page: Page):
    errors = page.get_by_role("alert")
    register(page)  # без отчества
    expect(page.get_by_role("status")).to_have_text("Добро пожаловать, ivan@mail.ru!")
    register(page, password="Abc defg1")
    expect(errors).to_contain_text("пробелы")
    register(page, password="A" * 21)
    expect(errors).to_contain_text("от 8 до 20")
    page.goto("/qa/lab/registration")
    expect(page.get_by_label("Подписаться на рассылку")).not_to_be_checked()


def add(page: Page, name: str, times: int = 1):
    row = page.get_by_role("list", name="Товары").get_by_role("listitem").filter(has_text=name)
    for _ in range(times):
        row.get_by_role("button", name="В корзину").click()


def test_qa_shop_lab_bugs_are_real(page: Page):
    cart = page.get_by_role("list", name="Корзина").get_by_role("listitem")

    page.goto("/qa/lab/shop")
    add(page, "Клавиатура", 2)
    expect(page.get_by_test_id("total")).to_have_text("5000.00 ₽")  # скидка не применилась ровно на 5000
    assert normalize(answers_of("bug-hunt-shop")[1]) == normalize("4500")  # а по требованиям — 4500

    page.goto("/qa/lab/shop")
    add(page, "Мышь")
    page.get_by_role("button", name="Уменьшить: Мышь").click()
    expect(page.get_by_test_id("qty")).to_have_text("0")

    page.goto("/qa/lab/shop")
    add(page, "Наушники")
    expect(cart).to_have_count(1)

    page.goto("/qa/lab/shop")
    page.get_by_role("button", name="Сортировать по цене").click()
    expect(page.get_by_role("list", name="Товары").get_by_role("listitem").last).to_contain_text("Коврик")

    page.goto("/qa/lab/shop")
    add(page, "Клавиатура")
    add(page, "Мышь")
    page.get_by_role("button", name="Удалить: Мышь").click()
    expect(cart).to_have_count(1)
    expect(cart).to_contain_text("Мышь")  # удалилась клавиатура, а не мышь

    page.goto("/qa/lab/shop")
    add(page, "Коврик", 3)
    expect(page.get_by_test_id("line-total")).to_have_text("299.96999999999997 ₽")


def test_qa_shop_lab_decoys_follow_spec(page: Page):
    page.goto("/qa/lab/shop")
    add(page, "Мышь")
    expect(page.get_by_test_id("delivery")).to_have_text("300.00 ₽")
    add(page, "Мышь", 2)  # 3600 ₽
    expect(page.get_by_test_id("delivery")).to_have_text("0.00 ₽")
    add(page, "Мышь", 7)  # пытаемся до 10
    expect(page.get_by_test_id("qty")).to_have_text("10")
    expect(page.get_by_role("button", name="Увеличить: Мышь")).to_be_disabled()
