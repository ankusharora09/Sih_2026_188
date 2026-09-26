/* =========================================================================
   Views — dashboard, cases, screening, case investigation, fraud graph,
   analytics, audit, health, settings. Every value rendered comes from a
   real backend response; loading and empty states are explicit.
   ========================================================================= */

const Views = (() => {
  const $ = (sel, el = document) => el.querySelector(sel);
  const $$ = (sel, el = document) => [...el.querySelectorAll(sel)];
  const { esc, badge, fmtTime, fmtDateTime, shortHash, STAGES } = App;
  const I = {
    ok: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4"><path d="m5 12.5 4.5 4.5L19 7.5"/></svg>',
    warn: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M12 5v9M12 18.2v.3"/></svg>',
    bad: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4"><path d="M6 6l12 12M18 6 6 18"/></svg>',
    na: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M6 12h12"/></svg>',
  };
  const REGISTERED = [];
  function route(name, fn) { App.registerRoute(name, fn); REGISTERED.push(name); }

  /* =====================================================================
     DASHBOARD
     ===================================================================== */
  function animateCounter(el, target, { suffix = '' } = {}) {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) { el.textContent = target + suffix; return; }
    const dur = 800, t0 = performance.now(), from = 0;
    function tick(t) {
      const p = Math.min(1, (t - t0) / dur);
      const eased = 1 - Math.pow(1 - p, 3);
      el.textContent = Math.round(from + (target - from) * eased).toLocaleString() + suffix;
      if (p < 1) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
  }

  async function dashboard(main) {
    main.innerHTML = `
      <div class="crumbs"><span>OVERVIEW</span><span class="sep">/</span><span class="here">Dashboard</span></div>
      <div class="page-head">
        <div><h2>Identity Screening Command Center</h2>
          <div class="sub">Real-time fraud screening posture across all identity submissions. Live data from the screening pipeline and audit chain.</div></div>
        <div class="page-actions">
          <button class="btn" id="dashNewCase">＋ New Case</button>
          <button class="btn btn-primary" id="dashScreen">Start Screening</button>
        </div>
      </div>
      <div class="kpis" id="kpis">${'<div class="kpi"><div class="lbl">—</div><div class="val"><div class="skeleton" style="width:64px;height:26px"></div></div></div>'.repeat(6)}</div>
      <div class="grid" style="grid-template-columns: 1.15fr 1fr;">
        <div class="card hoverable">
          <div class="card-head"><h3>Risk Distribution</h3><span class="hint" id="distWindow">30 DAYS</span></div>
          <div class="segbar" id="distSeg"></div>
          <div id="distRows"></div>
          <div class="legend" style="margin-top:14px">
            <span><i style="background:var(--green)"></i>LOW</span>
            <span><i style="background:var(--amber)"></i>MEDIUM</span>
            <span><i style="background:var(--red)"></i>HIGH</span>
            <span><i style="background:var(--purple)"></i>REVIEW REQUIRED</span>
          </div>
        </div>
        <div class="card hoverable">
          <div class="card-head"><h3>Live Activity</h3><span class="hint">REAL AUDIT EVENTS · 5s REFRESH</span></div>
          <div class="feed" id="dashFeed"><div class="skeleton" style="height:200px"></div></div>
        </div>
      </div>
      <div class="grid" style="grid-template-columns: 1fr 1.15fr; margin-top:16px;">
        <div class="card hoverable">
          <div class="card-head"><h3>Screening Volume</h3><span class="hint" id="volWindow">DAILY · 30D</span></div>
          <div class="spark" id="volSpark"><div class="skeleton" style="height:70px;width:100%"></div></div>
        </div>
        <div class="card hoverable">
          <div class="card-head"><h3>Stage Latency</h3><span class="hint">AVG MS · REAL TIMINGS</span></div>
          <div id="latList"><div class="skeleton" style="height:150px"></div></div>
        </div>
      </div>`;

    $('#dashScreen').addEventListener('click', () => { location.hash = '#/screening'; });
    $('#dashNewCase').addEventListener('click', () => { location.hash = '#/cases'; setTimeout(() => Views.focusNewCase?.(), 60); });

    const [analytics, activity] = await Promise.all([API.analytics(30), API.activity(20)]);
    renderKpis(analytics, activity);
    renderDistribution(analytics.risk_distribution || {});
    renderVolume(analytics.daily_volume || []);
    renderLatency(analytics.avg_stage_latency_ms || {});
    renderFeed($('#dashFeed'), activity);
    Views.onActivity = (evs) => { renderFeed($('#dashFeed'), evs, true); };
  }

  function renderKpis(an, activity) {
    const dist = an.risk_distribution || {};
    const screened = an.screened_runs ?? 0;
    const avgS = an.average_screening_seconds;
    const avg = avgS != null ? (avgS >= 10 ? `${Math.round(avgS)}s` : `${avgS}s`) : '—';
    const kpis = [
      { lbl: 'TOTAL CASES', val: an.total_cases ?? 0, cls: '' },
      { lbl: 'REVIEW REQUIRED', val: dist.review_required ?? 0, cls: 'p' },
      { lbl: 'HIGH RISK', val: dist.high ?? 0, cls: 'r' },
      { lbl: 'MEDIUM', val: dist.medium ?? 0, cls: 'a' },
      { lbl: 'VERIFIED (LOW)', val: dist.low ?? 0, cls: 'g' },
      { lbl: 'AVG SCREENING', val: avg, cls: '', raw: true, delta: `${screened} runs scored` },
    ];
    $('#kpis').innerHTML = kpis.map(k => `
      <div class="kpi ${k.cls}">
        <div class="lbl">${k.lbl}</div>
        <div class="val" data-raw="${k.raw ? esc(String(k.val)) : ''}">${k.raw ? esc(String(k.val)) : '0'}</div>
        ${k.delta ? `<div class="delta">${esc(k.delta)}</div>` : ''}
      </div>`).join('');
    $$('#kpis .kpi').forEach((el, i) => {
      if (!kpis[i].raw) animateCounter(el.querySelector('.val'), kpis[i].val || 0);
    });
  }

  function renderDistribution(dist, root = document) {
    const seg = root.querySelector('#distSeg'), rows = root.querySelector('#distRows');
    if (!rows) return;
    const order = [['low', 'bar-low', 'LOW'], ['medium', 'bar-medium', 'MEDIUM'], ['high', 'bar-high', 'HIGH'], ['review_required', 'bar-review', 'REVIEW']];
    const total = Object.values(dist).reduce((a, b) => a + (b || 0), 0) || 1;
    if (seg) seg.innerHTML = order.map(([k]) =>
      `<i class="bar-${k}" style="width:${((dist[k] || 0) / total * 100).toFixed(1)}%"></i>`).join('');
    rows.innerHTML = order.map(([k, barCls, label]) => `
      <div class="dist-row">
        <span class="name">${label}</span>
        <span class="bar ${barCls}"><i data-w="${((dist[k] || 0) / total * 100).toFixed(1)}"></i></span>
        <span class="n">${dist[k] || 0}</span>
      </div>`).join('');
    requestAnimationFrame(() =>
      root.querySelectorAll('#distRows .bar i').forEach(b => { b.style.width = b.dataset.w + '%'; }));
  }

  function renderVolume(daily) {
    const el = $('#volSpark');
    if (!daily.length) { el.innerHTML = '<div class="empty" style="padding:22px"><b>No screenings yet</b>Run a screening to populate volume.</div>'; return; }
    const max = Math.max(...daily.map(d => d.cases), 1);
    const recent = daily.slice(-24);
    el.innerHTML = recent.map(d =>
      `<div class="col" style="height:${Math.max(4, d.cases / max * 100).toFixed(0)}%" title="${esc(d.date)} · ${d.cases} case(s)"><span class="tip">${esc(d.date)} · ${d.cases}</span></div>`).join('');
  }

  function renderLatency(lat, root = document) {
    const list = root.querySelector('#latList');
    if (!list) return;
    const keys = Object.keys(lat);
    if (!keys.length) { list.innerHTML = '<div class="empty" style="padding:20px"><b>No timing data</b>Timings appear after the first screening run.</div>'; return; }
    const max = Math.max(...keys.map(k => lat[k]), 1);
    list.innerHTML = keys.slice(0, 8).map(k => `
      <div class="dist-row" style="grid-template-columns:150px 1fr 64px">
        <span class="name">${esc(k.replace(/_/g, ' '))}</span>
        <span class="bar" style="height:7px"><i style="width:${(lat[k] / max * 100).toFixed(1)}%;background:var(--cyan)"></i></span>
        <span class="n">${lat[k]}ms</span>
      </div>`).join('');
  }

  function renderFeed(el, events, animateNew = false) {
    if (!el) return;
    if (!events || !events.length) {
      el.innerHTML = '<div class="empty" style="padding:26px"><b>No activity yet</b>Audit events appear here in real time.</div>';
      return;
    }
    el.innerHTML = events.slice(0, 14).map((ev, i) => `
      <div class="feed-item" style="${animateNew && i === 0 ? 'animation:feedIn .5s both' : ''}">
        <time>${fmtTime(ev.timestamp)}</time>
        <div class="fi-body">
          <b>${esc(ev.action.replace(/_/g, ' '))}</b>${ev.case_id ? ` · case <span class="mono">${esc(ev.case_id.slice(0, 8))}</span>` : ''}
          ${ev.actor_id ? `<span class="fi-hash">by ${esc(ev.actor_id)} · ${esc(shortHash(ev.hash))}</span>` : ''}
        </div>
      </div>`).join('');
  }

  /* =====================================================================
     CASES
     ===================================================================== */
  let casesCache = null;
  async function casesView(main) {
    main.innerHTML = `
      <div class="crumbs"><span>OPERATIONS</span><span class="sep">/</span><span class="here">Cases</span></div>
      <div class="page-head">
        <div><h2>Case Register</h2><div class="sub">All identity screening cases. Click a row to open the investigation workspace.</div></div>
        <div class="page-actions"><button class="btn btn-primary" id="btnNewCase">＋ New Case</button></div>
      </div>
      <div class="filterbar">
        <input id="fSearch" placeholder="Filter by case / subject…" style="min-width:220px">
        <select id="fStatus"><option value="">All statuses</option><option>queued</option><option>screening</option><option>completed</option><option>review_required</option><option>failed</option></select>
        <span class="hint dim3" id="caseCount"></span>
      </div>
      <div class="card" style="padding:8px 6px"><div id="casesTable"><div class="skeleton" style="height:180px"></div></div></div>
      <div class="card section-gap" id="newCaseCard" hidden>
        <div class="card-head"><h3>New Case</h3></div>
        <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap">
          <input id="ncName" placeholder="Subject name (optional)" style="flex:1;min-width:220px;background:var(--bg-raise);border:1px solid var(--line);border-radius:8px;color:var(--ink);padding:9px 12px">
          <button class="btn btn-primary" id="ncCreate">Create Case</button>
        </div>
        <div class="sub dim3" style="margin-top:8px;font-size:12px">A case groups documents, screening runs and audit events for one identity submission.</div>
      </div>`;

    $('#btnNewCase').addEventListener('click', () => {
      const c = $('#newCaseCard'); c.hidden = !c.hidden;
      if (!c.hidden) $('#ncName').focus();
    });
    $('#ncCreate').addEventListener('click', async () => {
      try {
        const c = await API.createCase($('#ncName').value.trim() || null);
        App.toast(`Case ${c.case_id.slice(0, 8)} created`, 'ok');
        casesCache = null; App.refreshCases();
        location.hash = `#/case/${c.case_id}`;
      } catch (e) { App.toast(e.message, 'err'); }
    });
    $('#fSearch').addEventListener('input', renderCaseRows);
    $('#fStatus').addEventListener('change', renderCaseRows);

    if (!casesCache) casesCache = await API.listCases();
    App.refreshCases().then(c => { casesCache = c; renderCaseRows(); });
    renderCaseRows();
    function renderCaseRows() {
      const q = ($('#fSearch').value || '').toLowerCase();
      const st = $('#fStatus').value;
      const rows = casesCache.filter(c =>
        (!q || c.case_id.toLowerCase().includes(q) || (c.subject_name || '').toLowerCase().includes(q)) &&
        (!st || c.status === st));
      $('#caseCount').textContent = `${rows.length} of ${casesCache.length}`;
      if (!rows.length) { $('#casesTable').innerHTML = '<div class="empty" style="margin:10px"><b>No cases match</b>Adjust filters or create a new case.</div>'; return; }
      $('#casesTable').innerHTML = `
        <table class="tbl"><thead><tr>
          <th>Case</th><th>Subject</th><th>Status</th><th>Files</th><th>Created</th></tr></thead>
          <tbody>${rows.map(c => `
            <tr data-id="${esc(c.case_id)}">
              <td class="mono">${esc(c.case_id.slice(0, 8))}…</td>
              <td>${esc(c.subject_name || '—')}</td>
              <td>${badge(c.status)}</td>
              <td class="mono dim">${(c.files || []).length}</td>
              <td class="mono dim">${fmtDateTime(c.created_at)}</td>
            </tr>`).join('')}</tbody></table>`;
      $$('#casesTable tbody tr').forEach(tr =>
        tr.addEventListener('click', () => { location.hash = `#/case/${tr.dataset.id}`; }));
    }
  }
  function focusNewCase() { const c = $('#newCaseCard'); if (c) { c.hidden = false; $('#ncName')?.focus(); } }

  /* =====================================================================
     SCREENING WORKSPACE
     ===================================================================== */
  let screenSession = null; // { caseId, fileId, fileName }

  async function screeningView(main) {
    main.innerHTML = `
      <div class="crumbs"><span>OPERATIONS</span><span class="sep">/</span><span class="here">Screening</span></div>
      <div class="page-head">
        <div><h2>Screening Workspace</h2>
          <div class="sub">Upload a document, enqueue the AI pipeline, and watch each real stage as the backend reports it.</div></div>
      </div>
      <div class="grid" style="grid-template-columns: 340px 1fr;">
        <div style="display:flex;flex-direction:column;gap:16px">
          <div class="card">
            <div class="card-head"><h3>Document Input</h3></div>
            <div class="dropzone" id="dz" role="button" tabindex="0" aria-label="Upload document">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M12 16V5m0 0-4 4m4-4 4 4"/><path d="M4 15v3a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-3"/></svg>
              <b>Drop document here</b><span>or click to browse · JPEG / PNG / PDF</span>
              <input type="file" id="fileInput" accept=".jpg,.jpeg,.png,.pdf,.tif,.tiff" hidden>
            </div>
            <div class="filemeta" id="fileMeta" hidden></div>
            <div style="display:flex;gap:10px;margin-top:16px">
              <input id="scrSubject" placeholder="Applicant name (optional)" style="flex:1;min-width:0;background:var(--bg-raise);border:1px solid var(--line);border-radius:8px;color:var(--ink);padding:9px 12px">
              <button class="btn" id="scrCreate" title="Create a new case for this document">New case</button>
            </div>
            <button class="btn btn-primary btn-block" id="btnBegin" disabled style="margin-top:12px">Begin Screening</button>
            <div class="sub dim3" style="font-size:11.5px;margin-top:9px" id="scrHint">Select a case below or create one, then upload.</div>
          </div>
          <div class="card">
            <div class="card-head"><h3>Existing Cases</h3><span class="hint">CLICK TO TARGET</span></div>
            <div id="scrCases" style="max-height:230px;overflow:auto"><div class="skeleton" style="height:60px"></div></div>
          </div>
        </div>
        <div style="display:flex;flex-direction:column;gap:16px">
          <div class="card">
            <div class="card-head"><h3>Processing Pipeline</h3><span class="hint" id="pipeHint">IDLE</span></div>
            <div class="grid" style="grid-template-columns: 200px 1fr; gap:18px">
              <div class="scanwrap" id="scanwrap">
                <div id="scanPreview" style="padding:26px 14px;text-align:center;color:var(--ink-3);font:500 12px var(--font-mono)">NO DOCUMENT</div>
                <div class="scanline"></div>
              </div>
              <div class="pipe" id="pipe">${STAGES.map((s, i) => `
                <div class="pipe-step waiting" data-stage="${s}">
                  <div class="node"><span class="spin-ring" hidden></span><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><path d="m5 12.5 4.5 4.5L19 7.5"/></svg></div>
                  <div class="ps-head"><span class="ps-name">${s.replace(/_/g, ' ')}</span><span class="ps-status" id="ps-st-${i}"></span><span class="ps-ms" id="ps-ms-${i}"></span></div>
                  <div class="ps-note" id="ps-note-${i}"></div>
                </div>`).join('')}
              </div>
            </div>
          </div>
          <div class="card" id="resultHost" hidden>
            <div class="card-head"><h3>Result</h3><span id="pipeBadges" style="display:flex;gap:8px;flex-wrap:wrap"></span></div>
            <div id="resultBody"></div>
          </div>
        </div>
      </div>`;

    wireScreening(main);
    refreshScreenCases();
  }

  function wireScreening(main) {
    const dz = $('#dz'), fi = $('#fileInput');
    dz.addEventListener('click', () => fi.click());
    dz.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); fi.click(); } });
    ['dragover', 'dragenter'].forEach(ev => dz.addEventListener(ev, (e) => { e.preventDefault(); dz.classList.add('drag'); }));
    ['dragleave', 'drop'].forEach(ev => dz.addEventListener(ev, () => dz.classList.remove('drag')));
    dz.addEventListener('drop', (e) => { e.preventDefault(); if (e.dataTransfer.files[0]) pickFile(e.dataTransfer.files[0]); });
    fi.addEventListener('change', () => { if (fi.files[0]) pickFile(fi.files[0]); });

    $('#scrCreate').addEventListener('click', async () => {
      try {
        const c = await API.createCase($('#scrSubject').value.trim() || null);
        screenSession = { caseId: c.case_id, fileId: null };
        $('#scrHint').textContent = `Case ${c.case_id.slice(0, 8)} created — now upload the document.`;
        App.toast('Case created', 'ok');
        casesCache = null; refreshScreenCases();
      } catch (e) { App.toast(e.message, 'err'); }
    });

    $('#btnBegin').addEventListener('click', beginScreening);
  }

  function pickFile(file) {
    if (!screenSession?.caseId) { App.toast('Create or pick a case first', 'warn'); return; }
    screenSession.file = file;
    const meta = $('#fileMeta');
    meta.hidden = false;
    meta.innerHTML = `<span>${esc(file.name)}</span><span>${(file.size / 1024).toFixed(1)} KB</span><span>${esc(file.type || 'unknown type')}</span>`;
    $('#btnBegin').disabled = false;
    const prev = $('#scanPreview');
    if (file.type.startsWith('image/')) {
      const img = document.createElement('img');
      img.src = URL.createObjectURL(file);
      img.alt = 'Document preview';
      prev.innerHTML = ''; prev.appendChild(img);
    } else {
      prev.innerHTML = 'PDF DOCUMENT<br>READY FOR RASTERIZATION';
    }
    $('#scrHint').textContent = 'Document staged. Press Begin Screening to enqueue the pipeline.';
  }

  async function refreshScreenCases() {
    const el = $('#scrCases');
    try {
      casesCache = await App.refreshCases();
      if (!casesCache.length) { el.innerHTML = '<div class="empty" style="padding:18px"><b>No cases</b>Create one above.</div>'; return; }
      el.innerHTML = casesCache.slice(0, 12).map(c => `
        <div class="factor" data-cid="${esc(c.case_id)}" style="cursor:pointer">
          <span class="f-sig mono">${esc(c.case_id.slice(0, 8))}…<span class="f-reason">${esc(c.subject_name || 'unnamed')} · ${esc(c.status)}</span></span>
          ${badge(c.status)}
        </div>`).join('');
      $$('#scrCases .factor').forEach(r => r.addEventListener('click', () => {
        screenSession = { caseId: r.dataset.cid, fileId: null };
        $('#scrHint').textContent = `Targeting case ${r.dataset.cid.slice(0, 8)}. Upload a document for this case.`;
      }));
    } catch (e) { el.innerHTML = `<div class="empty">${esc(e.message)}</div>`; }
  }

  async function beginScreening() {
    const s = screenSession;
    if (!s?.caseId) return App.toast('Pick or create a case first', 'warn');
    if (!s.file) return App.toast('Upload a document first', 'warn');
    const btn = $('#btnBegin');
    btn.disabled = true; btn.innerHTML = '<span class="spinner"></span> Working…';
    try {
      // upload (201) — real file bytes
      const up = await API.uploadFile(s.caseId, s.file);
      s.fileId = up.file_id;
      // enqueue (202) — pipeline runs on the backend worker
      await API.startScreening(s.caseId);
      $('#pipeHint').textContent = `RUN ${s.caseId.slice(0, 8)} · LIVE`;
      $('#scanwrap').classList.add('scanning');
      App.toast('Screening enqueued (202)', 'ok');
      pollScreening(s.caseId);
    } catch (e) {
      App.toast(e.message, 'err');
      btn.disabled = false; btn.textContent = 'Begin Screening';
    }
  }

  let screenPoll = null;
  function pollScreening(caseId) {
    clearInterval(screenPoll);
    const t0 = Date.now();
    screenPoll = setInterval(async () => {
      try {
        const run = await API.getScreening(caseId);
        updatePipeline(run);
        if (['completed', 'failed'].includes(run.status) || Date.now() - t0 > 240000) {
          clearInterval(screenPoll);
          $('#scanwrap').classList.remove('scanning');
          $('#btnBegin').disabled = false; $('#btnBegin').textContent = 'Begin Screening';
          if (run.status === 'completed') renderRunResult(run);
        }
      } catch (e) {
        clearInterval(screenPoll);
        App.toast(e.message, 'err');
        $('#btnBegin').disabled = false; $('#btnBegin').textContent = 'Begin Screening';
      }
    }, 1500);
  }

  function stageState(sr) {
    if (!sr) return ['waiting', null];
    const s = sr.status;
    if (s === 'success') return ['done', null];
    if (s === 'running') return ['running', null];
    if (s === 'failed') return ['failed', sr.errors || 'stage failed'];
    if (s === 'unavailable') return ['review', 'model unavailable'];
    if (s === 'skipped') return ['review', sr.result?.reason || 'inputs missing'];
    return ['waiting', null];
  }

  function updatePipeline(run) {
    const byStage = Object.fromEntries((run.stage_results || []).map(sr => [sr.stage, sr]));
    STAGES.forEach((st, i) => {
      const el = $(`.pipe-step[data-stage="${st}"]`);
      if (!el) return;
      const [cls, note] = stageState(byStage[st]);
      el.className = `pipe-step ${cls}`;
      const msEl = $(`#ps-ms-${i}`), noteEl = $(`#ps-note-${i}`);
      msEl.textContent = byStage[st]?.processing_time_ms != null ? `${byStage[st].processing_time_ms}ms` : (cls === 'running' ? '…' : '');
      noteEl.textContent = note ? note.slice(0, 120) : '';
      $(`#ps-st-${i}`).innerHTML = byStage[st] ? badge(byStage[st].status) : '';
    });
    $('#pipeHint').textContent = run.status.toUpperCase();
  }

  function renderRunResult(run) {
    const host = $('#resultHost'); host.hidden = false;
    const sr = Object.fromEntries((run.stage_results || []).map(x => [x.stage, x]));
    const risk = sr.risk_engine?.result || {};
    const face = sr.face_verification?.result || {};
    const badges = [];
    if (risk.risk_level) badges.push(badge(risk.risk_level));
    if (sr.tampering_detection?.result?.tampered) badges.push('<span class="badge high">tampering</span>');
    $('#pipeBadges').innerHTML = badges.join(' ');
    const expl = (sr.explanation?.result?.explanation || '').split('\n').filter(Boolean).slice(0, 6);
    $('#resultBody').innerHTML = `
      <div class="gauge-wrap">
        <div class="gauge" id="gauge" style="--p:0;--gauge-c:${gaugeColor(risk.risk_level)}">
          <div class="g-inner"><div class="g-score">${risk.risk_score ?? '—'}</div><div class="g-cap">RISK SCORE</div></div>
        </div>
        <div style="flex:1;min-width:240px">
          ${(risk.contribution_details || []).slice(0, 7).map(d => `
            <div class="factor">
              <span class="f-sig">${esc(String(d.signal).replace(/_/g, ' '))}<span class="f-reason">${esc(d.reason || '')}</span></span>
              <span class="f-plus ${!(d.contribution > 0) ? 'zero' : ''}">+${Math.round((d.contribution || 0) * 100)}</span>
            </div>`).join('')}
        </div>
      </div>
      ${expl.length ? `<div class="section-gap"><div class="card-head"><h3>AI Explanation</h3></div>${expl.map(l => `<div class="dim" style="font-size:12.5px;padding:3px 0">${esc(l.replace(/^- /, ''))}</div>`).join('')}</div>` : ''}
      <div style="margin-top:14px"><button class="btn" onclick="location.hash='#/case/${esc(run.case_id)}'">Open full investigation →</button></div>`;
    requestAnimationFrame(() => { const g = $('#gauge'); if (g) g.style.setProperty('--p', risk.risk_score ?? 0); });
  }

  function gaugeColor(level) {
    return { low: 'var(--green)', medium: 'var(--amber)', high: 'var(--red)', review_required: 'var(--purple)' }[String(level).toLowerCase()] || 'var(--cyan)';
  }

  /* =====================================================================
     CASE INVESTIGATION
     ===================================================================== */
  async function caseView(main, [caseId]) {
    main.innerHTML = `<div class="skeleton" style="height:300px"></div>`;
    const [c, runResp, audit, verify] = await Promise.all([
      API.getCase(caseId), API.getScreening(caseId).catch(() => null),
      API.caseAudit(caseId).catch(() => []), API.verifyChain(caseId).catch(() => null),
    ]);
    const run = runResp; // latest run or null
    const sr = run ? Object.fromEntries((run.stage_results || []).map(x => [x.stage, x])) : {};
    const risk = sr.risk_engine?.result || {};
    const face = sr.face_verification?.result || {};
    const ocr = sr.ocr?.result || {};
    const fields = ocr.fields || {};
    const liveness = sr.liveness_detection?.result || {};
    const tamp = sr.tampering_detection?.result || {};
    const anomaly = sr.anomaly_detection?.result || {};
    const deepfake = sr.deepfake_detection?.result || {};
    const docFile = (c.files || []).find(f => f.file_type !== 'live_capture') || (c.files || [])[0];
    const liveFile = (c.files || []).find(f => f.file_type === 'live_capture');

    // Authorized image loads: <img> cannot send the Bearer header, so fetch blobs.
    async function loadFaceImages() {
      const docPanel = main.querySelector('.face-panel:first-child');
      const livePanel = main.querySelector('.face-panel:last-child');
      if (docFile) {
        try {
          const blob = await API.fileBlob(caseId, docFile.file_id);
          const url = URL.createObjectURL(blob);
          docPanel.innerHTML = `<img src="${url}" alt="Document face" loading="lazy"><span class="fp-tag">DOCUMENT</span>`;
        } catch (_) { docPanel.innerHTML = '<span class="fp-absent">document image unavailable</span>'; }
      }
      if (liveFile) {
        try {
          const blob = await API.fileBlob(caseId, liveFile.file_id);
          const url = URL.createObjectURL(blob);
          livePanel.innerHTML = `<img src="${url}" alt="Submitted face" loading="lazy"><span class="fp-tag">SUBMITTED</span>`;
        } catch (_) { livePanel.innerHTML = '<span class="fp-absent">live capture unavailable</span>'; }
      }
    }

    const riskLevel = String(risk.risk_level || c.status || 'unknown').toUpperCase();
    main.innerHTML = `
      <div class="crumbs"><a href="#/cases">CASES</a><span class="sep">/</span><span class="here mono">${esc(caseId.slice(0, 8))}…</span></div>
      <div class="page-head">
        <div>
          <h2 class="mono">CASE ${esc(caseId.slice(0, 8))}…</h2>
          <div class="sub">${esc(c.subject_name || 'Unnamed subject')} · created ${fmtDateTime(c.created_at)} · <span class="mono">${(c.files || []).length} file(s)</span></div>
        </div>
        <div class="hero-risk">
          ${badge(c.status)}
          <span class="hr-big" style="color:${gaugeColor(risk.risk_level)}">${esc(riskLevel)}</span>
          ${risk.risk_score != null ? `<span class="dim mono">${risk.risk_score}/100</span>` : ''}
        </div>
      </div>

      <div class="grid" style="grid-template-columns:1.25fr 1fr;">
        <!-- FACE VERIFICATION -->
        <div class="card hoverable" style="grid-row:span 2">
          <div class="card-head"><h3>Face Verification</h3><span class="hint">${esc(face.model || '')} ${esc(face.model_version || '')}</span></div>
          <div class="face-duel">
            <div class="face-panel">${docFile ? '<span class="fp-absent">loading document…</span>' : '<span class="fp-absent">no document image</span>'}</div>
            <div class="face-mid">
              <span class="vs">VS</span>
              <div class="verdict-ring ${verdictClass(face)}" id="vr">
                <span class="vr-val" id="vrVal">${face.similarity != null ? (face.similarity * 100).toFixed(1) + '%' : (run ? '—' : '·')}</span>
                <span class="vr-cap">${verdictCap(face)}</span>
              </div>
            </div>
            <div class="face-panel">${liveFile ? '<span class="fp-absent">loading…</span>' : '<span class="fp-absent">no live capture<br><br>upload a \'live_capture\' file to enable face matching</span>'}</div>
          </div>
          <div class="face-metrics">
            <div class="fm"><div class="fml">Match</div><div class="fmv ${face.match === true ? 'good' : face.match === false ? 'bad' : 'warn'}">${face.match == null ? 'UNCERTAIN' : face.match ? 'YES' : 'NO'}</div></div>
            <div class="fm"><div class="fml">Similarity</div><div class="fmv">${face.similarity != null ? (face.similarity * 100).toFixed(1) + '%' : '—'}</div></div>
            <div class="fm"><div class="fml">Threshold</div><div class="fmv">${face.threshold != null ? (face.threshold * 100).toFixed(0) + '%' : '—'}</div></div>
            <div class="fm"><div class="fml">Faces found</div><div class="fmv ${face.uncertainty === 'multiple_faces' ? 'warn' : ''}">${face.faces_count ?? '—'}</div></div>
            <div class="fm"><div class="fml">Uncertainty</div><div class="fmv ${face.uncertainty && face.uncertainty !== 'none' ? 'warn' : ''}">${esc((face.uncertainty || '—').replace(/_/g, ' '))}</div></div>
            <div class="fm"><div class="fml">Latency</div><div class="fmv">${face.processing_time_ms != null ? face.processing_time_ms + 'ms' : '—'}</div></div>
          </div>
          ${(face.signals || []).length ? `<div class="sig-chips">${face.signals.map(s => `<span class="sig-chip">${esc(s)}</span>`).join('')}</div>` : ''}
        </div>

        <!-- RISK -->
        <div class="card hoverable">
          <div class="card-head"><h3>Explainable Risk Score</h3><span class="hint">deterministic weights</span></div>
          <div class="gauge-wrap">
            <div class="gauge" id="cg" style="--p:0;--gauge-c:${gaugeColor(risk.risk_level)}">
              <div class="g-inner"><div class="g-score">${risk.risk_score ?? '—'}</div><div class="g-cap">${esc(riskLevel)}</div></div>
            </div>
            <div style="flex:1;min-width:220px">
              ${(risk.contribution_details || []).map(d => `
                <div class="factor">
                  <span class="f-sig">${esc(String(d.signal).replace(/_/g, ' '))}<span class="f-reason">${esc(d.reason || '')}${d.value != null ? ` · value ${esc(String(d.value))}` : ''}</span></span>
                  <span class="f-plus ${!(d.contribution > 0) ? 'zero' : ''}">+${Math.round((d.contribution || 0) * 100)}</span>
                </div>`).join('') || '<div class="empty" style="padding:16px">No risk computation stored for this case.</div>'}
            </div>
          </div>
        </div>

        <!-- EXTRACTED IDENTITY -->
        <div class="card hoverable">
          <div class="card-head"><h3>Extracted Identity</h3><span class="hint">OCR confidence ${ocr.confidence != null ? Math.round(ocr.confidence * 100) + '%' : '—'}</span></div>
          ${idRow('Name', fields.extracted_name, fields.name_cross_check === 'matched', fields.name_verification?.message)}
          ${idRow('Date of birth', fields.extracted_dob, !!fields.extracted_dob, fields.extracted_dob ? null : 'not found in OCR text')}
          ${idRow('Document number', fields.extracted_id_number, !!fields.extracted_id_number, fields.extracted_id_number ? null : 'not found in OCR text')}
          ${idRow('Gender', fields.extracted_gender, !!fields.extracted_gender, null)}
          ${idRow('Applicant cross-check', fields.name_verification?.status, fields.name_cross_check === 'matched', fields.name_verification?.message)}
        </div>
      </div>

      <div class="grid" style="grid-template-columns:1fr 1fr 1fr; margin-top:16px;">
        <!-- LIVENESS -->
        <div class="card hoverable">
          <div class="card-head"><h3>Liveness</h3><span class="hint">sharpness+entropy heuristic</span></div>
          <div class="tamp-status">
            <span class="tamp-score" style="color:${livenessStatusColor(liveness, sr.liveness_detection)}">${esc(livenessLabel(liveness, sr.liveness_detection))}</span>
          </div>
          <div class="kv">
            <dt>is_live</dt><dd>${liveness.is_live == null ? '—' : liveness.is_live}</dd>
            <dt>sharpness</dt><dd>${liveness.sharpness != null ? Number(liveness.sharpness).toFixed(1) : '—'}</dd>
            <dt>entropy</dt><dd>${liveness.entropy != null ? Number(liveness.entropy).toFixed(2) : '—'}</dd>
          </div>
          <div class="sub dim3" style="font-size:11.5px;margin-top:10px">Detects flat/blank images only. Not presentation-attack detection.</div>
        </div>
        <!-- TAMPERING -->
        <div class="card hoverable">
          <div class="card-head"><h3>Document Tampering</h3><span class="hint">error-level analysis</span></div>
          <div class="tamp-status">
            <span class="tamp-score" style="color:${tamp.tampered === true ? 'var(--red)' : 'var(--green)'}">${tamp.tampered == null ? '—' : tamp.tampered ? 'TAMPERED' : 'CLEAN'}</span>
            ${tamp.score != null ? `<span class="dim mono">score ${Number(tamp.score).toFixed(3)}</span>` : ''}
          </div>
          ${(tamp.signals || []).length ? `<div class="sig-chips" style="margin-top:0">${tamp.signals.map(s => `<span class="sig-chip">${esc(s)}</span>`).join('')}</div>` : '<div class="dim3" style="font-size:12px">No signals recorded.</div>'}
          ${(tamp.regions || []).length ? `
            <div class="tamp-regions section-gap">
              ${tamp.regions.slice(0, 4).map(r => `
                <div class="tamp-region"><span>region @ x${r.x} y${r.y}</span><span class="conf">${r.confidence != null ? (r.confidence * 100).toFixed(0) + '%' : ''}</span></div>`).join('')}
            </div>` : ''}
        </div>
        <!-- DEEPFAKE + ANOMALY -->
        <div class="card hoverable">
          <div class="card-head"><h3>Deepfake & Cross-Case</h3><span class="hint">${esc(deepfake.model || '')}</span></div>
          <div class="kv">
            <dt>deepfake score</dt><dd>${deepfake.score != null ? Number(deepfake.score).toFixed(3) : '—'}</dd>
            <dt>indicators</dt><dd>${(deepfake.indicators || []).length ? deepfake.indicators.map(i => esc(i)).join(', ') : '—'}</dd>
            <dt>anomaly score</dt><dd>${anomaly.score != null ? Number(anomaly.score).toFixed(2) : '—'}</dd>
          </div>
          ${(anomaly.anomalies || []).length ? `
            <div class="sig-chips">${anomaly.anomalies.map(a => `<span class="sig-chip" style="border-color:rgba(251,191,36,.4);color:var(--amber)">${esc(a)}</span>`).join('')}</div>`
            : '<div class="dim3" style="font-size:12px;margin-top:8px">No cross-case signals.</div>'}
        </div>
      </div>

      <div class="grid" style="grid-template-columns:1.2fr 1fr; margin-top:16px;">
        <!-- AI EXPLANATION -->
        <div class="card hoverable">
          <div class="card-head"><h3>AI Analysis</h3><span class="hint">derived from evidence only</span></div>
          ${((sr.explanation?.result?.explanation || '').split('\n').filter(Boolean)).map(l =>
            `<div class="dim" style="font-size:12.5px;padding:3.5px 0;border-bottom:1px solid var(--line-soft)">${esc(l.replace(/^- /, ''))}</div>`).join('') || '<div class="empty" style="padding:16px">No explanation stored.</div>'}
        </div>
        <!-- AUDIT -->
        <div class="card hoverable">
          <div class="card-head"><h3>Integrity & Audit</h3>
            <button class="btn btn-sm" id="btnVerify">VERIFY INTEGRITY</button></div>
          <div id="verifyLine" class="sig-chips" style="margin:0 0 10px">
            ${verify ? `<span class="badge ${verify.valid ? 'low' : 'high'}">${verify.valid ? 'chain intact' : 'chain compromised'}</span>` : ''}
          </div>
          <div class="tline" id="caseTline">${audit.slice(0, 14).map(tlItem).join('') || '<div class="empty" style="padding:14px">No audit events.</div>'}</div>
        </div>
      </div>`;

    requestAnimationFrame(() => { const g = $('#cg'); if (g && risk.risk_score != null) g.style.setProperty('--p', risk.risk_score); });
    loadFaceImages();
    $('#btnVerify')?.addEventListener('click', async () => {
      const line = $('#verifyLine');
      line.innerHTML = '<span class="badge running">verifying…</span>';
      try {
        const v = await API.verifyChain(caseId);
        line.innerHTML = `<span class="badge ${v.valid ? 'low' : 'high'}">${v.valid ? 'INTEGRITY VERIFIED' : 'INTEGRITY COMPROMISED'}</span>`;
        App.toast(v.note, v.valid ? 'ok' : 'err');
      } catch (e) { line.innerHTML = `<span class="badge high">verify failed</span>`; App.toast(e.message, 'err'); }
    });
  }

  function verdictClass(face) {
    if (face.match === true) return 'v-match';
    if (face.match === false) return 'v-mismatch';
    if (face.uncertainty || face.match === null) return 'v-uncertain';
    return 'v-pending';
  }
  function verdictCap(face) {
    if (face.match === true) return 'MATCH';
    if (face.match === false) return 'MISMATCH';
    if (face.uncertainty === 'no_face') return 'NO FACE';
    if (face.uncertainty) return 'UNCERTAIN';
    return 'PENDING';
  }
  function idRow(label, val, ok, note) {
    const ico = val == null || val === '' ? I.na : ok ? I.ok : I.warn;
    const cls = val == null || val === '' ? 'na' : ok ? 'ok' : 'warn';
    return `
      <div class="idfield">
        <div class="idf-ico ${cls}">${ico}</div>
        <div style="min-width:0">
          <div class="idf-lbl">${esc(label)}</div>
          <div class="idf-val">${esc(val == null || val === '' ? 'not available' : String(val))}</div>
          ${note ? `<div class="idf-note">${esc(note)}</div>` : ''}
        </div>
      </div>`;
  }
  function livenessLabel(res, stage) {
    if (stage?.status === 'skipped') return 'SKIPPED';
    if (stage?.status === 'unavailable') return 'UNAVAILABLE';
    if (res.is_live == null) return 'UNKNOWN';
    return res.is_live ? 'LIVE' : 'SPOOF?';
  }
  function livenessStatusColor(res, stage) {
    if (stage?.status === 'skipped' || stage?.status === 'unavailable' || res.is_live == null) return 'var(--ink-3)';
    return res.is_live ? 'var(--green)' : 'var(--red)';
  }
  function tlItem(ev, i = 0) {
    const cls = /fail|error|compromis/.test(ev.event_type) ? 'bad' : /complet|matched|verified|success/.test(ev.event_type) ? 'ok' : '';
    return `
      <div class="tl-item ${cls}">
        <time>${fmtDateTime(ev.timestamp)}</time>
        <div class="tl-act">${esc(ev.event_type.replace(/_/g, ' '))} <span class="dim3 mono" style="font-size:10.5px">· ${esc(ev.actor_id)}</span></div>
        <div class="tl-meta">hash <b>${esc(shortHash(ev.current_hash))}</b> ← prev <b>${esc(shortHash(ev.previous_hash))}</b></div>
      </div>`;
  }

  /* =====================================================================
     IDENTITY INTELLIGENCE (graph)
     ===================================================================== */
  async function graphView(main) {
    main.innerHTML = `
      <div class="crumbs"><span>INTELLIGENCE</span><span class="sep">/</span><span class="here">Identity Intelligence</span></div>
      <div class="page-head"><div><h2>Identity Intelligence Graph</h2>
        <div class="sub">Cases, subjects, documents and extracted ID numbers from real submissions. A shared ID across cases is a <b>repeated identity signal</b> — it requires review, it is not proof of fraud. <span class="hint" id="graphFocus"></span></div></div></div>
      <div class="graph-wrap"><div id="graphHost" style="width:100%;height:100%"><div class="skeleton" style="height:100%"></div></div>
        <div class="glegend">
          <span><i style="background:var(--cyan)"></i>case</span>
          <span><i style="background:var(--green)"></i>person</span>
          <span><i style="background:var(--ink-3)"></i>document</span>
          <span><i style="background:var(--purple)"></i>id number</span>
          <span><i style="background:var(--amber)"></i>reused id edge</span>
        </div>
      </div>`;

    const g = await API.fraudGraph(200);
    let nodes = g.nodes || [], edges = g.edges || [];
    if (!nodes.length) {
      $('#graphHost').innerHTML = '<div class="empty" style="margin:40px"><b>No graph data</b>Create and screen cases to populate the identity graph.</div>';
      return;
    }
    // Focus view: keep the newest cases (+ attached nodes) so the graph stays readable.
    const caseNodes = nodes.filter(n => n.type === 'case');
    const keptCases = new Set(caseNodes.slice(0, 24).map(n => n.id));
    const kept = new Set(keptCases);
    edges.forEach(e => { if (keptCases.has(e.source)) kept.add(e.target); if (keptCases.has(e.target)) kept.add(e.source); });
    nodes = nodes.filter(n => kept.has(n.id));
    edges = edges.filter(e => kept.has(e.source) && kept.has(e.target));
    drawGraph($('#graphHost'), nodes, edges);
    $('#graphFocus').textContent = `${caseNodes.length} cases in DB · showing newest ${Math.min(24, caseNodes.length)} + linked entities`;
  }

  function drawGraph(host, nodes, edges) {
    const W = host.clientWidth || 900, H = host.clientHeight || 480;
    const colors = { case: 'var(--cyan)', person: 'var(--green)', document: 'var(--ink-3)', id_number: 'var(--purple)' };
    // deterministic radial layout by type
    const byType = {};
    nodes.forEach(n => (byType[n.type] = byType[n.type] || []).push(n));
    const pos = {};
    const rings = [['case', 0.58], ['person', 0.86], ['id_number', 1.0], ['document', 1.12]];
    let seed = 42;
    const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
    for (const [type, rr] of rings) {
      const arr = byType[type] || [];
      arr.forEach((n, i) => {
        const ang = (i / Math.max(arr.length, 1)) * Math.PI * 2 + rnd() * 0.35;
        const rad = rr * Math.min(W, H) * 0.40 * (0.82 + rnd() * 0.36);
        pos[n.id] = { x: W / 2 + Math.cos(ang) * rad, y: H / 2 + Math.sin(ang) * rad };
      });
    }
    const known = new Set(nodes.map(n => n.id));
    const E = edges.filter(e => known.has(e.source) && known.has(e.target));
    const svg = `
      <svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Identity graph">
        ${E.map(e => {
          const a = pos[e.source], b = pos[e.target];
          if (!a || !b) return '';
          const mx = (a.x + b.x) / 2, my = (a.y + b.y) / 2;
          return `<path class="gedge ${e.signal ? 'signal' : ''}" d="M${a.x},${a.y} Q${mx},${my - 24} ${b.x},${b.y}"><title>${esc(e.relation)}${e.signal ? ' · ' + esc(e.signal) : ''}</title></path>`;
        }).join('')}
        ${nodes.map(n => {
          const p = pos[n.id]; if (!p) return '';
          const r = n.type === 'case' ? 14 : 9;
          const showLabel = n.type === 'case' || n.type === 'id_number' || n.type === 'person';
          return `<g class="gnode" transform="translate(${p.x},${p.y})">
            <circle r="${r}" fill="${colors[n.type] || 'var(--amber)'}" fill-opacity="0.85" stroke="rgba(232,237,247,0.35)"/>
            ${showLabel ? `<text y="${r + 13}" text-anchor="middle">${esc((n.label || n.id).slice(0, 16))}</text>` : ''}
            <title>${esc(n.type)} · ${esc(n.label || n.id)}${n.status ? ' · ' + esc(n.status) : ''}</title>
          </g>`;
        }).join('')}
      </svg>`;
    host.innerHTML = svg;
  }

  /* =====================================================================
     ANALYTICS
     ===================================================================== */
  async function analyticsView(main) {
    main.innerHTML = `
      <div class="crumbs"><span>OVERVIEW</span><span class="sep">/</span><span class="here">Analytics</span></div>
      <div class="page-head">
        <div><h2>Analytics</h2><div class="sub">Operational metrics computed from real screening rows — no sampled or synthetic data.</div></div>
        <div class="page-actions">
          <select id="anWindow" class="chip-toggle" style="padding:7px 12px"><option value="7">7 days</option><option value="30" selected>30 days</option><option value="90">90 days</option></select>
        </div>
      </div>
      <div class="kpis" id="anKpis"></div>
      <div class="grid" style="grid-template-columns:1fr 1fr;">
        <div class="card hoverable"><div class="card-head"><h3>Risk Mix</h3></div><div id="distRows"></div></div>
        <div class="card hoverable"><div class="card-head"><h3>Daily Volume</h3></div><div class="spark" id="anVol" style="height:120px"></div></div>
      </div>
      <div class="card section-gap"><div class="card-head"><h3>Stage Latency (avg ms)</h3><span class="hint">from stage_results.processing_time_ms</span></div><div id="latList"></div></div>`;

    async function load(days) {
      const an = await API.analytics(days);
      const dist = an.risk_distribution || {};
      $('#anKpis').innerHTML = [
        ['CASES', an.total_cases, ''], ['SCREENED RUNS', an.screened_runs, ''],
        ['AVG RISK', an.average_risk_score ?? '—', 'a'],
        ['AVG DURATION', an.average_screening_seconds != null ? an.average_screening_seconds + 's' : '—', 'p'],
        ['REVIEW REQ.', dist.review_required ?? 0, 'p'], ['HIGH', dist.high ?? 0, 'r'],
      ].map(([l, v, c]) => `<div class="kpi ${c}"><div class="lbl">${l}</div><div class="val">${esc(String(v))}</div></div>`).join('');
      renderDistribution(dist, main);
      const vol = an.daily_volume || [];
      const max = Math.max(...vol.map(d => d.cases), 1);
      $('#anVol').innerHTML = vol.length ? vol.slice(-30).map(d =>
        `<div class="col" style="height:${Math.max(4, d.cases / max * 100)}%" title="${esc(d.date)} · ${d.cases}"><span class="tip">${esc(d.date)} · ${d.cases}</span></div>`).join('')
        : '<div class="empty" style="padding:20px"><b>No data</b></div>';
      renderLatency(an.avg_stage_latency_ms || {}, main);
    }
    $('#anWindow').addEventListener('change', (e) => load(+e.target.value));
    await load(30);
  }

  /* =====================================================================
     AUDIT TRAIL
     ===================================================================== */
  async function auditView(main) {
    main.innerHTML = `
      <div class="crumbs"><span>INTELLIGENCE</span><span class="sep">/</span><span class="here">Audit Trail</span></div>
      <div class="page-head"><div><h2>Global Audit Trail</h2>
        <div class="sub">Every screening event is cryptographically sealed with its predecessor's hash. Verifying the chain detects any historical tampering.</div></div>
        <div class="page-actions"><button class="btn" id="btnGlobalVerify">VERIFY FULL CHAIN</button></div></div>
      <div class="card section-gap" style="padding:8px 6px"><div id="auditList"><div class="skeleton" style="height:220px"></div></div></div>`;
    const events = await API.activity(100);
    $('#auditList').innerHTML = events.length ? `
      <table class="tbl"><thead><tr><th>Time</th><th>Event</th><th>Case</th><th>Actor</th><th>Hash</th></tr></thead>
      <tbody>${events.map(ev => `
        <tr><td class="mono dim">${fmtDateTime(ev.timestamp)}</td>
        <td>${esc(ev.action.replace(/_/g, ' '))}</td>
        <td class="mono dim">${ev.case_id ? esc(ev.case_id.slice(0, 8)) + '…' : '—'}</td>
        <td class="mono dim">${esc(ev.actor_id)}</td>
        <td class="mono-hash">${esc(shortHash(ev.hash))}</td></tr>`).join('')}</tbody></table>`
      : '<div class="empty" style="margin:10px"><b>No audit events</b></div>';
    $('#btnGlobalVerify').addEventListener('click', async () => {
      try {
        const cases = await API.listCases();
        if (!cases.length) return App.toast('No cases to verify', 'warn');
        const v = await API.verifyChain(cases[0].case_id);
        App.toast(v.note, v.valid ? 'ok' : 'err');
      } catch (e) { App.toast(e.message, 'err'); }
    });
  }

  /* =====================================================================
     SYSTEM HEALTH
     ===================================================================== */
  async function healthView(main) {
    main.innerHTML = `
      <div class="crumbs"><span>SYSTEM</span><span class="sep">/</span><span class="here">System Health</span></div>
      <div class="page-head"><div><h2>System Health</h2>
        <div class="sub">Live component status from <span class="mono">/intelligence/health</span>. Degraded entries are honest limitations, not hidden failures.</div></div></div>
      <div class="card"><div id="healthList"><div class="skeleton" style="height:260px"></div></div></div>
      <div class="card section-gap"><div class="card-head"><h3>Stage Latency (avg ms)</h3></div><div id="healthLat"></div></div>`;
    await refreshHealth();
    async function refreshHealth() {
      const [h, an] = await Promise.all([API.health(), API.analytics(7).catch(() => ({}))]);
      const rows = Object.entries(h).map(([name, s]) => {
        const st = (s && s.status) || 'unknown';
        const detail = Object.entries(s || {}).filter(([k]) => k !== 'status')
          .map(([k, v]) => `${k}=${typeof v === 'object' ? JSON.stringify(v) : v}`).join(' · ');
        return `<div class="svc">
          <span class="s-name">${esc(name.replace(/_/g, ' '))}</span>
          <span class="s-detail">${esc(detail || '—')}</span>
          <span>${badge(st)}</span>
        </div>`;
      }).join('');
      $('#healthList').innerHTML = rows || '<div class="empty">No health data.</div>';
      const lat = an.avg_stage_latency_ms || {};
      const keys = Object.keys(lat);
      $('#healthLat').innerHTML = keys.length ? keys.map(k =>
        `<div class="dist-row" style="grid-template-columns:170px 1fr 70px">
          <span class="name">${esc(k.replace(/_/g, ' '))}</span>
          <span class="bar" style="height:7px"><i style="background:var(--cyan);width:${(lat[k] / Math.max(...keys.map(x => lat[x]), 1) * 100).toFixed(1)}%"></i></span>
          <span class="n">${lat[k]}ms</span></div>`).join('')
        : '<div class="empty" style="padding:14px"><b>No timing data yet</b></div>';
    }
    Views.onActivity = null;
  }

  /* =====================================================================
     DOCUMENTS & SETTINGS (lightweight, real data)
     ===================================================================== */
  async function documentsView(main) {
    main.innerHTML = `
      <div class="crumbs"><span>OPERATIONS</span><span class="sep">/</span><span class="here">Documents</span></div>
      <div class="page-head"><div><h2>Document Registry</h2><div class="sub">All uploaded evidence files with their integrity hashes.</div></div></div>
      <div class="card" style="padding:8px 6px" id="docList"><div class="skeleton" style="height:180px"></div></div>`;
    const cases = await API.listCases();
    const rows = [];
    for (const c of cases.slice(0, 30)) {
      for (const f of (c.files || [])) rows.push({ c, f });
    }
    $('#docList').innerHTML = rows.length ? `
      <table class="tbl"><thead><tr><th>File</th><th>Case</th><th>Type</th><th>Size</th><th>SHA-256</th><th>Uploaded</th></tr></thead>
      <tbody>${rows.map(({ c, f }) => `
        <tr style="cursor:default">
          <td>${esc(f.filename)}</td>
          <td class="mono dim"><a href="#/case/${esc(c.case_id)}">${esc(c.case_id.slice(0, 8))}…</a></td>
          <td>${badge({ document: 'neutral', live_capture: 'processing' }[f.file_type] || f.file_type || 'neutral')}</td>
          <td class="mono dim">${f.size_bytes != null ? (f.size_bytes / 1024).toFixed(1) + ' KB' : '—'}</td>
          <td class="mono-hash">${esc((f.content_hash || '').slice(0, 18))}…</td>
          <td class="mono dim">${fmtDateTime(f.uploaded_at)}</td>
        </tr>`).join('')}</tbody></table>`
      : '<div class="empty" style="margin:10px"><b>No documents</b>Upload from the Screening workspace.</div>';
  }

  async function settingsView(main) {
    main.innerHTML = `
      <div class="crumbs"><span>SYSTEM</span><span class="sep">/</span><span class="here">Settings</span></div>
      <div class="page-head"><div><h2>Settings & Session</h2><div class="sub">Session and appearance. Screening thresholds are configured in the backend, deliberately not editable here.</div></div></div>
      <div class="grid" style="grid-template-columns:1fr 1fr;">
        <div class="card"><div class="card-head"><h3>Session</h3></div>
          <div class="kv">
            <dt>officer</dt><dd>${esc(App.state.user?.id || '—')}</dd>
            <dt>role</dt><dd>${esc(App.state.user?.role || '—')}</dd>
            <dt>token</dt><dd class="mono-hash">${esc(shortHash(API.getToken()))}</dd>
          </div>
          <button class="btn btn-danger section-gap" id="btnLogout2">Sign Out</button></div>
        <div class="card"><div class="card-head"><h3>Appearance</h3></div>
          <div class="switch-row"><button class="chip-toggle on">Dark (only mode)</button></div>
          <div class="sub dim3" style="font-size:12px;margin-top:10px">The command-center theme is dark-first for control-room use; light theme is not provided.</div></div>
      </div>`;
    $('#btnLogout2').addEventListener('click', () => App.logout());
  }

  /* ---------------- registration ---------------- */
  route('dashboard', dashboard);
  route('cases', casesView);
  route('screening', screeningView);
  route('case', caseView);
  route('intelligence', graphView);
  route('fraud', graphView);
  route('analytics', analyticsView);
  route('audit', auditView);
  route('health', healthView);
  route('documents', documentsView);
  route('settings', settingsView);

  return { onActivity: null, focusNewCase, dashboard };
})();
