"""Проверка твоих тестов на вариантах песочницы.

Тест, который проходит, ещё не значит, что он что-то проверяет. verify.py
запускает твой тест на других версиях страницы — что именно ожидается,
зависит от типа миссии (см. missions.py):

  мутанты (обычные миссии) — в странице подложен баг, тест должен УПАСТЬ;
  «найди баг»              — тест должен упасть на текущей странице и пройти на исправленной;
  «почини тест»            — страницу «переделали», тест должен ПРОЙТИ на каждой версии.

Для некоторых миссий дополнительно проверяется структура кода
(Page Object, фикстуры, маркеры, отсутствие sleep и т.п.).

Примеры:
    python verify.py                     # все проверяемые миссии, для которых есть твои тесты
    python verify.py text-assertions     # одна миссия
    python verify.py --dir tests         # проверить эталонные решения
"""

import argparse
import ast
import json
import os
import re
import socket
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from missions import MISSIONS, MISSIONS_BY_SLUG, Mission

BASE_DIR = Path(__file__).resolve().parent


# ---------- статические проверки ----------

@dataclass
class TestSource:
    func: ast.FunctionDef
    modules: list[ast.Module]  # файл с тестом и conftest.py из той же папки


def find_source(directory: Path, func_name: str, test_file: Path | None = None) -> TestSource | None:
    conftests = [ast.parse(p.read_text(encoding="utf-8")) for p in directory.glob("conftest.py")]
    for path in [test_file] if test_file else sorted(directory.rglob("test_*.py")):
        try:
            module = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in module.body:
            if isinstance(node, ast.FunctionDef) and node.name == func_name:
                return TestSource(node, [module, *conftests])
    return None


def calls_in(node: ast.AST) -> list[str]:
    return [ast.unparse(n.func) for n in ast.walk(node) if isinstance(n, ast.Call)]


def top_level(src: TestSource, kind):
    return [n for module in src.modules for n in module.body if isinstance(n, kind)]


def is_fixture(node: ast.FunctionDef) -> bool:
    return any(ast.unparse(d).startswith(("pytest.fixture", "fixture")) for d in node.decorator_list)


def check_markers(src: TestSource) -> list[str]:
    marks = [ast.unparse(d) for d in src.func.decorator_list]
    return [] if any(m.startswith("pytest.mark.smoke") for m in marks) else ["тест не помечен @pytest.mark.smoke"]


def check_fixtures(src: TestSource) -> list[str]:
    fixtures = {f.name: f for f in top_level(src, ast.FunctionDef) if is_fixture(f)}
    used = [a.arg for a in src.func.args.args if a.arg in fixtures]
    if not used:
        return ["тест не использует собственную фикстуру (объяви её через @pytest.fixture и прими параметром)"]
    if not any("/api/login" in ast.unparse(fixtures[name]) for name in used):
        return ["фикстура должна входить через API: page.request.post(\"/api/login\", ...)"]
    return []


LOCATOR_METHODS = re.compile(r"\.(get_by_\w+|locator|frame_locator)$")


def check_page_object(src: TestSource) -> list[str]:
    problems = []
    pages = [c.name for c in top_level(src, ast.ClassDef) if c.name.endswith("Page")]
    if len(pages) < 2:
        problems.append("нужно минимум два класса Page Object с именами вида LoginPage, ProductsPage")
    direct = sorted({c for c in calls_in(src.func) if LOCATOR_METHODS.search(c)})
    if direct:
        problems.append("в самом тесте не должно быть локаторов — перенеси их в Page Object: " + ", ".join(direct))
    return problems


def check_allure(src: TestSource) -> list[str]:
    problems = []
    steps = [item for n in ast.walk(src.func) if isinstance(n, ast.With) for item in n.items
             if ast.unparse(item.context_expr).startswith("allure.step(")]
    if len(steps) < 3:
        problems.append(f"нужно минимум 3 шага with allure.step(...), сейчас {len(steps)}")
    if not any(c == "allure.attach" for c in calls_in(src.func)):
        problems.append("нет вложения allure.attach(...) со скриншотом")
    return problems


