"""Генерирует static/traces/trace-debug.zip для миссии «Почини тест по trace».

Прогоняет «упавший в CI тест коллеги» с записью trace. Запускать заново нужно,
только если поменялась песочница trace-debug:

    python tools/make_trace.py
"""

import sys
import threading
from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import expect, sync_playwright
from werkzeug.serving import make_server

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app import create_app  # noqa: E402

OUTPUT = BASE_DIR / "static" / "traces" / "trace-debug.zip"


def main() -> None:
    server = make_server("127.0.0.1", 0, create_app(), threaded=True)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base_url = f"http://127.0.0.1:{server.server_port}"

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(base_url=base_url)
        context.tracing.start(screenshots=True, snapshots=True, sources=False, title="test_trace_debug")
        page = context.new_page()
        try:
            page.goto("/play/trace-debug")
            page.get_by_placeholder("Промокод").fill("SALE10")
            page.get_by_role("button", name="Применить").click()
            expect(page.get_by_test_id("total")).to_have_text("Итого: 8100 ₽", timeout=3000)
        except AssertionError as error:
            print("Тест упал, как и задумано:", str(error).splitlines()[0])
        except PlaywrightTimeoutError as error:
            print("Тест упал по таймауту:", error)
        context.tracing.stop(path=OUTPUT)
        browser.close()
    server.shutdown()
    print(f"Trace сохранён: {OUTPUT.relative_to(BASE_DIR)}")


if __name__ == "__main__":
    main()
