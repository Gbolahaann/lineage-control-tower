/* ===================== 7. PERFORMANCE & COST ===================== */
const INCR_ROWS = 10e6; // generator/config.yaml incremental_min_rows
const matNow = i => ({ t: 'table', i: 'incremental', v: 'view' })[(A.MATD[i] || '').slice(-1)] || N[i].mat;
function rtTrend(i) { const rt = A.RTD[i] || []; const a7 = mean(rt.slice(ND - 7)), a28 = mean(rt.slice(ND - 35, ND - 7)); return a7 && a28 ? a7 / a28 - 1 : null; }
function rtTrendAt(i, to) { const rt = A.RTD[i] || []; const a7 = mean(rt.slice(Math.max(0, to - 6), to + 1)), a28 = mean(rt.slice(Math.max(0, to - 34), Math.max(0, to - 6))); return a7 && a28 ? a7 / a28 - 1 : null; }
RENDER.perf = el => {
  const w = win();
  el.style.gridTemplateColumns = '1.45fr 1fr'; el.style.gridTemplateRows = '96px 290px minmax(0, 1fr)'; el.style.gap = '14px';
  const costD = daily('cost'); const tot = sum(costD, w.from, w.to), ptot = w.hasPrior ? sum(costD, w.pfrom, w.pto) : null;
  const mods = MODELS.filter(nodeInPlat).map(i => { const rt = A.RTD[i] || []; return { i, rt: mean(rt.slice(w.from, w.to + 1)), cost: sum(A.COSTD[i] || [], w.from, w.to), tr: rtTrendAt(i, w.to), peakTr: Math.max(...Array.from({ length: Math.max(1, w.to - w.from + 1) }, (_, k) => rtTrendAt(i, w.from + k) ?? -1)), rows: A.ROWSMAX[i], mat: matNow(i) }; });
  // a candidate was a full-refresh table, over the row threshold, with runtime 25%+ above its 28-day average at some point in the window
  mods.forEach(m => { const md = A.MATD[m.i] || ''; m.cand = (m.rows || 0) > INCR_ROWS && Array.from({ length: w.to - w.from + 1 }, (_, k) => w.from + k).some(d => md[d] === 't' && (rtTrendAt(m.i, d) ?? 0) > .25); m.fixed = m.cand && md[ND - 1] === 'i'; m.fixDay = m.fixed ? md.indexOf('i') : null; });
  const cands = mods.filter(m => m.cand);
  const slow = [...mods].sort((a, b) => (b.rt || 0) - (a.rt || 0)).slice(0, 6);
  const top = [...mods].sort((a, b) => b.cost - a.cost).slice(0, 15);
  const sess = byId['model.acme_product.fct_sessions'];
  const expC = EXP.filter(nodeInPlat).map(e => ({ e, c: expCost(e, w.from, w.to) })).sort((a, b) => b.c - a.c).slice(0, 12);
  el.innerHTML = `<div style="grid-column:1/-1">${miniKpis([
    { t: 'Warehouse cost', v: fUsd(tot), c: change(tot, ptot, { goodUp: false }) },
    { t: 'Average per day', v: fUsd(tot / state.period), c: `${platsOn().map(p => `<span style="color:${PLAT_COL[p]};font-weight:600">${PLAT_NAME[p]}</span> ${fUsd(sum(A.S.cost[p], w.from, w.to) / state.period)}`).join(' · ')}` },
    { t: 'Slowest model', v: `<span class="mono" style="font-size:15px">${esc(N[slow[0].i].n)}</span>`, c: `${fDur(slow[0].rt)} average run${slow[0].tr != null ? ` · ${slow[0].tr > 0 ? '▲' : '▼'} ${Math.abs(slow[0].tr * 100).toFixed(0)}% 7d vs 28d` : ''}` },
    { t: 'Incremental candidates', v: `${cands.filter(m => !m.fixed).length}<small>open</small>`, c: cands.length ? cands.map(m => m.fixed ? `<span class="down-good">${esc(N[m.i].n)} switched ${dLab(m.fixDay)}</span>` : `<span class="up-bad">${esc(N[m.i].n)}</span>`).join(', ') : 'None in this period' }])}</div>
  <div class="card"><div class="card-h"><div><div class="card-t">Cost by platform, per day</div><div class="card-s">Estimated USD. Redshift winds down as marketing models move to Snowflake.</div></div><div class="right legend">${platsOn().map(p => `<span><i style="background:${PLAT_COL[p]}"></i>${PLAT_NAME[p]}</span>`).join('')}</div></div><div class="card-body" id="pf-cost"></div></div>
  <div class="card"><div class="card-h"><div><div class="card-t">Runtime of the six slowest models</div><div class="card-s">Average successful run per day. The highlighted line is the biggest change.</div></div></div><div class="card-body" id="pf-rt"></div></div>
  <div class="card"><div class="card-h"><div><div class="card-t">Most expensive models in this period</div><div class="card-s">Dot shows the platform. Flag shows full-refresh tables over 10M rows whose runtime grew more than 25%. Click a row to trace it.</div></div></div>
    <div class="card-body scroll"><table class="t"><thead><tr><th>Model</th><th>Built as</th><th class="r">Avg runtime</th><th class="r">7d vs 28d</th><th class="r">Largest build</th><th class="r">Cost</th><th></th></tr></thead><tbody>${top.map(m => `<tr class="click" data-blast="${m.i}"><td class="mono"><span class="pdot" style="background:${PLAT_COL[N[m.i].p]};margin-right:7px" title="${PLAT_NAME[N[m.i].p]}"></span>${esc(N[m.i].n)}</td><td>${m.mat}${m.fixed ? ' <span style="color:var(--ink-3)">(was table)</span>' : ''}</td><td class="r">${fDur(m.rt)}</td><td class="r" style="color:${m.tr > .25 ? 'var(--crit-ink)' : m.tr < -.25 ? 'var(--good-ink)' : 'var(--ink-2)'};font-weight:${Math.abs(m.tr || 0) > .25 ? 600 : 400}">${m.tr == null ? '-' : (m.tr > 0 ? '▲ ' : '▼ ') + Math.abs(m.tr * 100).toFixed(0) + '%'}</td><td class="r">${m.rows ? fK(m.rows) : '-'}</td><td class="r"><b>${fUsd(m.cost)}</b></td><td>${m.fixed ? '<span class="pill good">' + ICON.good + 'Switched ' + dLab(m.fixDay) + '</span>' : m.cand ? '<span class="pill warn">' + ICON.warn + 'Make incremental</span>' : ''}</td></tr>`).join('')}</tbody></table></div></div>
  <div class="card"><div class="card-h"><div><div class="card-t">What each data product costs to keep running</div><div class="card-s">Upstream build cost split evenly across the exposures each model feeds, plus the product's own queries</div></div></div><div class="card-body scroll">${hbars(expC.map(x => ({ l: esc(N[x.e].n) + (N[x.e].dec ? '' : ' <span class="tag obs">unregistered</span>'), v: x.c, tip: tipRows(esc(N[x.e].n), [['Cost in period', fUsd(x.c)], ['Usage', fInt(events(x.e, w.from, w.to)) + ' ' + (CT_NAME[N[x.e].ct] || 'events')], ['Cost per use', events(x.e, w.from, w.to) ? fUsd2(x.c / events(x.e, w.from, w.to)) : '-']]) })), { fmt: fUsd })}</div></div>`;
  timeChart(el.querySelector('#pf-cost'), { type: 'bar', series: platsOn().map(p => ({ name: PLAT_NAME[p], color: PLAT_COL[p], vals: A.S.cost[p] })), from: 0, to: ND - 1, band: [w.from, w.to], fmt: fUsd2, yFmt: v => '$' + fK(v), ann: [{ d: DATES.indexOf('2026-09-03'), label: 'HubSpot moves' }, { d: DATES.indexOf('2026-09-11'), label: 'Ads move' }, { d: DATES.indexOf('2026-10-04'), label: 'fct_sessions fixed', color: 'var(--good-ink)' }], label: 'Cost by platform per day' });
  const biggest = slow.reduce((a, b) => Math.abs(b.peakTr) > Math.abs(a.peakTr) ? b : a, slow[0]);
  timeChart(el.querySelector('#pf-rt'), { type: 'line', series: slow.map(m => ({ name: N[m.i].n, color: m === biggest ? 'var(--accent)' : '#B9C0C7', w: m === biggest ? 2.4 : 1.3, vals: (A.RTD[m.i] || []).map(v => v == null ? null : v / 60) })), from: 0, to: ND - 1, band: [w.from, w.to], fmt: v => v.toFixed(1) + ' min', yFmt: v => v.toFixed(0) + 'm', endLabels: true, mr: 150, label: 'Runtime of the slowest models' });
  el.querySelectorAll('[data-blast]').forEach(r => r.addEventListener('click', () => { state.blastNode = +r.dataset.blast; go('blast'); }));
};

