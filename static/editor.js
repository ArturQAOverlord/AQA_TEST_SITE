// Редактор теста на странице миссии: CodeMirror (если загрузился с CDN) или обычный textarea.
(function () {
  const box = document.getElementById('editor-box');
  if (!box) return;
  const slug = box.dataset.slug;
  const kind = box.dataset.kind;
  const textarea = document.getElementById('code');
  const runBtn = document.getElementById('run');
  const saveState = document.getElementById('save-state');
  const result = document.getElementById('run-result');
  const summary = document.getElementById('run-summary');
  const output = document.getElementById('run-output');
  const starter = JSON.parse(document.getElementById('starter').textContent);

  // Подсказки по Ctrl+Space и после точки: самое ходовое API Playwright и pytest
  const WORDS = [
    'goto', 'reload', 'get_by_role', 'get_by_text', 'get_by_label', 'get_by_placeholder', 'get_by_test_id',
    'get_by_alt_text', 'get_by_title', 'locator', 'frame_locator', 'content_frame', 'filter', 'first', 'last',
    'nth', 'and_', 'or_', 'all', 'count', 'click', 'dblclick', 'fill', 'clear', 'press', 'press_sequentially',
    'check', 'uncheck', 'set_checked', 'select_option', 'hover', 'focus', 'blur', 'drag_to', 'set_input_files',
    'scroll_into_view_if_needed', 'inner_text', 'all_inner_texts', 'text_content', 'input_value',
    'get_attribute', 'bounding_box', 'screenshot', 'evaluate', 'is_visible', 'is_hidden', 'is_enabled',
    'is_disabled', 'is_checked', 'wait_for', 'wait_for_url', 'wait_for_function', 'wait_for_load_state',
    'wait_for_timeout', 'expect_response', 'expect_request', 'expect_popup', 'expect_download',
    'expect_file_chooser', 'expect_websocket', 'expect_event', 'route', 'unroute', 'route_from_har',
    'route_web_socket', 'fulfill', 'abort', 'continue_', 'fetch', 'post_data_json', 'json', 'status', 'ok',
    'on', 'once', 'accept', 'dismiss', 'context', 'request', 'keyboard', 'mouse', 'clock', 'add_cookies',
    'cookies', 'storage_state', 'add_init_script', 'add_locator_handler', 'set_viewport_size', 'emulate_media',
    'grant_permissions', 'set_geolocation', 'set_offline', 'new_context', 'new_page', 'close',
    'to_have_text', 'to_contain_text', 'to_have_count', 'to_have_value', 'to_have_values', 'to_have_attribute',
    'to_have_class', 'to_have_css', 'to_have_id', 'to_have_url', 'to_have_title', 'to_be_visible',
    'to_be_hidden', 'to_be_enabled', 'to_be_disabled', 'to_be_checked', 'to_be_editable', 'to_be_empty',
    'to_be_focused', 'to_be_attached', 'to_have_accessible_name', 'to_have_accessible_description',
    'to_have_role', 'to_match_aria_snapshot', 'to_be_ok', 'not_to_be_visible', 'not_to_have_count',
    'not_to_be_checked', 'not_to_be_attached', 'not_to_have_text', 'expect', 'exact', 'name', 'has_text',
    'has', 'has_not', 'timeout', 'label', 'button', 'parametrize', 'fixture', 'mark',
  ];

  function hint(cm) {
    const cur = cm.getCursor();
    const line = cm.getLine(cur.line);
    let start = cur.ch;
    while (start && /\w/.test(line[start - 1])) start--;
    const word = line.slice(start, cur.ch);
    const list = WORDS.filter(w => w.startsWith(word) && w !== word);
    return { list, from: CodeMirror.Pos(cur.line, start), to: CodeMirror.Pos(cur.line, cur.ch) };
  }

  let editor = null;
  if (window.CodeMirror) {
    editor = CodeMirror.fromTextArea(textarea, {
      mode: 'python',
      theme: 'material-darker',
      lineNumbers: true,
      indentUnit: 4,
      tabSize: 4,
      indentWithTabs: false,
      matchBrackets: true,
      extraKeys: {
        Tab: cm => (cm.somethingSelected() ? cm.indentSelection('add') : cm.replaceSelection('    ')),
        'Shift-Tab': cm => cm.indentSelection('subtract'),
        'Ctrl-Space': cm => cm.showHint({ hint, completeSingle: false }),
        'Ctrl-Enter': () => run(),
        'Cmd-Enter': () => run(),
        'Ctrl-S': () => save(),
        'Cmd-S': () => save(),
        'Ctrl-/': 'toggleComment',
        'Cmd-/': 'toggleComment',
      },
    });
    editor.on('inputRead', (cm, change) => {
      if (change.text[0] === '.') cm.showHint({ hint, completeSingle: false });
    });
    editor.on('change', () => { saveState.textContent = 'есть несохранённые изменения'; });
  } else {
    textarea.classList.add('plain-editor');
    textarea.addEventListener('input', () => { saveState.textContent = 'есть несохранённые изменения'; });
    textarea.addEventListener('keydown', e => {
      if (e.key === 'Tab') {
        e.preventDefault();
        textarea.setRangeText('    ', textarea.selectionStart, textarea.selectionEnd, 'end');
      }
      if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') { e.preventDefault(); run(); }
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') { e.preventDefault(); save(); }
    });
  }
  const getCode = () => (editor ? editor.getValue() : textarea.value);
  const setCode = code => (editor ? editor.setValue(code) : (textarea.value = code));

  async function errorText(response) {
    try { return (await response.json()).error || `Ошибка ${response.status}`; }
    catch { return `Ошибка ${response.status}`; }
  }

  async function save() {
    const r = await fetch(`/api/solution/${slug}`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ code: getCode() }),
    });
    saveState.textContent = r.ok ? 'сохранён' : await errorText(r);
  }

  const VERDICTS = {
    0: ['ok', '✅ Тест прошёл'],
    1: kind === 'bug'
      ? ['warn', '❌ Тест упал. Для миссии «найди баг» это и нужно — убедись кнопкой «Запустить проверку», что он падает именно из-за бага']
      : ['fail', '❌ Тест упал — смотри причину в выводе ниже'],
    2: ['fail', '⚠ Прогон прерван: ошибка при сборе тестов (синтаксис, отступы или импорт)'],
    4: ['fail', '⚠ Ошибка запуска pytest'],
    5: ['fail', '⚠ pytest не нашёл тестов — функция должна называться test_…'],
    '-1': ['fail', '⏱ Тест не уложился в отведённое время и был остановлен'],
  };

  async function run() {
    if (runBtn.disabled) return;
    runBtn.disabled = true;
    const started = Date.now();
    const timer = setInterval(() => { runBtn.textContent = `⏳ Выполняется… ${Math.round((Date.now() - started) / 1000)} с`; }, 500);
    runBtn.textContent = '⏳ Выполняется…';
    result.classList.remove('hidden');
    summary.className = 'run-summary';
    summary.textContent = 'Запускаю pytest…';
    output.textContent = '';
    startLive();
    try {
      const headed = document.getElementById('headed');
      const r = await fetch(`/api/run/${slug}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code: getCode(), headed: headed ? headed.checked : false,
          slow: document.getElementById('slow').checked }),
      });
      if (!r.ok) {
        summary.className = 'run-summary fail';
        summary.textContent = await errorText(r);
        return;
      }
      const data = await r.json();
      const [cls, text] = VERDICTS[data.exit_code] || ['fail', `⚠ pytest завершился с кодом ${data.exit_code}`];
      summary.className = 'run-summary ' + cls;
      summary.textContent = `${text} · ${data.duration} с`;
      output.textContent = data.output;
      saveState.textContent = 'сохранён';
      if (data.solved) document.getElementById('solved-badge').classList.remove('hidden');
      showVideos(data.videos || [], document.getElementById('slow').checked);
    } catch (e) {
      summary.className = 'run-summary fail';
      summary.textContent = 'Не удалось связаться с сервером: ' + e;
    } finally {
      stopLive();
      clearInterval(timer);
      runBtn.disabled = false;
      runBtn.textContent = '▶ Запустить';
    }
  }

  // Правая панель: песочница (своя копия страницы) и запись того, что делал тест в своём браузере
  const tabSandbox = document.getElementById('tab-sandbox');
  const tabVideo = document.getElementById('tab-video');
  const sandboxPane = document.getElementById('sandbox-pane');
  const videoPane = document.getElementById('video-pane');

  function selectTab(video) {
    tabSandbox.setAttribute('aria-selected', String(!video));
    tabVideo.setAttribute('aria-selected', String(video));
    sandboxPane.hidden = video;
    videoPane.hidden = !video;
    if (!video) videoPane.querySelectorAll('video').forEach(v => v.pause());
  }

  // Пока тест идёт, справа — живой экран его браузера: кадры приходят с сервера по WebSocket
  let liveSocket = null;

  function startLive() {
    stopLive();
    const status = document.createElement('p');
    status.className = 'preview-hint';
    status.textContent = 'Запускаю браузер теста…';
    const img = document.createElement('img');
    img.className = 'live-frame';
    img.alt = 'Экран браузера, в котором выполняется тест';
    img.hidden = true;
    videoPane.replaceChildren(status, img);
    tabVideo.disabled = false;
    selectTab(true);

    const ws = new WebSocket(`${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws/live/${slug}`);
    ws.binaryType = 'blob';
    let shown = null;
    ws.addEventListener('message', e => {
      if (typeof e.data === 'string') return;
      const next = URL.createObjectURL(e.data);
      img.onload = () => { if (shown) URL.revokeObjectURL(shown); shown = next; };
      img.src = next;
      img.hidden = false;
      status.className = 'preview-hint live-status';
      status.textContent = '● Идёт прогон — это экран браузера, в котором работает твой тест';
    });
    liveSocket = ws;
  }

  function stopLive() {
    if (liveSocket) liveSocket.close();
    liveSocket = null;
  }

  function showVideos(urls, slow) {
    videoPane.replaceChildren();
    tabVideo.disabled = false;
    if (!urls.length) {
      const note = document.createElement('p');
      note.className = 'preview-hint';
      note.textContent = 'Записи нет: тест не открыл страницу через фикстуру page (или упал раньше).';
      videoPane.appendChild(note);
      selectTab(true);
      return;
    }
    const hint = document.createElement('p');
    hint.className = 'preview-hint';
    hint.textContent = 'Прогон завершён. Это запись того, что делал тест, — её можно пересмотреть, ' +
      'перемотать и замедлить в меню плеера.';
    videoPane.appendChild(hint);
    urls.forEach((url, i) => {
      if (urls.length > 1) {
        const label = document.createElement('p');
        label.className = 'video-label';
        label.textContent = `Страница ${i + 1} из ${urls.length}`;
        videoPane.appendChild(label);
      }
      const video = document.createElement('video');
      // Без замедления тест кликает быстрее, чем успеваешь заметить, — замедляем просмотр
      video.defaultPlaybackRate = slow ? 1 : 0.5;
      video.controls = true;
      video.muted = true;
      video.playsInline = true;
      video.autoplay = i === 0;
      video.src = url;
      videoPane.appendChild(video);
    });
    selectTab(true);
  }

  tabSandbox.addEventListener('click', () => selectTab(false));
  tabVideo.addEventListener('click', () => selectTab(true));

  runBtn.addEventListener('click', run);
  document.getElementById('save').addEventListener('click', save);
  document.getElementById('reset').addEventListener('click', () => {
    if (confirm('Заменить код в редакторе стартовым шаблоном? Сохранённый файл изменится, только когда ты нажмёшь «Сохранить» или «Запустить».')) setCode(starter);
  });
})();
