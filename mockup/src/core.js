/* ===================== data + state ===================== */
const A = JSON.parse(document.getElementById('lct-data').textContent);
const N = A.N, ND = A.meta.nd, DATES = A.meta.dates, PLATS = A.meta.plats, DOW = A.meta.dow;
const byId = {}; N.forEach((n, i) => byId[n.id] = i);
const EXP = N.map((n, i) => n.rt === 'exposure' ? i : -1).filter(i => i >= 0);
const MODELS = N.map((n, i) => n.rt === 'model' ? i : -1).filter(i => i >= 0);
const SOURCES = N.map((n, i) => n.rt === 'source' ? i : -1).filter(i => i >= 0);
const SEMS = N.map((n, i) => n.rt === 'semantic' ? i : -1).filter(i => i >= 0);
const CUR = i => A.CUR[i] || null;
const UPS = e => A.UP[e] || [];
const CHILDREN = {}, PARENTS = {};
A.E.forEach(([p, c]) => { (CHILDREN[p] = CHILDREN[p] || []).push(c); (PARENTS[c] = PARENTS[c] || []).push(p); });
// exposures each node feeds (reverse of the closure table)
const FEEDS = {};
EXP.forEach(e => UPS(e).forEach(([u, d]) => (FEEDS[u] = FEEDS[u] || []).push([e, d])));

const state = {
  view: 'health', period: 30, plat: 'all',
  selExp: byId['exposure.acme_core.executive_revenue_dashboard'],
  selNode: null, blastNode: byId['model.acme_core.stg_netsuite__journal_lines'],
  ganttDay: ND - 1, lineageMode: 'graph', healthGroup: 'all'
};
try { const s = JSON.parse(localStorage.getItem('lct-ui') || '{}'); if (s.period) state.period = s.period; if (s.plat) state.plat = s.plat; } catch (e) {}
function saveUi() { try { localStorage.setItem('lct-ui', JSON.stringify({ period: state.period, plat: state.plat })); } catch (e) {} }

function win() { const from = ND - state.period, to = ND - 1; const pf = from - state.period; return { from, to, pfrom: pf, pto: from - 1, hasPrior: pf >= 0 }; }
const platsOn = () => state.plat === 'all' ? PLATS : [state.plat];
function nodePlatAt(i, d) { const n = N[i]; if (n.mf && d < DATES.indexOf(n.md)) return n.mf; return n.p; }
function nodeInPlat(i) { if (state.plat === 'all') return true; const n = N[i]; return n.p === state.plat || n.mf === state.plat; }

/* ===================== format ===================== */
const sum = (a, f = 0, t = a.length - 1) => { let s = 0; for (let i = f; i <= t; i++) s += a[i] || 0; return s; };
const mean = a => { const v = a.filter(x => x != null); return v.length ? v.reduce((s, x) => s + x, 0) / v.length : null; };
const daily = key => { const out = new Array(ND).fill(0); platsOn().forEach(p => A.S[key][p].forEach((v, i) => out[i] += v)); return out; };
const fInt = v => v == null ? '-' : Math.round(v).toLocaleString('en-GB');
const fPct = (v, d = 1) => v == null || isNaN(v) ? '-' : (v * 100).toFixed(d) + '%';
const fUsd = v => v == null ? '-' : '$' + Math.round(v).toLocaleString('en-GB');
const fUsd2 = v => v == null ? '-' : (v < 10 ? '$' + v.toFixed(2) : fUsd(v));
const fK = v => v == null ? '-' : Math.abs(v) >= 1e6 ? (v / 1e6).toFixed(1) + 'M' : Math.abs(v) >= 1e3 ? (v / 1e3).toFixed(1) + 'K' : Math.round(v).toString();
const fDur = s => s == null ? '-' : s < 60 ? s.toFixed(0) + 's' : s < 3600 ? (s / 60).toFixed(1) + ' min' : (s / 3600).toFixed(1) + ' h';
const fHrs = h => h == null ? '-' : h < 1 ? Math.round(h * 60) + ' min' : h.toFixed(1) + ' h';
const MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const dLab = i => { const s = DATES[i]; return `${+s.slice(8)} ${MON[+s.slice(5, 7) - 1]}`; };
const tsLab = s => s ? `${+s.slice(8, 10)} ${MON[+s.slice(5, 7) - 1]}, ${s.slice(11, 16)}` : '-';
const DOWN = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const tipAttr = html => `data-tip="${encodeURIComponent(html)}"`;
const PLAT_NAME = { snowflake: 'Snowflake', databricks: 'Databricks', redshift: 'Redshift' };
const PLAT_COL = { snowflake: 'var(--p-snowflake)', databricks: 'var(--p-databricks)', redshift: 'var(--p-redshift)' };
const BI_NAME = { tableau: 'Tableau', sigma: 'Sigma', power_bi: 'Power BI' };
const LAYER_NAME = { source: 'Sources', staging: 'Staging', intermediate: 'Intermediate', mart: 'Marts', semantic: 'BI semantic layer', exposure: 'Exposures' };
const ET_NAME = { dashboard: 'Dashboard', notebook: 'Notebook', ml: 'ML model', data_app: 'Data app', agent: 'AI agent', data_hub: 'Data hub' };
const AP_NAME = { bi_semantic_layer: 'via BI semantic layer', direct_warehouse: 'direct to warehouse', dbt_semantic_layer: 'via dbt semantic layer', mcp_server: 'via MCP server', extract: 'via extract' };
const CT_NAME = { view: 'views', query: 'queries', app_session: 'app sessions', agent_call: 'agent calls' };