/* ===================== 8. USAGE & ADOPTION ===================== */
const ZOMBIE = { perMonth: 10, costPerUse: 5 }; // generator/config.yaml: zombie_max_events_30d, zombie_min_cost_per_event_usd
RENDER.usage = el => {
  const w = win();
  el.style.gridTemplateColumns = '1fr 1fr'; el.style.gridTemplateRows = '330px minmax(0, 1fr)'; el.style.gap = '14px';
  const ex = EXP.filter(nodeInPlat).map(e => { const ev = events(e, w.from, w.to), c = expCost(e, w.from, w.to), pm = ev / state.period * 30; return { e, ev, c, pm, cpu: ev ? c / ev : Infinity, cons: consumers30(e, w.from, w.to), z: pm < ZOMBIE.perMonth && (ev ? c / ev : Infinity) > ZOMBIE.costPerUse && N[e].dec }; });
  const prior = e => w.hasPrior ? events(e, w.pfrom, w.pto) : null;
  const types = [['view', 'Dashboard and hub views', 'var(--accent)'], ['query', 'Notebook and model queries', 'var(--accent)'], ['app_session', 'Data app sessions', 'var(--accent)'], ['agent_call', 'AI agent calls', 'var(--accent)']];
  const sems = SEMS.filter(nodeInPlat).map(i => { const s = A.SEM[i] || { ok: new Array(ND).fill(0), fail: new Array(ND).fill(0), skip: new Array(ND).fill(0), dur: [] }; const ok = sum(s.ok, w.from, w.to), fl = sum(s.fail, w.from, w.to), sk = sum(s.skip, w.from, w.to); return { i, ok, fl, sk, r: ok + fl ? ok / (ok + fl) : null, dur: mean(s.dur.slice(w.from, w.to + 1)) }; }).sort((a, b) => b.fl - a.fl || (a.r ?? 1) - (b.r ?? 1));
  el.innerHTML = `
  <div class="card"><div class="card-h"><div><div class="card-t">Cost against usage</div><div class="card-s">Each dot is a data product. Shaded corner: under ${ZOMBIE.perMonth} uses in 30 days and over $${ZOMBIE.costPerUse} per use, the candidates to retire. Both axes are logarithmic.</div></div></div><div class="card-body" id="us-scatter"></div><div class="legend" style="margin-top:6px"><span><i style="background:var(--accent);border-radius:50%"></i>Built by hand</span><span><i style="background:#5B5FC7;border-radius:50%"></i>AI-built</span><span><i style="background:var(--warn);border-radius:50%"></i>Unregistered</span><span><i style="background:var(--crit);border-radius:50%"></i>Retire candidate</span></div></div>
  <div class="card"><div class="card-h"><div><div class="card-t">Consumption by consumer type, per day</div><div class="card-s">Each type is counted in its own unit, so each gets its own scale</div></div></div><div class="card-body"><div class="smults">${types.map(t => `<div class="sm"><div class="sm-h"><span>${t[1]}</span><b class="num">${fK(EXP.filter(e => N[e].ct === t[0] && N[e].dec && nodeInPlat(e)).reduce((s, e) => s + events(e, w.from, w.to), 0))}</b></div><div class="sm-c" data-ct="${t[0]}"></div></div>`).join('')}</div></div></div>
  <div class="card"><div class="card-h"><div><div class="card-t">Data products ranked by use</div><div class="card-s">Usage in this period, change against the period before, and cost per use. Click a row to open its lineage.</div></div></div>
    <div class="card-body scroll"><table class="t"><thead><tr><th>Data product</th><th>Type</th><th>Built</th><th class="r">Uses</th><th class="r">Change</th><th class="r">Daily consumers</th><th class="r">Cost per use</th><th></th></tr></thead><tbody>${[...ex].sort((a, b) => b.ev - a.ev).map(x => { const p = prior(x.e); const ch = p ? (x.ev - p) / p : null; return `<tr class="click" data-exp="${x.e}"><td><b style="font-weight:600">${esc(N[x.e].n)}</b></td><td>${esc(expMeta(x.e))}</td><td>${N[x.e].bm === 'ai_assisted' ? '<span class="tag ai">AI-built</span>' : '<span class="tag">By hand</span>'}</td><td class="r">${fInt(x.ev)} <span style="color:var(--ink-3)">${(CT_NAME[N[x.e].ct] || '').split(' ').pop()}</span></td><td class="r" style="color:${ch == null ? 'var(--ink-3)' : ch < -.1 ? 'var(--crit-ink)' : ch > .1 ? 'var(--good-ink)' : 'var(--ink-2)'}">${ch == null ? '-' : (ch > 0 ? '▲ ' : '▼ ') + Math.abs(ch * 100).toFixed(0) + '%'}</td><td class="r">${x.cons.toFixed(1)}</td><td class="r">${isFinite(x.cpu) ? fUsd2(x.cpu) : '-'}</td><td>${x.z ? '<span class="pill crit">' + ICON.crit + 'Retire?</span>' : !N[x.e].dec ? '<span class="tag obs">Not registered</span>' : ''}</td></tr>`; }).join('')}</tbody></table></div></div>
  <div class="card"><div class="card-h"><div><div class="card-t">BI semantic layer refreshes</div><div class="card-s">dbt can be green while an extract fails. This is where that shows.</div></div></div>
    <div class="card-body scroll"><table class="t"><thead><tr><th>Semantic object</th><th>Tool</th><th>Mode</th><th class="r">Success</th><th class="r">Failed</th><th class="r">Avg refresh</th><th>Failures per day</th></tr></thead><tbody>${sems.map(x => `<tr class="click" data-blast="${x.i}"><td class="mono">${esc(N[x.i].n)}</td><td>${BI_NAME[N[x.i].bi]}</td><td>${N[x.i].cn}</td><td class="r" style="color:${x.r != null && x.r < .98 ? 'var(--crit-ink)' : 'var(--ink)'};font-weight:${x.r != null && x.r < .98 ? 600 : 400}">${fPct(x.r, 1)}</td><td class="r">${x.fl}</td><td class="r">${fDur(x.dur)}</td><td style="width:150px">${!A.SEM[x.i] ? '<span class="card-s">Live, no extract</span>' : barSpark(A.SEM[x.i].fail, { from: w.from, to: w.to, lab: 'Failed refreshes', color: 'var(--crit)', h: 18 })}</td></tr>`).join('')}</tbody></table></div></div>`;
  // scatter
  const box = el.querySelector('#us-scatter'); const W = box.clientWidth, H = box.clientHeight, m = { l: 46, r: 16, t: 16, b: 30 };
  const pts = ex.filter(x => x.ev > 0 && x.c > 0);
  if (!pts.length) { box.innerHTML = `<div class="empty">No data products read from ${PLAT_NAME[state.plat] || 'this platform'} in this period. Redshift models moved to Snowflake in September.</div>`; }
  else {
  const lx = v => Math.log10(v), xs = pts.map(x => lx(x.c)), ys = pts.map(x => lx(x.ev));
  const x0 = Math.floor(Math.min(...xs)), x1 = Math.ceil(Math.max(...xs)), y0 = Math.floor(Math.min(...ys)), y1 = Math.ceil(Math.max(...ys));
  const X = v => m.l + (lx(v) - x0) / (x1 - x0) * (W - m.l - m.r), Y = v => H - m.b - (lx(v) - y0) / (y1 - y0) * (H - m.t - m.b);
  let s = `<svg width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" role="img" aria-label="Cost against usage">`;
  // zombie region: uses below threshold (scaled to period) AND cost per use above threshold => y < thr and y < x/cpu
  const thrY = ZOMBIE.perMonth * state.period / 30;
  let poly = []; const steps = 40; for (let k = 0; k <= steps; k++) { const c = Math.pow(10, x0 + (x1 - x0) * k / steps); poly.push([X(c), Y(Math.max(Math.pow(10, y0), Math.min(thrY, c / ZOMBIE.costPerUse)))]); }
  s += `<path d="M${X(Math.pow(10, x0))} ${Y(Math.pow(10, y0))}L${poly.map(p => p.join(' ')).join('L')}L${X(Math.pow(10, x1))} ${Y(Math.pow(10, y0))}Z" fill="var(--crit-tint)" opacity=".85"/>`;
  s += '<g class="axis">';
  for (let k = x0; k <= x1; k++) s += `<line x1="${X(10 ** k)}" x2="${X(10 ** k)}" y1="${m.t}" y2="${H - m.b}" stroke="var(--line-soft)"/><text x="${X(10 ** k)}" y="${H - m.b + 13}" text-anchor="middle">$${fK(10 ** k)}</text>`;
  for (let k = y0; k <= y1; k++) s += `<line x1="${m.l}" x2="${W - m.r}" y1="${Y(10 ** k)}" y2="${Y(10 ** k)}" stroke="var(--line-soft)"/><text x="${m.l - 6}" y="${Y(10 ** k) + 3}" text-anchor="end">${fK(10 ** k)}</text>`;
  s += `<text x="${W - m.r}" y="${H - 3}" text-anchor="end">Cost in period →</text><text x="${m.l}" y="${m.t + 8}" text-anchor="start" dx="4">↑ Uses in period</text></g>`;
  const lab = [];
  pts.forEach(x => {
    const col = x.z ? 'var(--crit)' : !N[x.e].dec ? 'var(--warn)' : N[x.e].bm === 'ai_assisted' ? '#5B5FC7' : 'var(--accent)';
    s += `<circle cx="${X(x.c)}" cy="${Y(x.ev)}" r="${x.z ? 6 : 4.5}" fill="${col}" fill-opacity=".85" stroke="#fff" stroke-width="1.5" style="cursor:pointer" data-exp="${x.e}" ${tipAttr(tipRows(esc(N[x.e].n), [['Cost', fUsd(x.c)], ['Uses', fInt(x.ev) + ' ' + (CT_NAME[N[x.e].ct] || '')], ['Cost per use', fUsd2(x.cpu)], ['Built', N[x.e].bm === 'ai_assisted' ? 'AI-assisted' : 'By hand']]))}/>`;
    if (x.z || !N[x.e].dec || x.ev === Math.max(...pts.map(p => p.ev))) lab.push(x);
  });
  const placed = [];
  lab.sort((a, b) => Y(a.ev) - Y(b.ev)).forEach(x => {
    const txt = N[x.e].n.replace('Unregistered: ', ''), px = X(x.c), right = px > W * .62; let py = Y(x.ev) + 3.5;
    while (placed.some(p => Math.abs(p.y - py) < 12 && Math.abs(p.x - px) < 170)) py += 12;
    placed.push({ x: px, y: py });
    s += `<text x="${right ? px - 9 : px + 9}" y="${py}" text-anchor="${right ? 'end' : 'start'}" font-size="10" fill="var(--ink)" font-weight="${x.z ? 600 : 400}" paint-order="stroke" stroke="#fff" stroke-width="3">${esc(txt)}</text>`;
  });
  box.innerHTML = s + '</svg>';
  }
  box.querySelectorAll('[data-exp]').forEach(c => c.addEventListener('click', () => { state.selExp = +c.dataset.exp; state.selNode = null; go('lineage'); }));
  // small multiples
  el.querySelectorAll('.sm-c').forEach(c => { const ct = c.dataset.ct; const vals = Array.from({ length: ND }, (_, d) => EXP.filter(e => N[e].ct === ct && N[e].dec && nodeInPlat(e)).reduce((s, e) => s + ((A.CONS[e] || { ev: [] }).ev[d] || 0), 0)); timeChart(c, { type: 'bar', series: [{ name: CT_NAME[ct], color: 'var(--accent)', vals }], from: w.from, to: w.to, fmt: fInt, yFmt: fK, ml: 34, label: CT_NAME[ct] }); });
  el.querySelectorAll('tr[data-exp]').forEach(r => r.addEventListener('click', () => { state.selExp = +r.dataset.exp; state.selNode = null; go('lineage'); }));
  el.querySelectorAll('tr[data-blast]').forEach(r => r.addEventListener('click', () => { state.blastNode = +r.dataset.blast; go('blast'); }));
};

