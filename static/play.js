// Общий помощник для песочниц: статус миссии, защита от обходов и отправка прогресса.
(function () {
  const slug = document.body.dataset.slug;
  const statusEl = () => document.getElementById('mission-status');
  // Единственный источник правды о статусе — эта переменная, а не DOM:
  // подмену атрибута через page.evaluate() ловит MutationObserver ниже.
  let state = 'pending';
  let text = statusEl() ? statusEl().textContent : '';
  let internal = 0;

  function render() {
    const el = statusEl();
    if (!el) return;
    internal++;
    el.dataset.status = state;
    el.textContent = text;
    internal--;
  }

  function fail(reason) {
    if (state === 'fail') return;
    state = 'fail';
    text = '❌ Провал: ' + reason + '. Перезагрузи страницу, чтобы попробовать снова';
    render();
  }

  window.Lab = {
    slug,
    mutant: window.LAB_MUTANT || null,

    // Статус выставляется только после того, как прогресс сохранён на сервере,
    // поэтому тест, дождавшийся data-status="success", точно попал в зачёт.
    // record: false — показать успех, но не засчитывать миссию (её засчитает сервер).
    async success(message, { record = true } = {}) {
      if (state !== 'pending') return;
      state = 'saving';
      if (record && navigator.webdriver) {
        try { await fetch(`/api/progress/${slug}`, { method: 'POST' }); } catch (e) { /* офлайн — не страшно */ }
      }
      if (state !== 'saving') return;
      state = 'success';
      text = '✅ ' + (message || 'Миссия пройдена');
      render();
    },

    // Любая ошибка окончательна: после неё миссию на этой странице уже не пройти.
    fail,

    get failed() { return state === 'fail'; },

    // Программные клики самой страницы (например, input.click() для file chooser)
    // не должны считаться синтетическими событиями теста.
    internal(fn) {
      internal++;
      try { return fn(); } finally { internal--; }
    },

    async part(name, total) {
      const r = await fetch(`/api/parts/${slug}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ part: name, total }),
      });
      return r.json();
    },

    sleep(ms) {
      return new Promise(r => setTimeout(r, ms));
    },

    rand(min, max) {
      return Math.floor(Math.random() * (max - min + 1)) + min;
    },
  };

  // Клики и нажатия должны быть настоящими (Playwright шлёт их через протокол браузера,
  // у них isTrusted === true). dispatch_event() и el.click() из evaluate — нет.
  const GUARDED = ['click', 'dblclick', 'contextmenu', 'mousedown', 'mouseup', 'keydown', 'keyup'];
  GUARDED.forEach(type => window.addEventListener(type, e => {
    if (e.isTrusted || internal) return;
    e.stopImmediatePropagation();
    e.preventDefault();
    fail(`синтетическое событие «${type}» (dispatch_event или JS-клик) — используй настоящие действия Playwright`);
  }, true));

  // Колбэк срабатывает асинхронно, поэтому сравниваем DOM с state, а не полагаемся на флаг internal.
  const observer = new MutationObserver(() => {
    const el = statusEl();
    if (el && (el.dataset.status !== state || el.textContent !== text)) fail('статус миссии изменён вручную');
  });
  if (statusEl()) {
    statusEl().dataset.status = state;
    observer.observe(statusEl(), { attributes: true, childList: true, characterData: true, subtree: true });
  }
})();
