/* ===================== shared metric helpers ===================== */
function rate(okKey, badKeys, f, t) { const ok = daily(okKey), bad = badKeys.map(daily); const o = sum(ok, f, t), b = bad.reduce((s, a) => s + sum(a, f, t), 0); return o + b ? o / (o + b) : null; }
function rateDaily(okKey, badKeys) { const ok = daily(okKey), bad = badKeys.map(daily); return ok.map((v, i) => { const b = bad.reduce((s, a) => s + a[i], 0); return v + b ? v / (v + b) : null; }); }
function epsIn(f, t) { return A.EP.filter(e => e[4] != null && e[5] >= f && e[5] <= t && (state.plat === 'all' || nodePlatAt(e[0], e[5]) === state.plat)); }
function expsOn() { return EXP.filter(e => nodeInPlat(e)); }
function atRiskDaily() { const ex = expsOn(); return Array.from({ length: ND }, (_, d) => ex.filter(e => +A.EXPDAY[e].e[d] >= 2).length); }
function consumers30(e, f, t) { const c = A.CONS[e]; if (!c) return 0; const v = c.uc.slice(f, t + 1); return v.length ? v.reduce((s, x) => s + x, 0) / v.length : 0; }
function events(e, f, t) { const c = A.CONS[e]; return c ? sum(c.ev, f, t) : 0; }
function expCost(e, f, t) { const c = A.EXPCOST[e]; return c ? sum(c, f, t) : 0; }
function change(cur, prev, { kind = 'pct', goodUp = true, unit = '' } = {}) {
  if (cur == null || prev == null) return `<span class="flat">-</span> no earlier period`;
  let delta, txt;
  if (kind === 'pp') { delta = (cur - prev) * 100; txt = `${Math.abs(delta).toFixed(2)} pp`; }
  else if (kind === 'abs') { delta = cur - prev; txt = `${Math.abs(delta).toFixed(1)}${unit}`; }
  else { if (!prev) return `<span class="flat">-</span> vs prior ${state.period}d`; delta = (cur - prev) / prev; txt = `${Math.abs(delta * 100).toFixed(1)}%`; }
  if (Math.abs(delta) < 1e-9) return `<span class="flat">● 0</span> vs prior ${state.period}d`;
  const up = delta > 0, good = up === goodUp;
  return `<span class="${up ? 'up' : 'down'}-${good ? 'good' : 'bad'}">${up ? '▲' : '▼'} ${txt}</span> vs prior ${state.period}d`;
}
function nodeIssue(i) {
  const c = CUR(i), n = N[i]; if (!c) return '';
  if (n.rt === 'source') return c.s === 3 ? `Freshness error, ${fHrs(c.lag / 60)} since last load (error after ${fHrs(c.ea / 60)})` : `Loading late, ${fHrs(c.lag / 60)} behind (warn after ${fHrs(c.wa / 60)})`;
  if (n.rt === 'semantic') return c.s === 3 ? `Extract refresh failed at ${tsLab(c.at)}` : 'Refresh skipped, upstream not ready';
  if (c.rs === 'error') return `${(c.err || 'Run failed').split(':')[0]} at ${tsLab(c.at)}`;
  if (c.tf || c.tw) { const t = A.TESTS.find(t => t.node === i && t.fd[ND - 1]); return `${c.tf ? c.tf + ' test failing' : c.tw + ' test warning'}${t ? ': ' + t.n : ''}`; }
  return 'Needs attention';
}

