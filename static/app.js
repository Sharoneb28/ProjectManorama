const $ = s => document.querySelector(s);
const MAX = 10;
let items = [];
let seq = 0;
let dragId = null;

const esc = s => String(s).replace(/[&<>"']/g, c => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;',
  '"': '&quot;', "'": '&#39;'
}[c]));

const wc = t => (t.trim() ? t.trim().split(/\s+/).length : 0);

const debounce = (fn, ms) => {
  let t;
  return (...a) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...a), ms);
  };
};

const byId = id => items.find(i => i.id === id);
const hasError = it => it.flags.some(f => f.level === 'error');

const canApprove = it =>
  !!it.ticker.trim() &&
  wc(it.ticker) <= MAX &&
  !it.validating &&
  !hasError(it);

/* ---------- source fact highlighting ---------- */

const SKIP = new Set([
  'The', 'A', 'An', 'In', 'On', 'At', 'It', 'Its',
  'This', 'That', 'We', 'Our', 'He', 'She',
  'They', 'For', 'And', 'But', 'Of', 'To',
  'By', 'With', 'As', 'If', 'All', 'Join',
  'Bring', 'Everyone'
]);

const FACT_RE =
  /(?:[$₹€£]\s?)?\d[\d,]*(?:\.\d+)?\s?(?:%|percent|million|billion|trillion|crore|lakh|thousand)?|[A-Z][\w&'’.-]*(?:\s+[A-Z][\w&'’.-]*)*/g;

function paintSource(it) {
  const t = it.ticker.toLowerCase();
  let out = '', last = 0, m;

  FACT_RE.lastIndex = 0;

  while ((m = FACT_RE.exec(it.source))) {
    const raw = m[0].trim();

    if (!raw || SKIP.has(raw)) continue;

    const used =
      t.includes(raw.toLowerCase()) ||
      t.includes(
        raw.replace(/[^\d.]/g, '').toLowerCase() || '\u0000'
      );

    out += esc(it.source.slice(last, m.index)) +
      `<mark class="${used ? 'used' : ''}">${esc(m[0])}</mark>`;

    last = m.index + m[0].length;
  }

  return out + esc(it.source.slice(last));
}

/* ---------- rendering ---------- */

function flagsHtml(it) {
  return it.flags.map(f =>
    `<span class="flag ${esc(f.level)}" title="${esc(f.message)}">${esc(f.message)}</span>`
  ).join('');
}

function cardHtml(it, n) {
  return `<li class="card ${it.approved ? 'approved' : ''}" data-id="${esc(it.id)}">
    <div class="rank">
      <button data-act="up" aria-label="Move up">▲</button>
      <span class="pos" data-grip title="Drag to reorder">${n + 1}</span>
      <button data-act="down" aria-label="Move down">▼</button>
    </div>

    <div class="src">
      <h3>Source</h3>
      <p class="srctext">${paintSource(it)}</p>
    </div>

    <div class="tk">
      <h3>Ticker</h3>

      <textarea class="edit" rows="2" aria-label="Ticker text">${esc(it.ticker)}</textarea>

      <div class="meta">
        <span class="count"></span>
        <span class="flags">${flagsHtml(it)}</span>
      </div>

      <div class="alts">
        ${it.alternatives.map(a =>
          `<button data-act="alt" data-text="${esc(a)}" title="Use this wording">${esc(a)}</button>`
        ).join('')}
      </div>

      <div class="actions">
        <button data-act="regen">Regenerate</button>
        <button data-act="undo" ${it.undo.length ? '' : 'disabled'}>Undo</button>
        <button data-act="revert" ${it.ticker === it.generated ? 'disabled' : ''}>Revert</button>
        <button data-act="remove">Remove</button>

        <label class="approve">
          <input type="checkbox" data-act="approve" ${it.approved ? 'checked' : ''}>
          Approved
        </label>
      </div>
    </div>
  </li>`;
}

function render() {
  $('#list').innerHTML = items.map(cardHtml).join('');

  items.forEach(refreshMeta);

  $('#empty').hidden = items.length > 0;

  updateCounts();
  buildTicker();
}

