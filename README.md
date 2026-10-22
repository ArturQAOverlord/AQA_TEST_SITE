# AQA_TEST_SITE — Playwright Python Lab

Тренажёр для автотестировщиков: **110 миссий** на Playwright + pytest + Python — от первого локатора до
Page Object, HAR, WebSocket и параллельного запуска.

Каждая миссия — маленькая страница-«песочница» с заданием, подсказкой и эталонным решением. Ты пишешь
на неё автотест; когда тест доводит задание до конца, миссия засчитывается. Для многих миссий есть
проверка глубже — `verify.py` прогоняет твой тест на других версиях страницы и разбирает его код.

## Что внутри

| Раздел | Миссий | О чём |
|---|---|---|
| Locators Mastery | 22 | роли, текст, label, test-id, `filter`, `and_`/`or_`, цепочки, пагинация, Shadow DOM, iframe, CSS/XPath |
| Actions | 19 | клики, ввод, клавиатура, select, слайдер, contenteditable, drag-and-drop, файлы, canvas, диалоги, вкладки |
| Auto-waiting | 11 | actionability, таймауты, редиректы, `expect_response`/`expect_request`, перерисовка DOM, флейки |
| Strict Mode | 5 | несколько совпадений, `exact=True`, роли, `.all()`, `add_locator_handler` |
| Assertions | 11 | текст, количество, value, атрибуты, CSS, состояния, отрицания, доступность, ARIA-снимки, API |
| Network Interception | 9 | `route.abort/fulfill/fetch/continue_`, ошибки, заголовки, подсчёт запросов, медленная сеть |
| Browser Context | 8 | cookies, localStorage, `storage_state`, init-скрипты, viewport, тема, геолокация, `page.clock` |
| Advanced Web | 6 | WebSocket (наблюдение и мок), чат двух пользователей по SSE, виртуальный список, Service Worker, HAR |
| Multi-step flows | 6 | логин, e2e-покупка, условная форма, мастер, CRUD, `parametrize` |
| Test Architecture | 4 | маркеры, фикстуры, Page Object, независимые данные и `pytest -n` |
| Debugging & Reports | 3 | разбор trace, визуальная регрессия на Pillow, Allure |
| Bug Hunting & Refactoring | 6 | найди баг тестом (4), почини хрупкий тест (2) |

По сложности: Intro — 1, Easy — 31, Medium — 55, Hard — 23.

**Как учиться:**
- **Треки** — упорядоченные маршруты: «Новичок» (20 миссий), «Уверенный AQA» (29), «Подготовка к собеседованию» (21).
- **Теория** — короткая выжимка в начале каждого раздела каталога.
- **Шпаргалка** (`/cheatsheet`) — API Playwright и pytest по задачам со ссылками на миссии.

## Установка и запуск

Нужен Python 3.10+.

```bash
pip install -r requirements.txt
playwright install chromium
python app.py            # http://127.0.0.1:5000
```

### Через Docker

```bash
docker compose up --build        # http://localhost:5000
docker compose exec lab pytest exercises
```

Папки `exercises/` и `data/` (прогресс) примонтированы с хоста: решения пишешь в своей IDE, запускаешь в
контейнере. В контейнере нет экрана, так что `--headed` там не работает — для отладки запускай тесты локально.

## Как решать миссии

1. Открой миссию, прочитай задание, попробуй песочницу руками (она же доступна по `/play/<миссия>`).
2. Скопируй **стартовый шаблон** в файл в [exercises/](exercises/) — пример: [exercises/test_my_solutions.py](exercises/test_my_solutions.py).
   Имя функции оставь как в шаблоне (`test_<миссия>`) — по нему находится твой тест.
3. Запусти:

   ```bash
   pytest exercises --headed               # с видимым браузером
   pytest exercises -k first_click         # одна миссия
   pytest exercises -m smoke               # только тесты с маркером smoke
   pytest exercises -n 4                   # параллельно (pytest-xdist)
   ```

4. Последняя строка шаблона проверяет статус песочницы — когда тест прошёл, миссия зеленеет в каталоге.

Сайт не обязательно запускать отдельно: если на `127.0.0.1:5000` никто не отвечает, pytest поднимет
сервер сам (в том числе при `-n 4` — один на все воркеры, см. [conftest.py](conftest.py)).

### Проверка глубже: verify.py

На странице миссии есть кнопка **«Запустить проверку»** (то же самое в терминале: `python verify.py <миссия>`).
Что проверяется, зависит от типа миссии:

