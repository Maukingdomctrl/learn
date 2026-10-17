/* Mauforge collapsible preview panel.
   - Adds the header and toggle button.
   - Remembers open/collapsed between visits (desktop only).
   - Opens itself when preview content appears (or call mfPreview.open()).
   - Hides collapsed content from keyboard and screen readers. */
(function () {
  var shell = document.querySelector('.mf-shell');
  var panel = shell && shell.querySelector('.mf-preview');
  var body = panel && panel.querySelector('.mf-preview-body');
  if (!panel || !body) return;

  var head = panel.querySelector('.mf-preview-head');
  if (!head) {
    head = document.createElement('div');
    head.className = 'mf-preview-head';
    head.innerHTML = '<span class="mf-preview-title">Preview<span class="mf-preview-count"></span></span>';
    panel.insertBefore(head, body);
  }
  var btn = document.createElement('button');
  btn.type = 'button';
  btn.className = 'mf-toggle';
  btn.innerHTML = '<svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true"><path d="M8 4l6 6-6 6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  head.appendChild(btn);
  if (!panel.id) panel.id = 'mf-preview-panel';
  btn.setAttribute('aria-controls', panel.id);

  var KEY = 'mf-preview-state';
  var phone = window.matchMedia('(max-width: 1023px)').matches;

  function set(state, remember) {
    var open = state !== 'collapsed';
    shell.dataset.preview = open ? 'open' : 'collapsed';
    btn.setAttribute('aria-expanded', String(open));
    btn.setAttribute('aria-label', open ? 'Collapse preview panel' : 'Expand preview panel');
    body.inert = !open;
    if (remember && !phone) {
      try { localStorage.setItem(KEY, shell.dataset.preview); } catch (e) { /* private mode: ignore */ }
    }
  }

  var countEl = head.querySelector('.mf-preview-count');
  function count() {
    var g = body.querySelector('.mf-preview-grid');
    var n = g ? g.children.length : 0;
    if (countEl) countEl.textContent = n ? n + (n === 1 ? ' card' : ' cards') : '';
  }
  count();

  var saved;
  try { saved = localStorage.getItem(KEY); } catch (e) { /* ignore */ }
  set(phone ? 'collapsed' : (saved || 'open'), false);

  head.addEventListener('click', function (e) {
    if (phone && !btn.contains(e.target)) btn.click();
  });
  btn.addEventListener('click', function () {
    set(shell.dataset.preview === 'open' ? 'collapsed' : 'open', true);
  });

  new MutationObserver(function () {
    count();
    if (body.children.length) set('open', false);
  }).observe(body, { childList: true, subtree: true });

  window.mfPreview = {
    open: function () { set('open', true); },
    close: function () { set('collapsed', true); },
    toggle: function () { btn.click(); }
  };
})();
