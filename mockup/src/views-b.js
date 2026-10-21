function miniKpis(list) {
  return `<div class="kpis" style="grid-template-columns:repeat(${list.length},1fr)">${list.map(k => `<div class="card kpi" style="flex-direction:row;align-items:center;gap:14px;padding:12px 16px"><div style="flex:1;min-width:0"><div class="kpi-t">${k.t}</div><div class="kpi-v" style="font-size:22px">${k.v}</div><div class="kpi-c">${k.c || ''}</div></div>${k.side || ''}</div>`).join('')}</div>`;
}
const incAnn = (filterFn = () => true) => A.INC.filter(filterFn).map(x => ({ d: DATES.indexOf(x.s.slice(0, 10)), label: x.id.replace('INC-00', 'INC ') }));
function hbars(items, { fmt = fInt, color = 'var(--accent)', max } = {}) {
  const mx = max || Math.max(...items.map(x => x.v), 0) || 1;
  return `<div class="hbars">${items.map(x => `<div class="hbar" ${x.tip ? tipAttr(x.tip) : ''}><span class="l ${x.mono ? 'mono' : ''}">${x.l}</span><span class="v">${fmt(x.v)}</span><span class="track"><span style="width:${x.v / mx * 100}%;background:${x.c || color}"></span></span></div>`).join('')}</div>`;
}

