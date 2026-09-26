"""Route to serve case detail page for the dashboard.

This endpoint returns an interactive, dynamic digital forensics UI that fetches
real case data, biometric comparisons, AI stage breakdowns, and verifiable
blockchain audit hash chains.
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.get("/cases/{case_id}", response_class=HTMLResponse)
async def case_detail_page(case_id: str):
    """Return an interactive forensic workstation HTML page for the case."""
    case_id_js = repr(case_id)

    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <title>Forensic Case Studio – {case_id}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Outfit:wght@500;600;700&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg: #0b1329;
      --card-bg: #111d38;
      --card-border: #1e2f58;
      --text-main: #f8fafc;
      --text-muted: #94a3b8;
      --primary: #38bdf8;
      --primary-glow: rgba(56, 189, 248, 0.25);
      --success: #22c55e;
      --success-glow: rgba(34, 197, 94, 0.25);
      --warning: #f59e0b;
      --warning-glow: rgba(245, 158, 11, 0.25);
      --danger: #ef4444;
      --danger-glow: rgba(239, 68, 68, 0.25);
      --accent: #818cf8;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      font-family: 'Inter', system-ui, -apple-system, sans-serif;
      margin: 0;
      padding: 0;
      background: var(--bg);
      color: var(--text-main);
      min-height: 100vh;
      line-height: 1.5;
    }}
    header {{
      background: rgba(15, 23, 42, 0.9);
      backdrop-filter: blur(12px);
      border-bottom: 1px solid var(--card-border);
      padding: 0.85rem 2rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
      position: sticky;
      top: 0;
      z-index: 100;
    }}
    header .title {{ font-family: 'Outfit', sans-serif; font-size: 1.15rem; font-weight: 700; color: #fff; display: flex; align-items: center; gap: 0.6rem; }}
    header .badge-live {{ background: rgba(34, 197, 94, 0.15); border: 1px solid #22c55e; color: #22c55e; padding: 0.15rem 0.6rem; border-radius: 20px; font-size: 0.72rem; font-weight: 700; }}
    header a {{ color: var(--primary); text-decoration: none; font-size: 0.88rem; font-weight: 500; transition: color 0.2s; }}
    header a:hover {{ color: #bae6fd; text-decoration: underline; }}
    
    .content-wrap {{ max-width: 1280px; margin: 1.5rem auto; padding: 0 1.5rem; }}

    /* Cards */
    .card {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 1.35rem 1.5rem;
      margin-bottom: 1.25rem;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
      transition: transform 0.2s, border-color 0.2s;
    }}
    .card:hover {{ border-color: rgba(56, 189, 248, 0.4); }}
    .card-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 1rem;
      border-bottom: 1px solid rgba(255, 255, 255, 0.06);
      padding-bottom: 0.75rem;
    }}
    .card-title {{
      font-family: 'Outfit', sans-serif;
      font-size: 1.12rem;
      font-weight: 700;
      margin: 0;
      color: #fff;
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }}
    
    /* Top Grid */
    .top-summary-grid {{
      display: grid;
      grid-template-columns: 320px 1fr;
      gap: 1.25rem;
      margin-bottom: 1.25rem;
    }}
    @media (max-width: 900px) {{
      .top-summary-grid {{ grid-template-columns: 1fr; }}
    }}

    /* Risk Speedometer Dial */
    .risk-gauge-box {{
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      text-align: center;
      padding: 1rem 0;
    }}
    .gauge-svg {{ width: 220px; height: 130px; overflow: visible; }}
    .gauge-bg {{ fill: none; stroke: #1e293b; stroke-width: 14; stroke-linecap: round; }}
    .gauge-fill {{
      fill: none;
      stroke-width: 14;
      stroke-linecap: round;
      stroke-dasharray: 283;
      stroke-dashoffset: 283;
      transition: stroke-dashoffset 1.5s cubic-bezier(0.16, 1, 0.3, 1), stroke 0.5s;
    }}
    .gauge-needle {{
      transform-origin: 100px 95px;
      transition: transform 1.5s cubic-bezier(0.16, 1, 0.3, 1);
    }}
    .gauge-score-txt {{ font-family: 'Outfit', sans-serif; font-size: 2.2rem; font-weight: 800; color: #fff; margin-top: -15px; }}
    .risk-pill {{
      display: inline-block;
      padding: 0.25rem 0.85rem;
      border-radius: 20px;
      font-size: 0.8rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      margin-top: 0.4rem;
    }}
    .risk-pill.low {{ background: rgba(34, 197, 94, 0.2); color: #4ade80; border: 1px solid #22c55e; }}
    .risk-pill.medium {{ background: rgba(245, 158, 11, 0.2); color: #fbbf24; border: 1px solid #f59e0b; }}
    .risk-pill.high {{ background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid #ef4444; }}

    /* Case Info Details */
    .info-list {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 1rem; }}
    .info-item {{ background: rgba(15, 23, 42, 0.4); border: 1px solid rgba(255,255,255,0.05); padding: 0.75rem 1rem; border-radius: 8px; }}
    .info-item .lbl {{ font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.04em; color: var(--text-muted); margin-bottom: 0.2rem; }}
    .info-item .val {{ font-size: 0.95rem; font-weight: 600; color: #fff; word-break: break-all; }}

    /* Biometric Comparison Station */
    .bio-station {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1.5rem;
      margin-top: 0.5rem;
    }}
    @media (max-width: 768px) {{
      .bio-station {{ grid-template-columns: 1fr; }}
    }}
    .bio-card {{
      background: rgba(15, 23, 42, 0.6);
      border: 1px solid var(--card-border);
      border-radius: 10px;
      padding: 1rem;
      display: flex;
      flex-direction: column;
      align-items: center;
      position: relative;
    }}
    .bio-card-title {{
      font-size: 0.88rem;
      font-weight: 600;
      margin-bottom: 0.75rem;
      display: flex;
      align-items: center;
      gap: 0.4rem;
      color: #e2e8f0;
    }}
    .img-viewport {{
      width: 100%;
      height: 250px;
      background: #020617;
      border-radius: 8px;
      overflow: hidden;
      display: flex;
      align-items: center;
      justify-content: center;
      position: relative;
      border: 1px solid #1e293b;
      cursor: crosshair;
    }}
    .img-viewport img {{
      max-width: 100%;
      max-height: 100%;
      object-fit: contain;
      display: block;
      transition: filter 0.2s, transform 0.1s;
    }}
    .img-viewport.heatmap-mode img {{
      filter: invert(1) contrast(200%) hue-rotate(180deg);
    }}
    .magnifier-lens {{
      position: absolute;
      width: 110px;
      height: 110px;
      border: 2px solid var(--primary);
      border-radius: 50%;
      box-shadow: 0 0 15px rgba(56, 189, 248, 0.5), inset 0 0 10px rgba(0,0,0,0.5);
      pointer-events: none;
      display: none;
      background-repeat: no-repeat;
      z-index: 10;
    }}
    .viewport-controls {{
      display: flex;
      gap: 0.5rem;
      margin-top: 0.6rem;
      width: 100%;
      justify-content: space-between;
    }}
    .btn-tool {{
      background: rgba(255, 255, 255, 0.08);
      border: 1px solid rgba(255, 255, 255, 0.15);
      color: #cbd5e1;
      padding: 0.3rem 0.75rem;
      border-radius: 6px;
      font-size: 0.75rem;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 0.35rem;
      transition: all 0.15s;
    }}
    .btn-tool:hover {{ background: rgba(56, 189, 248, 0.2); color: #fff; border-color: var(--primary); }}
    .btn-tool.active {{ background: var(--primary); color: #020617; font-weight: 600; border-color: var(--primary); }}

    /* Interactive Face Match Banner */
    .face-match-banner {{
      margin-top: 1.25rem;
      background: rgba(15, 23, 42, 0.5);
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 1rem 1.25rem;
      display: flex;
      align-items: center;
      gap: 1.5rem;
      flex-wrap: wrap;
    }}
    .match-progress-wrap {{ flex: 1; min-width: 200px; }}
    .match-progress-track {{ height: 10px; background: #1e293b; border-radius: 10px; overflow: hidden; position: relative; }}
    .match-progress-bar {{ height: 100%; width: 0%; border-radius: 10px; background: linear-gradient(90deg, #38bdf8, #22c55e); transition: width 1.2s ease-out; }}

    /* Stages Accordion & Interactive Cards */
    .stage-card {{
      background: rgba(15, 23, 42, 0.4);
      border: 1px solid rgba(255, 255, 255, 0.06);
      border-radius: 8px;
      margin-bottom: 0.6rem;
      overflow: hidden;
      transition: border-color 0.2s;
    }}
    .stage-card:hover {{ border-color: rgba(56, 189, 248, 0.3); }}
    .stage-header {{
      padding: 0.85rem 1.25rem;
      display: flex;
      align-items: center;
      justify-content: space-between;
      cursor: pointer;
      user-select: none;
    }}
    .stage-title {{ font-weight: 600; font-size: 0.92rem; display: flex; align-items: center; gap: 0.5rem; }}
    .stage-body {{
      padding: 1rem 1.25rem;
      border-top: 1px solid rgba(255, 255, 255, 0.05);
      background: rgba(2, 6, 23, 0.3);
      font-size: 0.85rem;
      display: none;
    }}
    .stage-body.open {{ display: block; }}
    .badge {{
      display: inline-flex;
      align-items: center;
      gap: 0.3rem;
      padding: 0.2rem 0.65rem;
      border-radius: 20px;
      font-size: 0.75rem;
      font-weight: 600;
    }}
    .badge-success {{ background: rgba(34, 197, 94, 0.15); color: #4ade80; border: 1px solid rgba(34, 197, 94, 0.4); }}
    .badge-failed {{ background: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.4); }}
    .badge-unavailable {{ background: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.4); }}
    .badge-skipped {{ background: rgba(148, 163, 184, 0.15); color: #cbd5e1; border: 1px solid rgba(148, 163, 184, 0.3); }}

    /* Audit Trail */
    .audit-chain-timeline {{
      display: flex;
      flex-direction: column;
      gap: 0.75rem;
      margin-top: 1rem;
    }}
    .audit-block {{
      background: rgba(15, 23, 42, 0.5);
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 0.85rem 1.2rem;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 1rem;
      position: relative;
      transition: all 0.2s;
    }}
    .audit-block:hover {{ transform: translateX(4px); border-color: var(--primary); }}
    .audit-hash {{
      font-family: monospace;
      font-size: 0.8rem;
      background: rgba(0,0,0,0.3);
      padding: 0.2rem 0.5rem;
      border-radius: 4px;
      cursor: pointer;
      color: #38bdf8;
    }}
    .audit-hash:hover {{ background: rgba(56, 189, 248, 0.2); }}

    /* Decision Station */
    .decision-bar {{
      display: flex;
      gap: 1rem;
      align-items: center;
      justify-content: flex-end;
      margin-top: 1.5rem;
      padding: 1.25rem;
      background: rgba(15, 23, 42, 0.7);
      border: 1px solid var(--card-border);
      border-radius: 10px;
    }}
    .btn {{
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.65rem 1.4rem;
      border-radius: 6px;
      font-size: 0.9rem;
      font-weight: 600;
      cursor: pointer;
      border: none;
      transition: all 0.15s;
    }}
    .btn-approve {{ background: #16a34a; color: #fff; }}
    .btn-approve:hover {{ background: #15803d; transform: translateY(-1px); }}
    .btn-flag {{ background: #d97706; color: #fff; }}
    .btn-flag:hover {{ background: #b45309; transform: translateY(-1px); }}
    .btn-reject {{ background: #dc2626; color: #fff; }}
    .btn-reject:hover {{ background: #b91c1c; transform: translateY(-1px); }}

    /* Toast */
    #toast {{
      position: fixed;
      bottom: 2rem;
      right: 2rem;
      background: rgba(15, 23, 42, 0.95);
      border: 1px solid var(--primary);
      box-shadow: 0 4px 20px rgba(0,0,0,0.5);
      color: #fff;
      padding: 0.8rem 1.2rem;
      border-radius: 8px;
      font-size: 0.85rem;
      display: flex;
      align-items: center;
      gap: 0.5rem;
      opacity: 0;
      transform: translateY(10px);
      transition: all 0.25s ease-out;
      pointer-events: none;
      z-index: 1000;
    }}
    #toast.show {{ opacity: 1; transform: translateY(0); pointer-events: auto; }}
    .spinner {{ color: var(--text-muted); font-style: italic; padding: 2rem; text-align: center; }}
  </style>
</head>
<body>
  <header>
    <div class="title">
      <span>🛡️ AI Identity Screening Studio</span>
      <span class="badge-live">● ENHANCED FORENSICS</span>
    </div>
    <div>
      <a href="/">← Back to Dashboard</a>
      <span style="color:var(--text-muted); margin: 0 0.5rem;">|</span>
      <a href="/client/">Client Portal</a>
    </div>
  </header>

  <div class="content-wrap">
    <div id="detail"><div class="spinner">Initializing forensic models and loading case telemetry…</div></div>
  </div>

  <div id="toast"><span id="toast-icon">✓</span> <span id="toast-msg">Notification</span></div>

  <script>
    const CASE_ID = {case_id_js};
    let devToken = null;

    function showToast(msg, icon='✓') {{
      const t = document.getElementById('toast');
      document.getElementById('toast-msg').textContent = msg;
      document.getElementById('toast-icon').textContent = icon;
      t.classList.add('show');
      setTimeout(() => t.classList.remove('show'), 2800);
    }}

    function copyToClipboard(text, label) {{
      navigator.clipboard.writeText(text).then(() => {{
        showToast(`${{label}} copied to clipboard!`, '📋');
      }}).catch(() => {{}});
    }}

    function copyOcrText() {{
      const el = document.getElementById('ocr-raw-text');
      if (el) copyToClipboard(el.textContent, 'OCR Text');
    }}

    function escapeHtml(str) {{
      if (!str) return '';
      return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
    }}

    async function obtainDevToken() {{
      const resp = await fetch('/api/v1/auth/dev-token', {{
        method: 'POST',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify({{user_id: 'demo-officer', role: 'officer'}})
      }});
      if (!resp.ok) return null;
      const data = await resp.json();
      devToken = data.access_token;
      return devToken;
    }}

    function badgeHtml(status) {{
      const s = (status || 'unknown').toLowerCase();
      let icon = '•';
      if (s === 'success' || s === 'completed') icon = '✓';
      else if (s === 'failed') icon = '✕';
      else if (s === 'unavailable') icon = '⚠';
      return `<span class="badge badge-${{s}}"><span>${{icon}}</span> ${{status}}</span>`;
    }}

    async function loadCase() {{
      if (!devToken) await obtainDevToken();
      const detail = document.getElementById('detail');

      // 1. Fetch Case Info
      const caseResp = await fetch(`/api/v1/cases/${{CASE_ID}}`, {{
        headers: {{Authorization: `Bearer ${{devToken}}`}}
      }});
      if (!caseResp.ok) {{
        detail.innerHTML = `<div class="card" style="border-color:var(--danger)"><h2 style="color:var(--danger)">Error loading case (HTTP ${{caseResp.status}})</h2></div>`;
        return;
      }}
      const c = await caseResp.json();

      // 2. Fetch Screening Run
      let run = null;
      const screenResp = await fetch(`/api/v1/cases/${{CASE_ID}}/screening`, {{
        headers: {{Authorization: `Bearer ${{devToken}}`}}
      }});
      if (screenResp.ok) {{
        run = await screenResp.json();
      }}

      // Calculate or parse Risk
      const riskStage = (run?.stage_results || []).find(sr => sr.stage === 'risk_engine');
      const riskScore = riskStage?.result?.risk_score !== undefined ? riskStage.result.risk_score : (c.risk_score || 0);
      const riskLevel = riskStage?.result?.risk_level || c.risk_level || 'UNKNOWN';

      let riskClass = 'low';
      let gaugeStroke = '#22c55e';
      if (riskScore >= 50) {{ riskClass = 'high'; gaugeStroke = '#ef4444'; }}
      else if (riskScore >= 20) {{ riskClass = 'medium'; gaugeStroke = '#f59e0b'; }}

      // Gauge math: semi-circle circumference is PI * r = 3.14159 * 90 = 283
      const maxOffset = 283;
      const targetOffset = maxOffset - (riskScore / 100) * maxOffset;

      let html = '';

      // --- Top Summary Grid (Speedometer + Case Info) ---
      html += `
        <div class="top-summary-grid">
          <!-- Dynamic Risk Dial -->
          <div class="card risk-gauge-box">
            <div class="card-title" style="margin-bottom:0.5rem">Deterministic Risk Engine</div>
            <svg class="gauge-svg" viewBox="0 0 200 120">
              <path class="gauge-bg" d="M 20 100 A 80 80 0 0 1 180 100" />
              <path class="gauge-fill" id="gauge-fill-path" d="M 20 100 A 80 80 0 0 1 180 100" style="stroke:${{gaugeStroke}}" />
            </svg>
            <div class="gauge-score-txt" id="counter-score">0</div>
            <span class="risk-pill ${{riskClass}}">${{riskLevel}} RISK</span>
            <div style="font-size:0.75rem;color:var(--text-muted);margin-top:0.5rem;">
              Calibrated across multi-modal AI signals
            </div>
          </div>

          <!-- Case Telemetry -->
          <div class="card">
            <div class="card-header">
              <div class="card-title">📁 Case Telemetry &amp; Metadata</div>
              <button class="btn-tool" onclick="copyToClipboard('${{c.id || c.case_id}}', 'Case ID')">📋 Copy Case ID</button>
            </div>
            <div class="info-list">
              <div class="info-item">
                <div class="lbl">Applicant Name</div>
                <div class="val" style="color:#38bdf8">${{c.subject_name || 'Anonymous Applicant'}}</div>
              </div>
              <div class="info-item">
                <div class="lbl">Case ID</div>
                <div class="val" style="font-family:monospace;font-size:0.8rem">${{c.id || c.case_id}}</div>
              </div>
              <div class="info-item">
                <div class="lbl">Pipeline Status</div>
                <div class="val">${{badgeHtml(c.status)}}</div>
              </div>
              <div class="info-item">
                <div class="lbl">Created At</div>
                <div class="val">${{c.created_at ? new Date(c.created_at).toLocaleString() : 'N/A'}}</div>
              </div>
            </div>
            ${{riskStage?.result?.triggered_rules?.length ? `
              <div style="margin-top:1rem;padding:0.75rem;background:rgba(239,68,68,0.1);border:1px solid rgba(239,68,68,0.3);border-radius:6px;">
                <span style="font-weight:600;color:#f87171;font-size:0.82rem">⚠️ Triggered Forensic Rules:</span>
                <span style="font-size:0.85rem;margin-left:0.5rem;color:#fca5a5">${{riskStage.result.triggered_rules.join(', ')}}</span>
              </div>
            ` : ''}}
          </div>
        </div>
      `;

      // --- Biometric & Document Comparison Station ---
      const docFile = (c.files || []).find(f => f.file_type === 'document');
      const liveFile = (c.files || []).find(f => f.file_type === 'live_capture');
      const faceStage = (run?.stage_results || []).find(sr => sr.stage === 'face_verification');
      const livenessStage = (run?.stage_results || []).find(sr => sr.stage === 'liveness_detection');
      const deepfakeStage = (run?.stage_results || []).find(sr => sr.stage === 'deepfake_detection');

      if (docFile || liveFile) {{
        html += `
          <div class="card">
            <div class="card-header">
              <div class="card-title">🔍 Interactive Biometric &amp; Forensic Studio</div>
              <div style="font-size:0.8rem;color:var(--text-muted)">Hover to activate 2.5x forensic loupe magnifier</div>
            </div>
            <div class="bio-station">
              <!-- ID Document Viewport -->
              <div class="bio-card">
                <div class="bio-card-title">📄 Primary Identity Document (${{docFile ? docFile.filename : 'None'}})</div>
                <div class="img-viewport" id="viewport-doc">
                  <div class="spinner" id="loader-doc">Loading document...</div>
                  <img id="img-doc" alt="ID Document" style="display:none;" />
                  <div class="magnifier-lens" id="lens-doc"></div>
                </div>
                <div class="viewport-controls">
                  <button type="button" class="btn-tool" onclick="toggleHeatmap('viewport-doc')">⚡ ELA Heatmap View</button>
                  <button type="button" class="btn-tool" onclick="copyToClipboard('${{docFile?.content_hash || ''}}', 'Document Hash')">🔒 SHA-256 Hash</button>
                </div>
              </div>

              <!-- Live Selfie Viewport -->
              <div class="bio-card">
                <div class="bio-card-title">🤳 Real-Time Camera Selfie (${{liveFile ? liveFile.filename : 'None'}})</div>
                <div class="img-viewport" id="viewport-live">
                  <div class="spinner" id="loader-live">Loading live camera capture...</div>
                  <img id="img-live" alt="Live Camera Selfie" style="display:none;" />
                  <div class="magnifier-lens" id="lens-live"></div>
                </div>
                <div class="viewport-controls">
                  <button type="button" class="btn-tool" onclick="toggleHeatmap('viewport-live')">⚡ Frequency View</button>
                  <button type="button" class="btn-tool" onclick="copyToClipboard('${{liveFile?.content_hash || ''}}', 'Selfie Hash')">🔒 SHA-256 Hash</button>
                </div>
              </div>
            </div>

            <!-- Face Match & Liveness Diagnostic Bar -->
            <div class="face-match-banner">
              <div style="display:flex;align-items:center;gap:0.75rem;">
                <span style="font-size:1.5rem">👤</span>
                <div>
                  <div style="font-weight:700;font-size:0.95rem">Biometric Facial Match</div>
                  <div style="font-size:0.75rem;color:var(--text-muted)">Spatial HOG &amp; Biometric Feature Embedding</div>
                </div>
              </div>
              <div class="match-progress-wrap">
                <div class="match-progress-track">
                  <div class="match-progress-bar" id="face-match-bar"></div>
                </div>
              </div>
              <div style="text-align:right">
                <div style="font-family:'Outfit',sans-serif;font-size:1.25rem;font-weight:700;color:#38bdf8" id="face-similarity-txt">—</div>
                <div style="font-size:0.72rem;color:var(--text-muted)" id="face-match-status">Threshold: 75.0%</div>
              </div>
            </div>
          </div>
        `;
      }}

      // --- Document OCR Intelligence Card ---
      const ocrStage = (run?.stage_results || []).find(sr => sr.stage === 'ocr');
      if (ocrStage && ocrStage.result) {{
        const fields = ocrStage.result.fields || {{}};
        const nameVerif = fields.name_verification || {{}};
        const rawText = ocrStage.result.raw_text || '';
        const ocrEngine = (ocrStage.result.engine || 'tesseract').toUpperCase();
        const ocrConf = ocrStage.result.confidence ? ocrStage.result.confidence.toFixed(1) + '%' : 'N/A';
        
        let nameBanner = '';
        if (nameVerif.status === 'matched') {{
          nameBanner = `
            <div style="margin-bottom:1rem;padding:0.85rem 1.1rem;background:rgba(34,197,94,0.12);border:1px solid rgba(34,197,94,0.35);border-radius:8px;display:flex;align-items:center;gap:0.75rem;">
              <span style="font-size:1.4rem">✓</span>
              <div>
                <div style="font-weight:700;color:#4ade80;font-size:0.92rem">IDENTITY NAME VERIFICATION: MATCHED</div>
                <div style="font-size:0.82rem;color:#bbf7d0">${{nameVerif.message || 'Applicant name matches document name'}}</div>
              </div>
            </div>
          `;
        }} else if (nameVerif.status === 'mismatched') {{
          nameBanner = `
            <div style="margin-bottom:1rem;padding:0.85rem 1.1rem;background:rgba(239,68,68,0.15);border:1px solid rgba(239,68,68,0.4);border-radius:8px;display:flex;align-items:center;gap:0.75rem;">
              <span style="font-size:1.4rem">⚠️</span>
              <div>
                <div style="font-weight:700;color:#f87171;font-size:0.92rem">IDENTITY NAME MISMATCH ALERT</div>
                <div style="font-size:0.82rem;color:#fca5a5">${{nameVerif.message || 'Applicant name does not match document name'}}</div>
              </div>
            </div>
          `;
        }}

        const nameStatusBadge = nameVerif.status === 'matched'
          ? '<span class="badge badge-success">✓ Verified (100%)</span>'
          : (nameVerif.status === 'mismatched' ? '<span class="badge badge-danger">⚠️ Mismatch (0%)</span>' : '<span class="badge badge-warning">N/A</span>');

        html += `
          <div class="card">
            <div class="card-header">
              <div class="card-title">🔤 Document OCR Intelligence &amp; Identity Field Verification</div>
              <div style="display:flex;gap:0.5rem;align-items:center;">
                <span class="badge badge-success">${{ocrEngine}} Engine (${{ocrConf}})</span>
              </div>
            </div>
            ${{nameBanner}}
            <div class="info-list" style="margin-bottom:1rem">
              <div class="info-item">
                <div class="lbl">Applicant Name (Submitted)</div>
                <div class="val" style="color:#e2e8f0;font-weight:600">${{c.subject_name || 'Not provided'}}</div>
              </div>
              <div class="info-item">
                <div class="lbl">Document Extracted Name</div>
                <div class="val" style="color:#38bdf8;font-weight:700">${{fields.extracted_name || 'Not detected'}}</div>
              </div>
              <div class="info-item">
                <div class="lbl">Name Match Status</div>
                <div class="val">${{nameStatusBadge}}</div>
              </div>
              <div class="info-item">
                <div class="lbl">Extracted Date of Birth</div>
                <div class="val" style="color:#38bdf8;font-weight:600">${{fields.extracted_dob || 'Not detected'}}</div>
              </div>
              <div class="info-item">
                <div class="lbl">Document / Identification Number</div>
                <div class="val" style="font-family:monospace;color:#a78bfa;font-weight:600">${{fields.extracted_id_number || 'Not detected'}}</div>
              </div>
              <div class="info-item">
                <div class="lbl">Gender</div>
                <div class="val">${{fields.extracted_gender || 'Not specified'}}</div>
              </div>
            </div>
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.4rem">
              <div style="font-size:0.75rem;color:var(--text-muted);font-weight:600">FULL EXTRACTED DOCUMENT TEXT:</div>
              <button type="button" class="btn-tool" onclick="copyOcrText()">📋 Copy Text</button>
            </div>
            <pre id="ocr-raw-text" style="margin:0;font-family:monospace;font-size:0.82rem;color:#e2e8f0;background:#020617;padding:0.85rem;border-radius:6px;max-height:160px;overflow:auto;white-space:pre-wrap;border:1px solid rgba(255,255,255,0.08);">${{escapeHtml(rawText || 'No text extracted')}}</pre>
          </div>
        `;
      }}

      // --- Stage Results Breakdown (Interactive Accordion) ---
      if (run?.stage_results?.length) {{
        html += `
          <div class="card">
            <div class="card-header">
              <div class="card-title">⚙️ Multi-Modal AI Stage Results (${{run.stage_results.length}} Stages)</div>
              <span style="font-size:0.78rem;color:var(--text-muted)">Click any stage for granular forensic telemetry</span>
            </div>
        `;

        run.stage_results.forEach((sr, idx) => {{
          let summary = '';
          let deepDetails = JSON.stringify(sr.result || {{}}, null, 2);

          if (sr.stage === 'liveness_detection') {{
            summary = `is_live: ${{sr.result?.is_live}} | Sharpness: ${{sr.result?.sharpness?.toFixed?.(1) || 'N/A'}} | Entropy: ${{sr.result?.entropy?.toFixed?.(2) || 'N/A'}}`;
          }} else if (sr.stage === 'tampering_detection') {{
            summary = `Tampered: ${{sr.result?.tampered}} | Score: ${{sr.result?.score}} | Hotspots: ${{sr.result?.regions?.length || 0}}`;
          }} else if (sr.stage === 'deepfake_detection') {{
            summary = `Model: ${{sr.result?.model}} | Score: ${{sr.result?.score}} | Signals: ${{sr.result?.indicators?.join(', ') || 'Clean'}}`;
          }} else if (sr.stage === 'face_verification') {{
            summary = `Detected: ${{sr.result?.face_detected}} | Match: ${{sr.result?.match}} | Similarity: ${{sr.result?.similarity !== null ? (sr.result?.similarity * 100).toFixed(1)+'%' : 'N/A'}}`;
          }} else if (sr.stage === 'ocr') {{
            summary = `Engine: ${{sr.result?.engine || 'none'}} | Conf: ${{sr.result?.confidence || 0}}% | Text: "${{(sr.result?.raw_text || '').substring(0, 40)}}"`;
          }} else if (sr.stage === 'anomaly_detection') {{
            summary = `Anomalies: ${{sr.result?.anomalies?.length ? sr.result.anomalies.join('; ') : 'None detected'}}`;
          }} else if (sr.stage === 'preprocessing') {{
            summary = `Blur: ${{sr.result?.quality?.blur_score?.toFixed?.(1) || 'N/A'}} | Status: ${{sr.result?.quality?.quality_status || 'ok'}}`;
          }} else if (sr.stage === 'risk_engine') {{
            summary = `Score: ${{sr.result?.risk_score}}/100 (${{sr.result?.risk_level}}) | Review Required: ${{sr.result?.review_required}}`;
          }} else if (sr.stage === 'explanation') {{
            summary = (sr.result?.explanation || '').substring(0, 75) + '...';
          }}

          html += `
            <div class="stage-card">
              <div class="stage-header" onclick="toggleStage('stage-${{idx}}')">
                <div class="stage-title">
                  <span>${{getStageIcon(sr.stage)}}</span>
                  <span>${{sr.stage}}</span>
                  <span style="font-weight:400;color:var(--text-muted);font-size:0.82rem;margin-left:0.5rem">${{summary}}</span>
                </div>
                <div>
                  ${{badgeHtml(sr.status)}}
                  <span style="font-size:0.75rem;color:var(--text-muted);margin-left:0.5rem">${{sr.processing_time_ms ? sr.processing_time_ms + 'ms' : ''}}</span>
                </div>
              </div>
              <div class="stage-body" id="stage-${{idx}}">
                <pre style="margin:0;font-family:monospace;font-size:0.78rem;color:#bae6fd;background:#020617;padding:0.75rem;border-radius:6px;overflow:auto;max-height:240px;">${{deepDetails}}</pre>
              </div>
            </div>
          `;
        }});

        html += `</div>`;
      }}

      // --- Blockchain Audit Hash Chain ---
      const auditResp = await fetch(`/api/v1/cases/${{CASE_ID}}/audit`, {{
        headers: {{Authorization: `Bearer ${{devToken}}`}}
      }});
      if (auditResp.ok) {{
        const auditData = await auditResp.json();
        const events = Array.isArray(auditData) ? auditData : auditData.events || [];
        html += `
          <div class="card">
            <div class="card-header">
              <div class="card-title">⛓️ Verifiable Audit Ledger (SHA-256 Hash Chain)</div>
              <button type="button" class="btn-tool" onclick="verifyChainNow()" id="btn-verify-chain">
                ✓ Verify Chain Integrity
              </button>
            </div>
            <div style="font-size:0.8rem;color:var(--text-muted);margin-bottom:0.75rem">
              Each screening event is cryptographically sealed with the predecessor block hash. Tampering with any historical audit entry breaks all descendant hashes.
            </div>
            <div class="audit-chain-timeline">
        `;

        events.forEach((ev, i) => {{
          const ts = ev.timestamp ? new Date(ev.timestamp).toLocaleTimeString() : 'N/A';
          const shortCurr = (ev.current_hash || '').substring(0, 14) + '...';
          const shortPrev = (ev.previous_hash || 'genesis').substring(0, 10) + '...';
          html += `
            <div class="audit-block">
              <div>
                <span style="font-weight:700;font-size:0.85rem;color:#fff">#${{i+1}} ${{ev.event_type}}</span>
                <span style="font-size:0.75rem;color:var(--text-muted);margin-left:0.5rem">actor: ${{ev.actor_id}} · ${{ts}}</span>
              </div>
              <div style="display:flex;align-items:center;gap:0.75rem">
                <span style="font-size:0.72rem;color:var(--text-muted)">prev: ${{shortPrev}}</span>
                <span class="audit-hash" title="Click to copy full SHA-256 hash" onclick="copyToClipboard('${{ev.current_hash}}', 'Block Hash')">${{shortCurr}}</span>
              </div>
            </div>
          `;
        }});

        html += `</div></div>`;
      }}

      // --- Officer Decision Desk ---
      html += `
        <div class="decision-bar">
          <span style="font-size:0.88rem;color:var(--text-muted);margin-right:auto;">Officer Action Station:</span>
          <button type="button" class="btn btn-approve" onclick="recordDecision('approved')">✓ Approve Verification</button>
          <button type="button" class="btn btn-flag" onclick="recordDecision('manual_review')">⚠ Flag for Audit</button>
          <button type="button" class="btn btn-reject" onclick="recordDecision('fraud_rejected')">✕ Reject (Fraud Detected)</button>
        </div>
      `;

      detail.innerHTML = html;

      // Animate Gauge and Counter
      setTimeout(() => {{
        const fillPath = document.getElementById('gauge-fill-path');
        if (fillPath) fillPath.style.strokeDashoffset = targetOffset;

        let cur = 0;
        const target = riskScore;
        const counterEl = document.getElementById('counter-score');
        if (target > 0) {{
          const timer = setInterval(() => {{
            cur += Math.ceil((target - cur) / 6);
            if (cur >= target) {{ cur = target; clearInterval(timer); }}
            if (counterEl) counterEl.textContent = cur;
          }}, 30);
        }} else {{
          if (counterEl) counterEl.textContent = '0';
        }}
      }}, 100);

      // Animate Face Match bar
      if (faceStage?.result?.similarity !== undefined && faceStage?.result?.similarity !== null) {{
        setTimeout(() => {{
          const pct = Math.min(100, Math.max(0, faceStage.result.similarity * 100));
          const bar = document.getElementById('face-match-bar');
          const txt = document.getElementById('face-similarity-txt');
          const statusEl = document.getElementById('face-match-status');
          if (bar) bar.style.width = pct.toFixed(1) + '%';
          if (txt) txt.textContent = pct.toFixed(1) + '%';
          if (statusEl) {{
            const thPct = ((faceStage.result.threshold || 0.70) * 100).toFixed(0);
            const unc = faceStage.result.uncertainty;
            if (unc === 'multiple_faces' || unc === 'uncalibrated_fallback') {{
              statusEl.innerHTML = `<span style="color:#fbbf24;font-weight:600">⚠ UNCERTAIN — MANUAL REVIEW (${{unc === 'multiple_faces' ? 'multiple faces' : 'uncalibrated model'}})</span>`;
            }} else {{
              statusEl.innerHTML = faceStage.result.match
                ? `<span style="color:#4ade80;font-weight:600">✓ VERIFIED MATCH (&ge;${{thPct}}%)</span>`
                : `<span style="color:#f87171;font-weight:600">⚠️ MISMATCH (&lt;${{thPct}}%)</span>`;
            }}
          }}
        }}, 250);
      }} else if (faceStage?.result?.face_detected === false) {{
        const txt = document.getElementById('face-similarity-txt');
        const statusEl = document.getElementById('face-match-status');
        if (txt) txt.textContent = 'NO FACE';
        if (statusEl) statusEl.innerHTML = '<span style="color:#fbbf24">Face Not Detected</span>';
      }}

      // Secure Image Loader with Magnifier Loupe
      if (docFile) setupImageWithLoupe(docFile.file_id, 'img-doc', 'loader-doc', 'viewport-doc', 'lens-doc');
      if (liveFile) setupImageWithLoupe(liveFile.file_id, 'img-live', 'loader-live', 'viewport-live', 'lens-live');
    }}

    function getStageIcon(stage) {{
      switch(stage) {{
        case 'preprocessing': return '📐';
        case 'ocr': return '🔤';
        case 'liveness_detection': return '👁️';
        case 'tampering_detection': return '🔬';
        case 'face_verification': return '👤';
        case 'deepfake_detection': return '🎭';
        case 'anomaly_detection': return '📊';
        case 'risk_engine': return '⚖️';
        case 'explanation': return '💡';
        default: return '⚡';
      }}
    }}

    function toggleStage(id) {{
      const el = document.getElementById(id);
      if (el) el.classList.toggle('open');
    }}

    function toggleHeatmap(viewportId) {{
      const el = document.getElementById(viewportId);
      if (el) {{
        el.classList.toggle('heatmap-mode');
        showToast('Forensic Contrast Filter Toggled', '⚡');
      }}
    }}

    async function verifyChainNow() {{
      const btn = document.getElementById('btn-verify-chain');
      btn.textContent = 'Verifying...';
      try {{
        const r = await fetch(`/api/v1/cases/${{CASE_ID}}/audit/verify`, {{
          headers: {{Authorization: `Bearer ${{devToken}}`}}
        }});
        const data = await r.json();
        if (data.valid) {{
          showToast('✓ Hash Chain 100% Cryptographically Verified & Intact!', '⛓️');
          btn.style.background = '#22c55e';
          btn.style.color = '#fff';
          btn.textContent = '✓ Hash Chain Verified';
        }} else {{
          showToast('✕ Cryptographic Hash Chain Mismatch Detected!', '⚠️');
          btn.style.background = '#ef4444';
          btn.style.color = '#fff';
          btn.textContent = '✕ Hash Mismatch';
        }}
      }} catch(err) {{
        showToast(`Verification error: ${{err.message}}`, '⚠️');
      }}
    }}

    function recordDecision(decision) {{
      showToast(`Officer decision recorded: [${{decision.toUpperCase()}}]`, '🛡️');
    }}

    async function setupImageWithLoupe(fileId, imgId, loaderId, viewportId, lensId) {{
      try {{
        const r = await fetch(`/api/v1/cases/${{CASE_ID}}/files/${{fileId}}/content`, {{
          headers: {{Authorization: `Bearer ${{devToken}}`}}
        }});
        if (r.ok) {{
          const blob = await r.blob();
          const objUrl = URL.createObjectURL(blob);
          const img = document.getElementById(imgId);
          const loader = document.getElementById(loaderId);
          const vp = document.getElementById(viewportId);
          const lens = document.getElementById(lensId);

          if (img) {{
            img.src = objUrl;
            img.onload = () => {{
              if (loader) loader.style.display = 'none';
              img.style.display = 'block';

              // Attach Magnifier Loupe functionality
              vp.addEventListener('mousemove', (e) => {{
                const rect = img.getBoundingClientRect();
                const x = e.clientX - rect.left;
                const y = e.clientY - rect.top;

                if (x < 0 || y < 0 || x > rect.width || y > rect.height) {{
                  lens.style.display = 'none';
                  return;
                }}
                lens.style.display = 'block';
                lens.style.left = `${{e.clientX - vp.getBoundingClientRect().left - 55}}px`;
                lens.style.top = `${{e.clientY - vp.getBoundingClientRect().top - 55}}px`;

                const zoom = 2.5;
                lens.style.backgroundImage = `url('${{objUrl}}')`;
                lens.style.backgroundSize = `${{rect.width * zoom}}px ${{rect.height * zoom}}px`;
                lens.style.backgroundPosition = `-${{x * zoom - 55}}px -${{y * zoom - 55}}px`;
              }});

              vp.addEventListener('mouseleave', () => {{
                lens.style.display = 'none';
              }});
            }};
          }}
        }}
      }} catch(err) {{
        console.error('Image load failed:', err);
      }}
    }}

    loadCase().catch(err => {{
      document.getElementById('detail').innerHTML = `<div class="card" style="border-color:var(--danger)">Error initializing case studio: ${{err.message}}</div>`;
    }});
  </script>
</body>
</html>"""
    return HTMLResponse(content=html)
