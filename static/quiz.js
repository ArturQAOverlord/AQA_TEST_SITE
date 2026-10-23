// Прохождение теста трека Manual QA: один вопрос на экране, проверка ответа на сервере,
// разбор после каждого ответа, итог со списком ошибок и окно с теорией по теме теста.
// Тексты вопросов, вариантов и объяснений — наш контент, поэтому выводятся как HTML;
// всё, что вводит пользователь, — только через textContent.
(function () {
  const root = document.getElementById('quiz');
  if (!root) return;
  const slug = root.dataset.slug;
  const data = JSON.parse(document.getElementById('quiz-data').textContent);
  const questions = data.questions;
  let idx = 0, score = 0, mistakes = [];
  let theory = null;

  function h(tag, props = {}, ...children) {
    const node = document.createElement(tag);
    Object.entries(props).forEach(([k, v]) => {
      if (k === 'html') node.innerHTML = v;
      else if (k === 'text') node.textContent = v;
      else if (k.startsWith('on')) node.addEventListener(k.slice(2), v);
      else node.setAttribute(k, v);
    });
    children.flat().forEach(c => c && node.appendChild(c));
    return node;
  }

  function shuffled(items) {
    const a = items.slice();
    for (let i = a.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [a[i], a[j]] = [a[j], a[i]];
    }
    return a;
  }

  function progressBar() {
    return h('div', { class: 'quiz-progress' },
      h('span', { class: 'muted', text: `Вопрос ${idx + 1} из ${questions.length}` }),
      h('div', { class: 'progress-bar small' },
        h('div', { class: 'progress-fill', style: `width: ${idx / questions.length * 100}%` })));
  }

  function renderQuestion() {
    const q = questions[idx];
    const form = h('form', { class: 'quiz-form' });
    const hint = h('p', { class: 'muted quiz-hint' });

    if (q.kind === 'text') {
      form.appendChild(h('input', { type: 'text', name: 'answer', 'aria-label': 'Ответ',
        placeholder: q.placeholder || 'Твой ответ', autocomplete: 'off', class: 'quiz-input' }));
    } else {
      const type = q.kind === 'single' ? 'radio' : 'checkbox';
      hint.textContent = q.kind === 'multi' ? 'Выбери все подходящие варианты' : 'Выбери один вариант';
      const list = h('div', { class: 'quiz-options' });
      shuffled(q.options.map((text, id) => ({ text, id }))).forEach(o => {
        list.appendChild(h('label', { class: 'quiz-option', 'data-id': o.id },
          h('input', { type, name: 'answer', value: o.id }),
          h('span', { html: o.text })));
      });
      form.appendChild(list);
    }
    const submit = h('button', { type: 'submit', class: 'btn-primary', text: 'Ответить' });
    const error = h('p', { class: 'warn-mark', role: 'alert' });
    form.append(h('div', { class: 'row-gap' }, submit), error);
    form.addEventListener('submit', async e => {
      e.preventDefault();
      const answer = readAnswer(q, form);
      if (answer === null) { error.textContent = 'Сначала дай ответ'; return; }
      error.textContent = '';
      submit.disabled = true;
      const r = await fetch(`/api/qa/${slug}/check`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ qid: q.id, answer }),
      });
      if (!r.ok) { error.textContent = 'Не удалось проверить ответ, попробуй ещё раз'; submit.disabled = false; return; }
      showFeedback(q, form, answer, await r.json());
    });

    root.replaceChildren(progressBar(),
      h('div', { class: 'quiz-text', html: q.text }), hint, form);
    const first = form.querySelector('input');
    if (first && q.kind === 'text') first.focus();
  }

  function readAnswer(q, form) {
    if (q.kind === 'text') {
      const value = form.querySelector('input').value.trim();
      return value ? value : null;
    }
    const checked = [...form.querySelectorAll('input:checked')].map(i => Number(i.value));
    if (!checked.length) return null;
    return q.kind === 'single' ? checked[0] : checked;
  }

  function yourAnswerNode(q, answer) {
    if (q.kind === 'text') return h('span', { text: answer });
    const ids = Array.isArray(answer) ? answer : [answer];
    return h('span', { html: ids.map(id => q.options[id]).join('; ') });
  }

  function showFeedback(q, form, answer, res) {
    form.querySelectorAll('input, button').forEach(i => { i.disabled = true; });
    form.querySelectorAll('.quiz-option').forEach(label => {
      const id = Number(label.dataset.id);
      const chosen = label.querySelector('input').checked;
      if (res.correct_ids.includes(id)) label.classList.add('opt-correct');
      else if (chosen) label.classList.add('opt-wrong');
    });
    if (res.correct) score++;
    else mistakes.push({ q, answer, res });

    const last = idx === questions.length - 1;
    const next = h('button', { type: 'button', class: 'btn-primary',
      text: last ? 'Посмотреть результат' : 'Следующий вопрос →',
      onclick: () => { if (last) finish(); else { idx++; renderQuestion(); } } });
    root.appendChild(h('div', { class: `quiz-feedback ${res.correct ? 'ok' : 'fail'}` },
      h('p', { class: 'quiz-verdict', text: res.correct ? '✅ Верно' : '❌ Неверно' }),
      res.correct ? null : h('p', {}, h('b', { text: 'Правильный ответ: ' }), h('span', { html: res.answer })),
      h('div', { class: 'prose', html: res.explanation }),
      h('div', { class: 'row-gap' }, next)));
    next.focus();
  }

  // Теория приходит с сервера только после завершения теста, чтобы не подсказывать ответы
  async function loadTheory() {
    if (theory) return theory;
    try {
      const r = await fetch(`/api/qa/${slug}/theory`);
      if (r.ok) theory = await r.json();
    } catch (e) { /* без теории итог всё равно показывается */ }
    return theory;
  }

  function theoryDialog() {
    let dialog = document.getElementById('theory-dialog');
    if (dialog) return dialog;
    const close = () => dialog.close();
    dialog = h('dialog', { id: 'theory-dialog', class: 'theory-dialog', 'aria-labelledby': 'theory-title' },
      h('header', { class: 'theory-head' },
        h('h2', { id: 'theory-title', text: `📖 Теория: ${theory.title}` }),
        h('button', { type: 'button', class: 'theory-x', 'aria-label': 'Закрыть', text: '✕', onclick: close })),
      h('div', { class: 'theory-body prose', html: theory.html }),
      h('footer', { class: 'theory-foot' },
        h('button', { type: 'button', class: 'btn-primary', text: 'Понятно', onclick: close })));
    // Клик по затемнению вокруг окна тоже закрывает его
    dialog.addEventListener('click', e => { if (e.target === dialog) close(); });
    document.body.appendChild(dialog);
    return dialog;
  }

  function openTheory() {
    if (!theory) return;
    const dialog = theoryDialog();
    dialog.querySelector('.theory-body').scrollTop = 0;
    dialog.showModal();
  }

  async function finish() {
    const total = questions.length;
    const passed = score >= data.pass_ratio * total;
    let saved = null;
    try {
      const r = await fetch(`/api/qa/${slug}/result`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ score }),
      });
      if (r.ok) saved = await r.json();
    } catch (e) { /* результат просто не сохранится */ }
    await loadTheory();

    const list = h('ol', { class: 'quiz-mistakes' }, mistakes.map(m => h('li', {},
      h('div', { class: 'quiz-text', html: m.q.text }),
      h('p', {}, h('b', { text: 'Твой ответ: ' }), yourAnswerNode(m.q, m.answer)),
      h('p', {}, h('b', { text: 'Правильный: ' }), h('span', { html: m.res.answer })),
      h('div', { class: 'prose muted', html: m.res.explanation }))));

    // replaceChildren превращает null в текст «null», поэтому пустые части отфильтровываем
    root.replaceChildren(...[
      h('h2', { class: 'quiz-score', text: `Результат: ${score} из ${total}` }),
      h('p', { class: passed ? 'done-mark' : 'warn-mark',
        text: passed ? 'Тест сдан 🎉' : `Не сдан: нужно от ${Math.ceil(data.pass_ratio * total)} верных ответов` }),
      saved && saved.saved ? h('p', { class: 'muted', text: `Лучший результат: ${saved.best} из ${saved.total}` }) : null,
      mistakes.length ? h('h3', { text: 'Разбор ошибок' }) : h('p', { text: 'Ни одной ошибки!' }),
      mistakes.length ? list : null,
      h('div', { class: 'row-gap' },
        theory ? h('button', { type: 'button', class: 'btn-ghost', text: '📖 Теория по теме', onclick: openTheory }) : null,
        h('button', { type: 'button', class: 'btn-ghost', text: 'Пройти заново',
          onclick: () => { idx = 0; score = 0; mistakes = []; renderQuestion(); } }),
        data.next ? h('a', { class: 'btn-primary', href: data.next, text: 'Следующий тест →' }) : null,
        h('a', { class: 'btn-ghost', href: '/qa', text: 'К списку тестов' })),
    ].filter(Boolean));
    openTheory();
  }

  renderQuestion();
})();
