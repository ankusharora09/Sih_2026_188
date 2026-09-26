/* =========================================================================
   App core — auth gate, hash router, topbar, command palette, toasts,
   health poll, notification popover.
   ========================================================================= */

const App = (() => {
  const $ = (sel, el = document) => el.querySelector(sel);
  const $$ = (sel, el = document) => [...el.querySelectorAll(sel)];

  const state = {
    user: null,
    route: 'dashboard',
    params: [],
    health: null,
    lastActivityId: null,
    notifSeen: true,
  };

  const STAGES = ['preprocessing', 'ocr', 'liveness_detection', 'tampering_detection',
    'face_verification', 'deepfake_detection', 'anomaly_detection', 'risk_engine', 'explanation'];

  /* ---------------- toasts ---------------- */
  function toast(msg, kind = 'info', ms = 4200) {
    const el = document.createElement('div');
    el.className = `toast ${kind}`;
    el.textContent = msg;
    $('#toastZone').appendChild(el);
    setTimeout(() => {
      el.classList.add('leaving');
      el.addEventListener('animationend', () => el.remove(), { once: true });
    }, ms);
  }

  /* ---------------- formatting helpers ---------------- */
  function esc(s) {
    return String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  }
  function fmtTime(iso) {
    if (!iso) return '—';
    const d = new Date(iso.endsWith('Z') || iso.includes('+') ? iso : iso + 'Z');
    return isNaN(d) ? iso : d.toLocaleTimeString('en-GB');
  }
  function fmtDateTime(iso) {
    if (!iso) return '—';
    const d = new Date(iso.endsWith('Z') || iso.includes('+') ? iso : iso + 'Z');
    return isNaN(d) ? iso : d.toLocaleString('en-GB', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit', second: '2-digit' });
  }
  function badge(status) {
    const s = String(status || 'unknown').toLowerCase();
    const map = { review_required: 'uncertain', completed: 'low', matched: 'matched', succeeded: 'success' };
    return `<span class="badge ${esc(map[s] || s)}">${esc(s.replace(/_/g, ' '))}</span>`;
  }
  function shortHash(h) { return h ? `${String(h).slice(0, 10)}…${String(h).slice(-6)}` : '—'; }

  /* ---------------- boot ---------------- */
  async function boot() {
    API.setUnauthorizedHandler(showLogin);
    wireShell();
    wireLogin();

    // Real backend probe decides the "System Operational" line — no faked status.
    try {
      const h = await fetch('/api/v1/health');
      if (!h.ok) throw new Error();
      setLoginStatus('SYSTEM OPERATIONAL · ENCRYPTED SESSION', true);
    } catch (_) {
      setLoginStatus('API UNREACHABLE', false);
    }

    const saved = sessionStorage.getItem('sih_token');
    const savedUser = sessionStorage.getItem('sih_user');
    if (saved && savedUser) {
      try { savedUser && enter(JSON.parse(savedUser)); } catch (_) { showLogin(); }
    } else {
      showLogin();
    }
  }

  function setLoginStatus(txt, ok) {
    $('#lgStatus').textContent = txt;
    $('#lgDot').style.background = ok ? 'var(--green)' : 'var(--red)';
    $('#lgDot').style.boxShadow = `0 0 8px ${ok ? 'var(--green)' : 'var(--red)'}`;
  }

  function showLogin() {
    $('#loginGate').style.display = 'flex';
    $('#app').classList.remove('ready');
    stopPolling();
  }

  function wireLogin() {
    $('#loginForm').addEventListener('submit', async (e) => {
      e.preventDefault();
      const uid = $('#lgUser').value.trim();
      const role = $('#lgRole').value;
      if (!uid) return;
      const btn = $('#lgBtn');
      btn.disabled = true;
      btn.textContent = 'Authenticating…';
      try {
        const resp = await API.devToken(uid, role);
        API.setToken(resp.access_token);
        const user = { id: uid, role };
        sessionStorage.setItem('sih_user', JSON.stringify(user));
        enter(user);
      } catch (err) {
        const el = $('#lgErr');
        el.textContent = err.status === 403
          ? 'Dev token minting is disabled on this deployment. Use officer credentials.'
          : `Authentication failed: ${err.message}`;
        el.classList.add('show');
      } finally {
        btn.disabled = false;
        btn.textContent = 'Authenticate';
      }
    });
  }

  function enter(user) {
    state.user = user;
    $('#loginGate').style.display = 'none';
    $('#app').classList.add('ready');
    $('#ocName').textContent = user.id;
    $('#ocRole').textContent = String(user.role).toUpperCase();
    $('#ocAvatar').textContent = (user.id || '?').slice(0, 2).toUpperCase();
    startPolling();
    if (!location.hash) location.hash = '#/dashboard';
    handleRoute();
  }

  function logout() {
    API.setToken('');
    sessionStorage.removeItem('sih_user');
    state.user = null;
    showLogin();
  }

  /* ---------------- router ---------------- */
  const routes = {}; // filled by views.js: registerRoute(name, render)

  function registerRoute(name, render) { routes[name] = render; }

  function handleRoute() {
    const hash = location.hash.replace(/^#\//, '') || 'dashboard';
    const [name, ...rest] = hash.split('/');
    state.route = name || 'dashboard';
    state.params = rest;
    $$('#sideNav a').forEach(a => a.classList.toggle('active', a.dataset.route === state.route));
    const render = routes[state.route] || routes.dashboard;
    render($('#main'), rest).catch(err => {
      console.error('[view:' + state.route + ']', err);
      window.__viewErr = { route: state.route, stack: err && err.stack };
      $('#main').innerHTML = `
        <div class="empty" style="margin-top:40px">
          <b>Could not load this view</b>
          ${esc(err.message || 'Unknown error')}
          <div style="margin-top:14px"><button class="btn" onclick="location.reload()">Retry</button></div>
        </div>`;
      toast(err.message || 'Failed to load view', 'err');
    });
    $('#notifPop').classList.remove('open');
  }

  /* ---------------- shell wiring ---------------- */
  function wireShell() {
    $('#btnCollapse').addEventListener('click', () => {
      $('#app').classList.toggle('sidebar-collapsed');
      if (window.innerWidth <= 820) $('#sidebar').classList.toggle('open');
    });
    $('#btnSearch').addEventListener('click', () => openPalette());
    $('#btnNotif').addEventListener('click', () => {
      const pop = $('#notifPop');
      pop.classList.toggle('open');
      if (pop.classList.contains('open')) { state.notifSeen = true; $('#notifDot').hidden = true; renderNotifFeed(); }
    });
    document.addEventListener('click', (e) => {
      const pop = $('#notifPop');
      if (pop.classList.contains('open') && !pop.contains(e.target) && e.target.id !== 'btnNotif' && !$('#btnNotif').contains(e.target)) {
        pop.classList.remove('open');
      }
    });
    window.addEventListener('hashchange', handleRoute);
    document.addEventListener('keydown', onKeydown);
    $('#officerChip').addEventListener('dblclick', logout); // hidden quick-logout
  }

  function onKeydown(e) {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
      e.preventDefault();
      $('#paletteVeil').classList.contains('open') ? closePalette() : openPalette();
      return;
    }
    if (e.key === 'Escape') { closePalette(); $('#notifPop').classList.remove('open'); return; }
    if (e.altKey && /^[1-9]$/.test(e.key)) {
      const links = $$('#sideNav a');
      const target = links[parseInt(e.key, 10) - 1];
      if (target) { e.preventDefault(); target.click(); }
      return;
    }
    if (paletteOpen) paletteKeys(e);
  }

  /* ---------------- polling: health + activity (real endpoints) ---------------- */
  let pollTimer = null;
  function startPolling() {
    stopPolling();
    pollHealth(); pollActivity();
    pollTimer = setInterval(() => { pollHealth(); pollActivity(); }, 5000);
  }
  function stopPolling() { if (pollTimer) { clearInterval(pollTimer); pollTimer = null; } }

  async function pollHealth() {
    try {
      state.health = await API.health();
      const statuses = Object.values(state.health).map(s => (s && s.status) || '');
      const pill = $('#sysPill');
      const degraded = statuses.includes('degraded');
      const down = statuses.includes('unavailable') || statuses.includes('failed');
      pill.classList.toggle('degraded', degraded && !down);
      pill.classList.toggle('down', down);
      $('#sysPillTxt').textContent = down ? 'DEGRADED' : degraded ? 'DEGRADED' : 'OPERATIONAL';
    } catch (_) { /* transient */ }
  }

  async function pollActivity() {
    try {
      const events = await API.activity(20);
      const first = events[0];
      const newId = first ? first.timestamp + first.hash : null;
      if (state.lastActivityId !== null && newId !== state.lastActivityId && state.notifSeen) {
        $('#notifDot').hidden = false;
      }
      state.lastActivityId = newId;
      renderNotifFeed(events);
      if (typeof Views !== 'undefined' && Views.onActivity) Views.onActivity(events);
    } catch (_) { /* transient */ }
  }

  function renderNotifFeed(events) {
    const el = $('#notifFeed');
    if (!el) return;
    if (!events || !events.length) {
      el.innerHTML = '<div class="pal-empty">No audit events yet — screen a case to generate activity.</div>';
      return;
    }
    el.innerHTML = events.slice(0, 12).map(ev => `
      <div class="feed-item">
        <time>${fmtTime(ev.timestamp)}</time>
        <div class="fi-body">
          <b>${esc(ev.action.replace(/_/g, ' '))}</b>${ev.case_id ? ` · <span class="mono">${esc(ev.case_id.slice(0, 8))}</span>` : ''}
          <span class="fi-hash" title="audit hash">${esc(shortHash(ev.hash))}</span>
        </div>
      </div>`).join('');
  }

  /* ---------------- command palette ---------------- */
  let paletteOpen = false;
  let palItems = [];
  let palSel = 0;
  let caseCache = null;

  const PAL_COMMANDS = [
    { icon: 'dash', label: 'Go to Dashboard', hint: 'G D', run: () => { location.hash = '#/dashboard'; } },
    { icon: 'case', label: 'Open Cases', hint: 'G C', run: () => { location.hash = '#/cases'; } },
    { icon: 'scan', label: 'Start New Screening', hint: 'G S', run: () => { location.hash = '#/screening'; } },
    { icon: 'graph', label: 'Open Fraud Network', run: () => { location.hash = '#/fraud'; } },
    { icon: 'shield', label: 'View Audit Trail', run: () => { location.hash = '#/audit'; } },
    { icon: 'pulse', label: 'System Health', run: () => { location.hash = '#/health'; } },
    { icon: 'chart', label: 'Analytics', run: () => { location.hash = '#/analytics'; } },
    { icon: 'shield', label: 'Verify Latest Case Audit Chain', run: async () => {
        try {
          const cases = await API.listCases();
          if (!cases.length) return toast('No cases yet', 'warn');
          const last = cases[0];
          const v = await API.verifyChain(last.case_id);
          toast(v.note, v.valid ? 'ok' : 'err');
        } catch (err) { toast(err.message, 'err'); }
      } },
    { icon: 'off', label: 'Sign Out', run: () => logout() },
  ];

  const PAL_ICONS = {
    dash: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="3" width="8" height="8" rx="1.5"/><rect x="13" y="3" width="8" height="5" rx="1.5"/><rect x="13" y="10" width="8" height="11" rx="1.5"/><rect x="3" y="13" width="8" height="8" rx="1.5"/></svg>',
    case: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/></svg>',
    scan: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 8V6a2 2 0 0 1 2-2h2M16 4h2a2 2 0 0 1 2 2v2M20 16v2a2 2 0 0 1-2 2h-2M8 20H6a2 2 0 0 1-2-2v-2M7 12h10"/></svg>',
    graph: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="5" cy="6" r="2.2"/><circle cx="19" cy="6" r="2.2"/><circle cx="12" cy="18" r="2.2"/><path d="M7 7.5 L10.5 16M17 7.5 L13.5 16M7.2 6h9.6"/></svg>',
    shield: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 3 L21 7 v6 c0 5-4 7.5-9 9-5-1.5-9-4-9-9V7z"/></svg>',
    pulse: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M3 12 h4 l2.5-6 4 12 2.5-6 h5"/></svg>',
    chart: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/></svg>',
    off: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M15 12H4m4-4-4 4 4 4"/><path d="M11 5h7a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2h-7"/></svg>',
  };

  async function openPalette(prefill = '') {
    const veil = $('#paletteVeil');
    veil.classList.add('open');
    paletteOpen = true;
    const input = $('#palInput');
    input.value = prefill;
    input.focus();
    // preload case list for search (real data)
    if (!caseCache) {
      try { caseCache = await API.listCases(); } catch (_) { caseCache = []; }
    }
    renderPalette(prefill);
  }
  function closePalette() {
    $('#paletteVeil').classList.remove('open');
    paletteOpen = false;
  }
  function renderPalette(q) {
    const query = (q || '').trim().toLowerCase();
    let items = PAL_COMMANDS.filter(c => c.label.toLowerCase().includes(query))
      .map(c => ({ kind: 'cmd', label: c.label, run: c.run, icon: c.icon || 'dash' }));
    if (query && caseCache) {
      const hits = caseCache.filter(c =>
        c.case_id.toLowerCase().includes(query) ||
        (c.subject_name || '').toLowerCase().includes(query) ||
        (c.status || '').toLowerCase().includes(query)).slice(0, 7);
      items = hits.map(c => ({
        kind: 'case', label: `Case ${c.case_id.slice(0, 8)} · ${c.subject_name || 'unnamed'}`,
        sub: c.status, run: () => { location.hash = `#/case/${c.case_id}`; }, icon: 'case',
      })).concat(items);
    }
    palItems = items;
    palSel = Math.min(palSel, Math.max(0, items.length - 1));
    const list = $('#palList');
    if (!items.length) { list.innerHTML = '<div class="pal-empty">No matching commands or cases</div>'; return; }
    list.innerHTML = items.map((it, i) => `
      <div class="pal-item ${i === palSel ? 'sel' : ''}" data-i="${i}" role="option">
        ${PAL_ICONS[it.icon] || PAL_ICONS.dash}
        <span>${esc(it.label)}</span>
        ${it.kind === 'case' ? '<kbd>CASE</kbd>' : ''}
      </div>`).join('');
    $$('.pal-item', list).forEach(el => {
      el.addEventListener('click', () => { closePalette(); palItems[+el.dataset.i].run(); });
    });
  }
  function paletteKeys(e) {
    if (e.key === 'ArrowDown') { e.preventDefault(); palSel = Math.min(palSel + 1, palItems.length - 1); renderPalette($('#palInput').value); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); palSel = Math.max(palSel - 1, 0); renderPalette($('#palInput').value); }
    else if (e.key === 'Enter') { e.preventDefault(); const it = palItems[palSel]; if (it) { closePalette(); it.run(); } }
  }

  function wirePalette() {
    $('#palInput').addEventListener('input', (e) => { palSel = 0; renderPalette(e.target.value); });
    $('#paletteVeil').addEventListener('click', (e) => { if (e.target === e.currentTarget) closePalette(); });
  }

  /* ---------------- public surface ---------------- */
  document.addEventListener('DOMContentLoaded', () => {
    wirePalette();
    boot();
  });

  return {
    state, STAGES, routes,
    registerRoute, handleRoute, toast,
    esc, fmtTime, fmtDateTime, badge, shortHash,
    openPalette, logout,
    getCaseCache: () => caseCache, refreshCases: async () => { caseCache = await API.listCases(); return caseCache; },
  };
})();
