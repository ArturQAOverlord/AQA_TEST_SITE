"""Каталог миссий.

Текст задания, подсказка и сама «песочница» каждой миссии лежат в
templates/playgrounds/<slug>.html, эталонное решение — функция
test_<slug_с_подчёркиваниями> в одном из файлов tests/test_*.py.

mutants — варианты песочницы для verify.py. Что с ними делать, зависит от kind:
  normal — «сломанные» версии: в каждой есть баг, который должны поймать
           assertions из задания, тест обязан на них упасть. Миссия при этом
           всё равно доходит до статуса success, так что баг виден только проверкам;
  bug    — по умолчанию страница содержит баг, а мутант "fixed" — исправленная
           версия: тест должен упасть на текущей и пройти на исправленной;
  robust — «редизайны» страницы: тест обязан пройти на каждом.
static_check — verify.py дополнительно проверяет структуру кода теста (см. verify.py).
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Category:
    id: str
    title: str
    description: str


@dataclass(frozen=True)
class Mission:
    slug: str
    category: str
    title: str
    level: str
    minutes: int
    summary: str
    skills: tuple[str, ...] = ()
    # False — песочница засчитывает только действие, а главная часть
    # задания (assertions) проверяется самим тестом и verify.py
    autocheck: bool = True
    mutants: tuple[tuple[str, str], ...] = ()
    kind: str = "normal"
    static_check: bool = False

    @property
    def func_name(self) -> str:
        return "test_" + self.slug.replace("-", "_")

    @property
    def verifiable(self) -> bool:
        return bool(self.mutants) or self.static_check


@dataclass(frozen=True)
class Track:
    id: str
    title: str
    description: str
    slugs: tuple[str, ...] = field(default_factory=tuple)


FIXED = (("fixed", "Исправленная версия страницы: на ней тест должен пройти"),)


CATEGORIES = [
    Category("locators", "Locators Mastery",
             "Как находить элементы надёжно: роли, тексты, label, test-id, фильтры, цепочки, Shadow DOM, iframe."),
    Category("actions", "Actions",
             "Клики, ввод текста, клавиатура, select, слайдеры, drag-and-drop, файлы, рисование, диалоги, вкладки."),
    Category("waiting", "Auto-waiting",
             "Как Playwright ждёт элементы и когда нужно ждать явно: таймауты, URL, запросы и ответы, флейки."),
    Category("strict", "Strict Mode",
             "Что делать, когда локатор находит несколько элементов, и как сделать его однозначным."),
    Category("assertions", "Assertions",
             "Web-first проверки expect(): текст, количество, value, атрибуты, CSS, доступность, ARIA-снимки, API."),
    Category("network", "Network Interception",
             "page.route(): блокировка, моки, ошибки сервера, подмена запросов и ответов, заголовки, медленная сеть."),
    Category("context", "Browser Context",
             "Cookies, localStorage, storage_state, init-скрипты, viewport, тема, геолокация и управление временем."),
    Category("advanced", "Advanced Web",
             "WebSocket, SSE и несколько пользователей, виртуальные списки, Service Worker и офлайн, запись HAR."),
    Category("flows", "Multi-step flows",
             "Сценарии из нескольких шагов и приёмы pytest, где всё изученное нужно собрать вместе."),
    Category("architecture", "Test Architecture",
             "Page Object, фикстуры, маркеры, независимые данные и параллельный запуск."),
    Category("debug", "Debugging & Reports",
             "Trace Viewer, визуальная регрессия, отчёты Allure."),
    Category("quality", "Bug Hunting & Refactoring",
             "Найди баг тестом — и почини чужие хрупкие тесты так, чтобы они пережили редизайн."),
]

INTRO, EASY, MEDIUM, HARD = "Intro", "Easy", "Medium", "Hard"

MISSIONS = [
    # ---------- Locators ----------
    Mission("first-click", "locators", "Первый клик", INTRO, 2,
            "Найди кнопку по роли и нажми её.", ("get_by_role", "click")),
    Mission("by-text", "locators", "Найди по тексту", EASY, 3,
            "Кликни по карточке с точным текстом, не попав в похожую.", ("get_by_text", "exact=True")),
    Mission("by-label", "locators", "Поля по label", EASY, 4,
            "Заполни форму, находя поля по подписям.", ("get_by_label", "fill", "check")),
    Mission("by-placeholder", "locators", "Поиск через placeholder", EASY, 3,
            "Поля без label — ищем по placeholder.", ("get_by_placeholder", "press")),
    Mission("test-id", "locators", "data-testid — золотой стандарт", EASY, 3,
            "Три одинаковые кнопки, различаются только data-testid.", ("get_by_test_id",)),
    Mission("alt-title", "locators", "alt и title", EASY, 3,
            "Картинки по alt, иконки по title.", ("get_by_alt_text", "get_by_title")),
    Mission("accordion", "locators", "Аккордеон и aria-expanded", EASY, 4,
            "Раскрой нужный вопрос FAQ, не перепутав его со ссылкой.", ("get_by_role", "aria-expanded")),
    Mission("filter-has-text", "locators", "Найди товар со скидкой", MEDIUM, 5,
            "Отфильтруй карточки по тексту и нажми кнопку внутри нужной.", ("filter(has_text=)",)),
    Mission("filter-has", "locators", "Filter по вложенному элементу", MEDIUM, 5,
            "Карточку выдаёт только иконка без текста.", ("filter(has=)", "filter(has_not=)")),
    Mission("nth-first-last", "locators", "Позиционные локаторы", MEDIUM, 4,
            "Первый, третий и последний — без хардкода селекторов.", ("first", "nth", "last")),
    Mission("chaining", "locators", "Цепочка локаторов", MEDIUM, 5,
            "Одинаковые письма в двух папках — открой нужное.", ("get_by_role('region')", "chaining")),
    Mission("and-or", "locators", "and_ и or_", MEDIUM, 5,
            "Пересечение и объединение локаторов, A/B-тест кнопки.", ("and_", "or_")),
    Mission("cheapest-product", "locators", "Самый дешёвый товар", MEDIUM, 6,
            "Прочитай цены всех карточек и купи минимальную.", ("all()", "inner_text", "Python-логика")),
    Mission("bad-markup", "locators", "Форма без label", MEDIUM, 6,
            "Подписи не связаны с полями — ищем поле рядом с текстом.", ("filter", "xpath following-sibling")),
    Mission("shadow-dom", "locators", "Shadow DOM", MEDIUM, 4,
            "Поле и кнопка спрятаны внутри custom element.", ("shadow DOM", "get_by_label")),
    Mission("nested-shadow", "locators", "Вложенный Shadow DOM", MEDIUM, 5,
            "Три уровня веб-компонентов друг в друге.", ("shadow DOM", "get_by_role('switch')")),
    Mission("dynamic-ids", "locators", "Динамические id", MEDIUM, 4,
            "id и классы меняются при каждой загрузке.", ("стабильные локаторы",)),
    Mission("iframe", "locators", "Форма внутри iframe", MEDIUM, 5,
            "Элементы в iframe не видны обычному локатору.", ("frame_locator", "content_frame")),
    Mission("pagination", "locators", "Пагинация", MEDIUM, 6,
            "Нужный сотрудник где-то на одной из страниц таблицы.", ("count()", "циклы")),
    Mission("table", "locators", "Таблица с одинаковыми строками", HARD, 7,
            "Два сотрудника с одинаковым именем — выбери правильного.", ("get_by_role('row')", "get_by_role('cell')")),
    Mission("css-xpath", "locators", "Легаси-вёрстка: CSS и XPath", HARD, 7,
            "Ни ролей, ни label, ни test-id. Только CSS и XPath.", ("locator('css=')", "locator('xpath=')")),
    Mission("nested-iframes", "locators", "iframe внутри iframe", HARD, 7,
            "Платёжный виджет: поле карты во вложенном фрейме.", ("frame_locator().frame_locator()",)),

    # ---------- Actions ----------
    Mission("click-variants", "actions", "Двойной и правый клик", EASY, 4,
            "dblclick и контекстное меню.", ("dblclick", "click(button='right')")),
    Mission("login-form", "actions", "Заполни форму входа", EASY, 3,
            "Логин, пароль, чекбокс, отправка.", ("fill", "check", "click")),
    Mission("select-option", "actions", "Dropdown — select_option", EASY, 4,
            "Обычный и множественный select.", ("select_option",)),
    Mission("checkbox-radio", "actions", "Чекбоксы и радиокнопки", EASY, 4,
            "check / uncheck / set_checked.", ("check", "uncheck", "set_checked")),
    Mission("blur-validation", "actions", "Валидация по blur", EASY, 4,
            "Ошибка появляется, только когда поле теряет фокус.", ("blur", "press('Tab')")),
    Mission("press-sequentially", "actions", "Посимвольный ввод", MEDIUM, 5,
            "Автокомплит реагирует только на нажатия клавиш — fill() не поможет.", ("press_sequentially",)),
    Mission("keyboard", "actions", "Клавиатура: Enter, Escape, хоткеи", MEDIUM, 5,
            "Отправь сообщение Enter'ом, закрой модалку Escape'ом, открой палитру Ctrl+K.", ("press", "keyboard")),
    Mission("keyboard-listbox", "actions", "Список только с клавиатуры", MEDIUM, 6,
            "Кастомный combobox игнорирует мышь — выбирай стрелками.", ("focus", "press('ArrowDown')", "aria-activedescendant")),
    Mission("drag-and-drop", "actions", "Drag-and-Drop карточки", MEDIUM, 5,
            "Перетащи задачу в колонку Done.", ("drag_to",)),
    Mission("hover-menu", "actions", "Hover → меню → click", MEDIUM, 4,
            "Пункт меню появляется только при наведении.", ("hover",)),
    Mission("custom-slider", "actions", "Кастомный слайдер", MEDIUM, 5,
            "role=slider без input — двигай клавиатурой.", ("aria-valuenow", "press")),
    Mission("contenteditable", "actions", "Редактор contenteditable", MEDIUM, 5,
            "Напечатай текст, выдели всё и сделай жирным.", ("fill", "Control+A")),
    Mission("infinite-scroll", "actions", "Бесконечная лента", MEDIUM, 6,
            "Нужная статья появится только после прокрутки.", ("mouse.wheel", "scroll_into_view_if_needed")),
    Mission("file-upload", "actions", "Загрузка файла", MEDIUM, 5,
            "Скрытый input[type=file] и кнопка с file chooser.", ("set_input_files", "expect_file_chooser")),
    Mission("download", "actions", "Скачивание файла", MEDIUM, 6,
            "Скачай отчёт и прочитай из него контрольную сумму.", ("expect_download", "download.path()")),
    Mission("dialogs", "actions", "alert, confirm, prompt", MEDIUM, 5,
            "Нативные диалоги браузера надо обработать заранее.", ("page.on('dialog')", "dialog.accept")),
    Mission("new-tab", "actions", "Новая вкладка", MEDIUM, 5,
            "Ссылка открывается в новой вкладке — забери оттуда код.", ("expect_popup",)),
    Mission("date-picker", "actions", "Кастомный date picker", HARD, 7,
            "Пролистай календарь до нужного месяца и выбери дату.", ("loops", "to_have_text")),
    Mission("canvas-draw", "actions", "Подпись на canvas", HARD, 7,
            "Нарисуй подпись мышью: page.mouse.down/move/up.", ("page.mouse", "bounding_box")),

    # ---------- Auto-waiting ----------
    Mission("wait-appear", "waiting", "Подожди появления", EASY, 3,
            "Карточка появляется через пару секунд.", ("auto-waiting",)),
    Mission("custom-timeout", "waiting", "Custom timeout в expect", EASY, 4,
            "Отчёт готовится дольше 5 секунд стандартного таймаута.", ("expect(timeout=)",)),
    Mission("wait-url", "waiting", "Дождись редиректа", EASY, 4,
            "После оплаты страница сама переходит на другой URL.", ("to_have_url", "wait_for_url"),
            mutants=(("no-order", "Редирект на страницу успеха без номера заказа в URL"),
                     ("wrong-heading", "На странице успеха заголовок «Оплата обрабатывается»"))),
    Mission("actionability", "waiting", "click() сам ждёт actionability", MEDIUM, 4,
            "Кнопка disabled, потом закрыта оверлеем, потом едет.", ("actionability",)),
    Mission("wait-response", "waiting", "Дождись API-ответа", MEDIUM, 6,
            "Значение есть только в ответе сервера — достань его.", ("expect_response",)),
    Mission("wait-request", "waiting", "Проверь отправленный запрос", MEDIUM, 6,
            "UI говорит «Спасибо», а что ушло на сервер?", ("expect_request", "post_data_json"), False,
            mutants=(("rating-string", "Оценка уходит строкой \"5\" вместо числа"),
                     ("no-source", "Из запроса пропало поле source"),
                     ("wrong-method", "Отзыв отправляется методом PUT"))),
    Mission("toast", "waiting", "Всплывающее уведомление", MEDIUM, 5,
            "Тост появляется на пару секунд — проверь и появление, и исчезновение.", ("to_be_visible", "to_be_hidden"), False,
            mutants=(("toast-stays", "Уведомление не исчезает"),
                     ("toast-text", "В тексте уведомления опечатка: «Изменения сохраненны»"))),
    Mission("stale-elements", "waiting", "Перерисовка списка", MEDIUM, 6,
            "Список перерисовывается каждые 0,7 с — купи, когда цена упадёт.", ("locator vs element_handle", "regex")),
    Mission("flaky-fix", "waiting", "Почини флейкающий тест", MEDIUM, 6,
            "Список подгружается по одному элементу — без sleep.", ("to_have_count", "all()")),
    Mission("networkidle", "waiting", "wait_for_load_state", MEDIUM, 5,
            "Дашборд догружает виджеты после load.", ("wait_for_load_state", "networkidle")),
    Mission("wait-for-function", "waiting", "wait_for_function", HARD, 6,
            "Готовность приложения видна только в JS-переменной.", ("wait_for_function",)),

    # ---------- Strict mode ----------
    Mission("strict-three-buttons", "strict", "Три одинаковые кнопки", EASY, 4,
            "Почему падает strict mode и как его успокоить.", ("strict mode", "filter")),
    Mission("exact-match", "strict", "exact=True — точное совпадение", EASY, 3,
            "«Сохранить», «Сохранить как…», «Сохранить черновик».", ("exact=True",)),
    Mission("role-disambiguation", "strict", "Один текст — разные роли", EASY, 3,
            "Ссылка, кнопка и заголовок с одинаковым текстом.", ("get_by_role",)),
    Mission("all-elements", "strict", "Действия над несколькими элементами", MEDIUM, 4,
            "Отметь все чекбоксы списка.", ("all()", "count()")),
    Mission("random-popup", "strict", "Случайный попап", HARD, 7,
            "Баннер может выскочить в любой момент. А может и нет.", ("add_locator_handler", "or_")),

    # ---------- Assertions ----------
    Mission("text-assertions", "assertions", "Точный текст vs содержит", EASY, 4,
            "Номер заказа случайный — проверь текст регуляркой.", ("to_have_text", "to_contain_text"), False,
            mutants=(("short-number", "Номер заказа стал 4-значным"),
                     ("typo", "В сообщении опечатка: «успешно оформлн»"),
                     ("list-order", "Пункты «Что дальше» поменялись местами"))),
    Mission("count-assertions", "assertions", "Проверь количество", EASY, 4,
            "Корзина и бейдж со счётчиком.", ("to_have_count",), False,
            mutants=(("badge-stale", "Бейдж не обновляется после удаления"),
                     ("remove-noop", "Кнопка «Убрать» не удаляет позицию"),
                     ("double-add", "Первый добавленный товар попадает в корзину дважды"))),
    Mission("value-assertions", "assertions", "Проверь value input'а", EASY, 4,
            "Индекс подставляется сам, телефон форматируется маской.", ("to_have_value",), False,
            mutants=(("wrong-zip", "Для Казани подставляется индекс 420000"),
                     ("no-mask", "Маска телефона не применяется"),
                     ("comment-prefilled", "Комментарий заполнен пробелом"))),
    Mission("state-assertions", "assertions", "Enabled / Disabled / Checked", EASY, 4,
            "Кнопка активна только после согласия.", ("to_be_disabled", "to_be_enabled", "to_be_checked"), False,
            mutants=(("always-enabled", "Кнопка регистрации активна сразу"),
                     ("login-editable", "Поле «Логин» можно редактировать"),
                     ("terms-prechecked", "Чекбокс согласия отмечен заранее"))),
    Mission("page-assertions", "assertions", "URL и title страницы", EASY, 3,
            "Вкладки меняют адрес и заголовок.", ("to_have_url", "to_have_title"), False,
            mutants=(("title-stale", "Заголовок окна не меняется при переключении вкладки"),
                     ("url-stale", "URL не меняется при переключении вкладки"),
                     ("wrong-initial-title", "Начальный заголовок «Профиль | Личный кабинет»"))),
    Mission("css-assertions", "assertions", "Проверь CSS", EASY, 4,
            "Цвет опасной кнопки и тёмная тема.", ("to_have_css",), False,
            mutants=(("danger-color", "Кнопка «Удалить аккаунт» стала оранжевой"),
                     ("theme-not-applied", "Тёмная тема не меняет фон панели"))),
    Mission("attribute-assertions", "assertions", "Атрибуты и классы", MEDIUM, 4,
            "Переключатель меняет aria-checked и класс.", ("to_have_attribute", "to_have_class"), False,
            mutants=(("aria-stuck", "aria-checked не меняется при переключении"),
                     ("no-class", "Класс is-on не добавляется"),
                     ("link-same-tab", "У ссылки пропал target=\"_blank\""))),
    Mission("negative-assertions", "assertions", "Отрицательные assertions", MEDIUM, 4,
            "Ошибка должна исчезнуть.", ("not_to_be_visible", "to_be_hidden"), False,
            mutants=(("error-stays", "Ошибка не исчезает после исправления"),
                     ("button-stays", "Кнопка «Подписаться» не пропадает"),
                     ("error-on-load", "Ошибка видна сразу при загрузке"))),
    Mission("a11y-assertions", "assertions", "Доступность: имена и описания", MEDIUM, 5,
            "Иконки-кнопки, подсказки к полям и диалоги.", ("to_have_accessible_name", "to_have_accessible_description", "to_have_role"), False,
            mutants=(("close-no-label", "У кнопки ✕ пропал aria-label"),
                     ("no-description", "Подсказка к паролю больше не связана с полем"),
                     ("dialog-no-name", "У диалога нет доступного имени"))),
    Mission("api-assertions", "assertions", "API-тест + проверка в UI", MEDIUM, 7,
            "Создай задачу через page.request и найди её на странице.", ("page.request", "APIResponse"), False,
            mutants=(("status-200", "POST /api/todos отвечает 200 вместо 201"),
                     ("done-true", "Новая задача создаётся уже выполненной"),
                     ("users-2", "GET /api/users возвращает двух пользователей вместо трёх"))),
    Mission("aria-snapshot", "assertions", "ARIA-снимок меню", HARD, 6,
            "Проверь структуру навигации одним to_match_aria_snapshot.", ("to_match_aria_snapshot",), False,
            mutants=(("missing-item", "После входа в меню нет пункта «Профиль»"),
                     ("renamed", "Пункт «Выйти» переименован в «Выход»"))),

    # ---------- Network ----------
    Mission("mock-empty", "network", "Пустой ответ", EASY, 4,
            "Пустой массив — пустое состояние.", ("route.fulfill",),
            mutants=(("no-link", "В пустом состоянии нет ссылки «Перейти в каталог»"),
                     ("empty-table", "Рядом с пустым состоянием рисуется пустая таблица"))),
    Mission("block-requests", "network", "Заблокируй аналитику и рекламу", MEDIUM, 5,
            "route.abort() до загрузки страницы.", ("page.route", "route.abort")),
    Mission("mock-500", "network", "Симулируй 500 ошибку", MEDIUM, 5,
            "Проверь, как UI переживает падение сервера.", ("route.fulfill(status=500)",),
            mutants=(("no-code", "Сообщение об ошибке без кода: «Сервер недоступен»"),
                     ("retry-broken", "После «Повторить» показываются только 2 пользователя"))),
    Mission("mock-data", "network", "Замокай API", MEDIUM, 5,
            "Подсунь странице свои товары.", ("route.fulfill(json=)",),
            mutants=(("wrong-total", "«Итого» считается без последнего товара"),
                     ("extra-card", "К товарам добавляется рекламная карточка"))),
    Mission("auth-header", "network", "Добавь заголовок авторизации", MEDIUM, 5,
            "API отвечает 401 без Authorization.", ("route.continue_(headers=)", "set_extra_http_headers")),
    Mission("count-requests", "network", "Посчитай запросы", MEDIUM, 6,
            "Каждая кнопка шлёт событие аналитики — ровно по одному.", ("page.on('request')",), False,
            mutants=(("double-like", "«Нравится» отправляет событие дважды"),
                     ("wrong-event", "«Поделиться» отправляет событие shared вместо share"))),
    Mission("modify-response", "network", "Подмени поле в настоящем ответе", HARD, 7,
            "Возьми реальный ответ и поменяй в нём одно поле.", ("route.fetch", "fulfill(response=)")),
    Mission("modify-request", "network", "Подмени запрос", HARD, 6,
            "Поле поиска заблокировано, а искать нужно другое.", ("route.continue_(url=)",)),
    Mission("slow-network", "network", "Медленная сеть", HARD, 7,
            "Задержи ответ и проверь лоадер.", ("route.continue_",)),

    # ---------- Browser context ----------
    Mission("cookies", "context", "Cookies и фича-флаг", EASY, 4,
            "Бета-функции включаются cookie.", ("context.add_cookies",)),
    Mission("local-storage", "context", "localStorage", EASY, 4,
            "Пропусти онбординг, записав флаг в localStorage.", ("evaluate", "reload")),
    Mission("mobile-viewport", "context", "Мобильная вёрстка", EASY, 4,
            "На узком экране меню прячется в бургер.", ("set_viewport_size", "devices")),
    Mission("color-scheme", "context", "Тёмная тема", EASY, 3,
            "Кнопка видна только при prefers-color-scheme: dark.", ("emulate_media",)),
    Mission("init-script", "context", "add_init_script", MEDIUM, 5,
            "Фича-флаг читается до того, как ты успеешь что-то сделать.", ("add_init_script",)),
    Mission("geolocation", "context", "Геолокация и разрешения", MEDIUM, 5,
            "Притворись, что ты в Казани.", ("grant_permissions", "set_geolocation")),
    Mission("storage-state", "context", "storage_state: вход один раз", HARD, 8,
            "Сохрани сессию и открой кабинет в новом контексте без логина.", ("storage_state", "browser.new_context")),
    Mission("clock", "context", "Управление временем", HARD, 7,
            "Дождись Нового года за секунду.", ("page.clock",)),

    # ---------- Flows ----------
    Mission("login-flow", "flows", "Логин с валидацией", MEDIUM, 8,
            "Проверь ошибки, войди, выйди.", ("fill", "to_have_text"),
            mutants=(("password-kept", "Пароль не очищается после выхода"),
                     ("wrong-greeting", "Приветствие «Добро пожаловать, Admin!»"))),
    Mission("conditional-form", "flows", "Условная форма", MEDIUM, 7,
            "Поля появляются в зависимости от выбора.", ("select_option", "check"),
            mutants=(("inn-error-text", "Ошибка ИНН звучит как «Неверный ИНН»"),
                     ("no-confirmation", "После отправки нет сообщения «Заявка принята»"))),
    Mission("wizard", "flows", "Пошаговый мастер", MEDIUM, 8,
            "Три шага, кнопка «Назад» и сохранение данных.", ("to_have_value",),
            mutants=(("summary-wrong-plan", "В сводке на шаге 3 указан тариф Basic"),
                     ("title-wrong-step", "На третьем шаге заголовок «Шаг 2 из 3»"))),
    Mission("parametrize", "flows", "Параметризация: правила пароля", MEDIUM, 8,
            "Шесть случаев — один тест с @pytest.mark.parametrize.", ("pytest.mark.parametrize",),
            mutants=(("digit-message", "Ошибка про цифру звучит как «Добавьте число»"),)),
    Mission("e2e-purchase", "flows", "Полный e2e: купи телефон", HARD, 10,
            "Каталог → корзина → оформление → подтверждение.", ("e2e",),
            mutants=(("wrong-total", "«Итого» в корзине не учитывает количество"),
                     ("summary-qty", "В сводке заказа количество 1"))),
    Mission("crud-table", "flows", "CRUD в таблице", HARD, 10,
            "Добавь, измени и удали записи, затем проверь итог.", ("modal", "dialog", "to_have_text"),
            mutants=(("edit-not-shown", "Изменённый телефон не обновляется в таблице"),)),

    # ---------- Advanced web ----------
    Mission("websocket-frames", "advanced", "Цена из WebSocket-фрейма", MEDIUM, 6,
            "Котировки приходят по WebSocket, на экране цифр нет.", ("page.on('websocket')", "framereceived")),
    Mission("virtual-list", "advanced", "Виртуализированный список", HARD, 7,
            "10 000 строк, в DOM — только видимые два десятка.", ("evaluate scrollTop", "mouse.wheel")),
    Mission("websocket-mock", "advanced", "Мок WebSocket-сервера", HARD, 8,
            "Сервер не знает тикер — притворись сервером сам.", ("route_web_socket",)),
    Mission("multi-user-chat", "advanced", "Чат двух пользователей", HARD, 8,
            "Два контекста браузера в одном тесте, сообщения по SSE.", ("browser.new_context", "Server-Sent Events")),
    Mission("offline-sw", "advanced", "Офлайн и Service Worker", HARD, 8,
            "Выключи сеть и проверь, что страница работает из кэша.", ("set_offline", "service worker")),
    Mission("har-replay", "advanced", "Запись и воспроизведение HAR", HARD, 8,
            "Запиши ответы API в HAR и прогони тест без сервера.", ("route_from_har",)),

    # ---------- Test architecture ----------
    Mission("markers", "architecture", "Маркеры и подмножества тестов", EASY, 5,
            "Пометь smoke-тест и запусти только его.", ("pytest.mark", "-m"), static_check=True),
    Mission("fixtures", "architecture", "Своя фикстура: вход через API", MEDIUM, 7,
            "Логин в фикстуре через page.request, а не через форму.", ("pytest.fixture", "page.request"), static_check=True),
    Mission("page-object", "architecture", "Page Object", MEDIUM, 12,
            "Две страницы админки — два класса, тест без локаторов.", ("Page Object",), static_check=True),
    Mission("isolation", "architecture", "Независимые данные и xdist", HARD, 8,
            "Общая доска, по которой ходят «коллеги». Тест должен быть независимым.", ("uuid", "pytest -n")),

    # ---------- Debugging & reports ----------
    Mission("allure-steps", "debug", "Шаги и вложения Allure", EASY, 6,
            "Разбей тест на шаги и приложи скриншот к отчёту.", ("allure.step", "allure.attach"), static_check=True),
    Mission("trace-debug", "debug", "Почини тест по trace", MEDIUM, 8,
            "Тест упал в CI, есть только trace.zip. Разберись, что случилось.", ("show-trace", "--tracing")),
    Mission("visual-regression", "debug", "Визуальная регрессия", HARD, 10,
            "Сравни скриншот графика с эталоном, замаскировав дату.", ("locator.screenshot", "mask", "Pillow"), False,
            mutants=(("bar-color", "Один столбец графика другого цвета"),
                     ("bar-height", "Один столбец на 6 px ниже"),
                     ("title-size", "Заголовок графика на 2 px крупнее"))),

    # ---------- Bug hunting & refactoring ----------
    Mission("bug-cart-total", "quality", "Найди баг: скидка в корзине", EASY, 5,
            "Проверь правило скидки по спецификации.", ("спецификация",), False, FIXED, kind="bug"),
    Mission("bug-boundary", "quality", "Найди баг: граничные значения", MEDIUM, 7,
            "Длина пароля 8–20 символов. Все ли границы работают?", ("parametrize", "граничные значения"), False, FIXED, kind="bug"),
    Mission("bug-sorting", "quality", "Найди баг: сортировка", MEDIUM, 6,
            "Таблица сортируется по цене. Точно ли правильно?", ("all_inner_texts", "sorted"), False, FIXED, kind="bug"),
    Mission("bug-pagination", "quality", "Найди баг: пагинация", HARD, 8,
            "23 товара по 5 на странице. Все ли на месте?", ("циклы", "set"), False, FIXED, kind="bug"),
    Mission("fix-brittle-locators", "quality", "Почини хрупкие локаторы", MEDIUM, 7,
            "Тест на nth-child и id ломается от любого редизайна.", ("get_by_label", "get_by_role"), True,
            (("classes-renamed", "Редизайн: новые классы и id у всех элементов"),
             ("reordered", "Редизайн: поля переставлены, добавлено поле «Телефон»"),
             ("wrapped", "Редизайн: каждое поле обёрнуто в дополнительные div")),
            kind="robust", static_check=True),
    Mission("fix-sleeps", "quality", "Почини тест на sleep", MEDIUM, 6,
            "time.sleep и is_visible() — флейк в чистом виде.", ("expect(timeout=)",), True,
            (("slow", "Генерация занимает 4 секунды"),
             ("very-slow", "Генерация занимает 8 секунд"),
             ("fast", "Генерация занимает 0,2 секунды")),
            kind="robust", static_check=True),
]

MISSIONS_BY_SLUG = {m.slug: m for m in MISSIONS}

TRACKS = [
    Track("beginner", "Новичок",
          "Базовые локаторы, действия и проверки. Начни отсюда, если Playwright видишь впервые.",
          ("first-click", "by-text", "by-label", "by-placeholder", "test-id", "alt-title", "login-form",
           "select-option", "checkbox-radio", "wait-appear", "exact-match", "strict-three-buttons",
           "text-assertions", "count-assertions", "value-assertions", "state-assertions", "mock-empty",
           "cookies", "markers", "bug-cart-total")),
    Track("confident", "Уверенный AQA",
          "Фильтры и цепочки, сложные элементы, ожидания, моки и архитектура тестов.",
          ("filter-has-text", "filter-has", "chaining", "table", "iframe", "shadow-dom", "press-sequentially",
           "keyboard", "file-upload", "download", "dialogs", "new-tab", "custom-timeout", "wait-url",
           "wait-response", "flaky-fix", "all-elements", "negative-assertions", "attribute-assertions",
           "mock-500", "mock-data", "block-requests", "local-storage", "login-flow", "e2e-purchase",
           "fixtures", "page-object", "fix-brittle-locators", "allure-steps")),
    Track("interview", "Подготовка к собеседованию",
          "Темы, о которых спрашивают на собеседованиях AQA: от actionability до HAR и параллельного запуска.",
          ("css-xpath", "actionability", "random-popup", "wait-for-function", "stale-elements",
           "modify-response", "slow-network", "storage-state", "api-assertions", "parametrize",
           "page-object", "fixtures", "isolation", "trace-debug", "bug-boundary", "bug-sorting",
           "fix-sleeps", "visual-regression", "websocket-mock", "har-replay", "multi-user-chat")),
]

TRACKS_BY_ID = {t.id: t for t in TRACKS}