| Значок | Тип | Тест должен… |
|---|---|---|
| 🧬 | мутанты | **упасть** на каждой «сломанной» версии страницы (опечатка, неверный счётчик, пропавший `aria-label`…) |
| 🔍 | найди баг | **упасть** на текущей странице (там баг) и **пройти** на исправленной |
| 🛠 | почини тест | **пройти** на каждом «редизайне» страницы (другие классы, порядок, обёртки, скорость) |
| 📐 | структура | быть написан как в задании: Page Object без локаторов в тесте, фикстура со входом через API, маркер, шаги Allure, без `sleep` |

Миссии 🔍 и 🛠 засчитываются только этой проверкой. Результат виден на странице миссии и в каталоге.
Если твой тест уже есть в `exercises/`, на странице миссии можно **сравнить его с эталоном** бок о бок.

### Что считается провалом

- **Любая ошибка окончательна** — тест, который кликает всё подряд, миссию не пройдёт.
- **Только настоящие события** — `dispatch_event("click")` и `el.click()` из `evaluate` проваливают миссию.
- **Статус нельзя подделать** через `evaluate`.
- **Сценарий нельзя обойти**: прямой переход на страницу результата, `force=True` по движущейся кнопке, клик до готовности приложения.

### Отладка упавших тестов

В [pytest.ini](pytest.ini) включено `--screenshot only-on-failure --tracing retain-on-failure`: для каждого упавшего
теста в `test-results/` появляются скриншот и trace. Открыть trace: `playwright show-trace test-results/…/trace.zip`.
Ещё полезно: `--video retain-on-failure`, `PWDEBUG=1` (Inspector), `page.pause()`, `playwright codegen`.

Allure: `pytest exercises --alluredir=allure-results`, затем `allure serve allure-results`
(нужен [Allure CLI](https://allurereport.org/docs/install/)).

### Прогресс

- Засчитываются только прохождения **из автотеста** (страница проверяет `navigator.webdriver`).
- Прогресс — `progress.json`, результаты verify — `verified.json` (оба в `.gitignore`; в Docker — в `data/`).
  Сбросить можно кнопкой в каталоге.
- Эталонные решения из `tests/` прогресс не засчитывают.

## Эталонные решения и CI

```bash
pytest tests -n 4                    # все эталоны + самопроверка защиты песочниц
python verify.py --dir tests         # эталоны проходят все проверки verify.py
```

Эталонные тесты миссий 🔍 в обычном прогоне помечены как `xfail` — они и должны падать на странице с багом.

Оба шага запускаются в GitHub Actions на каждый push и PR ([.github/workflows/tests.yml](.github/workflows/tests.yml)).
Артефакты упавших тестов (скриншоты, trace, данные Allure) прикладываются к прогону.

## Структура проекта

```
app.py                     Flask: страницы, прогресс, учебные API (REST, SSE, WebSocket), режим вариантов страниц
missions.py                Каталог миссий, разделы, треки, мутанты
verify.py                  Проверка тестов вариантами страниц и разбором кода
templates/
  index.html, mission.html, track.html, cheatsheet.html
  theory/<раздел>.html     Теория разделов
  play.html                Базовый шаблон песочницы
  playgrounds/<slug>.html  Песочница: блоки brief (задание), hint (подсказка), content, script
static/play.js             window.Lab: статус миссии, защита от обходов, прогресс
static/sw-offline.js       Service Worker для миссии offline-sw
static/traces/             trace для миссии trace-debug (пересоздать: python tools/make_trace.py)
tests/test_*.py            Эталонные решения: функция test_<slug> на каждую миссию
tests/selfcheck/           Тесты защиты песочниц от обходных решений
exercises/                 Твои решения
```

## Как добавить свою миссию

1. Добавь `Mission(...)` в [missions.py](missions.py) (и, если нужно, в трек).
2. Создай `templates/playgrounds/<slug>.html` по образцу соседних: блоки `brief`, `hint`, `content`, `script`.
   Когда задание выполнено — `Lab.success()`, при ошибке — `Lab.fail("почему")`.
3. Напиши эталон `test_<slug_через_подчёркивания>` в одном из `tests/test_*.py` — он сам появится на странице миссии
   вместе с хелперами, которыми пользуется (классы, фикстуры, константы из того же файла).
4. Для проверки глубже: варианты страницы в `mutants=` и ветки `if (Lab.mutant === 'имя')` в песочнице
   (для миссий «найди баг» — один вариант `fixed`), статические проверки — в `STATIC_CHECKS` в [verify.py](verify.py).
   Проверь: `python verify.py <slug> --dir tests`.