function refreshMeta(it) {
  const li = $(`[data-id="${it.id}"]`);
  if (!li) return;

  const n = wc(it.ticker);
  const c = li.querySelector('.count');

  c.textContent = `${n}/${MAX} words`;
  c.classList.toggle('over', n > MAX);

  li.querySelector('.flags').innerHTML = flagsHtml(it);
  li.querySelector('.srctext').innerHTML = paintSource(it);

  const cb = li.querySelector('[data-act=approve]');

  if (it.approved && !canApprove(it)) {
    it.approved = false;
  }

  cb.disabled = !canApprove(it);
  cb.checked = it.approved;

  cb.title = hasError(it)
    ? 'Fix the unsupported facts flagged here before approving'
    : it.validating
      ? 'Checking…'
      : wc(it.ticker) > MAX
        ? 'Over 10 words'
        : '';

  li.classList.toggle('approved', it.approved);

  li.querySelector('[data-act=undo]').disabled = !it.undo.length;
  li.querySelector('[data-act=revert]').disabled =
    it.ticker === it.generated;
}

function updateCounts() {
  const a = items.filter(i => i.approved).length;

  $('#counts').textContent = items.length
    ? `${a} of ${items.length} approved`
    : '';
}

/* ---------- live ticker preview ---------- */

function buildTicker() {
  const ready = items.filter(i => i.ticker.trim());
  const appr = ready.filter(i => i.approved);
  const use = appr.length ? appr : ready;

  $('#tickerMode').textContent = !ready.length
    ? ''
    : appr.length
      ? `${appr.length} approved`
      : 'draft: all tickers';

  const track = $('#track');

  track.style.animation = 'none';
  track.innerHTML = '';

  if (!use.length) {
    track.innerHTML =
      '<span class="empty">Your tickers will scroll here.</span>';
    return;
  }

  const html = use.map(i =>
    `<span class="tk-item">${esc(i.ticker)}</span>`
  ).join('');

  const first = document.createElement('div');
  first.className = 'seq';
  first.innerHTML = html;

  track.appendChild(first);

  const vw = $('#viewport').clientWidth;

  for (
    let r = 0;
    first.getBoundingClientRect().width < vw && r < 30;
    r++
  ) {
    first.insertAdjacentHTML('beforeend', html);
  }

  const second = first.cloneNode(true);
  second.setAttribute('aria-hidden', 'true');

  track.appendChild(second);

  const width = first.getBoundingClientRect().width;

  track.style.setProperty(
    '--dur',
    (width / +$('#speed').value) + 's'
  );

  void track.offsetWidth;
  track.style.animation = '';
}

const rebuildSoon = debounce(buildTicker, 350);

/* ---------- input ---------- */

const parseBlocks = text =>
  text.split(/^\s*-{3,}\s*$/m)
    .map(s => s.trim())
    .filter(Boolean);

function setStatus(msg, err) {
  const s = $('#status');
  s.textContent = msg;
  s.classList.toggle('err', !!err);
}

$('#file').addEventListener('change', async e => {
  const parts = [];

  for (const f of e.target.files) {
    const raw = await f.text();

    if (f.name.endsWith('.json')) {
      try {
        const arr = JSON.parse(raw);

        (Array.isArray(arr) ? arr : [arr]).forEach(x => {
          parts.push(
            typeof x === 'string'
              ? x
              : (x.text || x.body || x.announcement || '')
          );
        });
      } catch {
        setStatus(`${f.name} is not valid JSON`, true);
      }
    } else {
      parts.push(raw);
    }
  }

  const box = $('#paste');

  box.value = [
    box.value.trim(),
    ...parts.map(p => p.trim())
  ].filter(Boolean).join('\n---\n');

  e.target.value = '';

  setStatus(
    `${parseBlocks(box.value).length} announcement(s) ready`
  );
});

