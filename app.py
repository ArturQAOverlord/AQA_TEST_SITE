"""AQA Lab — тренажёр локаторов и Playwright.

Запуск: python app.py  ->  http://127.0.0.1:5000

Переменная окружения LAB_MUTANT="<slug>:<мутант>" включает другую версию
одной песочницы — так verify.py проверяет тесты (см. missions.py).
"""

import ast
import hashlib
import hmac
import itertools
import json
import os
import random
import secrets
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path

from flask import Flask, Response, abort, jsonify, make_response, render_template, request, send_from_directory
from flask_sock import Sock
from jinja2 import TemplateNotFound
from markupsafe import Markup

from missions import CATEGORIES, MISSIONS, MISSIONS_BY_SLUG, TRACKS, TRACKS_BY_ID

BASE_DIR = Path(__file__).resolve().parent
# В Docker прогресс хранится в примонтированной папке (LAB_DATA_DIR), локально — рядом с app.py
DATA_DIR = Path(os.environ.get("LAB_DATA_DIR", BASE_DIR))
PROGRESS_FILE = DATA_DIR / "progress.json"
VERIFIED_FILE = DATA_DIR / "verified.json"
SOLUTIONS_DIR = BASE_DIR / "tests"
EXERCISES_DIR = BASE_DIR / "exercises"
# Сюда сохраняет код редактор на странице миссии: exercises/web/test_<миссия>.py
WEB_SOLUTIONS_DIR = EXERCISES_DIR / "web"
RUN_TIMEOUT = 180
MAX_CODE_SIZE = 100_000
# Запуск кода из редактора — это выполнение произвольного Python на сервере.
# По умолчанию разрешён только с этой же машины; в Docker порт публикуется
# только на localhost хоста, и проверка адреса отключается (LAB_ALLOW_REMOTE_RUN=1).
ALLOW_REMOTE_RUN = os.environ.get("LAB_ALLOW_REMOTE_RUN") == "1"
# Без дисплея (Docker) браузер можно запускать только headless
HEADLESS_ONLY = os.environ.get("LAB_HEADLESS_ONLY") == "1"

STARTER_TEMPLATE = '''import re

from playwright.sync_api import Page, expect


def {func}(page: Page):
    page.goto("/play/{slug}")

    # TODO: твой код здесь

    {check}
'''

BUG_STARTER_TEMPLATE = '''import re

from playwright.sync_api import Page, expect


def {func}(page: Page):
    page.goto("/play/{slug}")

    # TODO: проверь поведение страницы по спецификации из задания.
    # На текущей версии страницы этот тест должен УПАСТЬ — значит, баг найден.
    # Убедиться, что тест падает именно из-за бага: python verify.py {slug}
'''

STATUS_CHECK = 'expect(page.get_by_test_id("mission-status")).to_have_attribute("data-status", "success")'

# Подпись идентификаторов прогноза (миссия har-replay): так сервер узнаёт свой
# старый ответ даже после перезапуска, ничего не храня.
FORECAST_KEY = b"aqa-lab-forecast"

_file_lock = threading.Lock()


def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def mark_solved(slug: str) -> None:
    with _file_lock:
        progress = read_json(PROGRESS_FILE)
        progress.setdefault(slug, datetime.now().isoformat(timespec="seconds"))
        write_json(PROGRESS_FILE, progress)


def _node_name(node: ast.stmt) -> str | None:
    if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
        return node.name
    if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
        return node.targets[0].id
    return None


def _used_names(node: ast.AST) -> set[str]:
    names = {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}
    if isinstance(node, ast.FunctionDef):
        names |= {a.arg for a in node.args.args}  # фикстуры приходят параметрами
    return names


def _with_decorators(source: str, node: ast.stmt) -> str:
    decorators = "".join("@" + ast.get_source_segment(source, d) + "\n" for d in getattr(node, "decorator_list", []))
    return decorators + ast.get_source_segment(source, node)