/* ===================== 1. HEALTH OVERVIEW ===================== */
RENDER.health = el => {
  const w = win();
  el.style.gridTemplateRows = '128px minmax(0, 1fr)'; el.style.gap = '14px';
    const costD = daily('cost'), riskD = atRiskDaily();
  const mttrD = Array.from({ length: ND }, (_, d) => { const e = epsIn(d, d); return e.length ? mean(e.map(x => x[4])) : null; });
  const mttr = (f, t) => { const e = epsIn(f, t); return e.length ? mean(e.map(x => x[4])) : null; };
  const nowRisk = expsOn().filter(e => CUR(e).s >= 2), nowRed = nowRisk.filter(e => CUR(e).s === 3).length;
  const K = [
    { t: 'Run success', v: fPct(rate('runOk', ['runErr'], w.from, w.to), 2), c: change(rate('runOk', ['runErr'], w.from, w.to), w.hasPrior ? rate('runOk', ['runErr'], w.pfrom, w.pto) : null, { kind: 'pp' }), sp: barSpark(daily('runErr'), { from: w.from, to: w.to, lab: 'Failed model runs', color: 'var(--accent)' }), cap: 'Bars: failed runs per day', tip: 'Successful model runs divided by all model runs, skipped runs excluded.' },
    { t: 'Test pass rate', v: fPct(rate('testPass', ['testWarn', 'testFail'], w.from, w.to), 2), c: change(rate('testPass', ['testWarn', 'testFail'], w.from, w.to), w.hasPrior ? rate('testPass', ['testWarn', 'testFail'], w.pfrom, w.pto) : null, { kind: 'pp' }), sp: barSpark(daily('testWarn').map((v, k) => v + daily('testFail')[k]), { from: w.from, to: w.to, lab: 'Tests not passing' }), cap: 'Bars: failing or warning tests per day', tip: 'Passing tests divided by all tests run. Warnings count as not passing.' },
    { t: 'Freshness SLA', v: fPct(rate('frPass', ['frWarn', 'frErr'], w.from, w.to), 2), c: change(rate('frPass', ['frWarn', 'frErr'], w.from, w.to), w.hasPrior ? rate('frPass', ['frWarn', 'frErr'], w.pfrom, w.pto) : null, { kind: 'pp' }), sp: barSpark(daily('frWarn').map((v, k) => v + daily('frErr')[k]), { from: w.from, to: w.to, lab: 'Late source checks' }), cap: 'Bars: late source checks per day', tip: 'Hourly source freshness checks that passed, divided by all checks.' },
    { t: 'Exposures at risk', v: `${nowRisk.length}<small>of ${expsOn().length} now</small>`, c: `<span class="${nowRed ? 'up-bad' : 'flat'}">${nowRed} critical</span> · ${nowRisk.length - nowRed} warning`, sp: barSpark(riskD, { from: w.from, to: w.to, lab: 'At risk at end of day', color: 'var(--warn)' }), tip: 'Exposures whose upstream chain has a failing model, late source, failed refresh or failing test right now. Bars show the count at the end of each day.' },
    { t: 'Mean time to recover', v: fHrs(mttr(w.from, w.to)), c: change(mttr(w.from, w.to), w.hasPrior ? mttr(w.pfrom, w.pto) : null, { goodUp: false }), sp: barSpark(mttrD, { from: w.from, to: w.to, fmt: fHrs, lab: 'Mean recovery time' }), tip: 'Average time from a node’s first failure to its next success, across model runs, source freshness and BI refreshes.' },
    { t: 'Warehouse cost', v: fUsd(sum(costD, w.from, w.to)), c: change(sum(costD, w.from, w.to), w.hasPrior ? sum(costD, w.pfrom, w.pto) : null, { goodUp: false }), sp: barSpark(costD, { from: w.from, to: w.to, fmt: fUsd2, lab: 'Daily cost' }), tip: 'Estimated compute cost of dbt builds plus queries from data products, in USD.' },
  ];
  const kpis = `<div class="kpis" style="grid-template-columns:repeat(6,1fr)">${K.map(k => `<div class="card kpi"><div class="kpi-t" ${tipAttr(`<div class="th">${k.t}</div><div style="max-width:240px">${k.tip}</div>`)}>${k.t}<svg width="11" height="11" viewBox="0 0 12 12" aria-hidden="true"><circle cx="6" cy="6" r="5" fill="none" stroke="currentColor"/><path d="M6 5.4v3M6 3.6v.1" stroke="currentColor" stroke-linecap="round"/></svg></div><div class="kpi-v">${k.v}</div><div class="kpi-c">${k.c}</div>${k.sp}</div>`).join('')}</div>`;

  // exposure grid
  const groups = [['bi', 'BI dashboards'], ['apps', 'Apps, ML and notebooks'], ['agents', 'AI agents and data hubs'], ['unregistered', 'Unregistered, found in query history']];
  const only = state.healthGroup === 'risk';
  const tile = e => {
    const n = N[e], c = CUR(e), sc = A.SCORE[e], score = sc ? sc[ND - 1] : null;
    const why = c.why.length ? c.why.slice(0, 3).map(([u, s]) => `<div class="tr"><span>${esc(N[u].n)}</span><span class="tv" style="color:${STATUS_COL[s]}">${ST[s].l}</span></div>`).join('') : '<div>Every upstream step is healthy</div>';
    const tipH = `<div class="th">${esc(n.n)}</div><div class="tr"><span class="tl">Status</span><span class="tv">${ST[c.s].trust}</span></div><div class="tr"><span class="tl">Health score (7d)</span><span class="tv">${score ?? '-'}</span></div><div class="tr"><span class="tl">Owner</span><span class="tv">${esc(n.o || 'No owner')}</span></div><div class="tl" style="margin-top:6px">Why</div>${why}<div class="tl" style="margin-top:6px">Click to open lineage</div>`;
    return `<button class="xtile ${sKey(c.s)}" data-exp="${e}" ${tipAttr(tipH)}>
      <span class="xt-top"><span class="xt-name">${esc(n.n)}</span><span class="dot ${sKey(c.s)}"></span></span>
      <span class="xt-meta">${esc(expMeta(e))} · ${n.o ? esc(n.o) : '<b style="color:var(--crit-ink)">No owner</b>'}</span>
      <span class="xt-foot"><span class="xt-trust ${sKey(c.s)}">${ST[c.s].trust}</span>${n.bm === 'ai_assisted' ? '<span class="tag ai">AI-built</span>' : ''}<span class="xt-score num">${score == null ? '' : score.toFixed(1)}</span></span></button>`;
  };
  const grid = groups.map(([k, lab]) => {
    const list = expsOn().filter(e => expKind(e) === k && (!only || CUR(e).s >= 2)).sort((a, b) => CUR(b).s - CUR(a).s || N[a].n.localeCompare(N[b].n));
    if (!list.length) return '';
    return `<div class="xg-label">${lab}<span>${list.length}</span></div><div class="xgrid">${list.map(tile).join('')}</div>`;
  }).join('') || '<div class="empty">No exposures need attention for this platform.</div>';

  // attention list
  const nodesBad = N.map((n, i) => i).filter(i => N[i].rt !== 'exposure' && (CUR(i) || {}).s >= 2 && nodeInPlat(i)).sort((a, b) => CUR(b).s - CUR(a).s || (FEEDS[b] || []).length - (FEEDS[a] || []).length);
  const openInc = A.INC.filter(x => !x.e);
  const att = nodesBad.map(i => {
    const c = CUR(i), inc = openInc.find(x => x.node === i), nf = (FEEDS[i] || []).length;
    return `<button class="alert ${sKey(c.s)}" data-blast="${i}"><span class="al-ic">${ICON[sKey(c.s)]}</span><span class="al-b"><span class="al-t"><span class="mono">${esc(N[i].n)}</span>${inc ? `<span class="tag">${inc.id}</span>` : ''}</span><span class="al-s">${esc(nodeIssue(i))}</span><span class="al-s">${LAYER_NAME[N[i].l]} · ${PLAT_NAME[N[i].p]} · <b>affects ${nf} exposure${nf === 1 ? '' : 's'}</b>${inc ? ` · open since ${tsLab(inc.s).split(',')[0]}` : ''}</span></span><span class="al-go">›</span></button>`;
  }).join('') || '<div class="empty">Nothing needs attention right now.</div>';

  // layer health
  const layers = ['source', 'staging', 'intermediate', 'mart', 'semantic', 'exposure'];
  const lh = layers.map(l => {
    const ids = N.map((n, i) => i).filter(i => N[i].l === l && nodeInPlat(i)); const cnt = [0, 0, 0, 0];
    ids.forEach(i => cnt[(CUR(i) || { s: 0 }).s]++);
    const tot = ids.length || 1;
    const seg = [1, 2, 3, 0].filter(s => cnt[s]).map(s => `<span style="width:${cnt[s] / tot * 100}%;background:${STATUS_COL[s]}" ${tipAttr(tipRows(LAYER_NAME[l], [[ST[s].l, cnt[s] + ' of ' + ids.length]]))}></span>`).join('');
    return `<div class="lh-row"><span class="lh-l">${LAYER_NAME[l]}</span><span class="lh-bar">${seg}</span><span class="lh-n num">${cnt[2] + cnt[3] ? `<b style="color:${cnt[3] ? 'var(--crit-ink)' : 'var(--warn-ink)'}">${cnt[2] + cnt[3]}</b> / ` : ''}${ids.length}</span></div>`;
  }).join('');

  el.innerHTML = `${kpis}
  <div style="display:grid;grid-template-columns:1fr 410px;gap:14px;min-height:0">
    <div class="card"><div class="card-h"><div><div class="card-t">Exposure status</div><div class="card-s">Every data product, traced through its full upstream chain. Score is the 7-day health score (0 to 100). Click a tile to open its lineage.</div></div>
      <div class="right"><div class="seg" id="hg"><button data-v="all" class="${only ? '' : 'on'}">All</button><button data-v="risk" class="${only ? 'on' : ''}">Needs attention</button></div></div></div>
      <div class="card-body scroll">${grid}</div>
      <div class="legend" style="margin-top:8px"><span><i style="background:var(--good)"></i>Trusted</span><span><i style="background:var(--warn)"></i>Use with caution</span><span><i style="background:var(--crit)"></i>Do not use</span><span style="margin-left:auto;color:var(--ink-3)">Trust badges can be surfaced inside each dashboard for business users</span></div>
    </div>
    <div style="display:grid;grid-template-rows:minmax(0,1fr) auto;gap:14px;min-height:0">
      <div class="card"><div class="card-h"><div><div class="card-t">Needs attention now</div><div class="card-s">Upstream nodes that are failing, late or warning. Click one to see who is affected.</div></div></div><div class="card-body scroll"><div class="alerts">${att}</div></div></div>
      <div class="card"><div class="card-h"><div><div class="card-t">Health by layer</div><div class="card-s">Where in the chain the trouble sits, right now</div></div></div><div class="lh">${lh}</div></div>
    </div>
  </div>`;
  el.querySelectorAll('[data-exp]').forEach(b => b.addEventListener('click', () => { state.selExp = +b.dataset.exp; state.selNode = null; go('lineage'); }));
  el.querySelectorAll('[data-blast]').forEach(b => b.addEventListener('click', () => { state.blastNode = +b.dataset.blast; go('blast'); }));
  el.querySelectorAll('#hg button').forEach(b => b.addEventListener('click', () => { state.healthGroup = b.dataset.v; render(); }));
};