$('#sample').addEventListener('click', async () => {
  try {
    const response = await fetch('samples.txt');

    if (!response.ok) {
      throw new Error('Could not load sample announcements.');
    }

    $('#paste').value = await response.text();

    setStatus(
      `${parseBlocks($('#paste').value).length} sample announcements loaded`
    );
  } catch (err) {
    setStatus(err.message, true);
  }
});

$('#generate').addEventListener('click', async () => {
  const blocks = parseBlocks($('#paste').value);

  if (!blocks.length) {
    return setStatus(
      'Paste at least one announcement first.',
      true
    );
  }

  if (blocks.length > 50) {
    return setStatus(
      `${blocks.length} announcements is too many; the limit is 50 per batch.`,
      true
    );
  }

  const long = blocks.findIndex(b => b.length > 8000);

  if (long >= 0) {
    return setStatus(
      `Announcement #${long + 1} is too long. The limit is 8000 characters.`,
      true
    );
  }

  const btn = $('#generate');

  btn.disabled = true;
  setStatus(`Generating ${blocks.length} ticker(s)…`);

  try {
    const payload = blocks.map(text => ({
      id: 'a' + (++seq),
      text
    }));

    const res = await fetch('/api/generate', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        announcements: payload
      })
    });

    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.error || 'Request failed');
    }

    data.items.forEach(r => {
      items.push({
        id: r.id,
        source: r.source,
        ticker: r.ticker,
        generated: r.ticker,
        alternatives: r.alternatives || [],
        flags: r.flags || [],
        approved: false,
        undo: [],
        prev: r.ticker,
        validating: false,
        vseq: 0
      });
    });

    $('#paste').value = '';

    const rej = (data.rejected || [])
      .map(r => `#${r.index}: ${r.reason}`)
      .join('; ');

    setStatus(
      `Added ${data.items.length} ticker(s).` +
      (rej ? ` Rejected: ${rej}` : ''),
      !!rej
    );

    render();

  } catch (err) {
    setStatus(err.message, true);
  } finally {
    btn.disabled = false;
  }
});

/* ---------- editing and validation ---------- */

async function validateNow(it) {
  const currentSeq = ++it.vseq;

  it.validating = true;

  refreshMeta(it);
  updateCounts();

  try {
    const response = await fetch('/api/check', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        source: it.source,
        ticker: it.ticker
      })
    });

    if (!response.ok) {
      throw new Error('Validation failed');
    }

    const r = await response.json();

    if (!Array.isArray(r.flags)) {
      throw new Error('Invalid validation response');
    }

    if (currentSeq !== it.vseq) return;

    it.flags = r.flags;

  } catch {
    if (currentSeq === it.vseq) {
      it.flags = [{
        level: 'error',
        code: 'check_failed',
        message: 'Could not validate; is the server running?'
      }];
    }
  }

  if (currentSeq === it.vseq) {
    it.validating = false;

    refreshMeta(it);
    updateCounts();
    buildTicker();
  }
}

/* ---------- independent validation timers ---------- */

const validationTimers = new Map();

function scheduleValidation(it) {
  clearTimeout(validationTimers.get(it.id));

  validationTimers.set(
    it.id,
    setTimeout(() => {
      validationTimers.delete(it.id);
      validateNow(it);
    }, 350)
  );
}

function invalidateTicker(it) {
  clearTimeout(validationTimers.get(it.id));
  validationTimers.delete(it.id);

  it.vseq++;
  it.approved = false;
  it.validating = true;
}

function setTicker(it, text, pushUndo = true) {
  if (pushUndo && it.ticker !== text) {
    it.undo.push(it.ticker);
  }

  if (it.ticker !== text) {
    invalidateTicker(it);
  }

  it.ticker = text;
}

const list = $('#list');

list.addEventListener('input', e => {
  if (!e.target.classList.contains('edit')) return;

  const it = byId(
    e.target.closest('.card').dataset.id
  );

  it.ticker = e.target.value.replace(/\n/g, ' ');

  invalidateTicker(it);

  refreshMeta(it);
  updateCounts();
  scheduleValidation(it);
  rebuildSoon();
});