/* ===================== status ===================== */
const ST = { 0: { k: 'none', l: 'No data', trust: 'No recent runs' }, 1: { k: 'good', l: 'Healthy', trust: 'Trusted' }, 2: { k: 'warn', l: 'Warning', trust: 'Use with caution' }, 3: { k: 'crit', l: 'Critical', trust: 'Do not use' } };
const ICON = {
  good: '<svg viewBox="0 0 12 12"><circle cx="6" cy="6" r="5.5" fill="currentColor" opacity=".18"/><path d="m3.6 6.2 1.6 1.6 3.2-3.4" stroke="currentColor" stroke-width="1.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  warn: '<svg viewBox="0 0 12 12"><path d="M6 1.2 11 10.4H1z" fill="currentColor" opacity=".2"/><path d="M6 4.6v2.6M6 8.7v.1" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>',
  crit: '<svg viewBox="0 0 12 12"><circle cx="6" cy="6" r="5.5" fill="currentColor" opacity=".18"/><path d="m4 4 4 4M8 4 4 8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>',
  none: '<svg viewBox="0 0 12 12"><circle cx="6" cy="6" r="5.5" fill="currentColor" opacity=".18"/><path d="M3.8 6h4.4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>'
};
const pill = (s, label) => { const x = ST[s] || ST[0]; return `<span class="pill ${x.k}">${ICON[x.k]}${label || x.l}</span>`; };
const sKey = s => (ST[s] || ST[0]).k;
const STATUS_COL = { 0: 'var(--none)', 1: 'var(--good)', 2: 'var(--warn)', 3: 'var(--crit)' };
const platTag = p => p ? `<span class="tag"><span class="pdot" style="background:${PLAT_COL[p]}"></span>${PLAT_NAME[p]}</span>` : '';
const expKind = i => { const n = N[i]; if (!n.dec) return 'unregistered'; if (n.et === 'dashboard') return 'bi'; if (n.et === 'agent' || n.et === 'data_hub') return 'agents'; return 'apps'; };
const expMeta = i => { const n = N[i]; return n.bi ? BI_NAME[n.bi] : ET_NAME[n.et]; };

/* ===================== tooltip ===================== */
const stage = document.getElementById('stage'), tip = document.getElementById('tip');
let SCALE = 1;
function placeTip(ev) {
  const r = stage.getBoundingClientRect();
  let x = (ev.clientX - r.left) / SCALE + 14, y = (ev.clientY - r.top) / SCALE + 14;
  const w = tip.offsetWidth, h = tip.offsetHeight;
  if (x + w > 1590) x = x - w - 28; if (y + h > 990) y = y - h - 28;
  tip.style.left = x + 'px'; tip.style.top = y + 'px';
}
function showTip(ev, html) { tip.innerHTML = html; tip.style.display = 'block'; placeTip(ev); }
function hideTip() { tip.style.display = 'none'; }
stage.addEventListener('mouseover', ev => { const t = ev.target.closest('[data-tip]'); if (t) showTip(ev, decodeURIComponent(t.dataset.tip)); });
stage.addEventListener('mousemove', ev => { if (tip.style.display === 'block' && ev.target.closest('[data-tip]')) placeTip(ev); });
stage.addEventListener('mouseout', ev => { const t = ev.target.closest('[data-tip]'); if (t && !t.contains(ev.relatedTarget)) hideTip(); });
const tipRows = (title, rows) => `<div class="th">${title}</div>` + rows.map(([l, v]) => `<div class="tr"><span class="tl">${l}</span><span class="tv">${v}</span></div>`).join('');