/* ===================== 2. LINEAGE EXPLORER ===================== */
function expSelect(id, sel) {
  const groups = [['bi', 'BI dashboards'], ['apps', 'Apps, ML and notebooks'], ['agents', 'AI agents and data hubs'], ['unregistered', 'Unregistered']];
  return `<select class="sel" id="${id}" aria-label="Choose an exposure">${groups.map(([k, l]) => `<optgroup label="${l}">${EXP.filter(e => expKind(e) === k).map(e => `<option value="${e}" ${e === sel ? 'selected' : ''}>${esc(N[e].n)}${CUR(e).s >= 2 ? (CUR(e).s === 3 ? '  ●  critical' : '  ●  warning') : ''}</option>`).join('')}</optgroup>`).join('')}</select>`;
}
RENDER.lineage = el => {
  const e = state.selExp;
  const scope = A.LAY[e] || [];
  if (state.selNode == null || !scope.some(s => s[0] === state.selNode)) state.selNode = (CUR(e).why[0] || [e])[0];
  el.style.gridTemplateColumns = '1fr 340px'; el.style.gridTemplateRows = 'minmax(0, 1fr)'; el.style.gap = '14px';
  const c = CUR(e), n = N[e];
  el.innerHTML = `<div class="card" style="padding-bottom:10px"><div class="card-h" style="align-items:center">
      ${expSelect('lin-exp', e)}
      <span>${pill(c.s, ST[c.s].trust)}</span>
      <span class="card-s" style="margin:0">${esc(ET_NAME[n.et])}${n.bi ? ' in ' + BI_NAME[n.bi] : ''}, ${AP_NAME[n.ap] || ''} · ${scope.length - 1} upstream nodes</span>
      <div class="right"><div class="seg" id="lin-mode"><button data-v="graph" class="${state.lineageMode === 'graph' ? 'on' : ''}">Graph</button><button data-v="table" class="${state.lineageMode === 'table' ? 'on' : ''}">Table</button></div></div></div>
    <div class="card-body ${state.lineageMode === 'table' ? 'scroll' : ''}" id="lin-body"></div>
    <div class="legend" style="margin-top:6px"><span><i style="background:var(--good)"></i>Healthy</span><span><i style="background:var(--warn)"></i>Warning</span><span><i style="background:var(--crit)"></i>Critical</span><span style="margin-left:10px"><i style="background:var(--p-snowflake)"></i>Snowflake</span><span><i style="background:var(--p-databricks)"></i>Databricks</span><span><i style="background:var(--p-redshift)"></i>Redshift (before migration)</span><span style="margin-left:auto;color:var(--ink-3);font-style:italic">Hover a node to trace its path, click it for details</span></div>
  </div>
  <div class="card" id="lin-panel"></div>`;
  el.querySelector('#lin-exp').addEventListener('change', ev => { state.selExp = +ev.target.value; state.selNode = null; render(); });
  el.querySelectorAll('#lin-mode button').forEach(b => b.addEventListener('click', () => { state.lineageMode = b.dataset.v; render(); }));
  if (state.lineageMode === 'graph') drawLineage(el.querySelector('#lin-body'), e, scope); else lineageTable(el.querySelector('#lin-body'), e, scope);
  nodePanel(el.querySelector('#lin-panel'), state.selNode);
};
function drawLineage(box, e, scope) {
  const W = box.clientWidth, H = box.clientHeight;
  const inS = new Set(scope.map(s => s[0]));
  const xs = scope.map(s => s[1]), ys = scope.map(s => s[2]);
  const ymin = Math.min(...ys), ymax = Math.max(...ys);
  const colW = (W - 16) / 6, nw = colW - 24, nh = Math.max(13, Math.min(22, (H - 50) / ((ymax - ymin) + 1.4) - 2));
  const top = 34, bottom = H - 8 - nh;
  const PX = x => 8 + Math.floor(x) * colW, PY = y => ymax === ymin ? (top + bottom) / 2 : top + (y - ymin) / (ymax - ymin) * (bottom - top);
  const pos = {}; scope.forEach(([i, x, y]) => pos[i] = [PX(x), PY(y)]);
  const edges = A.E.filter(([p, c2]) => inS.has(p) && inS.has(c2));
  let s = `<svg width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" role="img" aria-label="Lineage graph for ${esc(N[e].n)}">`;
  [0, 1, 2, 3, 4, 5].forEach(k => { const lab = ['Sources', 'Staging', 'Intermediate', 'Marts', 'BI semantic layer', 'Exposure'][k]; s += `<text x="${PX(k) + 2}" y="14" font-size="9.5" letter-spacing="1" fill="var(--ink-3)" font-weight="600">${lab.toUpperCase()}</text>`; if (k) s += `<line x1="${PX(k) - 6}" x2="${PX(k) - 6}" y1="4" y2="${H}" stroke="var(--line-soft)"/>`; });
  edges.forEach(([p, c2]) => {
    const [x1, y1] = pos[p], [x2, y2] = pos[c2]; const same = Math.abs(x1 - x2) < 1; const ax = x1 + nw, ay = y1 + nh / 2, bx = same ? x2 + nw : x2, by = y2 + nh / 2, mx = same ? ax + 16 : (ax + bx) / 2;
    const bad = Math.max((CUR(p) || {}).s || 0, 0) >= 2 ? (CUR(p).s === 3 ? 'crit' : 'warn') : '';
    s += `<path class="ed ${bad}" data-p="${p}" data-c="${c2}" d="M${ax} ${ay}C${mx} ${ay} ${mx} ${by} ${bx} ${by}" fill="none" stroke="${bad === 'crit' ? 'var(--crit)' : bad === 'warn' ? 'var(--warn)' : '#CBD0D5'}" stroke-width="${bad ? 1.4 : 1}" opacity="${bad ? .8 : 1}"/>`;
  });
  const maxCh = Math.floor((nw - 30) / 5.7);
  scope.forEach(([i]) => {
    const [x, y] = pos[i], st = (i === e ? CUR(e).s : (CUR(i) || { s: 0 }).s), k = sKey(st), n = N[i];
    const plat = nodePlatAt(i, ND - 1), short = n.n.replace(/^(stg_|int_|raw_)/, ''), name = short.length > maxCh ? short.slice(0, maxCh - 1) + '…' : short;
    const fill = st === 3 ? 'var(--crit-tint)' : st === 2 ? 'var(--warn-tint)' : '#fff';
    const stroke = i === state.selNode ? 'var(--navy)' : st >= 2 ? STATUS_COL[st] : 'var(--line)';
    const tipH = tipRows(esc(n.n), [['Layer', LAYER_NAME[n.l]], ['Platform', PLAT_NAME[plat] + (n.mf ? ` (moved from ${PLAT_NAME[n.mf]} ${dLab(DATES.indexOf(n.md))})` : '')], ['Status', ST[st].l], ...(CUR(i) && CUR(i).rt != null ? [['Last runtime', fDur(CUR(i).rt)]] : []), ...(CUR(i) && CUR(i).lag != null ? [['Lag now', fHrs(CUR(i).lag / 60)]] : []), ['Owner', esc(n.o || 'No owner')]]);
    s += `<g class="nd" data-n="${i}" style="cursor:pointer" ${tipAttr(tipH)}><rect x="${x}" y="${y}" width="${nw}" height="${nh}" rx="${Math.min(6, nh / 2)}" fill="${fill}" stroke="${stroke}" stroke-width="${i === state.selNode ? 2 : 1}"/>
      <circle cx="${x + 8}" cy="${y + nh / 2}" r="3.2" fill="${STATUS_COL[st]}"/>
      <text x="${x + 16}" y="${y + nh / 2 + 3.4}" font-size="${nh < 16 ? 9.5 : 10.5}" font-family="var(--f-code)" fill="var(--ink)" ${i === e ? 'font-weight="600"' : ''}>${esc(name)}</text>
      <rect x="${x + nw - 7}" y="${y + 3}" width="3" height="${nh - 6}" rx="1.5" fill="${PLAT_COL[plat]}"/></g>`;
  });
  box.innerHTML = s + '</svg>';
  const svg = box.firstChild;
  const reach = (start, map) => { const out = new Set([start]), st = [start]; while (st.length) { const v = st.pop(); (map[v] || []).forEach(u => { if (inS.has(u) && !out.has(u)) { out.add(u); st.push(u); } }); } return out; };
  svg.querySelectorAll('.nd').forEach(g => {
    const i = +g.dataset.n;
    g.addEventListener('mouseenter', () => { const up = reach(i, PARENTS), dn = reach(i, CHILDREN); svg.querySelectorAll('.nd').forEach(o => o.style.opacity = up.has(+o.dataset.n) || dn.has(+o.dataset.n) ? 1 : .22); svg.querySelectorAll('.ed').forEach(p => { const on = (up.has(+p.dataset.p) && up.has(+p.dataset.c)) || (dn.has(+p.dataset.p) && dn.has(+p.dataset.c)); p.style.opacity = on ? 1 : .1; if (on && !p.classList.contains('crit') && !p.classList.contains('warn')) p.setAttribute('stroke', 'var(--accent)'); }); });
    g.addEventListener('mouseleave', () => { svg.querySelectorAll('.nd').forEach(o => o.style.opacity = 1); svg.querySelectorAll('.ed').forEach(p => { p.style.opacity = ''; if (!p.classList.contains('crit') && !p.classList.contains('warn')) p.setAttribute('stroke', '#CBD0D5'); }); });
    g.addEventListener('click', () => { state.selNode = i; render(); });
  });
}
function lineageTable(box, e, scope) {
  const depth = {}; UPS(e).forEach(([u, d]) => depth[u] = d);
  const rows = scope.filter(s => s[0] !== e).map(s => s[0]).sort((a, b) => N[a].lo - N[b].lo || (CUR(b) || { s: 0 }).s - (CUR(a) || { s: 0 }).s);
  box.innerHTML = `<table class="t"><thead><tr><th>Node</th><th>Layer</th><th>Platform</th><th>Status</th><th class="r">Hops</th><th>Last run or check</th><th class="r">Runtime</th><th class="r">Tests</th><th>Owner</th></tr></thead><tbody>${rows.map(i => { const c = CUR(i) || { s: 0 }; return `<tr class="click ${i === state.selNode ? 'sel' : ''}" data-n="${i}"><td class="mono">${esc(N[i].n)}</td><td>${LAYER_NAME[N[i].l]}</td><td>${platTag(N[i].p)}</td><td>${pill(c.s)}</td><td class="r">${depth[i] ?? ''}</td><td>${tsLab(c.at)}</td><td class="r">${c.rt != null ? fDur(c.rt) : c.lag != null ? 'lag ' + fHrs(c.lag / 60) : ''}</td><td class="r">${c.tp != null ? `${c.tp}<span style="color:var(--ink-3)"> pass</span>${c.tf ? ` · <b style="color:var(--crit-ink)">${c.tf} fail</b>` : ''}${c.tw ? ` · <b style="color:var(--warn-ink)">${c.tw} warn</b>` : ''}` : ''}</td><td>${esc(N[i].o || '')}</td></tr>`; }).join('')}</tbody></table>`;
  box.querySelectorAll('tr[data-n]').forEach(r => r.addEventListener('click', () => { state.selNode = +r.dataset.n; render(); }));
}
function nodePanel(el, i) {
  const n = N[i], c = CUR(i) || { s: 0 }, w = win();
  const st = n.rt === 'exposure' ? CUR(i).s : c.s;
  let body = `<div class="card-h"><div style="min-width:0"><div class="card-s" style="margin:0 0 3px">${LAYER_NAME[n.l]} · ${n.rt === 'exposure' ? ET_NAME[n.et] : n.mat || n.so || n.rt}</div><div class="card-t mono" style="font-size:13px;word-break:break-all">${esc(n.n)}</div></div></div>
    <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:12px">${pill(st, n.rt === 'exposure' ? ST[st].trust : null)}${platTag(nodePlatAt(i, ND - 1))}${n.mf ? `<span class="tag">moved from ${PLAT_NAME[n.mf]} on ${dLab(DATES.indexOf(n.md))}</span>` : ''}${n.bm === 'ai_assisted' ? '<span class="tag ai">AI-built</span>' : ''}${!n.dec ? '<span class="tag obs">Not registered</span>' : ''}</div>`;
  if (st >= 2 && n.rt !== 'exposure') body += `<div class="callout ${st === 3 ? 'crit' : 'warn'}" style="margin-bottom:10px">${esc(nodeIssue(i))}${c.err ? `<div class="mono" style="font-size:10px;margin-top:4px;opacity:.85;white-space:normal">${esc(c.err)}</div>` : ''}</div>`;
  if (n.rt === 'exposure' && CUR(i).why.length) body += `<div class="callout ${st === 3 ? 'crit' : 'warn'}" style="margin-bottom:10px">${CUR(i).why.map(([u, s]) => `<div><b class="mono">${esc(N[u].n)}</b>: ${esc(nodeIssue(u))}</div>`).join('')}</div>`;
  const own = A.OWN[n.o];
  body += `<dl class="kv"><dt>Owner</dt><dd>${n.o ? esc(n.o) : '<b style="color:var(--crit-ink)">No owner</b>'}</dd>${own ? `<dt>Team</dt><dd>${esc(own.t)}</dd><dt>Slack</dt><dd class="mono">${esc(own.sl)}</dd>` : ''}${n.pj ? `<dt>dbt project</dt><dd class="mono">${esc(n.pj)}</dd>` : ''}${n.sch ? `<dt>Schema</dt><dd class="mono">${esc(n.sch)}</dd>` : ''}<dt>Documented</dt><dd>${n.desc ? 'Yes' : '<b style="color:var(--warn-ink)">No description</b>'}</dd>${n.rt === 'model' ? `<dt>Tests defined</dt><dd>${n.tc || '<b style="color:var(--warn-ink)">None</b>'}</dd>` : ''}</dl>`;
  if (n.rt === 'model') {
    const rt = A.RTD[i] || [], a7 = mean(rt.slice(ND - 7)), a28 = mean(rt.slice(ND - 35, ND - 7));
    const runs = sum(A.RUNSD[i] || [], w.from, w.to), errs = sum(A.ERRD[i] || [], w.from, w.to);
    body += `<div class="sec-label">Runtime, 90 days</div><div style="display:flex;justify-content:space-between;font-size:11px;margin-bottom:4px"><span>Last run <b>${fDur(c.rt)}</b> at ${tsLab(c.at)}</span><span>${a7 && a28 ? `<b style="color:${a7 / a28 - 1 > .25 ? 'var(--crit-ink)' : a7 / a28 - 1 < -.25 ? 'var(--good-ink)' : 'var(--ink)'}">${a7 / a28 > 1 ? '▲' : '▼'} ${Math.abs((a7 / a28 - 1) * 100).toFixed(0)}%</b> 7d vs 28d` : ''}</span></div>${lineSpark(rt, { w: 300, h: 44, from: w.from, lab: 'Runtime' })}
    <div class="sec-label">Runs in period</div><div style="font-size:11px">${fInt(runs)} runs · <b style="color:${errs ? 'var(--crit-ink)' : 'var(--good-ink)'}">${errs} failed</b>${c.rows != null ? ` · ${fK(c.rows)} rows last build` : ''}</div>`;
    const th = A.TH[i];
    if (th) body += `<div class="sec-label">Tests, last 30 days</div><div class="strip">${th.slice(ND - 30).split('').map((v, k) => `<span style="background:${['var(--line-soft)', 'var(--good)', 'var(--warn)', 'var(--crit)'][+v]}" ${tipAttr(tipRows(`${DOWN[DOW[ND - 30 + k]]} ${dLab(ND - 30 + k)}`, [['Worst result', ['No run', 'All passed', 'Warning', 'Failed'][+v]]]))}></span>`).join('')}</div><div style="font-size:10.5px;color:var(--ink-3);margin-top:4px">Latest: ${c.tp ?? 0} passing${c.tw ? `, ${c.tw} warning` : ''}${c.tf ? `, <b style="color:var(--crit-ink)">${c.tf} failing</b>` : ''}</div>`;
  } else if (n.rt === 'source') {
    const pctW = Math.min(1, c.lag / (c.ea * 1.25));
    body += `<div class="sec-label">Freshness now</div><div class="bullet" style="margin:4px 0 2px"><span class="bz" style="width:${c.wa / (c.ea * 1.25) * 100}%;background:var(--good-tint)"></span><span class="bz" style="width:${(c.ea - c.wa) / (c.ea * 1.25) * 100}%;background:var(--warn-tint)"></span><span class="bz" style="flex:1;background:var(--crit-tint)"></span><span class="bm" style="width:${pctW * 100}%;background:${STATUS_COL[c.s]}"></span></div><div style="display:flex;justify-content:space-between;font-size:10.5px;color:var(--ink-3)"><span>Lag <b style="color:var(--ink)">${fHrs(c.lag / 60)}</b></span><span>warn ${fHrs(c.wa / 60)} · error ${fHrs(c.ea / 60)}</span></div>
    <div class="sec-label">Daily worst lag, 90 days</div>${lineSpark((A.LAGD[i] || []).map(v => v == null ? null : v / 60), { w: 300, h: 44, from: w.from, color: 'var(--accent)', lab: 'Lag' })}`;
  } else if (n.rt === 'semantic') {
    const sm = A.SEM[i] || { ok: [], fail: new Array(ND).fill(0), skip: [], dur: [] }; const ok = sum(sm.ok, w.from, w.to), fl = sum(sm.fail, w.from, w.to), sk = sum(sm.skip, w.from, w.to);
    body += `<div class="sec-label">Refreshes in period</div><div style="font-size:11px">${fInt(ok)} succeeded · <b style="color:${fl ? 'var(--crit-ink)' : 'var(--ink)'}">${fl} failed</b> · ${sk} skipped · ${n.cn} connection${A.SEM[i] ? '' : ', queries the warehouse live so there is nothing to refresh'}</div>
    <div class="sec-label">Failed refreshes per day</div>${barSpark(sm.fail, { from: w.from, to: w.to, lab: 'Failed refreshes', color: 'var(--crit)' })}`;
  } else if (n.rt === 'exposure') {
    const sc = A.SCORE[i]; const cons = consumers30(i, w.from, w.to), ev = events(i, w.from, w.to), cost = expCost(i, w.from, w.to);
    body += `<div class="sec-label">Health score, 90 days</div><div style="font-size:11px;margin-bottom:4px">Now <b>${sc ? sc[ND - 1].toFixed(1) : '-'}</b> / 100</div>${sc ? lineSpark(sc, { w: 300, h: 44, from: w.from, lab: 'Health score' }) : ''}
    <div class="sec-label">In this period</div><dl class="kv"><dt>Usage</dt><dd>${fInt(ev)} ${CT_NAME[n.ct] || 'events'}</dd><dt>Daily consumers</dt><dd>${cons.toFixed(1)} on average</dd><dt>Est. cost</dt><dd>${fUsd(cost)}${ev ? ` · ${fUsd2(cost / ev)} per ${(CT_NAME[n.ct] || 'event').replace(/s$/, '')}` : ''}</dd></dl>`;
  }
  body += `<div style="margin-top:auto;padding-top:12px;display:flex;gap:8px">${n.rt !== 'exposure' ? `<button class="btn primary" id="np-blast"><svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="3"/><circle cx="12" cy="12" r="8"/></svg>Trace downstream impact</button>` : `<button class="btn primary" id="np-usage">See usage and cost</button>`}</div>`;
  el.innerHTML = body;
  const b1 = el.querySelector('#np-blast'); if (b1) b1.addEventListener('click', () => { state.blastNode = i; go('blast'); });
  const b2 = el.querySelector('#np-usage'); if (b2) b2.addEventListener('click', () => go('usage'));
}