list.addEventListener('focusin', e => {
  if (!e.target.classList.contains('edit')) return;

  const it = byId(
    e.target.closest('.card').dataset.id
  );

  it.prev = it.ticker;
});

list.addEventListener('change', e => {
  const it = byId(
    e.target.closest('.card')?.dataset.id
  );

  if (!it) return;

  if (e.target.classList.contains('edit')) {
    if (it.prev !== it.ticker) {
      it.undo.push(it.prev);
    }

    refreshMeta(it);

  } else if (e.target.dataset.act === 'approve') {
    if (e.target.checked && !canApprove(it)) {
      e.target.checked = false;
      return;
    }

    if (
      e.target.checked &&
      it.flags.some(f => f.level === 'warn') &&
      !confirm(
        'This ticker has review warnings. Approve anyway?'
      )
    ) {
      e.target.checked = false;
      return;
    }

    it.approved = e.target.checked;

    refreshMeta(it);
    updateCounts();
    buildTicker();
  }
});
/* ---------- ticker action buttons ---------- */

list.addEventListener('click', async e => {
  const btn = e.target.closest('button');

  if (!btn) return;

  const li = btn.closest('.card');
  if (!li) return;

  const it = byId(li.dataset.id);
  if (!it) return;

  const act = btn.dataset.act;
  const idx = items.indexOf(it);

  if (act === 'up' && idx > 0) {
    items.splice(idx - 1, 0, items.splice(idx, 1)[0]);
    render();

  } else if (act === 'down' && idx < items.length - 1) {
    items.splice(idx + 1, 0, items.splice(idx, 1)[0]);
    render();

  } else if (act === 'alt') {
    setTicker(it, btn.dataset.text);

    it.flags = [];

    render();
    validateNow(it);

  } else if (act === 'undo' && it.undo.length) {
    const previous = it.undo.pop();

    invalidateTicker(it);
    it.ticker = previous;

    render();
    validateNow(it);

  } else if (act === 'revert') {
    setTicker(it, it.generated);

    render();
    validateNow(it);

  } else if (act === 'remove') {
    clearTimeout(validationTimers.get(it.id));
    validationTimers.delete(it.id);

    items.splice(idx, 1);

    render();

  } else if (act === 'regen') {
    btn.disabled = true;
    btn.textContent = '…';

    const avoid = [
      it.generated,
      it.ticker,
      ...it.alternatives
    ].filter(Boolean);

    try {
      const response = await fetch('/api/regenerate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          id: it.id,
          text: it.source,
          avoid
        })
      });

      if (!response.ok) {
        throw new Error('Regeneration failed.');
      }

      const r = await response.json();

      if (r.ticker) {
        setTicker(it, r.ticker);

        it.alternatives = r.alternatives || [];
        it.flags = r.flags || [];

        render();
        validateNow(it);

      } else {
        setStatus(
          r.exhausted
            ? 'No other wording available for this announcement.'
            : 'Nothing new to suggest.',
          true
        );

        render();
      }

    } catch (err) {
      setStatus(
        err.message || 'Could not regenerate ticker.',
        true
      );

      render();
    }
  }
});

/* ---------- drag to reorder ---------- */

list.addEventListener('mousedown', e => {
  const c = e.target.closest('.card');

  if (c) {
    c.draggable = !!e.target.closest('[data-grip]');
  }
});

list.addEventListener('dragstart', e => {
  const c = e.target.closest('.card');

  if (!c) return;

  dragId = c.dataset.id;

  c.classList.add('dragging');

  e.dataTransfer.effectAllowed = 'move';
});

list.addEventListener('dragend', () => {
  dragId = null;
  render();
});

list.addEventListener('dragover', e => {
  const c = e.target.closest('.card');

  if (!c || !dragId) return;

  e.preventDefault();

  list.querySelectorAll('.over').forEach(x => {
    x.classList.remove('over');
  });

  c.classList.add('over');
});