/* ===================== 4. RUN & FAILURES ===================== */
RENDER.runs = el => {
  const w = win();
  el.style.gridTemplateColumns = '1fr 380px'; el.style.gridTemplateRows = '220px minmax(0, 1fr) 236px'; el.style.gap = '14px';
  const pIdx = state.plat === 'all' ? null : PLATS.indexOf(state.plat);
  const runs = A.JR.filter(r => pIdx == null || r[1] === pIdx);
  const errs = A.ERR.filter(x => { const d = DATES.indexOf(x[1].slice(0, 10)); return d >= w.from && d <= w.to && (state.plat === 'all' || nodePlatAt(x[0], d) === state.plat); });
  const cat = {}; errs.forEach(x => cat[x[2]] = (cat[x[2]] || 0) + 1);
  const byModel = {}; errs.forEach(x => byModel[x[0]] = (byModel[x[0]] || 0) + 1);
  const CATN = { database: 'Database error', compilation: 'Compilation error', permission: 'Permission denied', timeout: 'Timeout', schema_change: 'Schema change' };
  const jobsShown = A.JOBS.map((j, k) => k).filter(k => runs.some(r => r[0] === k));
  const day = state.ganttDay;
  el.innerHTML = `
  <div class="card" style="grid-column:1/-1"><div class="card-h"><div><div class="card-t">Failed and skipped model runs per day</div><div class="card-s">A failed model makes everything downstream skip. Dashed lines mark incidents. Click a day to load its run timeline below.</div></div><div class="right legend"><span><i style="background:var(--crit)"></i>Failed</span><span><i style="background:#C3C9CF"></i>Skipped because upstream failed</span></div></div><div class="card-body" id="rn-daily"></div></div>
  <div class="card"><div class="card-h" style="align-items:center"><div><div class="card-t">Job run timeline</div><div class="card-s">Every dbt job run on the selected day, coloured by outcome</div></div>
    <div class="right"><button class="icon-btn" id="gd-prev" aria-label="Previous day"><svg viewBox="0 0 24 24"><path d="m15 6-6 6 6 6"/></svg></button><span style="font-weight:600;min-width:118px;text-align:center" class="num">${DOWN[DOW[day]]} ${dLab(day)} 2026</span><button class="icon-btn" id="gd-next" aria-label="Next day"><svg viewBox="0 0 24 24"><path d="m9 6 6 6-6 6"/></svg></button></div></div>
    <div class="card-body" id="rn-gantt"></div>
    <div class="legend" style="margin-top:6px"><span><i style="background:#9DB9D6"></i>Succeeded</span><span><i style="background:var(--crit)"></i>Failed</span><span><i style="background:#C3C9CF"></i>Cancelled</span><span><i style="background:var(--warn);border-radius:50%"></i>Tests failed in run</span></div></div>
  <div class="card"><div class="card-h"><div><div class="card-t">Why runs failed</div><div class="card-s">${errs.length} failed model runs in this period</div></div></div>
    <div class="card-body scroll">${hbars(Object.entries(cat).sort((a, b) => b[1] - a[1]).map(([k, v]) => ({ l: CATN[k] || k, v, c: 'var(--crit)' })))}
    <div class="sec-label">Models that failed most</div>${hbars(Object.entries(byModel).sort((a, b) => b[1] - a[1]).slice(0, 7).map(([k, v]) => ({ l: esc(N[k].n), v, mono: 1, c: 'var(--crit)' })))}</div></div>
  <div class="card"><div class="card-h"><div><div class="card-t">Recent errors</div><div class="card-s">Newest first. Hover a message to read it in full.</div></div></div>
    <div class="card-body scroll"><table class="t"><thead><tr><th>When</th><th>Model</th><th>Category</th><th>Message</th></tr></thead><tbody>${errs.slice(0, 60).map(x => `<tr class="click" data-blast="${x[0]}"><td class="num">${tsLab(x[1])}</td><td class="mono">${esc(N[x[0]].n)}</td><td>${CATN[x[2]] || x[2]}</td><td style="max-width:440px;overflow:hidden;text-overflow:ellipsis;color:var(--ink-2)" ${tipAttr(`<div class="th">${esc(N[x[0]].n)}</div><div class="mono" style="white-space:normal;font-size:10.5px">${esc(x[3])}</div><div class="tl" style="margin-top:4px">Job run ${x[4]} · click to trace impact</div>`)}>${esc(x[3])}</td></tr>`).join('') || '<tr><td colspan="4" class="empty">No failures in this period.</td></tr>'}</tbody></table></div></div>
  <div class="card"><div class="card-h"><div><div class="card-t">Mean time to recover</div><div class="card-s">Rolling 7-day average, in hours. Long tails come from issues that wait for the next daily run.</div></div></div><div class="card-body" id="rn-mttr"></div></div>`;
  const errD = daily('runErr'), skipD = daily('runSkip');
  timeChart(el.querySelector('#rn-daily'), { type: 'bar', series: [{ name: 'Failed', color: 'var(--crit)', vals: errD }, { name: 'Skipped', color: '#C3C9CF', vals: skipD }], from: 0, to: ND - 1, band: [w.from, w.to], sel: day, ann: incAnn(), onClick: d => { state.ganttDay = d; render(); }, label: 'Failed and skipped runs per day', tipExtra: d => { const inc = A.INC.filter(x => DATES.indexOf(x.s.slice(0, 10)) === d); return inc.map(x => `<div style="margin-top:4px;max-width:260px;white-space:normal"><b>${x.id}</b> ${esc(x.title)}</div>`).join(''); } });
  // MTTR rolling 7d
  const mt = Array.from({ length: ND }, (_, d) => { const e = epsIn(Math.max(0, d - 6), d); return e.length ? mean(e.map(x => x[4])) : null; });
  timeChart(el.querySelector('#rn-mttr'), { type: 'line', series: [{ name: 'Mean recovery', color: 'var(--accent)', vals: mt, area: true }], from: 0, to: ND - 1, band: [w.from, w.to], fmt: fHrs, yFmt: v => v.toFixed(0) + 'h', label: 'Mean time to recover' });
  // gantt
  const g = el.querySelector('#rn-gantt'); const GW = g.clientWidth, GH = g.clientHeight;
  const lw = 210, rowH = Math.min(26, (GH - 22) / Math.max(jobsShown.length, 1)), X = m => lw + m / 1440 * (GW - lw - 8);
  let s = `<svg width="${GW}" height="${GH}" viewBox="0 0 ${GW} ${GH}" role="img" aria-label="Job runs on ${dLab(day)}"><g class="axis">`;
  for (let h = 0; h <= 24; h += 3) s += `<line x1="${X(h * 60)}" x2="${X(h * 60)}" y1="0" y2="${jobsShown.length * rowH}" stroke="var(--line-soft)"/><text x="${X(h * 60)}" y="${jobsShown.length * rowH + 14}" text-anchor="${h === 24 ? 'end' : h === 0 ? 'start' : 'middle'}">${String(h).padStart(2, '0')}:00</text>`;
  s += '</g>';
  jobsShown.forEach((k, r) => {
    const J = A.JOBS[k]; const y = r * rowH;
    s += `<rect x="0" y="${y}" width="${GW}" height="${rowH}" fill="${r % 2 ? '#FBFBFA' : '#fff'}"/><text x="4" y="${y + rowH / 2 + 3.5}" font-size="10.5" font-family="var(--f-code)" fill="var(--ink)">${esc(J.n)}</text><text x="${lw - 8}" y="${y + rowH / 2 + 3.5}" font-size="9" text-anchor="end" fill="var(--ink-3)">${J.sch.replace('on_pull_request', 'on PR')}</text>`;
    runs.filter(rr => rr[0] === k && Math.floor(rr[2] / 1440) === day).forEach(rr => {
      const m0 = rr[2] - day * 1440, dur = Math.max(rr[3] / 60, 3); const col = rr[4] === 1 ? 'var(--crit)' : rr[4] === 2 ? '#C3C9CF' : '#9DB9D6';
      const t = tipRows(`${esc(J.n)} · ${PLATS[rr[1]] ? PLAT_NAME[PLATS[rr[1]]] : ''}`, [['Started', `${String(Math.floor(m0 / 60)).padStart(2, '0')}:${String(m0 % 60).padStart(2, '0')}`], ['Duration', fDur(rr[3])], ['Outcome', ['Succeeded', 'Failed', 'Cancelled'][rr[4]]], ['Models run', rr[5]], ['Models failed', rr[6]], ['Models skipped', rr[7]], ['Tests failed', rr[8]]]);
      s += `<rect x="${X(m0)}" y="${y + rowH * .22}" width="${Math.max(X(m0 + dur) - X(m0), 2.5)}" height="${rowH * .56}" rx="2" fill="${col}" ${tipAttr(t)}/>`;
      if (rr[8] > 0) s += `<circle cx="${X(m0 + dur) + 3}" cy="${y + rowH / 2}" r="2.6" fill="var(--warn)" stroke="#fff" stroke-width="1"/>`;
    });
  });
  g.innerHTML = s + '</svg>';
  el.querySelector('#gd-prev').addEventListener('click', () => { state.ganttDay = Math.max(0, day - 1); render(); });
  el.querySelector('#gd-next').addEventListener('click', () => { state.ganttDay = Math.min(ND - 1, day + 1); render(); });
  el.querySelectorAll('[data-blast]').forEach(r => r.addEventListener('click', () => { state.blastNode = +r.dataset.blast; go('blast'); }));
};