/* ===================== charts ===================== */
const SVGNS = 'http://www.w3.org/2000/svg';
function niceMax(v) { if (v <= 0) return 1; const p = Math.pow(10, Math.floor(Math.log10(v))); const m = v / p; return (m <= 1 ? 1 : m <= 2 ? 2 : m <= 2.5 ? 2.5 : m <= 5 ? 5 : 10) * p; }

/* mini bar trend for KPI cards: whole 90 days, current window in accent */
function barSpark(vals, { from, to, fmt = fInt, lab = '', color = 'var(--accent)', h = 30 } = {}) {
  const W = 300, n = vals.length, bw = W / n;
  const mx = Math.max(...vals.filter(v => v != null), 0) || 1;
  let s = `<svg class="spark" viewBox="0 0 ${W} ${h}" preserveAspectRatio="none" role="img" aria-label="${esc(lab)} daily trend">`;
  vals.forEach((v, i) => {
    if (v == null) return;
    const bh = Math.max(1.2, (v / mx) * (h - 2)); const inW = i >= from && i <= to;
    s += `<rect x="${(i * bw + .35).toFixed(2)}" y="${(h - bh).toFixed(2)}" width="${Math.max(bw - .7, .8).toFixed(2)}" height="${bh.toFixed(2)}" rx="1" fill="${inW ? color : '#D9DCD7'}" ${tipAttr(`<div class="th">${dLab(i)}</div><div class="tr"><span class="tl">${esc(lab)}</span><span class="tv">${fmt(v)}</span></div>`)}/>`;
  });
  return s + '</svg>';
}
/* smooth line sparkline */
function lineSpark(vals, { w = 220, h = 34, color = 'var(--accent)', from = 0, fmt = v => v, lab = '', min = null } = {}) {
  const pts = vals.map((v, i) => [i, v]).filter(p => p[1] != null);
  if (!pts.length) return `<svg width="${w}" height="${h}"></svg>`;
  const lo = min ?? Math.min(...pts.map(p => p[1])), hi = Math.max(...pts.map(p => p[1])); const rg = hi - lo || 1;
  const X = i => 2 + i / (vals.length - 1) * (w - 6), Y = v => h - 3 - (v - lo) / rg * (h - 8);
  const d = pts.map((p, k) => (k ? 'L' : 'M') + X(p[0]).toFixed(1) + ' ' + Y(p[1]).toFixed(1)).join('');
  const last = pts[pts.length - 1];
  const area = d + `L${X(last[0]).toFixed(1)} ${h - 1}L${X(pts[0][0]).toFixed(1)} ${h - 1}Z`;
  const band = from > 0 ? `<rect x="${X(from)}" y="0" width="${w - X(from)}" height="${h}" fill="var(--accent)" opacity=".05"/>` : '';
  return `<svg width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" role="img" aria-label="${esc(lab)}">${band}<path d="${area}" fill="${color}" opacity=".08"/><path d="${d}" fill="none" stroke="${color}" stroke-width="1.6" stroke-linejoin="round"/><circle cx="${X(last[0])}" cy="${Y(last[1])}" r="2.6" fill="${color}" stroke="#fff" stroke-width="1.2"/></svg>`;
}