list.addEventListener('drop', e => {
  const c = e.target.closest('.card');

  if (!c || !dragId || c.dataset.id === dragId) {
    return;
  }

  e.preventDefault();

  const from = items.findIndex(i => i.id === dragId);

  if (from < 0) return;

  const moved = items.splice(from, 1)[0];

  const targetIndex = items.findIndex(
    i => i.id === c.dataset.id
  );

  if (targetIndex < 0) {
    items.push(moved);
  } else {
    items.splice(targetIndex, 0, moved);
  }

  render();
});

/* ---------- approve all ---------- */

$('#approveAll').addEventListener('click', () => {
  let skipped = 0;

  items.forEach(i => {
    const hasWarning = i.flags.some(
      f => f.level === 'warn'
    );

    if (canApprove(i) && !hasWarning) {
      i.approved = true;
    } else if (!i.approved) {
      skipped++;
    }
  });

  items.forEach(refreshMeta);

  updateCounts();
  buildTicker();

  if (skipped) {
    setStatus(
      `${skipped} ticker(s) skipped: fix warnings/errors or approve them individually after review.`,
      true
    );
  } else {
    setStatus('All eligible tickers approved.');
  }
});

/* ---------- structured JSON export ---------- */

function exportData() {
  const ok = items.filter(
    i => i.approved && canApprove(i)
  );

  return {
    schema_version: '1.0',
    exported_at: new Date().toISOString(),
    max_words: MAX,
    count: ok.length,

    tickers: ok.map((i, n) => ({
      position: n + 1,
      id: i.id,
      ticker: i.ticker.trim(),
      word_count: wc(i.ticker),
      edited: i.ticker.trim() !== i.generated,
      generated_ticker: i.generated,
      source_text: i.source,
      flags: i.flags.map(f => f.code)
    }))
  };
}

/* ---------- validate before export ---------- */

async function validatedExport() {
  const cand = items.filter(i => i.approved);

  if (!cand.length) {
    setStatus(
      'Approve at least one ticker first.',
      true
    );
    return null;
  }

  try {
    const res = await fetch('/api/validate', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        items: cand.map(i => ({
          id: i.id,
          source: i.source,
          ticker: i.ticker
        }))
      })
    });

    if (!res.ok) {
      throw new Error('Export validation failed.');
    }

    const data = await res.json();

    if (!Array.isArray(data.results)) {
      throw new Error('Invalid export validation response.');
    }

    let blocked = 0;

    data.results.forEach(r => {
      const it = byId(r.id);

      if (!it) return;

      it.flags = r.flags || [];

      if (!r.ok) {
        it.approved = false;
        blocked++;
      }
    });

    render();

    if (blocked) {
      setStatus(
        `${blocked} ticker(s) failed validation and were un-approved. Fix them, then export again.`,
        true
      );

      return null;
    }

    return exportData();

  } catch (err) {
    setStatus(
      err.message || 'Could not validate tickers for export.',
      true
    );

    return null;
  }
}

/* ---------- download approved tickers ---------- */

$('#export').addEventListener('click', async () => {
  const d = await validatedExport();

  if (!d) return;

  const a = document.createElement('a');

  const url = URL.createObjectURL(
    new Blob(
      [JSON.stringify(d, null, 2)],
      { type: 'application/json' }
    )
  );

  a.href = url;
  a.download = 'approved-tickers.json';

  document.body.appendChild(a);
  a.click();
  a.remove();

  setTimeout(() => URL.revokeObjectURL(url), 1000);

  setStatus(`Exported ${d.count} ticker(s).`);
});

/* ---------- copy approved tickers ---------- */

$('#copy').addEventListener('click', async () => {
  const d = await validatedExport();

  if (!d) return;

  try {
    await navigator.clipboard.writeText(
      JSON.stringify(d, null, 2)
    );

    setStatus('Approved set copied as JSON.');

  } catch {
    setStatus(
      'Could not copy. Try downloading the JSON instead.',
      true
    );
  }
});

/* ---------- ticker speed and window resize ---------- */

$('#speed').addEventListener('change', buildTicker);

window.addEventListener(
  'resize',
  debounce(buildTicker, 300)
);

/* ---------- initial rendering ---------- */

render();