/* ===================== 3. BLAST RADIUS ===================== */
function downstream(i) { const out = new Set(), st = [i]; while (st.length) { const v = st.pop(); (CHILDREN[v] || []).forEach(u => { if (!out.has(u)) { out.add(u); st.push(u); } }); } return out; }
function failRate(i, f, t) {
  const n = N[i];
  if (n.rt === 'model') { const r = sum(A.RUNSD[i] || [], f, t); return r ? sum(A.ERRD[i] || [], f, t) / r : 0; }
  if (n.rt === 'source') { const l = A.LAGD[i] || []; let bad = 0, tot = 0; for (let d = f; d <= t; d++) { if (l[d] == null) continue; tot++; if (l[d] > n.ea) bad++; } return tot ? bad / tot : 0; }
  if (n.rt === 'semantic') { const s = A.SEM[i]; if (!s) return 0; const ok = sum(s.ok, f, t), fl = sum(s.fail, f, t); return ok + fl ? fl / (ok + fl) : 0; }
  return 0;
}
RENDER.blast = el => {
  const i = state.blastNode, w = win(), n = N[i], c = CUR(i) || { s: 0 };
  el.style.gridTemplateColumns = '1fr 1fr'; el.style.gridTemplateRows = 'auto minmax(0, 1fr) 300px'; el.style.gap = '14px';
  const dn = downstream(i), exps = (FEEDS[i] || []).map(x => x[0]).filter(nodeInPlat);
  const models = [...dn].filter(u => N[u].rt === 'model'), sems = [...dn].filter(u => N[u].rt === 'semantic');
  const cons = exps.reduce((s, e) => s + consumers30(e, w.from, w.to), 0);
  const owners = [...new Set(exps.map(e => N[e].o).filter(Boolean))];
  const noOwner = exps.filter(e => !N[e].o).length;
  const und = A.OBS.filter(o => o.m == null && (o.node === i || dn.has(o.node)) && sum(o.q, w.from, w.to) > 0);
  const opts = [['source', 'Sources'], ['staging', 'Staging'], ['intermediate', 'Intermediate'], ['mart', 'Marts'], ['semantic', 'BI semantic layer']].map(([l, lab]) => `<optgroup label="${lab}">${N.map((x, k) => k).filter(k => N[k].l === l).sort((a, b) => N[a].n.localeCompare(N[b].n)).map(k => `<option value="${k}" ${k === i ? 'selected' : ''}>${esc(N[k].n)}${(CUR(k) || {}).s >= 2 ? '  ●' : ''}</option>`).join('')}</optgroup>`).join('');
  const msg = `Heads up: ${n.n} (${LAYER_NAME[n.l].toLowerCase()}, ${PLAT_NAME[n.p]}) ${c.s >= 2 ? 'has an issue: ' + nodeIssue(i).toLowerCase() : 'is being changed'}. It feeds ${exps.length} data product${exps.length === 1 ? '' : 's'} used by about ${Math.round(cons)} people, apps or agents a day: ${exps.map(e => `${N[e].n} (${N[e].o || 'no owner'}${A.OWN[N[e].o] ? ', ' + A.OWN[N[e].o].sl : ''})`).join('; ')}. Treat these numbers with caution until we confirm the fix here.`;
  const chip = (v, l, warn) => `<div class="bchip"><div class="bv num" ${warn ? 'style="color:var(--crit-ink)"' : ''}>${v}</div><div class="bl">${l}</div></div>`;
  // risk table across all nodes
  const risk = N.map((x, k) => k).filter(k => ['source', 'model', 'semantic'].includes(N[k].rt) && nodeInPlat(k)).map(k => { const ex = (FEEDS[k] || []).map(x => x[0]); const cs = ex.reduce((s, e) => s + consumers30(e, w.from, w.to), 0); const fr = failRate(k, w.from, w.to); return { k, ex: ex.length, cs, fr, r: cs * fr }; }).filter(x => x.r > 0).sort((a, b) => b.r - a.r).slice(0, 10);
  const rmax = risk.length ? risk[0].r : 1;
  // downstream columns
  const col = (lab, list) => `<div class="dcol"><div class="dcol-h">${lab}<span>${list.length}</span></div>${list.slice(0, 12).map(u => `<div class="dnode ${sKey((u === i ? c : CUR(u) || { s: 0 }).s)}" ${tipAttr(tipRows(esc(N[u].n), [['Status', ST[(CUR(u) || { s: 0 }).s].l], ['Owner', esc(N[u].o || 'No owner')]]))}><span class="dot ${sKey((CUR(u) || { s: 0 }).s)}"></span><span class="mono">${esc(N[u].n)}</span></div>`).join('')}${list.length > 12 ? `<div class="card-s">+ ${list.length - 12} more</div>` : ''}${!list.length ? '<div class="card-s">None</div>' : ''}</div>`;
  el.innerHTML = `
  <div class="card bhead" style="grid-column:1/-1">
    <div style="display:flex;flex-direction:column;gap:6px;min-width:0"><span class="ctl-label">Node to trace</span><select class="sel" id="bl-node" style="max-width:300px">${opts}</select><span style="display:flex;gap:6px">${pill(c.s)}${platTag(n.p)}<span class="tag">${LAYER_NAME[n.l]}</span></span></div>
    <div class="bsum"><div class="bsum-t">If <span class="mono">${esc(n.n)}</span> breaks, <b>${exps.length} data product${exps.length === 1 ? '' : 's'}</b> and about <b>${Math.round(cons).toLocaleString('en-GB')} daily consumers</b> are affected.</div><div class="card-s">${c.s >= 2 ? esc(nodeIssue(i)) : 'Currently healthy. Use this view before changing or deprecating it.'}</div>
    <div class="bchips">${chip(models.length, 'downstream models')}${chip(sems.length, 'BI semantic objects')}${chip(exps.length, 'exposures')}${chip(owners.length, 'owners to notify')}${chip(und.length ? [...new Set(und.map(o => o.p))].length : 0, 'unregistered readers', und.length)}</div></div>
    <button class="btn" id="bl-copy" title="Copy a ready-to-send incident message"><svg viewBox="0 0 24 24"><rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V5a1 1 0 0 0-1-1H5a1 1 0 0 0-1 1v10a1 1 0 0 0 1 1h3"/></svg><span>Copy incident message</span></button>
  </div>
  <div class="card"><div class="card-h"><div><div class="card-t">Who to tell</div><div class="card-s">Affected exposures, their owners and how many consumers used them each day on average in this period</div></div></div>
    <div class="card-body scroll"><table class="t"><thead><tr><th>Exposure</th><th>Type</th><th>Owner</th><th>Slack</th><th class="r">Daily consumers</th><th>Status</th></tr></thead><tbody>${exps.sort((a, b) => consumers30(b, w.from, w.to) - consumers30(a, w.from, w.to)).map(e => `<tr class="click" data-exp="${e}"><td><b style="font-weight:600">${esc(N[e].n)}</b></td><td>${esc(expMeta(e))}</td><td>${N[e].o ? esc(N[e].o) : '<b style="color:var(--crit-ink)">No owner</b>'}</td><td class="mono">${A.OWN[N[e].o] ? esc(A.OWN[N[e].o].sl) : '-'}</td><td class="r">${consumers30(e, w.from, w.to).toFixed(1)}</td><td>${pill(CUR(e).s, ST[CUR(e).s].trust)}</td></tr>`).join('') || '<tr><td colspan="6" class="empty">Nothing downstream on this platform.</td></tr>'}</tbody></table>
    ${und.length ? `<div class="callout warn" style="margin-top:10px"><b>Not on this list:</b> ${[...new Set(und.map(o => o.p))].map(p => `<span class="mono">${esc(p)}</span>`).join(', ')} also read${und.length === 1 ? 's' : ''} this data but ${und.length === 1 ? 'is' : 'are'} not registered as an exposure, so nobody would be told. See Governance.</div>` : ''}${noOwner ? `<div class="callout crit" style="margin-top:8px">${noOwner} affected exposure${noOwner === 1 ? ' has' : 's have'} no owner to notify.</div>` : ''}</div></div>
  <div class="card"><div class="card-h"><div><div class="card-t">Downstream path</div><div class="card-s">Everything built on this node, by layer</div></div></div><div class="card-body scroll"><div class="dcols">${col('Models', models.sort((a, b) => N[a].lo - N[b].lo))}${col('BI semantic layer', sems)}${col('Exposures', exps)}</div></div></div>
  <div class="card" style="grid-column:1/-1"><div class="card-h"><div><div class="card-t">Riskiest nodes in this period</div><div class="card-s">Risk = average daily consumers downstream × failure rate. Failure rate is failed runs for models, days past the error threshold for sources, and failed refreshes for BI semantic objects. Click a row to trace it.</div></div></div>
    <div class="card-body scroll"><table class="t"><thead><tr><th>#</th><th>Node</th><th>Layer</th><th>Platform</th><th class="r">Exposures fed</th><th class="r">Daily consumers</th><th class="r">Failure rate</th><th style="width:28%">Risk score</th><th>Now</th></tr></thead><tbody>${risk.map((x, r) => `<tr class="click ${x.k === i ? 'sel' : ''}" data-k="${x.k}"><td class="num" style="color:var(--ink-3)">#${r + 1}</td><td class="mono">${esc(N[x.k].n)}</td><td>${LAYER_NAME[N[x.k].l]}</td><td>${platTag(N[x.k].p)}</td><td class="r">${x.ex}</td><td class="r">${x.cs.toFixed(0)}</td><td class="r">${fPct(x.fr, 1)}</td><td><div class="bar-cell"><div class="bt"><span style="width:${x.r / rmax * 100}%"></span></div><span class="num" style="min-width:34px;text-align:right">${x.r.toFixed(1)}</span></div></td><td>${pill((CUR(x.k) || { s: 0 }).s)}</td></tr>`).join('')}</tbody></table></div></div>`;
  el.querySelector('#bl-node').addEventListener('change', ev => { state.blastNode = +ev.target.value; render(); });
  el.querySelectorAll('tr[data-k]').forEach(r => r.addEventListener('click', () => { state.blastNode = +r.dataset.k; render(); }));
  el.querySelectorAll('tr[data-exp]').forEach(r => r.addEventListener('click', () => { state.selExp = +r.dataset.exp; state.selNode = i; go('lineage'); }));
  const cb = el.querySelector('#bl-copy');
  cb.addEventListener('click', () => {
    const done = t => { cb.querySelector('span').textContent = t; setTimeout(() => cb.querySelector('span').textContent = 'Copy incident message', 1800); };
    try { navigator.clipboard.writeText(msg).then(() => done('Copied'), () => fallback()); } catch (e) { fallback(); }
    function fallback() { const ta = document.createElement('textarea'); ta.value = msg; ta.style.cssText = 'position:absolute;left:20px;top:20px;width:600px;height:120px;z-index:60'; stage.appendChild(ta); ta.select(); done('Press Ctrl+C to copy'); ta.addEventListener('blur', () => ta.remove()); }
  });
};