def load_solutions(directory: Path = SOLUTIONS_DIR, expand_helper: bool = True) -> dict[str, str]:
    """Достаёт исходники test_* функций из test_*.py, ключ — имя функции.

    Вместе с тестом берутся определения из того же файла, которыми он пользуется
    (Page Object классы, фикстуры, константы), — чтобы решение было полным.
    Хелпер assert_passed(page) разворачивается в полную проверку статуса,
    чтобы решение можно было скопировать в свой файл как есть.
    """
    solutions = {}
    pattern = "test_*.py" if directory == SOLUTIONS_DIR else "**/test_*.py"
    for path in sorted(directory.glob(pattern)):
        source = path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue
        helpers = {name: node for node in tree.body
                   if (name := _node_name(node)) and not name.startswith("test_") and name != "assert_passed"}
        for node in tree.body:
            if not (isinstance(node, ast.FunctionDef) and node.name.startswith("test_")):
                continue
            needed, queue = set(), [node]
            while queue:
                for name in _used_names(queue.pop()) & helpers.keys() - needed:
                    needed.add(name)
                    queue.append(helpers[name])
            parts = [_with_decorators(source, n) for n in tree.body if _node_name(n) in needed] + [_with_decorators(source, node)]
            code = "\n\n\n".join(parts)
            if expand_helper:
                code = code.replace("assert_passed(page)", STATUS_CHECK)
            solutions[node.name] = code
    return solutions


def forecast_id(issued_ms: int) -> str:
    sig = hmac.new(FORECAST_KEY, str(issued_ms).encode(), hashlib.sha256).hexdigest()[:10]
    return f"{issued_ms}-{sig}"


def forecast_issued_at(fid: str) -> int | None:
    issued, _, sig = fid.partition("-")
    if not issued.isdigit() or not hmac.compare_digest(forecast_id(int(issued)), fid):
        return None
    return int(issued)


def solution_path(mission) -> Path:
    return WEB_SOLUTIONS_DIR / f"{mission.func_name}.py"