/* ===================== 5. DATA QUALITY ===================== */
RENDER.quality = el => {
  const w = win();
  el.style.gridTemplateColumns = '1fr 420px'; el.style.gridTemplateRows = '96px minmax(0, 1fr)'; el.style.gap = '14px';
  const pass = rate('testPass', ['testWarn', 'testFail'], w.from, w.to), ppass = w.hasPrior ? rate('testPass', ['testWarn', 'testFail'], w.pfrom, w.pto) : null;
  const tests = A.TESTS.filter(t => nodeInPlat(t.node));
  const cnt = (o, f, t) => Object.entries(o).reduce((s, [d, v]) => +d >= f && +d <= t ? s + v : s, 0);
  const failingNow = tests.filter(t => t.fd[ND - 1]);
  const mods = MODELS.filter(nodeInPlat), tested = mods.filter(i => N[i].tc > 0);
  const failTests = tests.map(t => ({ t, f: cnt(t.fd, w.from, w.to), wn: cnt(t.wd, w.from, w.to) })).filter(x => x.f + x.wn > 0).sort((a, b) => b.f - a.f || b.wn - a.wn);
  const typeTot = {}; Object.entries(A.TYPE_D).forEach(([ty, arr]) => typeTot[ty] = sum(arr, w.from, w.to));
  const TYN = { not_null: 'not_null', unique: 'unique', relationships: 'relationships', accepted_values: 'accepted_values', custom: 'custom (singular)' };
  el.innerHTML = `<div style="grid-column:1/-1">${miniKpis([
    { t: 'Test pass rate', v: fPct(pass, 2), c: change(pass, ppass, { kind: 'pp' }) },
    { t: 'Failing right now', v: `${failingNow.length}<small>tests</small>`, c: failingNow.length ? `<span class="up-bad">${failingNow.map(t => t.n).slice(0, 1).join(', ')}</span>` : 'All tests passing' },
    { t: 'Tests run in period', v: fK(sum(daily('testPass'), w.from, w.to) + sum(daily('testWarn'), w.from, w.to) + sum(daily('testFail'), w.from, w.to)), c: `${tests.length} distinct tests` },
    { t: 'Model test coverage', v: fPct(tested.length / mods.length, 0), c: `${mods.length - tested.length} of ${mods.length} models have no tests` }])}</div>
  <div class="card"><div class="card-h"><div><div class="card-t">Test outcomes by model and day</div><div class="card-s">Worst test result per model per day. Models with any warning or failure in this period, most failures first. Look for repeating columns.</div></div><div class="right legend"><span><i style="background:var(--good-tint);border:1px solid #CFE8DA"></i>Passed</span><span><i style="background:var(--warn)"></i>Warning</span><span><i style="background:var(--crit)"></i>Failed</span><span><i style="background:#F1F2F0"></i>No run</span></div></div><div class="card-body" id="dq-heat"></div></div>
  <div style="display:grid;grid-template-rows:minmax(0,1fr) auto auto;gap:14px;min-height:0">
    <div class="card"><div class="card-h"><div><div class="card-t">Tests that keep failing</div><div class="card-s">Days with a failure or warning in this period, and which weekdays they land on</div></div></div>
      <div class="card-body scroll">${failTests.slice(0, 8).map(x => { const wd = [0, 0, 0, 0, 0, 0, 0]; Object.entries(x.t.fd).forEach(([d, v]) => { if (+d >= w.from && +d <= w.to) wd[DOW[+d]] += 1; }); Object.entries(x.t.wd).forEach(([d, v]) => { if (+d >= w.from && +d <= w.to) wd[DOW[+d]] += .5; }); const mx = Math.max(...wd) || 1; return `<div class="ftest"><div class="ft-n mono" ${tipAttr(tipRows(esc(x.t.n), [['Model', esc(N[x.t.node].n)], ['Type', x.t.ty], ['Column', esc(x.t.col || '-')], ['Severity', x.t.sev], ['Fail days', x.f], ['Warn days', x.wn]]))}>${esc(x.t.n)}</div><div class="ft-m"><span class="ft-c">${x.f ? `<b style="color:var(--crit-ink)">${x.f} fail</b>` : ''}${x.f && x.wn ? ' · ' : ''}${x.wn ? `<span style="color:var(--warn-ink)">${x.wn} warn</span>` : ''}</span><span class="wk">${wd.map((v, k) => `<span title="${DOWN[k]}"><i style="height:${Math.max(2, v / mx * 16)}px;background:${v ? (x.f ? 'var(--crit)' : 'var(--warn)') : 'var(--line)'}"></i><em>${DOWN[k][0]}</em></span>`).join('')}</span></div></div>`; }).join('') || '<div class="empty">No failing tests in this period.</div>'}</div></div>
    <div class="card"><div class="card-h"><div><div class="card-t">Issues by test type</div><div class="card-s">Failures and warnings in this period</div></div></div>${hbars(Object.entries(typeTot).sort((a, b) => b[1] - a[1]).map(([k, v]) => ({ l: TYN[k] || k, v, mono: 1, c: 'var(--warn)' })))}</div>
    <div class="card"><div class="card-h"><div><div class="card-t">Test coverage by domain</div><div class="card-s">Share of models with at least one test</div></div></div>${hbars([...new Set(mods.map(i => N[i].d))].map(d => { const m = mods.filter(i => N[i].d === d); return { l: d, v: m.filter(i => N[i].tc > 0).length / m.length, tip: tipRows(d, [['Models', m.length], ['With tests', m.filter(i => N[i].tc > 0).length]]) }; }).sort((a, b) => a.v - b.v), { fmt: v => fPct(v, 0), max: 1 })}</div>
  </div>`;
  // heatmap
  const box = el.querySelector('#dq-heat'); const BW = box.clientWidth, BH = box.clientHeight;
  const span = Math.max(30, state.period), d0 = ND - span;
  const rows = MODELS.filter(nodeInPlat).map(i => { const th = A.TH[i] || ''; let f = 0, wn = 0; for (let d = w.from; d <= w.to; d++) { if (th[d] === '3') f++; else if (th[d] === '2') wn++; } return { i, f, wn }; }).filter(x => x.f + x.wn > 0).sort((a, b) => b.f - a.f || b.wn - a.wn);
  const lw = 210, rw = 54, top = 18; const maxRows = Math.floor((BH - top - 4) / 13); const shown = rows.slice(0, maxRows);
  const cw = (BW - lw - rw) / span, ch = Math.min(18, (BH - top - 4) / Math.max(shown.length, 1));
  let s = `<svg width="${BW}" height="${BH}" viewBox="0 0 ${BW} ${BH}" role="img" aria-label="Test outcome heatmap">`;
  for (let k = 0; k < span; k++) { const d = d0 + k; if (DOW[d] === 0) s += `<text x="${lw + k * cw + cw / 2}" y="11" font-size="9" text-anchor="middle" fill="${'var(--ink-3)'}">${span <= 30 ? 'Mon ' : ''}${dLab(d)}</text>`; }
  if (w.from > d0) s += `<rect x="${lw + (w.from - d0) * cw - 1}" y="${top - 2}" width="${(w.to - w.from + 1) * cw + 2}" height="${shown.length * ch + 3}" fill="none" stroke="var(--navy)" stroke-width="1" rx="3"/>`;
  shown.forEach((x, r) => {
    const y = top + r * ch, th = A.TH[x.i] || '';
    s += `<text x="${lw - 8}" y="${y + ch / 2 + 3.3}" font-size="10" text-anchor="end" font-family="var(--f-code)" fill="var(--ink)">${esc(N[x.i].n)}</text>`;
    for (let k = 0; k < span; k++) { const d = d0 + k, v = +(th[d] || 0); const col = ['#F1F2F0', '#E3F2E9', 'var(--warn)', 'var(--crit)'][v]; s += `<rect x="${lw + k * cw + .6}" y="${y + .6}" width="${Math.max(cw - 1.2, .8)}" height="${ch - 1.2}" rx="1.5" fill="${col}" ${v >= 2 ? tipAttr(tipRows(`${esc(N[x.i].n)}`, [[`${DOWN[DOW[d]]} ${dLab(d)}`, ['No run', 'All passed', 'Warning', 'Failed'][v]]])) : ''}/>`; }
    s += `<text x="${BW - 4}" y="${y + ch / 2 + 3.3}" font-size="10" text-anchor="end" fill="${x.f ? 'var(--crit-ink)' : 'var(--warn-ink)'}" font-weight="600">${x.f ? x.f + 'F' : ''} ${x.wn ? x.wn + 'W' : ''}</text>`;
  });
  if (rows.length > shown.length) s += `<text x="${lw}" y="${BH - 2}" font-size="10" fill="var(--ink-3)">+ ${rows.length - shown.length} more models with occasional warnings</text>`;
  box.innerHTML = s + '</svg>';
};