/* ===================== 9. GOVERNANCE ===================== */
RENDER.gov = el => {
  const w = win();
  el.style.gridTemplateColumns = '1fr 1fr 1fr'; el.style.gridTemplateRows = '96px minmax(0, 1fr) minmax(0, 1fr)'; el.style.gap = '14px';
  const mods = MODELS.filter(nodeInPlat), exps = EXP.filter(nodeInPlat);
  const docC = mods.filter(i => N[i].desc).length / mods.length, testC = mods.filter(i => N[i].tc > 0).length / mods.length, ownC = exps.filter(e => N[e].o).length / exps.length;
  const obs = A.OBS.filter(o => nodeInPlat(o.node) && sum(o.q, w.from, w.to) > 0);
  const prin = [...new Set(obs.map(o => o.p))]; const mapped = prin.filter(p => obs.some(o => o.p === p && o.m != null));
  const und = prin.filter(p => !obs.some(o => o.p === p && o.m != null)).map(p => { const rows = obs.filter(o => o.p === p); return { p, pt: rows[0].pt, nodes: rows.map(o => o.node), q: rows.reduce((s, o) => s + sum(o.q, w.from, w.to), 0), gb: rows.reduce((s, o) => s + o.gb, 0), first: rows.map(o => o.first).sort()[0], inf: rows[0].inf }; });
  const domains = [...new Set(N.filter(n => n.rt === 'model' || n.rt === 'exposure').map(n => n.d))].sort();
  const cell = v => v == null ? '<td class="r" style="color:var(--ink-4)">-</td>' : `<td class="r"><span class="hcell" style="background:${v >= .9 ? 'var(--good-tint)' : v >= .7 ? 'var(--warn-tint)' : 'var(--crit-tint)'};color:${v >= .9 ? 'var(--good-ink)' : v >= .7 ? 'var(--warn-ink)' : 'var(--crit-ink)'}">${fPct(v, 0)}</span></td>`;
  const teams = [...new Set(N.filter(n => n.t && (n.rt === 'model' || n.rt === 'source')).map(n => n.t))].map(t => { const ns = N.map((n, i) => i).filter(i => N[i].t === t && (N[i].rt === 'model' || N[i].rt === 'source') && nodeInPlat(i)); if (!ns.length) return null; const ms = ns.filter(i => N[i].rt === 'model'); const d = ns.filter(i => N[i].desc).length / ns.length; const tc = ms.length ? ms.filter(i => N[i].tc > 0).length / ms.length : 1; return { t, n: ns.length, d, tc, h: (d + tc) / 2 }; }).filter(Boolean).sort((a, b) => a.h - b.h);
  const sprawl = exps.filter(e => N[e].bm === 'ai_assisted' && N[e].et === 'dashboard');
  const sprawlSem = {}; sprawl.forEach(e => UPS(e).filter(([u, d]) => d === 1 && N[u].rt === 'semantic').forEach(([u]) => sprawlSem[u] = (sprawlSem[u] || 0) + 1));
  const topSem = Object.entries(sprawlSem).sort((a, b) => b[1] - a[1])[0];
  const overlap = topSem ? exps.filter(e => N[e].bm !== 'ai_assisted' && UPS(e).some(([u, d]) => d === 1 && u === +topSem[0])) : [];
  const noOwn = exps.filter(e => !N[e].o), noTests = mods.filter(i => !N[i].tc), noDesc = mods.filter(i => !N[i].desc);
  const mat = { high: 0, medium: 0, low: 0 }; exps.forEach(e => mat[N[e].mt] = (mat[N[e].mt] || 0) + 1);
  el.innerHTML = `<div style="grid-column:1/-1">${miniKpis([
    { t: 'Ownership coverage', v: fPct(ownC, 0), c: `${noOwn.length} of ${exps.length} exposures have no owner` },
    { t: 'Documentation coverage', v: fPct(docC, 0), c: `${noDesc.length} models have no description` },
    { t: 'Test coverage', v: fPct(testC, 0), c: `${noTests.length} models have no tests` },
    { t: 'Declared consumers', v: fPct(prin.length ? mapped.length / prin.length : null, 0), c: `<span class="${und.length ? 'up-bad' : 'flat'}">${und.length} reader${und.length === 1 ? '' : 's'} in query history</span> not registered as exposures` }])}</div>
  <div class="card" style="grid-column:1/3"><div class="card-h"><div><div class="card-t">Unregistered consumers found in query history</div><div class="card-s">These read warehouse data in this period but no exposure accounts for them. Nobody is told when their data breaks, and their cost has no owner.</div></div><div class="right"><span class="tag">From warehouse query history</span></div></div>
    <div class="card-body scroll"><table class="t"><thead><tr><th>Principal</th><th>Kind</th><th>Reads</th><th class="r">Queries</th><th class="r">Scanned</th><th class="r">Cost</th><th>First seen</th><th>Likely what</th></tr></thead><tbody>${und.sort((a, b) => b.q - a.q).map(x => `<tr class="click" data-exp="${x.inf}"><td class="mono"><b style="font-weight:500">${esc(x.p)}</b></td><td>${{ service: 'Service account', human: 'Personal login', agent: 'Agent', app: 'App' }[x.pt] || x.pt}</td><td class="mono" style="white-space:normal;max-width:220px">${x.nodes.map(n => esc(N[n].n)).join(', ')}</td><td class="r">${fInt(x.q)}</td><td class="r">${fInt(x.gb)} GB</td><td class="r">${fUsd(A.PCOST[x.p])}</td><td>${dLab(DATES.indexOf(x.first))}</td><td>${x.inf != null ? esc(N[x.inf].n.replace('Unregistered: ', '')) : '-'}</td></tr>`).join('') || '<tr><td colspan="8" class="empty">Every reader is registered.</td></tr>'}</tbody></table>
    <div class="callout info" style="margin-top:10px">Register each one as a dbt exposure with an owner and its own service account, then it shows up in Lineage, Blast radius and Usage like everything else.</div></div></div>
  <div class="card"><div class="card-h"><div><div class="card-t">AI-built dashboard sprawl</div><div class="card-s">${sprawl.length} AI-assisted dashboards${topSem ? `, ${topSem[1]} of them on <span class="mono">${esc(N[topSem[0]].n)}</span>` : ''}</div></div></div>
    <div class="card-body scroll">${sprawl.map(e => { const ev = events(e, w.from, w.to), p = w.hasPrior ? events(e, w.pfrom, w.pto) : null; return `<div class="spr" data-exp="${e}"><div style="display:flex;justify-content:space-between;gap:8px"><b>${esc(N[e].n)}</b><span class="num" style="color:var(--ink-2)">${fInt(ev)} views${p ? ` <span style="color:${ev < p ? 'var(--crit-ink)' : 'var(--good-ink)'}">${ev < p ? '▼' : '▲'} ${Math.abs((ev - p) / p * 100).toFixed(0)}%</span>` : ''}</span></div><div class="card-s">${esc(N[e].o)} · created ${dLab(Math.max(0, DATES.indexOf(N[e].cd)))} · maturity ${N[e].mt}</div></div>`; }).join('')}
    ${overlap.length ? `<div class="callout warn" style="margin-top:8px">They read the same semantic object as ${overlap.map(e => `<b>${esc(N[e].n)}</b>`).join(' and ')}. Consider merging them into one governed view before the numbers drift apart.</div>` : ''}</div></div>
  <div class="card"><div class="card-h"><div><div class="card-t">Coverage by domain</div><div class="card-s">Green from 90%, amber from 70%</div></div></div><div class="card-body scroll"><table class="t"><thead><tr><th>Domain</th><th class="r">Models</th><th class="r">Docs</th><th class="r">Tests</th><th class="r">Owned</th></tr></thead><tbody>${domains.map(d => { const m = mods.filter(i => N[i].d === d), e = exps.filter(i => N[i].d === d); return `<tr><td>${d}</td><td class="r">${m.length}</td>${cell(m.length ? m.filter(i => N[i].desc).length / m.length : null)}${cell(m.length ? m.filter(i => N[i].tc > 0).length / m.length : null)}${cell(e.length ? e.filter(i => N[i].o).length / e.length : null)}</tr>`; }).join('')}</tbody></table></div></div>
  <div class="card"><div class="card-h"><div><div class="card-t">Hygiene score by team</div><div class="card-s">Average of documentation and test coverage for the sources and models each team owns</div></div></div><div class="card-body scroll">${hbars(teams.map(t => ({ l: t.t, v: t.h, c: t.h >= .9 ? 'var(--good)' : t.h >= .7 ? 'var(--warn)' : 'var(--crit)', tip: tipRows(t.t, [['Nodes owned', t.n], ['Documented', fPct(t.d, 0)], ['Tested', fPct(t.tc, 0)]]) })), { fmt: v => fPct(v, 0), max: 1 })}
    <div class="sec-label">Exposure maturity</div><div class="matbar">${['high', 'medium', 'low'].map(k => `<span style="flex:${mat[k] || 0}" class="m-${k}">${k} ${mat[k] || 0}</span>`).join('')}</div></div></div>
  <div class="card"><div class="card-h"><div><div class="card-t">Gaps to close</div><div class="card-s">The quickest wins for the next sprint</div></div></div><div class="card-body scroll">
    <div class="sec-label" style="margin-top:0">No owner</div>${noOwn.map(e => `<div class="gap-row"><span class="dot crit"></span>${esc(N[e].n)}</div>`).join('') || '<div class="card-s">None</div>'}
    <div class="sec-label">No tests</div>${noTests.map(i => `<div class="gap-row mono"><span class="dot warn"></span>${esc(N[i].n)}</div>`).join('') || '<div class="card-s">None</div>'}
    <div class="sec-label">No description</div>${noDesc.map(i => `<div class="gap-row mono"><span class="dot warn"></span>${esc(N[i].n)}</div>`).join('') || '<div class="card-s">None</div>'}</div></div>`;
  el.querySelectorAll('[data-exp]').forEach(r => r.addEventListener('click', () => { const v = +r.dataset.exp; if (!isNaN(v)) { state.selExp = v; state.selNode = null; go('lineage'); } }));
};

