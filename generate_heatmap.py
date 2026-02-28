"""
Reads sector_heatmap_data.json and generates a standalone sector_heatmap.html
No external template file needed — HTML is fully self-contained.
"""

import json, os

# ── Load scan data ──────────────────────────────────────────
if not os.path.exists("sector_heatmap_data.json"):
    print("⚠️  sector_heatmap_data.json not found — skipping heatmap generation")
    exit(0)

with open("sector_heatmap_data.json") as f:
    data = json.load(f)

scan_json = json.dumps(data)

# ── Inject into self-contained HTML ─────────────────────────
html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>NSE Sector Pulse</title>
<link href="https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@400;600;800&display=swap" rel="stylesheet">
<style>
:root{{--bg:#09090f;--surface:#0f0f1a;--border:#1e1e30;--text:#e0e0f0;--muted:#5a5a80;--accent:#7b61ff}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:var(--bg);color:var(--text);font-family:'Syne',sans-serif;min-height:100vh;overflow-x:hidden}}
body::before{{content:'';position:fixed;inset:0;background:repeating-linear-gradient(0deg,transparent,transparent 2px,rgba(0,0,0,.07) 2px,rgba(0,0,0,.07) 4px);pointer-events:none;z-index:9999}}
header{{padding:28px 40px 20px;border-bottom:1px solid var(--border);display:flex;align-items:flex-end;justify-content:space-between;flex-wrap:wrap;gap:12px}}
.logo-area h1{{font-size:2rem;font-weight:800;letter-spacing:-.5px;color:#fff}}
.logo-area h1 span{{color:var(--accent)}}
.logo-area p{{font-family:'Space Mono',monospace;font-size:.65rem;color:var(--muted);margin-top:6px;letter-spacing:2px;text-transform:uppercase}}
.scan-meta{{text-align:right;font-family:'Space Mono',monospace;font-size:.7rem;color:var(--muted);line-height:1.8}}
.pulse{{display:inline-block;width:7px;height:7px;border-radius:50%;background:#23c56e;margin-right:6px;animation:blink 1.4s ease-in-out infinite;vertical-align:middle}}
@keyframes blink{{0%,100%{{opacity:1}}50%{{opacity:.2}}}}
.legend-strip{{display:flex;align-items:center;gap:8px;padding:14px 40px;border-bottom:1px solid var(--border);flex-wrap:wrap}}
.legend-label{{font-family:'Space Mono',monospace;font-size:.6rem;color:var(--muted);letter-spacing:1.5px;text-transform:uppercase;margin-right:4px}}
.legend-bar{{display:flex;gap:3px;align-items:center}}
.legend-swatch{{width:28px;height:14px;border-radius:2px}}
.legend-endpoints{{font-family:'Space Mono',monospace;font-size:.58rem;color:var(--muted);margin:0 4px}}
.metric-tabs{{display:flex;padding:16px 40px 0}}
.tab{{padding:8px 20px;font-family:'Space Mono',monospace;font-size:.65rem;letter-spacing:1.5px;text-transform:uppercase;color:var(--muted);border:1px solid var(--border);border-bottom:none;cursor:pointer;transition:all .2s;background:var(--bg);position:relative;top:1px}}
.tab:first-child{{border-radius:6px 0 0 0}}.tab:last-child{{border-radius:0 6px 0 0}}
.tab.active{{color:var(--text);background:var(--surface);border-color:var(--accent);border-bottom:1px solid var(--surface)}}
.heatmap-wrap{{padding:0 40px 24px;border-top:1px solid var(--accent)}}
.heatmap-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:12px;padding-top:20px}}
.sector-card{{border-radius:10px;border:1px solid var(--border);overflow:hidden;cursor:pointer;transition:transform .18s,box-shadow .18s;position:relative}}
.sector-card:hover{{transform:translateY(-3px);box-shadow:0 8px 32px rgba(0,0,0,.5);z-index:10}}
.card-header{{padding:14px 18px 10px;position:relative}}
.card-header::after{{content:'';position:absolute;bottom:0;left:18px;right:18px;height:1px;background:rgba(255,255,255,.06)}}
.sector-name{{font-size:1rem;font-weight:600;color:#fff}}
.sector-signal{{font-family:'Space Mono',monospace;font-size:.6rem;letter-spacing:2px;text-transform:uppercase;margin-top:2px}}
.score-area{{position:absolute;top:12px;right:16px}}
.score-ring{{width:52px;height:52px;position:relative}}
.score-ring svg{{transform:rotate(-90deg)}}
.score-ring .track{{fill:none;stroke:rgba(255,255,255,.06);stroke-width:5}}
.score-ring .fill{{fill:none;stroke-width:5;stroke-linecap:round;transition:stroke-dashoffset .8s cubic-bezier(.4,0,.2,1)}}
.score-number{{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;font-family:'Space Mono',monospace;font-size:.75rem;font-weight:700;color:#fff}}
.card-body{{padding:12px 18px 14px;display:grid;gap:8px}}
.metric-row{{display:flex;align-items:center;gap:10px}}
.metric-label{{font-family:'Space Mono',monospace;font-size:.55rem;letter-spacing:1px;text-transform:uppercase;color:var(--muted);width:64px;flex-shrink:0}}
.metric-bar-wrap{{flex:1;height:5px;background:rgba(255,255,255,.05);border-radius:3px;overflow:hidden}}
.metric-bar-fill{{height:100%;border-radius:3px}}
.metric-value{{font-family:'Space Mono',monospace;font-size:.6rem;color:var(--text);width:32px;text-align:right;flex-shrink:0}}
.surge-badge{{display:inline-flex;align-items:center;gap:4px;font-family:'Space Mono',monospace;font-size:.55rem;letter-spacing:1px;text-transform:uppercase;padding:3px 8px;border-radius:20px;margin-top:6px}}
.surge-badge.bullish{{background:rgba(0,255,136,.1);color:#23c56e;border:1px solid rgba(0,255,136,.2)}}
.surge-badge.neutral{{background:rgba(255,255,255,.04);color:var(--muted);border:1px solid var(--border)}}
.adr-chip{{font-size:.58rem;color:var(--muted);font-family:'Space Mono',monospace}}
.summary-bar{{display:grid;grid-template-columns:repeat(4,1fr);gap:1px;background:var(--border);border:1px solid var(--border);border-radius:10px;overflow:hidden;margin:20px 40px}}
.summary-cell{{background:var(--surface);padding:14px 20px;text-align:center}}
.summary-cell .sv{{font-family:'Space Mono',monospace;font-size:1.5rem;font-weight:700;color:#fff;line-height:1}}
.summary-cell .sl{{font-family:'Space Mono',monospace;font-size:.55rem;letter-spacing:1.5px;text-transform:uppercase;color:var(--muted);margin-top:5px}}
.sv.bull{{color:#23c56e}}.sv.bear{{color:#e62a3c}}.sv.neut{{color:#ffd166}}
.drawer-overlay{{position:fixed;inset:0;background:rgba(0,0,0,.7);backdrop-filter:blur(4px);z-index:1000;opacity:0;pointer-events:none;transition:opacity .25s}}
.drawer-overlay.open{{opacity:1;pointer-events:all}}
.drawer{{position:fixed;top:0;right:0;width:420px;max-width:100vw;height:100vh;background:var(--surface);border-left:1px solid var(--border);overflow-y:auto;transform:translateX(100%);transition:transform .3s cubic-bezier(.4,0,.2,1);z-index:1001}}
.drawer.open{{transform:translateX(0)}}
.drawer-header{{padding:24px;border-bottom:1px solid var(--border);position:sticky;top:0;background:var(--surface);z-index:2;display:flex;justify-content:space-between;align-items:flex-start}}
.drawer-close{{background:none;border:1px solid var(--border);color:var(--muted);width:30px;height:30px;border-radius:6px;cursor:pointer;font-size:1rem;display:flex;align-items:center;justify-content:center;transition:color .15s;flex-shrink:0}}
.drawer-close:hover{{color:var(--text)}}
.drawer-body{{padding:20px 24px}}
.drawer-sector-title{{font-size:1.4rem;font-weight:800;color:#fff}}
.drawer-date{{font-family:'Space Mono',monospace;font-size:.6rem;color:var(--muted);margin-top:4px}}
.drawer-score-grid{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin:20px 0}}
.score-box{{background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:14px 12px;text-align:center}}
.score-box .sb-value{{font-family:'Space Mono',monospace;font-size:1.3rem;font-weight:700;color:#fff;line-height:1}}
.score-box .sb-label{{font-family:'Space Mono',monospace;font-size:.5rem;letter-spacing:1.5px;text-transform:uppercase;color:var(--muted);margin-top:6px}}
.stock-table-title{{font-family:'Space Mono',monospace;font-size:.6rem;letter-spacing:2px;text-transform:uppercase;color:var(--muted);margin-bottom:10px}}
table{{width:100%;border-collapse:collapse;font-size:.78rem}}
thead th{{font-family:'Space Mono',monospace;font-size:.55rem;letter-spacing:1.5px;text-transform:uppercase;color:var(--muted);text-align:left;padding:6px 8px;border-bottom:1px solid var(--border)}}
tbody tr{{border-bottom:1px solid rgba(255,255,255,.04);transition:background .12s}}
tbody tr:hover{{background:rgba(255,255,255,.03)}}
tbody td{{padding:8px;font-family:'Space Mono',monospace;font-size:.6rem}}
.tick{{font-weight:700;color:var(--text)}}
.pass-dot{{display:inline-block;width:7px;height:7px;border-radius:50%}}
.pass-dot.yes{{background:#23c56e}}.pass-dot.no{{background:#e62a3c}}
@media(max-width:600px){{header,.legend-strip,.metric-tabs,.heatmap-wrap{{padding-left:20px;padding-right:20px}}.summary-bar{{margin:16px 20px;grid-template-columns:1fr 1fr}}.drawer{{width:100vw}}}}
</style>
</head>
<body>
<header>
  <div class="logo-area">
    <h1>NSE Sector <span>Pulse</span></h1>
    <p>Minervini SEPA × Qullamaggie VCP — Weekly Scan</p>
  </div>
  <div class="scan-meta">
    <div><span class="pulse"></span>LIVE DATA</div>
    <div id="scanDate">—</div>
    <div id="stockCount">—</div>
  </div>
</header>
<div class="legend-strip">
  <span class="legend-label">Sentiment</span>
  <div class="legend-bar">
    <span class="legend-endpoints">BEAR</span>
    <div class="legend-swatch" style="background:#7a1f2e"></div>
    <div class="legend-swatch" style="background:#a02030"></div>
    <div class="legend-swatch" style="background:#2a2a3d"></div>
    <div class="legend-swatch" style="background:#1aaa5c"></div>
    <div class="legend-swatch" style="background:#00ff88"></div>
    <span class="legend-endpoints">BULL</span>
  </div>
  <span style="flex:1"></span>
  <span class="legend-label">Score = Minervini 40% · Qullamaggie 40% · Volume 20%</span>
</div>
<div class="metric-tabs">
  <button class="tab active" onclick="setMetric('composite',this)">Composite</button>
  <button class="tab" onclick="setMetric('minervini',this)">Minervini</button>
  <button class="tab" onclick="setMetric('qullamaggie',this)">Qullamaggie</button>
  <button class="tab" onclick="setMetric('volume',this)">Vol Surge</button>
</div>
<div class="heatmap-wrap"><div class="heatmap-grid" id="heatmapGrid"></div></div>
<div class="summary-bar">
  <div class="summary-cell"><div class="sv bull" id="sumBull">—</div><div class="sl">Bullish Sectors</div></div>
  <div class="summary-cell"><div class="sv neut" id="sumNeut">—</div><div class="sl">Neutral</div></div>
  <div class="summary-cell"><div class="sv bear" id="sumBear">—</div><div class="sl">Bearish Sectors</div></div>
  <div class="summary-cell"><div class="sv" id="sumAvg">—</div><div class="sl">Market Pulse Score</div></div>
</div>
<div class="drawer-overlay" id="overlay" onclick="closeDrawer()"></div>
<div class="drawer" id="drawer">
  <div class="drawer-header">
    <div><div class="drawer-sector-title" id="drawerTitle">—</div><div class="drawer-date" id="drawerDate">—</div></div>
    <button class="drawer-close" onclick="closeDrawer()">✕</button>
  </div>
  <div class="drawer-body">
    <div class="drawer-score-grid" id="drawerScoreGrid"></div>
    <div class="stock-table-title">Stock Breakdown</div>
    <table><thead><tr><th>Ticker</th><th>Minervini</th><th>Quillamag</th><th>ADR%</th><th>RS 3M</th><th>Vol↑</th></tr></thead>
    <tbody id="drawerTable"></tbody></table>
  </div>
</div>
<script>
const SCAN_DATA = {scan_json};
let activeMetric = 'composite';

function scoreToColor(s){{
  if(s>=80)return'#00ff88';if(s>=65)return'#23c56e';if(s>=50)return'#1aaa5c';
  if(s>=40)return'#2a3a2e';if(s>=30)return'#2a2a3d';if(s>=20)return'#7a1f2e';
  if(s>=10)return'#a02030';return'#ff2d42';
}}
function scoreToBg(s){{
  if(s>=65)return'linear-gradient(135deg,#0a1f14,#091a10)';
  if(s>=40)return'linear-gradient(135deg,#0f0f1a,#0d0d16)';
  return'linear-gradient(135deg,#1a090c,#140809)';
}}
function getScore(d){{
  return activeMetric==='minervini'?d.minervini_pct:activeMetric==='qullamaggie'?d.qullamaggie_pct:activeMetric==='volume'?d.surge_pct:d.bullish_score;
}}
function signal(s){{
  return s>=65?{{t:'▲ BULLISH',c:'#00ff88'}}:s>=40?{{t:'◆ NEUTRAL',c:'#ffd166'}}:{{t:'▼ BEARISH',c:'#ff2d42'}};
}}

function renderHeatmap(){{
  const grid=document.getElementById('heatmapGrid');
  grid.innerHTML='';
  let bull=0,neut=0,bear=0,total=0;
  const list=Object.values(SCAN_DATA.sectors).sort((a,b)=>getScore(b)-getScore(a));
  list.forEach((d,i)=>{{
    const sc=d.bullish_score,color=scoreToColor(sc),bg=scoreToBg(sc),sig=signal(sc);
    const circ=2*Math.PI*20,dash=(sc/100)*circ;
    if(sc>=65)bull++;else if(sc>=40)neut++;else bear++;
    total+=sc;
    const surge=d.surge_pct>=30;
    const card=document.createElement('div');
    card.className='sector-card';
    card.style.cssText=`background:${{bg}};border-color:${{color}}22`;
    card.innerHTML=`
      <div class="card-header">
        <div class="sector-name">${{d.sector}}</div>
        <div class="sector-signal" style="color:${{sig.c}}">${{sig.t}}</div>
        <div class="score-area"><div class="score-ring">
          <svg viewBox="0 0 50 50" width="52" height="52">
            <circle class="track" cx="25" cy="25" r="20"/>
            <circle class="fill" cx="25" cy="25" r="20" stroke="${{color}}"
              stroke-dasharray="${{dash}} ${{circ}}" stroke-dashoffset="0"/>
          </svg>
          <div class="score-number">${{Math.round(sc)}}</div>
        </div></div>
      </div>
      <div class="card-body">
        <div class="metric-row"><span class="metric-label">Minervini</span>
          <div class="metric-bar-wrap"><div class="metric-bar-fill" style="width:${{d.minervini_pct}}%;background:#7b61ff"></div></div>
          <span class="metric-value">${{d.minervini_pct}}%</span></div>
        <div class="metric-row"><span class="metric-label">Quillamag</span>
          <div class="metric-bar-wrap"><div class="metric-bar-fill" style="width:${{d.qullamaggie_pct}}%;background:#00c9ff"></div></div>
          <span class="metric-value">${{d.qullamaggie_pct}}%</span></div>
        <div class="metric-row"><span class="metric-label">Vol Surge</span>
          <div class="metric-bar-wrap"><div class="metric-bar-fill" style="width:${{d.surge_pct}}%;background:#ffd166"></div></div>
          <span class="metric-value">${{d.surge_pct}}%</span></div>
        <span class="surge-badge ${{surge?'bullish':'neutral'}}">${{surge?'⚡ Vol Surge '+d.surge_pct+'%':'Vol Quiet '+d.surge_pct+'%'}}</span>
        <div class="adr-chip">Avg ADR ${{d.avg_adr}}%</div>
      </div>`;
    card.addEventListener('click',()=>openDrawer(d.sector));
    grid.appendChild(card);
  }});
  document.getElementById('sumBull').textContent=bull;
  document.getElementById('sumNeut').textContent=neut;
  document.getElementById('sumBear').textContent=bear;
  const avg=list.length?Math.round(total/list.length):0;
  const el=document.getElementById('sumAvg');
  el.textContent=avg; el.style.color=scoreToColor(avg);
  document.getElementById('scanDate').textContent=SCAN_DATA.scan_date;
  document.getElementById('stockCount').textContent=list.reduce((a,s)=>a+(s.stocks||[]).length,0)+' stocks scanned';
}}

function setMetric(m,btn){{
  activeMetric=m;
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
  btn.classList.add('active');
  renderHeatmap();
}}

function openDrawer(name){{
  const d=SCAN_DATA.sectors[name];if(!d)return;
  const sig=signal(d.bullish_score);
  document.getElementById('drawerTitle').textContent=name;
  document.getElementById('drawerDate').textContent=SCAN_DATA.scan_date;
  document.getElementById('drawerScoreGrid').innerHTML=`
    <div class="score-box"><div class="sb-value" style="color:${{scoreToColor(d.bullish_score)}}">${{d.bullish_score}}</div><div class="sb-label">Bull Score</div></div>
    <div class="score-box"><div class="sb-value" style="color:#7b61ff">${{d.minervini_pct}}%</div><div class="sb-label">Minervini</div></div>
    <div class="score-box"><div class="sb-value" style="color:#00c9ff">${{d.qullamaggie_pct}}%</div><div class="sb-label">Qullamag</div></div>
    <div class="score-box"><div class="sb-value" style="color:#ffd166">${{d.surge_pct}}%</div><div class="sb-label">Vol Surge</div></div>
    <div class="score-box"><div class="sb-value">${{d.avg_adr}}%</div><div class="sb-label">Avg ADR</div></div>
    <div class="score-box"><div class="sb-value" style="color:${{sig.c}};font-size:.8rem">${{sig.t}}</div><div class="sb-label">Signal</div></div>`;
  const tbody=document.getElementById('drawerTable');
  tbody.innerHTML='';
  (d.stocks||[]).sort((a,b)=>b.minervini_score-a.minervini_score).forEach(s=>{{
    const tick=s.ticker.replace('.NS','');
    const rs=s.rs_return>0?`+${{s.rs_return}}%`:`${{s.rs_return}}%`;
    const rsc=s.rs_return>0?'#00ff88':'#ff2d42';
    tbody.innerHTML+=`<tr>
      <td class="tick">${{tick}}</td>
      <td><span class="pass-dot ${{s.minervini_passed?'yes':'no'}}"></span></td>
      <td><span class="pass-dot ${{s.qullamaggie_passed?'yes':'no'}}"></span></td>
      <td>${{s.adr}}%</td>
      <td style="color:${{rsc}}">${{rs}}</td>
      <td>${{s.volume_surge&&s.volume_surge.bullish_surge?'⚡':'—'}}</td></tr>`;
  }});
  document.getElementById('drawer').classList.add('open');
  document.getElementById('overlay').classList.add('open');
}}

function closeDrawer(){{
  document.getElementById('drawer').classList.remove('open');
  document.getElementById('overlay').classList.remove('open');
}}

renderHeatmap();
</script>
</body>
</html>"""

with open("sector_heatmap.html", "w", encoding="utf-8") as f:
    f.write(html)

print("✅ sector_heatmap.html generated successfully")