/* ===================== 6. FRESHNESS & SLAs ===================== */
RENDER.fresh = el => {
  const w = win();
  el.style.gridTemplateColumns = '1fr 1fr'; el.style.gridTemplateRows = 'minmax(0, 1fr) minmax(0, 1fr)'; el.style.gap = '14px';
  const src = SOURCES.filter(nodeInPlat).sort((a, b) => (CUR(b).lag / CUR(b).ea) - (CUR(a).lag / CUR(a).ea));
  const late = src.filter(i => CUR(i).s >= 2);
  const bullets = src.map(i => { const c = CUR(i), M = Math.max(c.ea * 1.25, c.lag * 1.05); return `<div class="brow" ${tipAttr(tipRows(esc(N[i].n), [['Lag now', fHrs(c.lag / 60)], ['Warn after', fHrs(c.wa / 60)], ['Error after', fHrs(c.ea / 60)], ['Checked', tsLab(c.at)], ['Platform', PLAT_NAME[N[i].p]], ['Feeds', (FEEDS[i] || []).length + ' exposures']]))}><span class="mono bl">${esc(N[i].n)}</span><span class="bullet"><span class="bz" style="width:${c.wa / M * 100}%;background:var(--good-tint)"></span><span class="bz" style="width:${(c.ea - c.wa) / M * 100}%;background:var(--warn-tint)"></span><span class="bz" style="flex:1;background:var(--crit-tint)"></span><span class="bm" style="width:${Math.max(.5, c.lag / M * 100)}%;background:${STATUS_COL[c.s]}"></span></span><span class="bv num" style="color:${c.s >= 2 ? STATUS_COL[c.s] : 'var(--ink-2)'};font-weight:${c.s >= 2 ? 700 : 500}">${fHrs(c.lag / 60)}</span></div>`; }).join('');
  // compliance by platform
  const plats = platsOn();
  const comp = plats.map(p => ({ name: PLAT_NAME[p], color: PLAT_COL[p], vals: A.S.frPass[p].map((v, k) => { const t = v + A.S.frWarn[p][k] + A.S.frErr[p][k]; return t ? v / t : null; }) }));
  // calendar
  const br = daily('frWarn').map((v, k) => v + daily('frErr')[k]), er = daily('frErr');
  const start = 0 - ((DOW[0] + 7) % 7); const weeks = Math.ceil((ND - start) / 7);
  let cal = `<div class="cal" style="grid-template-columns:34px repeat(${weeks},1fr)">`;
  for (let r = 0; r < 7; r++) {
    cal += `<span class="cal-l">${DOWN[r]}</span>`;
    for (let c = 0; c < weeks; c++) { const d = start + c * 7 + r; if (d < 0 || d >= ND) { cal += '<span class="cal-c" style="background:none"></span>'; continue; } const v = br[d], e = er[d]; const bg = e ? 'var(--crit)' : v ? 'var(--warn)' : d >= w.from ? '#E3F2E9' : '#EEF0EE'; cal += `<span class="cal-c" style="background:${bg};${d === ND - 1 ? 'outline:1.5px solid var(--navy);outline-offset:1px' : ''}" ${tipAttr(tipRows(`${DOWN[DOW[d]]} ${dLab(d)}`, [['Late checks', v], ['Past error threshold', e]]))}>${v ? `<b>${v}</b>` : ''}</span>`; }
  }
  cal += '</div>';
  el.innerHTML = `
  <div class="card" style="grid-row:1/3"><div class="card-h"><div><div class="card-t">How late is each source right now?</div><div class="card-s">Lag since last load against its SLA. Green zone is on time, amber is past the warn threshold, red is past the error threshold. Latest check ${tsLab(CUR(SOURCES[0]).at)}.</div></div></div><div class="card-body scroll"><div class="brows">${bullets}</div></div></div>
  <div class="card"><div class="card-h"><div><div class="card-t">Freshness SLA compliance by platform</div><div class="card-s">Share of hourly checks that passed each day. The axis starts at 90%.</div></div></div><div class="card-body" id="fr-comp"></div></div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;min-height:0">
    <div class="card"><div class="card-h"><div><div class="card-t">Late checks by day</div><div class="card-s">Number shows late checks. Outlined day is today.</div></div></div><div class="card-body">${cal}</div><div class="legend" style="margin-top:6px"><span><i style="background:var(--warn)"></i>Warn</span><span><i style="background:var(--crit)"></i>Error</span><span><i style="background:#E3F2E9"></i>On time</span></div></div>
    <div class="card"><div class="card-h"><div><div class="card-t">Late right now</div><div class="card-s">And the data products waiting on them</div></div></div><div class="card-body scroll">${late.map(i => { const ex = (FEEDS[i] || []).map(x => x[0]); return `<div class="late"><div style="display:flex;gap:8px;align-items:center">${pill(CUR(i).s)}<span class="mono" style="font-weight:500">${esc(N[i].n)}</span></div><div class="card-s" style="margin:4px 0 6px">${esc(nodeIssue(i))}</div><div style="display:flex;flex-wrap:wrap;gap:4px">${ex.map(e => `<button class="tag" data-exp="${e}" style="cursor:pointer">${esc(N[e].n)}</button>`).join('')}</div></div>`; }).join('') || '<div class="empty">Every source is on time.</div>'}</div></div>
  </div>`;
  timeChart(el.querySelector('#fr-comp'), { type: 'line', series: comp.map(c => ({ ...c, w: 1.8 })), from: 0, to: ND - 1, band: [w.from, w.to], yMin: .9, yMax: 1, yTicks: [.9, .95, 1], fmt: v => fPct(v, 1), yFmt: v => fPct(v, 0), ann: incAnn(x => x.cat === 'freshness'), mr: 70, endLabels: true, label: 'Freshness compliance by platform' });
  el.querySelectorAll('[data-exp]').forEach(b => b.addEventListener('click', () => { state.selExp = +b.dataset.exp; state.selNode = null; go('lineage'); }));
};