def check_no_sleep(src: TestSource) -> list[str]:
    bad = sorted({c for c in calls_in(src.func) if c.endswith(("sleep", "wait_for_timeout", "is_visible"))})
    return ["в тесте остались " + ", ".join(bad) + " — используй web-first expect()"] if bad else []


def check_no_brittle_css(src: TestSource) -> list[str]:
    brittle = []
    for node in ast.walk(src.func):
        if isinstance(node, ast.Call) and ast.unparse(node.func).endswith(".locator") and node.args:
            arg = node.args[0]
            if isinstance(arg, ast.Constant) and re.search(r"nth-child|#[\w-]|\.[A-Za-z]|>", str(arg.value)):
                brittle.append(str(arg.value))
    return ["хрупкие CSS-селекторы: " + "; ".join(brittle)] if brittle else []


STATIC_CHECKS = {
    "markers": check_markers,
    "fixtures": check_fixtures,
    "page-object": check_page_object,
    "allure-steps": check_allure,
    "fix-sleeps": check_no_sleep,
    "fix-brittle-locators": check_no_brittle_css,
}


# ---------- запуск ----------

def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def collect(test_dir: str) -> dict[str, str]:
    """Имя тестовой функции -> 'путь::функция' (параметризованные случаи запускаются все вместе).

    Если функция объявлена в нескольких файлах (например, в своём и в exercises/web/
    из редактора на сайте), берётся файл, который менялся последним.
    """
    result = subprocess.run(
        [sys.executable, "-m", "pytest", test_dir, "--collect-only", "-q", "-p", "no:cacheprovider"],
        cwd=BASE_DIR, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    tests: dict[str, str] = {}
    for line in result.stdout.splitlines():
        match = re.match(r"^(\S+\.py)::(test_\w+)", line.strip())
        if not match:
            continue
        path, func = match.groups()
        current = tests.get(func)
        if current is None or (BASE_DIR / path).stat().st_mtime > (BASE_DIR / current.split("::")[0]).stat().st_mtime:
            tests[func] = f"{path}::{func}"
    return tests


def run_test(node: str, variant: str | None) -> int:
    """0 — тест прошёл, 1 — упал, остальное — ошибка запуска."""
    env = {**os.environ, "LAB_MUTANT": variant or "", "LAB_VERIFY": "1", "PYTHONIOENCODING": "utf-8"}
    cmd = [sys.executable, "-m", "pytest", node, "-q", "-x", "-p", "no:cacheprovider",
           "--tracing", "off", "--screenshot", "off", "--video", "off",
           "--base-url", f"http://127.0.0.1:{free_port()}"]
    return subprocess.run(cmd, cwd=BASE_DIR, env=env, capture_output=True).returncode


def verify_mission(mission: Mission, node: str, src: TestSource | None) -> dict:
    report = {"slug": mission.slug, "kind": mission.kind, "node": node, "items": [], "notes": []}
    if mission.static_check:
        report["notes"] = STATIC_CHECKS[mission.slug](src) if src else ["не удалось разобрать исходник теста"]

    if mission.kind == "bug":
        report["baseline"] = run_test(node, f"{mission.slug}:fixed") == 0
        if report["baseline"]:
            code = run_test(node, None)
            report["items"].append({"name": "bug", "description": "Тест падает на текущей версии страницы",
                                    "ok": code == 1, "status": {0: "passed", 1: "failed"}.get(code, "error")})
    else:
        report["baseline"] = run_test(node, None) == 0
        if report["baseline"]:
            for name, description in mission.mutants:
                code = run_test(node, f"{mission.slug}:{name}")
                status = {0: "passed", 1: "failed"}.get(code, "error")
                ok = status == ("passed" if mission.kind == "robust" else "failed")
                report["items"].append({"name": name, "description": description, "ok": ok, "status": status})

    report["ok"] = report["baseline"] and all(i["ok"] for i in report["items"]) and not report["notes"]
    return report


BASELINE_ERROR = {
    "normal": "тест не проходит на исправной странице — сначала добейся зелёного прогона",
    "robust": "тест не проходит даже на исходной странице",
    "bug": "тест не проходит на ИСПРАВЛЕННОЙ странице — значит, он проверяет что-то не то",
}
ITEM_MARKS = {
    "normal": {True: "✔ убит  ", False: "✘ ВЫЖИЛ "},
    "robust": {True: "✔ прошёл", False: "✘ УПАЛ  "},
    "bug": {True: "✔ баг найден", False: "✘ тест не падает на версии с багом"},
}


def print_report(report: dict) -> None:
    print(f"\n🧬 {report['slug']}  ({report['node']})")
    if not report["baseline"]:
        print("   ✘ " + BASELINE_ERROR[report["kind"]])
    for item in report["items"]:
        mark = ITEM_MARKS[report["kind"]][item["ok"]]
        label = "" if report["kind"] == "bug" else f" {item['name']}: {item['description']}"
        print(f"   {mark}{label}" + (" (ошибка запуска)" if item["status"] == "error" else ""))
    for note in report["notes"]:
        print(f"   ✘ структура: {note}")
    print("   Итог: " + ("✅ пройдено" if report["ok"] else "❌ есть замечания"))


def main() -> int:
    # В консоли Windows при перенаправлении вывода кодировка может быть cp1251 — без этого упадём на эмодзи
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Проверка тестов на вариантах песочницы")
    parser.add_argument("slugs", nargs="*", help="миссии (по умолчанию все проверяемые, для которых есть тест)")
    parser.add_argument("--dir", default="exercises", help="папка с тестами (по умолчанию exercises)")
    parser.add_argument("--jobs", type=int, default=4, help="сколько миссий проверять параллельно")
    parser.add_argument("--json", action="store_true", help="вывести результат одной строкой JSON")
    args = parser.parse_args()

    unknown = [s for s in args.slugs if s not in MISSIONS_BY_SLUG]
    if unknown:
        parser.error("нет таких миссий: " + ", ".join(unknown))
    not_verifiable = [s for s in args.slugs if not MISSIONS_BY_SLUG[s].verifiable]
    if not_verifiable:
        parser.error("у этих миссий нет проверки verify.py: " + ", ".join(not_verifiable))

    test_dir = (BASE_DIR / args.dir).resolve()
    tests = collect(args.dir)
    targets = [MISSIONS_BY_SLUG[s] for s in args.slugs] if args.slugs else [m for m in MISSIONS if m.verifiable]
    jobs = [(m, tests[m.func_name], find_source(test_dir, m.func_name, BASE_DIR / tests[m.func_name].split("::")[0]))
            for m in targets if m.func_name in tests]
    missing = [m for m in targets if m.func_name not in tests]

    if not jobs:
        message = f"Нечего проверять: в {args.dir}/ нет тестов " + (
            ", ".join(m.func_name for m in missing) if args.slugs else "для проверяемых миссий")
        print(json.dumps([{"error": message}], ensure_ascii=False) if args.json else message)
        return 1
    if not args.json:
        for mission in missing if args.slugs else []:
            print(f"⚠ {mission.slug}: в {args.dir}/ нет функции {mission.func_name}")
        print(f"Проверяю миссий: {len(jobs)}. Это займёт пару минут…")

    with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
        reports = list(pool.map(lambda job: verify_mission(*job), jobs))

    save = test_dir == (BASE_DIR / "exercises").resolve()
    if save:
        from app import VERIFIED_FILE, mark_solved, read_json, write_json
        verified = read_json(VERIFIED_FILE)
        for report in reports:
            items = report["items"]
            verified[report["slug"]] = {
                "ok": report["ok"],
                "kind": report["kind"],
                "baseline": report["baseline"],
                "passed": sum(i["ok"] for i in items),
                "total": len(items),
                "failed": [i["name"] for i in items if not i["ok"]],
                "notes": report["notes"],
                "at": datetime.now().isoformat(timespec="seconds"),
            }
            if report["ok"]:
                mark_solved(report["slug"])
        write_json(VERIFIED_FILE, verified)

    if args.json:
        print(json.dumps(reports, ensure_ascii=False))
    else:
        for report in reports:
            print_report(report)
        all_ok = all(r["ok"] for r in reports)
        print("\n" + ("Все проверки пройдены 💪" if all_ok else "Есть замечания — смотри выше."))
    return 0 if all(r["ok"] for r in reports) else 1


if __name__ == "__main__":
    sys.exit(main())