def create_app() -> Flask:
    app = Flask(__name__)
    app.json.ensure_ascii = False
    sock = Sock(app)

    mutant_slug, _, mutant_name = os.environ.get("LAB_MUTANT", "").partition(":")
    sessions: dict[str, str] = {}
    todos: list[dict] = []
    parts: dict[tuple[str, bool], set[str]] = {}
    verify_jobs: dict[str, dict] = {}
    run_locks: dict[str, threading.Lock] = {}

    chat_rooms: dict[str, list[dict]] = {}
    chat_cond = threading.Condition()

    board_lock = threading.Lock()
    board: list[dict] = []
    board_titles: set[str] = set()
    board_ids = itertools.count(1)

    def mutant_for(slug):
        return mutant_name if slug == mutant_slug else None

    def is_reference():
        return bool(request.headers.get("X-Lab-Reference"))

    def runner_forbidden():
        """Ответ 403, если код с этого адреса запускать нельзя (см. ALLOW_REMOTE_RUN)."""
        if ALLOW_REMOTE_RUN or request.remote_addr in ("127.0.0.1", "::1"):
            return None
        return jsonify(error="Запуск тестов разрешён только с компьютера, где работает сайт"), 403

    def get_mission(slug):
        mission = MISSIONS_BY_SLUG.get(slug)
        if mission is None:
            abort(404)
        return mission

    def render_block(mission, block):
        """Рендерит один {% block %} из шаблона песочницы (бриф, подсказка)."""
        tmpl = app.jinja_env.get_template(f"playgrounds/{mission.slug}.html")
        if block not in tmpl.blocks:
            return ""
        ctx = tmpl.new_context({"mission": mission, "mutant": None})
        return Markup("".join(tmpl.blocks[block](ctx)))

    @app.context_processor
    def inject_globals():
        return {"missions_by_slug": MISSIONS_BY_SLUG, "tracks": TRACKS}

    # ---------- страницы ----------

    @app.get("/")
    def index():
        progress = read_json(PROGRESS_FILE)
        groups = [(c, [m for m in MISSIONS if m.category == c.id]) for c in CATEGORIES]
        return render_template("index.html", groups=groups, progress=progress,
                               verified=read_json(VERIFIED_FILE), total=len(MISSIONS))

    @app.get("/tracks/<track_id>")
    def track_page(track_id):
        track = TRACKS_BY_ID.get(track_id) or abort(404)
        return render_template("track.html", track=track, progress=read_json(PROGRESS_FILE),
                               verified=read_json(VERIFIED_FILE))

    @app.get("/cheatsheet")
    def cheatsheet():
        return render_template("cheatsheet.html")

    @app.get("/missions/<slug>")
    def mission_page(slug):
        mission = get_mission(slug)
        idx = MISSIONS.index(mission)
        template = BUG_STARTER_TEMPLATE if mission.kind == "bug" else STARTER_TEMPLATE
        in_tracks = [
            (t, t.slugs.index(slug), MISSIONS_BY_SLUG.get(t.slugs[t.slugs.index(slug) + 1])
             if t.slugs.index(slug) + 1 < len(t.slugs) else None)
            for t in TRACKS if slug in t.slugs
        ]
        starter = template.format(func=mission.func_name, slug=slug, check=STATUS_CHECK)
        saved = solution_path(mission)
        return render_template(
            "mission.html",
            mission=mission,
            category=next(c for c in CATEGORIES if c.id == mission.category),
            brief=render_block(mission, "brief"),
            hint=render_block(mission, "hint"),
            starter=starter,
            editor_code=saved.read_text(encoding="utf-8") if saved.exists() else starter,
            editor_path=saved.relative_to(BASE_DIR).as_posix(),
            editor_saved=saved.exists(),
            headless_only=HEADLESS_ONLY,
            solution=load_solutions().get(mission.func_name),
            user_solution=load_solutions(EXERCISES_DIR, expand_helper=False).get(mission.func_name),
            solved_at=read_json(PROGRESS_FILE).get(slug),
            verification=read_json(VERIFIED_FILE).get(slug),
            in_tracks=in_tracks,
            prev=MISSIONS[idx - 1] if idx > 0 else None,
            next=MISSIONS[idx + 1] if idx + 1 < len(MISSIONS) else None,
        )

    @app.get("/play/<slug>")
    def playground(slug):
        return render_template(f"playgrounds/{slug}.html", mission=get_mission(slug), mutant=mutant_for(slug))

    @app.get("/play/<slug>/<page>")
    def playground_subpage(slug, page):
        mission = get_mission(slug)
        try:
            return render_template(f"playgrounds/{slug}__{page}.html", mission=mission, mutant=mutant_for(slug))
        except TemplateNotFound:
            abort(404)

    @app.get("/sw-offline.js")
    def service_worker():
        # Лежит в корне сайта, чтобы его scope мог покрыть /play/offline-sw
        resp = send_from_directory(app.static_folder, "sw-offline.js", mimetype="application/javascript")
        resp.headers["Cache-Control"] = "no-cache"
        return resp

    # ---------- прогресс и проверка ----------

    @app.get("/api/progress")
    def progress_list():
        return jsonify(read_json(PROGRESS_FILE))

    @app.post("/api/progress/<slug>")
    def progress_mark(slug):
        mission = get_mission(slug)
        # Миссии «найди баг» и «почини тест» засчитывает только verify.py
        if is_reference() or mutant_slug or mission.kind != "normal":
            return jsonify(ok=True, counted=False)
        mark_solved(slug)
        return jsonify(ok=True, counted=True)

    @app.delete("/api/progress")
    def progress_reset():
        with _file_lock:
            write_json(PROGRESS_FILE, {})
            write_json(VERIFIED_FILE, {})
        parts.clear()
        return jsonify(ok=True)

    @app.post("/api/parts/<slug>")
    def parts_mark(slug):
        """Миссии из нескольких тестов (параметризация): засчитываются, когда покрыты все части."""
        get_mission(slug)
        data = request.get_json(force=True)
        covered = parts.setdefault((slug, is_reference()), set())
        covered.add(str(data["part"]))
        complete = len(covered) >= int(data["total"])
        if complete and not is_reference() and not mutant_slug:
            mark_solved(slug)
        return jsonify(covered=sorted(covered), total=int(data["total"]), complete=complete)

    # ---------- редактор: сохранение и запуск кода ----------

    def save_solution(mission, code) -> Path:
        path = solution_path(mission)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(code, encoding="utf-8", newline="\n")
        return path

    def read_code():
        code = (request.get_json(force=True, silent=True) or {}).get("code")
        if not isinstance(code, str):
            abort(400)
        if len(code) > MAX_CODE_SIZE:
            abort(413)
        return code

    @app.put("/api/solution/<slug>")
    def solution_save(slug):
        mission = get_mission(slug)
        if forbidden := runner_forbidden():
            return forbidden
        path = save_solution(mission, read_code())
        return jsonify(ok=True, path=path.relative_to(BASE_DIR).as_posix())

    @app.post("/api/run/<slug>")
    def solution_run(slug):
        mission = get_mission(slug)
        if forbidden := runner_forbidden():
            return forbidden
        code = read_code()
        headed = bool((request.get_json(silent=True) or {}).get("headed")) and not HEADLESS_ONLY
        lock = run_locks.setdefault(slug, threading.Lock())
        if not lock.acquire(blocking=False):
            return jsonify(error="Тест этой миссии уже выполняется — дождись результата"), 409
        try:
            path = save_solution(mission, code)
            # Тест ходит в этот же сервер: прогресс засчитывается как при обычном запуске pytest
            cmd = [sys.executable, "-m", "pytest", path.relative_to(BASE_DIR).as_posix(),
                   "-q", "--tb=short", "--color=no", "-p", "no:cacheprovider",
                   "--base-url", request.host_url.rstrip("/")]
            if headed:
                cmd += ["--headed", "--slowmo", "300"]
            env = {**os.environ, "PYTHONIOENCODING": "utf-8", "LAB_MUTANT": ""}
            started = time.time()
            try:
                proc = subprocess.run(cmd, cwd=BASE_DIR, env=env, capture_output=True, text=True,
                                      encoding="utf-8", errors="replace", timeout=RUN_TIMEOUT)
                exit_code, output = proc.returncode, (proc.stdout + proc.stderr).strip()
            except subprocess.TimeoutExpired:
                exit_code, output = -1, f"Тест не уложился в {RUN_TIMEOUT} секунд и был остановлен."
            return jsonify(
                exit_code=exit_code,
                output=output[-20_000:],
                duration=round(time.time() - started, 1),
                path=path.relative_to(BASE_DIR).as_posix(),
                solved=slug in read_json(PROGRESS_FILE),
            )
        finally:
            lock.release()

    @app.post("/api/verify/<slug>")
    def verify_start(slug):
        mission = get_mission(slug)
        if forbidden := runner_forbidden():
            return forbidden
        if not mission.verifiable:
            return jsonify(error="У этой миссии нет проверки verify.py"), 400
        job = verify_jobs.get(slug)
        if job and job["state"] == "running":
            return jsonify(job), 202
        job = {"state": "running", "started": time.time(), "result": None}
        verify_jobs[slug] = job

        def run():
            proc = subprocess.run(
                [sys.executable, str(BASE_DIR / "verify.py"), slug, "--json"],
                cwd=BASE_DIR, capture_output=True, text=True, encoding="utf-8", errors="replace",
            )
            lines = proc.stdout.strip().splitlines()
            try:
                job["result"] = json.loads(lines[-1])
            except (IndexError, json.JSONDecodeError):
                job["result"] = {"error": (proc.stdout + proc.stderr)[-3000:]}
            job["state"] = "done"

        threading.Thread(target=run, daemon=True).start()
        return jsonify(job), 202

    @app.get("/api/verify/<slug>")
    def verify_status(slug):
        get_mission(slug)
        return jsonify(verify_jobs.get(slug, {"state": "idle"}))

    # ---------- учебные API ----------

    @app.post("/api/analytics/track")
    def analytics_track():
        return "", 204

    @app.post("/api/feedback")
    def feedback():
        return "", 204

    @app.get("/api/users")
    def api_users():
        users = [
            {"id": 1, "name": "Алиса", "role": "QA Lead"},
            {"id": 2, "name": "Борис", "role": "Developer"},
            {"id": 3, "name": "Вера", "role": "AQA Engineer"},
        ]
        if mutant_for("api-assertions") == "users-2":
            users = users[:2]
        return jsonify(users)

    @app.get("/api/products")
    def api_products():
        return jsonify([
            {"id": 1, "name": "Механическая клавиатура", "price": 7490},
            {"id": 2, "name": "Мышь беспроводная", "price": 2190},
            {"id": 3, "name": "Монитор 27\"", "price": 24990},
        ])

    @app.get("/api/orders")
    def api_orders():
        return jsonify([
            {"id": 1001, "title": "Книга «Чистый код»", "status": "Доставлен"},
            {"id": 1002, "title": "Наушники", "status": "В пути"},
        ])

    @app.get("/api/articles")
    def api_articles():
        return jsonify([
            {"id": 1, "title": "Локаторы, которые не ломаются"},
            {"id": 2, "title": "Почему sleep — зло"},
            {"id": 3, "title": "Моки в Playwright за 5 минут"},
        ])

    @app.get("/api/profile")
    def api_profile():
        request_id = uuid.uuid4().hex
        resp = jsonify({"name": "Гость", "plan": "free", "request_id": request_id})
        resp.headers["X-Request-Id"] = request_id
        return resp

    @app.get("/api/search")
    def api_search():
        q = request.args.get("q", "").strip().lower()
        items = ["Playwright", "pytest", "Selenium", "Python", "Postman", "Allure"]
        resp = jsonify([i for i in items if q in i.lower()])
        resp.headers["X-Lab-Query"] = q
        return resp

    @app.get("/api/rates")
    def api_rates():
        time.sleep(random.uniform(0.8, 1.6))
        return jsonify({"currency": "USD", "rate": round(random.uniform(80, 99), 2)})

    @app.get("/api/widgets/<int:n>")
    def api_widget(n):
        time.sleep(0.4 + 0.3 * n)
        return jsonify({"id": n, "value": random.randint(100, 999)})

    @app.get("/api/secret")
    def api_secret():
        if request.headers.get("Authorization") != "Bearer lab-token":
            return jsonify(error="unauthorized"), 401
        return jsonify(code="LAB-" + secrets.token_hex(3).upper())

    @app.post("/api/login")
    def api_login():
        data = request.get_json(force=True)
        if data.get("username") != "student" or data.get("password") != "playwright123":
            return jsonify(error="Неверный логин или пароль"), 401
        token = secrets.token_hex(16)
        sessions[token] = data["username"]
        resp = jsonify(ok=True)
        resp.set_cookie("lab_session", token, httponly=True, samesite="Lax")
        return resp

    @app.get("/api/me")
    def api_me():
        user = sessions.get(request.cookies.get("lab_session", ""))
        if not user:
            return jsonify(error="unauthorized"), 401
        return jsonify(username=user)

    @app.post("/api/logout")
    def api_logout():
        sessions.pop(request.cookies.get("lab_session", ""), None)
        resp = jsonify(ok=True)
        resp.delete_cookie("lab_session")
        return resp

    @app.get("/api/todos")
    def api_todos():
        return jsonify(todos)

    @app.post("/api/todos")
    def api_todo_create():
        data = request.get_json(force=True, silent=True) or {}
        title = str(data.get("title", "")).strip()
        if not title:
            return jsonify(error="title is required"), 422
        mutant = mutant_for("api-assertions")
        todo = {"id": len(todos) + 1, "title": title, "done": mutant == "done-true"}
        todos.append(todo)
        resp = make_response(jsonify(todo), 200 if mutant == "status-200" else 201)
        resp.set_cookie("lab_todo", str(todo["id"]), samesite="Lax")
        return resp

    # --- har-replay ---

    @app.get("/api/forecast")
    def api_forecast():
        return jsonify(id=forecast_id(int(time.time() * 1000)), city="Казань",
                       temp=random.randint(-15, 25), condition=random.choice(["Ясно", "Облачно", "Снег", "Дождь"]))

    @app.get("/api/forecast/check")
    def api_forecast_check():
        issued = forecast_issued_at(request.args.get("id", ""))
        since = float(request.args.get("since", 0))
        # Ответ «из HAR» — это прогноз, выданный сервером раньше, чем загрузилась страница
        return jsonify(replayed=issued is not None and issued < since)

    # --- isolation: общая доска, по которой «ходят коллеги» ---

    def board_noise():
        if random.random() < 0.4:
            n = next(board_ids)
            board.append({"id": n, "title": f"Задача коллеги #{n}", "mine": False})
        colleagues = [c for c in board if not c["mine"]]
        if colleagues and random.random() < 0.3:
            board.remove(random.choice(colleagues))

    @app.get("/api/board")
    def api_board():
        with board_lock:
            board_noise()
            return jsonify([{"id": c["id"], "title": c["title"]} for c in board])

    @app.post("/api/board")
    def api_board_create():
        title = str((request.get_json(force=True, silent=True) or {}).get("title", "")).strip()
        if not title:
            return jsonify(error="Название обязательно"), 422
        with board_lock:
            if title in board_titles:
                return jsonify(error="Карточка с таким названием уже создавалась — используй уникальные данные"), 409
            board_titles.add(title)
            card = {"id": next(board_ids), "title": title, "mine": True}
            board.append(card)
        return jsonify(id=card["id"], title=title), 201

    @app.delete("/api/board/<int:card_id>")
    def api_board_delete(card_id):
        with board_lock:
            for card in board:
                if card["id"] == card_id:
                    board.remove(card)
                    return "", 204
        return jsonify(error="not found"), 404

    # --- multi-user-chat: Server-Sent Events ---

    @app.post("/api/chat/send")
    def chat_send():
        data = request.get_json(force=True)
        room = str(data.get("room", ""))[:64]
        message = {"author": str(data.get("author", ""))[:40], "text": str(data.get("text", ""))[:500]}
        with chat_cond:
            chat_rooms.setdefault(room, []).append(message)
            chat_cond.notify_all()
        return jsonify(ok=True)

    @app.get("/api/chat/stream")
    def chat_stream():
        room = request.args.get("room", "")[:64]

        def events():
            sent = 0
            yield "retry: 1000\n\n"
            while True:
                with chat_cond:
                    if len(chat_rooms.get(room, [])) <= sent:
                        chat_cond.wait(timeout=10)
                    new = chat_rooms.get(room, [])[sent:]
                sent += len(new)
                for message in new:
                    yield f"data: {json.dumps(message, ensure_ascii=False)}\n\n"
                if not new:
                    yield ": ping\n\n"

        return Response(events(), mimetype="text/event-stream", headers={"Cache-Control": "no-cache"})

    # --- websocket: котировки ---

    @sock.route("/ws/quotes")
    def ws_quotes(ws):
        prices = {"PWRT": 1250.0, "PYTS": 830.0, "SELN": 410.0}
        try:
            request_data = json.loads(ws.receive(timeout=10) or "{}")
        except json.JSONDecodeError:
            request_data = {}
        symbol = request_data.get("subscribe")
        if symbol not in prices:
            ws.send(json.dumps({"error": "unknown symbol", "symbol": symbol}))
            return
        price = prices[symbol]
        while True:
            price = round(max(1.0, price + random.uniform(-5, 5)), 2)
            ws.send(json.dumps({"symbol": symbol, "price": price}))
            time.sleep(0.5)

    return app


if __name__ == "__main__":
    create_app().run(
        host=os.environ.get("LAB_HOST", "127.0.0.1"),
        port=int(os.environ.get("LAB_PORT", "5000")),
        debug=os.environ.get("LAB_DEBUG", "1") == "1",
        threaded=True,
        # Автоперезагрузка не должна срабатывать на решения: редактор сохраняет их
        # прямо во время запроса «Запустить», и перезапуск оборвал бы этот запрос
        exclude_patterns=["*exercises*", "*tests*", "*test-results*", "*__snapshots__*"],
    )