/* generic time chart: lines or stacked bars over day indices, with crosshair tooltip, annotations and click */
function timeChart(el, o) {
  el.innerHTML = '';
  const W = el.clientWidth || 600, H = o.h || el.clientHeight || 200;
  const m = { l: o.ml ?? 38, r: o.mr ?? 12, t: o.mt ?? (o.ann && o.ann.length ? 28 : 8), b: 20 };
  const x0 = o.from ?? 0, x1 = o.to ?? ND - 1, n = x1 - x0 + 1;
  const iw = W - m.l - m.r, ih = H - m.t - m.b;
  const bw = iw / n;
  const X = i => m.l + (i - x0 + .5) * bw;
  let ymax;
  if (o.type === 'bar') { ymax = 0; for (let i = x0; i <= x1; i++) { let s = 0; o.series.forEach(se => s += se.vals[i] || 0); ymax = Math.max(ymax, s); } }
  else ymax = Math.max(...o.series.flatMap(se => se.vals.slice(x0, x1 + 1).filter(v => v != null)));
  const ymin = o.yMin ?? 0;
  ymax = o.yMax ?? niceMax((ymax - ymin) * 1.05) + ymin;
  if (ymax <= ymin) ymax = ymin + 1;
  const Y = v => m.t + ih - (v - ymin) / (ymax - ymin) * ih;
  const fmt = o.fmt || fInt;
  let s = `<svg width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(o.label || 'chart')}">`;
  // grid + y labels
  const ticks = o.yTicks || [ymin, ymin + (ymax - ymin) / 2, ymax];
  s += '<g class="grid">' + ticks.map(t => `<line x1="${m.l}" x2="${W - m.r}" y1="${Y(t)}" y2="${Y(t)}"/>`).join('') + '</g>';
  s += '<g class="axis">' + ticks.map(t => `<text x="${m.l - 6}" y="${Y(t) + 3}" text-anchor="end">${(o.yFmt || fmt)(t)}</text>`).join('');
  // x labels: month starts (90d) or weekly (<=30d)
  for (let i = x0; i <= x1; i++) {
    const dd = +DATES[i].slice(8);
    const show = i === x0 || (i - x0 >= (n > 40 ? 9 : 4) && (n > 40 ? dd === 1 : n > 10 ? DOW[i] === 0 : true));
    if (show) s += `<text x="${X(i)}" y="${H - 5}" text-anchor="${i === x0 ? 'start' : 'middle'}">${dLab(i)}</text>`;
  }
  s += '</g>';
  if (o.band) s += `<rect x="${X(o.band[0]) - bw / 2}" y="${m.t}" width="${(o.band[1] - o.band[0] + 1) * bw}" height="${ih}" fill="var(--accent)" opacity=".05"/>`;
  if (o.type === 'bar') {
    const gap = bw > 4 ? 1.2 : .4;
    for (let i = x0; i <= x1; i++) {
      let acc = 0;
      o.series.forEach(se => {
        const v = se.vals[i] || 0; if (!v) return;
        const y1 = Y(ymin + acc), y2 = Y(ymin + acc + v); acc += v;
        const hh = Math.max(y1 - y2 - (acc > v ? 1 : 0), .8);
        s += `<rect x="${X(i) - bw / 2 + gap / 2}" y="${y2}" width="${Math.max(bw - gap, .6)}" height="${hh}" rx="${bw > 5 ? 1.5 : 0}" fill="${se.color}" opacity="${o.sel != null && o.sel !== i ? .55 : 1}"/>`;
      });
      if (o.sel === i) s += `<rect x="${X(i) - bw / 2 - 1}" y="${m.t}" width="${bw + 2}" height="${ih}" fill="none" stroke="var(--navy)" stroke-width="1.2" rx="2"/>`;
    }
  } else {
    o.series.forEach(se => {
      let d = '', on = false;
      for (let i = x0; i <= x1; i++) { const v = se.vals[i]; if (v == null) { on = false; continue; } d += (on ? 'L' : 'M') + X(i).toFixed(1) + ' ' + Y(Math.max(ymin, Math.min(ymax, v))).toFixed(1); on = true; }
      if (se.area) { const firstI = se.vals.findIndex((v, i) => i >= x0 && v != null); s += `<path d="${d}L${X(x1)} ${Y(ymin)}L${X(firstI)} ${Y(ymin)}Z" fill="${se.color}" opacity=".08"/>`; }
      s += `<path d="${d}" fill="none" stroke="${se.color}" stroke-width="${se.w || 2}" stroke-linejoin="round" ${se.dash ? `stroke-dasharray="${se.dash}"` : ''} opacity="${se.op ?? 1}"/>`;
      if (o.endLabels) { let li = x1; while (li > x0 && se.vals[li] == null) li--; if (se.vals[li] != null) { s += `<circle cx="${X(li)}" cy="${Y(se.vals[li])}" r="2.8" fill="${se.color}" stroke="#fff" stroke-width="1.2"/>`; } }
    });
    if (o.endLabels) {
      // de-collide end labels
      const labs = o.series.map(se => { let li = x1; while (li > x0 && se.vals[li] == null) li--; return { se, y: Y(se.vals[li] ?? ymin) }; }).sort((a, b) => a.y - b.y);
      for (let k = 1; k < labs.length; k++) if (labs[k].y - labs[k - 1].y < 11) labs[k].y = labs[k - 1].y + 11;
      labs.forEach(({ se, y }) => s += `<text x="${W - m.r + 6}" y="${y + 3}" font-size="10" fill="var(--ink-2)" font-weight="${se.w > 2 ? 600 : 400}">${esc(se.name)}</text>`);
    }
  }
  let lastX = -1e9, lvl = 0;
  (o.ann || []).filter(a => a.d >= x0 && a.d <= x1).sort((a, b) => a.d - b.d).forEach(a => {
    const x = X(a.d); lvl = x - lastX < 70 ? (lvl + 1) % 2 : 0; lastX = x; const ly = m.t - 6 - lvl * 11, right = x > W - m.r - 70;
    s += `<line x1="${x}" x2="${x}" y1="${ly + 3}" y2="${m.t + ih}" stroke="${a.color || 'var(--ink-3)'}" stroke-dasharray="2 3" stroke-width="1"/><text x="${right ? x - 3 : x + 3}" y="${ly}" text-anchor="${right ? 'end' : 'start'}" font-size="9.5" fill="${a.color || 'var(--ink-2)'}" font-weight="600">${esc(a.label)}</text>`;
  });
  s += `<line class="xh" x1="0" x2="0" y1="${m.t}" y2="${m.t + ih}" stroke="var(--ink-3)" stroke-width="1" opacity="0"/>`;
  s += `<rect class="hit" x="${m.l}" y="${m.t}" width="${iw}" height="${ih}" fill="transparent" style="cursor:${o.onClick ? 'pointer' : 'crosshair'}"/></svg>`;
  el.innerHTML = s;
  const svg = el.firstChild, hit = svg.querySelector('.hit'), xh = svg.querySelector('.xh');
  const idxAt = ev => { const r = svg.getBoundingClientRect(); const px = (ev.clientX - r.left) / (r.width / W); return Math.max(x0, Math.min(x1, Math.floor((px - m.l) / bw) + x0)); };
  hit.addEventListener('mousemove', ev => {
    const i = idxAt(ev); xh.setAttribute('x1', X(i)); xh.setAttribute('x2', X(i)); xh.setAttribute('opacity', .5);
    const rows = o.series.filter(se => !se.noTip).map(se => [`<span style="display:inline-block;width:8px;height:8px;border-radius:2px;background:${se.color};margin-right:6px"></span>${esc(se.name)}`, se.vals[i] == null ? '-' : fmt(se.vals[i])]);
    let extra = o.tipExtra ? o.tipExtra(i) : '';
    showTip(ev, tipRows(`${DOWN[DOW[i]]} ${dLab(i)}`, rows) + extra + (o.onClick ? '<div class="tl" style="margin-top:4px">Click to select this day</div>' : ''));
  });
  hit.addEventListener('mouseleave', () => { xh.setAttribute('opacity', 0); hideTip(); });
  if (o.onClick) hit.addEventListener('click', ev => o.onClick(idxAt(ev)));
}