/* ===================== 10. ABOUT ===================== */
RENDER.about = el => {
  el.style.gridTemplateColumns = '1.1fr 1fr 1fr'; el.style.gridTemplateRows = 'minmax(0, 1fr)'; el.style.gap = '14px';
  const cnt = t => N.filter(n => n.rt === t).length;
  el.innerHTML = `
  <div class="card"><div class="card-h"><div><div class="card-t">What this is</div></div></div><div class="card-body scroll prose">
    <p>Lineage Control Tower monitors every data product at Acme Retail Co. and traces each one back through dbt to the raw tables that feed it. It answers one question per page: what broke, who is affected, what is slow, what is expensive, and what nobody uses.</p>
    <p>A data product here is anything that reads the warehouse: BI dashboards in Tableau, Sigma and Power BI, notebooks, ML models, Databricks apps, AI agents and data hubs built in Claude. Each one is registered as a <span class="mono">dbt exposure</span>, so it sits at the end of the lineage chain.</p>
    <div class="chain">${['Raw sources', 'Staging', 'Intermediate', 'Marts', 'BI semantic layer', 'Exposures'].map((l, k) => `<span>${l}<em>${[cnt('source'), N.filter(n => n.l === 'staging').length, N.filter(n => n.l === 'intermediate').length, N.filter(n => n.l === 'mart').length, cnt('semantic'), cnt('exposure')][k]}</em></span>`).join('<i>→</i>')}</div>
    <p><b>How to use it.</b> Start on Health overview. Click any exposure tile to see its lineage, click any node to see its history, then use Trace downstream impact to see who to tell. Period and Platform at the top apply to every page.</p>
    <div class="callout info"><b>The data is synthetic.</b> Acme Retail Co. is fictional. 90 days of dbt runs, tests, freshness checks, BI refreshes, warehouse cost and usage were generated in Python with eleven planted stories, such as a Monday test failure, a Stripe outage on month-end close and an AI agent reading data nobody registered.</div>
  </div></div>
  <div class="card"><div class="card-h"><div><div class="card-t">Where the numbers come from</div><div class="card-s">In production, every table maps to something you already have</div></div></div><div class="card-body scroll"><table class="t"><thead><tr><th>Table</th><th>Production source</th></tr></thead><tbody>${[['dim_nodes, lineage edges', 'dbt manifest.json + BI metadata APIs'], ['Model runs, tests', 'run_results.json or the Elementary package'], ['Source freshness', 'sources.json'], ['Job runs', 'dbt Cloud Admin API'], ['BI refreshes', 'Tableau Admin Insights, Power BI and Sigma APIs'], ['Warehouse cost', 'Snowflake ACCOUNT_USAGE, Databricks system.billing, Redshift SYS_QUERY_HISTORY'], ['Consumption', 'BI activity logs, app logs, agent call logs'], ['Observed access', 'Warehouse query history by principal']].map(r => `<tr><td>${r[0]}</td><td style="white-space:normal;color:var(--ink-2)">${r[1]}</td></tr>`).join('')}</tbody></table>
    <div class="sec-label">Built for any tool</div><p class="card-s" style="font-size:11.5px;line-height:1.55">The data model is the product. This view is built in Tableau, and the same tables can drive Sigma, Power BI, Looker, a Claude-built data hub, or an agent that answers questions about data health.</p></div></div>
  <div class="card"><div class="card-h"><div><div class="card-t">Metric definitions</div></div></div><div class="card-body scroll"><dl class="defs">${[
    ['Run success', 'Successful model runs ÷ all model runs, skipped excluded'],
    ['Test pass rate', 'Passing tests ÷ all tests run. Warnings count as not passing'],
    ['Freshness SLA', 'Passing hourly freshness checks ÷ all checks'],
    ['Exposure status', 'Critical if anything upstream has failed, is past its freshness error threshold or failed to refresh. Warning for failing tests, late sources or skipped refreshes'],
    ['Health score', '40% upstream run success + 30% test pass + 30% freshness, over 7 days'],
    ['Mean time to recover', 'First failure to next success, per node'],
    ['Risk score', 'Daily downstream consumers × failure rate'],
    ['Cost per exposure', 'Upstream build cost split evenly across exposures fed, plus own queries'],
    ['Retire candidate', `Under ${ZOMBIE.perMonth} uses in 30 days and over $${ZOMBIE.costPerUse} per use`],
    ['Incremental candidate', 'Table over 10M rows whose 7-day runtime is 25%+ above its 28-day average']].map(([a, b]) => `<dt>${a}</dt><dd>${b}</dd>`).join('')}</dl></div></div>`;
};