/* ===================== router ===================== */
const VIEWS = {
  health: { t: 'Health overview', q: 'Is anything on fire right now?', g: 'Monitor' },
  runs: { t: 'Run & failures', q: 'What failed, when, why, and how fast did we recover?', g: 'Monitor' },
  fresh: { t: 'Freshness & SLAs', q: 'Is the data arriving on time?', g: 'Monitor' },
  lineage: { t: 'Lineage explorer', q: 'What feeds this exposure, and is every step healthy?', g: 'Investigate' },
  blast: { t: 'Blast radius', q: 'If this breaks, who do I need to tell?', g: 'Investigate' },
  quality: { t: 'Data quality', q: 'Which tests keep failing, and where are we untested?', g: 'Investigate' },
  perf: { t: 'Performance & cost', q: 'What is getting slower and more expensive?', g: 'Optimise' },
  usage: { t: 'Usage & adoption', q: 'Which data products earn their keep?', g: 'Optimise' },
  gov: { t: 'Governance', q: 'Is everything owned, documented, tested and declared?', g: 'Govern' },
  about: { t: 'About & how to use', q: 'What this is, where the numbers come from', g: 'About' }
};
const RENDER = {};
function go(view, push = true) {
  if (!VIEWS[view]) view = 'health';
  state.view = view; hideTip();
  document.querySelectorAll('.nav-item').forEach(b => b.classList.toggle('active', b.dataset.view === view));
  document.querySelectorAll('.view').forEach(v => v.classList.toggle('on', v.id === 'v-' + view));
  const V = VIEWS[view];
  document.getElementById('crumb').innerHTML = `${V.g} / <b>${V.t}</b>`;
  document.getElementById('title').innerHTML = `${esc(V.t)}<span class="q">${esc(V.q)}</span>`;
  if (push) { try { history.replaceState(null, '', '#' + view); } catch (e) {} }
  render();
}
function render() {
  document.querySelectorAll('#f-period button').forEach(b => b.classList.toggle('on', +b.dataset.v === state.period));
  document.querySelectorAll('#f-plat button').forEach(b => b.classList.toggle('on', b.dataset.v === state.plat));
  const w = win();
  document.getElementById('filter-hint').textContent = w.hasPrior ? `Changes compare with the ${state.period} days before` : 'No earlier period in the data to compare with';
  const chip = document.getElementById('sel-chip');
  const selFor = { lineage: state.selExp, usage: state.selExp, blast: state.blastNode }[state.view];
  if (selFor != null && ['lineage', 'blast'].includes(state.view)) { chip.hidden = false; document.getElementById('sel-chip-text').innerHTML = `${state.view === 'blast' ? 'Selected node' : 'Selected exposure'}: <b>${esc(N[selFor].n)}</b>`; }
  else chip.hidden = true;
  (RENDER[state.view] || (() => {}))(document.getElementById('v-' + state.view));
  navCounts();
}
function navCounts() {
  const atRisk = EXP.filter(e => (CUR(e) || {}).s >= 2 && nodeInPlat(e));
  const red = atRisk.filter(e => CUR(e).s === 3).length;
  const c = document.getElementById('nc-health'); c.textContent = atRisk.length || ''; c.className = 'count ' + (red ? 'crit' : 'warn');
  const lateSrc = SOURCES.filter(i => (CUR(i) || {}).s >= 2 && nodeInPlat(i)).length;
  const f = document.getElementById('nc-fresh'); f.textContent = lateSrc || ''; f.className = 'count warn';
  const failingTests = A.TESTS.filter(t => t.fd[ND - 1] && nodeInPlat(t.node)).length;
  const q = document.getElementById('nc-quality'); q.textContent = failingTests || ''; q.className = 'count crit';
  const und = EXP.filter(e => !N[e].dec).length;
  const g = document.getElementById('nc-gov'); g.textContent = und || ''; g.className = 'count warn';
}
document.querySelectorAll('.nav-item').forEach(b => b.addEventListener('click', () => go(b.dataset.view)));
document.querySelectorAll('#f-period button').forEach(b => b.addEventListener('click', () => { state.period = +b.dataset.v; saveUi(); render(); }));
document.querySelectorAll('#f-plat button').forEach(b => b.addEventListener('click', () => { state.plat = b.dataset.v; saveUi(); render(); }));
document.getElementById('sel-clear').addEventListener('click', () => { if (state.view === 'blast') state.blastNode = byId['model.acme_core.stg_netsuite__journal_lines']; else state.selExp = byId['exposure.acme_core.executive_revenue_dashboard']; state.selNode = null; render(); });
document.getElementById('info-btn').addEventListener('click', () => go('about'));

/* fit the fixed canvas to the screen without horizontal scroll */
function fit() {
  const wrap = document.getElementById('stage-wrap');
  const avail = wrap.parentElement.clientWidth - parseFloat(getComputedStyle(document.body).paddingLeft) * 0 ;
  SCALE = Math.min(1, wrap.clientWidth / 1600);
  stage.style.transform = `scale(${SCALE})`;
  wrap.style.height = (1000 * SCALE) + 'px';
}
window.addEventListener('resize', fit);
