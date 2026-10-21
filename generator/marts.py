"""Build the Tableau-ready mart layer for Lineage Control Tower.

This plays the role of the `dbt_ops` mart layer: it rolls the raw generated tables up to the grains the
dashboard reads, and pre-computes the graph logic Tableau cannot do across fact tables (exposure status,
upstream culprits, reachability, lineage layout).

Usage:
    python generator/aggregate.py data mockup/data/lct_agg.json            # step 1, shared logic with the HTML mockup
    python generator/marts.py data mockup/data/lct_agg.json data/marts      # step 2, writes the CSVs Tableau connects to
"""
import sys, os, json, math, re
import numpy as np, pandas as pd

RAW, AGG, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(OUT, exist_ok=True)
A = json.load(open(AGG))
N = A['N']; ND = A['meta']['nd']; DATES = A['meta']['dates']
START = pd.Timestamp(DATES[0])
nid = {n['id']: i for i, n in enumerate(N)}
EXP = [i for i, n in enumerate(N) if n['rt'] == 'exposure']
STATUS = {0: 'No data', 1: 'Healthy', 2: 'Warning', 3: 'Critical'}
TRUST = {0: 'No recent runs', 1: 'Trusted', 2: 'Use with caution', 3: 'Do not use'}
LAYER_COL = {'source': 0, 'staging': 1, 'intermediate': 2, 'mart': 3, 'semantic': 4, 'exposure': 5}
g = lambda d, k, default=None: d.get(str(k), default) if isinstance(d, dict) else default

def write(df, name):
    df.to_csv(os.path.join(OUT, name + '.csv'), index=False)
    print(f'{name:28s} {len(df):>7,d} rows  {len(df.columns):>3d} cols')

raw_nodes = pd.read_csv(f'{RAW}/dim_nodes.csv')
owners = pd.read_csv(f'{RAW}/dim_owners.csv')
mr = pd.read_csv(f'{RAW}/fct_model_runs.csv', parse_dates=['run_started_at'])
tr = pd.read_csv(f'{RAW}/fct_test_results.csv', parse_dates=['run_at'])
sf = pd.read_csv(f'{RAW}/fct_source_freshness.csv', parse_dates=['checked_at'])
sr = pd.read_csv(f'{RAW}/fct_semantic_refresh.csv', parse_dates=['refresh_started_at'])
wc = pd.read_csv(f'{RAW}/fct_warehouse_cost.csv', parse_dates=['date'])
jr = pd.read_csv(f'{RAW}/fct_job_runs.csv', parse_dates=['run_started_at', 'run_completed_at'])
oa = pd.read_csv(f'{RAW}/fct_observed_access.csv', parse_dates=['date'])
inc = pd.read_csv(f'{RAW}/fct_incidents.csv', parse_dates=['started_at', 'resolved_at'])
for df, c in [(mr, 'run_started_at'), (tr, 'run_at'), (sf, 'checked_at'), (sr, 'refresh_started_at')]:
    df['date'] = df[c].dt.normalize()

def plat_at(i, d):  # platform a node ran on, on day index d (handles the Redshift -> Snowflake migration)
    n = N[i]
    return n['mf'] if n['mf'] and d < DATES.index(n['md']) else n['p']

# ---------- reachability (whole graph) ----------
CH, PA = {}, {}
for p, c, _ in A['E']: CH.setdefault(p, []).append(c); PA.setdefault(c, []).append(p)
def reach(i, m):
    out, st = {i: 0}, [i]
    while st:
        v = st.pop()
        for u in m.get(v, []):
            if u not in out or out[u] > out[v] + 1: out[u] = out[v] + 1; st.append(u)
    out.pop(i); return out
DOWN = {i: reach(i, CH) for i in range(len(N))}
UPR = {i: reach(i, PA) for i in range(len(N))}
FEEDS = {}
for e in EXP:
    for u, d in g(A['UP'], e, []): FEEDS.setdefault(u, []).append(e)

# ---------- helpers on the aggregate ----------
def issue(i):
    n, c = N[i], g(A['CUR'], i, {}) or {}
    if not c or c.get('s', 1) < 2: return None
    if n['rt'] == 'source': return (f"Freshness error, {c['lag']/60:.1f} h since last load (error after {c['ea']/60:.1f} h)" if c['s'] == 3
                                    else f"Loading late, {c['lag']/60:.1f} h behind (warn after {c['wa']/60:.1f} h)")
    if n['rt'] == 'semantic': return 'Extract refresh failed' if c['s'] == 3 else 'Refresh skipped, upstream not ready'
    if c.get('rs') == 'error': return (c.get('err') or 'Run failed').split(':')[0]
    if c.get('tf') or c.get('tw'):
        t = next((t for t in A['TESTS'] if t['node'] == i and str(ND - 1) in t['fd']), None)
        return f"{c.get('tf') or c.get('tw')} test {'failing' if c.get('tf') else 'warning'}" + (f": {t['n']}" if t else '')
    return 'Needs attention'
def exp_group(n):
    if not n['dec']: return 'Unregistered, found in query history'
    if n['et'] == 'dashboard': return 'BI dashboards'
    if n['et'] in ('agent', 'data_hub'): return 'AI agents and data hubs'
    return 'Apps, ML and notebooks'
cons = {int(k): v for k, v in A['CONS'].items()}
def avg_consumers(e, days):
    c = cons.get(e); return round(float(np.mean(c['uc'][ND - days:])), 2) if c else 0.0
open_inc = {r.root_node_id: r.incident_id for r in inc[inc.resolved_at.isna()].itertuples()}
# Start time of that open incident, so the Health alert list can say "open since 19 Oct" from dim_nodes alone
open_inc_at = {r.root_node_id: r.started_at for r in inc[inc.resolved_at.isna()].itertuples()}

# ---------- 1. dim_nodes (shared) : attributes + current status snapshot ----------
dn = raw_nodes.copy()
dn.insert(0, 'node_key', range(len(dn)))
rows = []
for i, n in enumerate(N):
    c = g(A['CUR'], i, {}) or {}
    s = c.get('s', 0)
    row = dict(node_key=i, display_short=re.sub(r'^(stg_|int_|raw_)', '', n['n']),
               layer_column=LAYER_COL[n['l']], platform_now=n['p'],
               platform_filter_values=('|' + n['p'] + '|' + (n['mf'] + '|' if n['mf'] else '')),
               current_status_code=s, current_status=STATUS[s], status_reason=issue(i),
               last_event_at=c.get('at'), last_run_status=c.get('rs'), last_runtime_sec=c.get('rt'), last_rows=c.get('rows'),
               last_error_message=c.get('err'), tests_passing=c.get('tp'), tests_warning=c.get('tw'), tests_failing=c.get('tf'),
               freshness_lag_min=c.get('lag'), last_refresh_sec=c.get('dur'),
               materialization_now={'t': 'table', 'i': 'incremental', 'v': 'view'}.get((g(A['MATD'], i, '') or '')[-1:], n['mat']),
               max_rows_built=g(A['ROWSMAX'], i), exposures_fed=len(FEEDS.get(i, [])),
               downstream_models=sum(1 for u in DOWN[i] if N[u]['rt'] == 'model'),
               open_incident_id=open_inc.get(n['id']), open_incident_started_at=open_inc_at.get(n['id']),
               # Every node downstream of this one, as |key|key|, so Observed Access sheets can test
               # "is this reader downstream of the selected node?" without reaching the lineage tables
               downstream_keys='|' + '|'.join(str(k) for k in sorted(DOWN[i])) + '|' if DOWN[i] else None,
               # Average daily consumers of every exposure this node feeds, per period option,
               # so the risk score (consumers x failure rate) can be built on Node Daily
               downstream_consumers_7d=round(sum(avg_consumers(e, 7) for e in FEEDS.get(i, [])), 2),
               downstream_consumers_30d=round(sum(avg_consumers(e, 30) for e in FEEDS.get(i, [])), 2),
               downstream_consumers_90d=round(sum(avg_consumers(e, 90) for e in FEEDS.get(i, [])), 2))
    if n['rt'] == 'exposure':
        cu = A['CUR'][str(i)]
        row.update(current_status_code=cu['s'], current_status=STATUS[cu['s']], trust_badge=TRUST[cu['s']],
                   culprit_nodes='; '.join(f"{N[u]['n']} ({STATUS[s2]})" for u, s2 in cu['why']),
                   culprit_count=len(cu['why']), health_score_now=(g(A['SCORE'], i) or [None])[-1],
                   exposure_group=exp_group(n), upstream_node_count=len(g(A['UP'], i, [])),
                   avg_daily_consumers_7d=avg_consumers(i, 7), avg_daily_consumers_30d=avg_consumers(i, 30), avg_daily_consumers_90d=avg_consumers(i, 90))
    rows.append(row)
extra = pd.DataFrame(rows)
dn = dn.merge(extra, on='node_key', how='left')
dn['owner_name'] = dn['owner_name'].fillna('No owner')
# Columns added after the Tableau source was connected go last, so the text connector's
# column positions (ordinals) for every existing column stay the same
LATE_COLS = ['open_incident_started_at', 'downstream_keys', 'downstream_consumers_7d', 'downstream_consumers_30d', 'downstream_consumers_90d']
dn = dn[[c for c in dn.columns if c not in LATE_COLS] + LATE_COLS]
write(dn, 'dim_nodes')
owners = pd.concat([owners, pd.DataFrame([dict(owner_name='No owner', owner_team='Unassigned', email=None, slack_channel=None, on_call_rotation='no')])], ignore_index=True)
write(owners, 'dim_owners')

# ---------- 2. dim_date (shared) ----------
dd = pd.read_csv(f'{RAW}/dim_date.csv')
dd['day_index'] = range(len(dd))
write(dd, 'dim_date')

# ---------- 3. mart_node_daily : node x day ----------
idx = pd.MultiIndex.from_product([raw_nodes.node_id, pd.to_datetime(DATES)], names=['node_id', 'date'])
nd = pd.DataFrame(index=idx)
def add(series, name): nd[name] = series.reindex(idx)
add(mr[mr.status != 'skipped'].groupby(['node_id', 'date']).size(), 'runs')
add(mr[mr.status == 'error'].groupby(['node_id', 'date']).size(), 'runs_failed')
add(mr[mr.status == 'skipped'].groupby(['node_id', 'date']).size(), 'runs_skipped')
add(mr[mr.status == 'success'].groupby(['node_id', 'date']).execution_time_sec.mean().round(1), 'avg_runtime_sec')
add(wc[wc.cost_type == 'build'].groupby(['node_id', 'date']).est_cost_usd.sum().round(3), 'build_cost_usd')
add(wc[wc.cost_type == 'consumer_query'].groupby(['node_id', 'date']).est_cost_usd.sum().round(3), 'consumer_query_cost_usd')
for st, nm in [('pass', 'tests_pass'), ('warn', 'tests_warn')]: add(tr[tr.status == st].groupby(['node_id', 'date']).size(), nm)
add(tr[tr.status.isin(['fail', 'error'])].groupby(['node_id', 'date']).size(), 'tests_fail')
for st, nm in [('pass', 'fresh_checks_pass'), ('warn', 'fresh_checks_warn'), ('error', 'fresh_checks_error')]:
    add(sf[sf.status == st].groupby(['source_node_id', 'date']).size().rename_axis(['node_id', 'date']), nm)
add(sf.groupby(['source_node_id', 'date']).lag_minutes.max().rename_axis(['node_id', 'date']), 'max_lag_min')
for st, nm in [('success', 'refresh_ok'), ('failed', 'refresh_failed'), ('skipped_upstream', 'refresh_skipped')]:
    add(sr[sr.status == st].groupby(['node_id', 'date']).size(), nm)
add(sr.groupby(['node_id', 'date']).duration_sec.mean().round(1), 'avg_refresh_sec')
nd = nd.reset_index()
cnt_cols = ['runs', 'runs_failed', 'runs_skipped', 'tests_pass', 'tests_warn', 'tests_fail', 'fresh_checks_pass', 'fresh_checks_warn', 'fresh_checks_error', 'refresh_ok', 'refresh_failed', 'refresh_skipped', 'build_cost_usd', 'consumer_query_cost_usd']
nd[cnt_cols] = nd[cnt_cols].fillna(0)
di = (nd.date - START).dt.days
ki = nd.node_id.map(nid)
nd['platform_on_day'] = [plat_at(k, d) for k, d in zip(ki, di)]
nd['materialization_on_day'] = [{'t': 'table', 'i': 'incremental', 'v': 'view'}.get((g(A['MATD'], k, '') or '-' * ND)[d], None) for k, d in zip(ki, di)]
nd['worst_test_code'] = [int((g(A['TH'], k, '0' * ND) or '0' * ND)[d]) for k, d in zip(ki, di)]
nd['runtime_7d_avg_sec'] = nd.groupby('node_id').avg_runtime_sec.transform(lambda s: s.rolling(7, min_periods=1).mean()).round(1)
nd['runtime_prior28d_avg_sec'] = nd.groupby('node_id').avg_runtime_sec.transform(lambda s: s.shift(7).rolling(28, min_periods=1).mean()).round(1)
nd['runtime_trend_pct'] = (nd.runtime_7d_avg_sec / nd.runtime_prior28d_avg_sec - 1).round(4)
nd = nd[(nd[cnt_cols].sum(axis=1) > 0) | nd.avg_runtime_sec.notna() | nd.max_lag_min.notna()]
nd['date'] = nd.date.dt.date
write(nd, 'mart_node_daily')

# ---------- 4. mart_exposure_daily : exposure x day ----------
rows = []
for e in EXP:
    ed = A['EXPDAY'][str(e)]; sc = g(A['SCORE'], e) or [None] * ND; c = cons.get(e); cost = g(A['EXPCOST'], e) or [0] * ND
    for d in range(ND):
        rows.append(dict(exposure_id=N[e]['id'], date=DATES[d], status_eod_code=int(ed['e'][d]), status_eod=STATUS[int(ed['e'][d])],
                         status_worst_code=int(ed['w'][d]), health_score=sc[d], consumption_type=N[e]['ct'],
                         events=c['ev'][d] if c else 0, unique_consumers=c['uc'][d] if c else 0,
                         avg_latency_sec=c['lat'][d] if c else None, metrics_called=c['mc'][d] if c else None,
                         failed_calls=c['fc'][d] if c else None, is_observed_only=bool(c and c.get('observed')),
                         allocated_cost_usd=cost[d]))
write(pd.DataFrame(rows), 'mart_exposure_daily')

# ---------- 5. mart_blast_radius : upstream node x exposure it feeds ----------
rows = []
for e in EXP:
    n = N[e]; ow = owners.set_index('owner_name').to_dict('index').get(n['o'] or '', {})
    for u, d in g(A['UP'], e, []):
        rows.append(dict(node_id=N[u]['id'], exposure_id=n['id'], hops=d, exposure_name=n['n'], exposure_type=n['et'], bi_tool=n['bi'],
                         exposure_owner=n['o'] or 'No owner', exposure_team=n['t'], slack_channel=ow.get('slack_channel'),
                         exposure_status=STATUS[A['CUR'][str(e)]['s']], exposure_trust=TRUST[A['CUR'][str(e)]['s']],
                         is_registered=n['dec'], avg_daily_consumers_7d=avg_consumers(e, 7),
                         avg_daily_consumers_30d=avg_consumers(e, 30), avg_daily_consumers_90d=avg_consumers(e, 90)))
write(pd.DataFrame(rows), 'mart_blast_radius')

# ---------- 6. mart_node_reach : every node to every node it can reach, both directions ----------
rows = []
for i in range(len(N)):
    for direction, m in (('downstream', DOWN[i]), ('upstream', UPR[i])):
        for u, h in m.items():
            c = g(A['CUR'], u, {}) or {}
            rows.append(dict(node_id=N[i]['id'], related_node_id=N[u]['id'], direction=direction, hops=h,
                             related_name=N[u]['n'], related_layer=N[u]['l'], related_layer_column=LAYER_COL[N[u]['l']],
                             related_resource_type=N[u]['rt'], related_status=STATUS[(A['CUR'][str(u)]['s'] if N[u]['rt'] == 'exposure' else c.get('s', 0))],
                             related_owner=N[u]['o'] or 'No owner'))
write(pd.DataFrame(rows), 'mart_node_reach')

# ---------- 7. mart_lineage_layout : snapped node boxes + 12-point edge paths, per scope ----------
NODE_W = 0.8  # node box occupies [column, column + 0.8] in x units
rows = []
for scope, pts in A['LAY'].items():
    scope_id = 'global' if scope == 'global' else N[int(scope)]['id']
    pos = {i: (math.floor(x), y) for i, x, y in pts}
    inS = set(pos)
    for i, (x, y) in pos.items():
        rel = {i} | {u for u in UPR[i] if u in inS} | {u for u in DOWN[i] if u in inS}
        rows.append(dict(layout_scope=scope_id, row_type='node', node_id=N[i]['id'], child_node_id=None, edge_id=None,
                         point_order=None, x=x, y=y, x_label=x + 0.06, reach_keys='|' + '|'.join(str(k) for k in sorted(rel)) + '|'))
    for k, (p, c, cross) in enumerate(A['E']):
        if p not in inS or c not in inS: continue
        (x1, y1), (x2, y2) = pos[p], pos[c]
        same = x1 == x2
        for t in range(12):
            u = t / 11
            if same:  # bracket on the right side for a dependency inside the same layer
                xx = x1 + NODE_W + 0.14 * math.sin(math.pi * u); yy = y1 + (y2 - y1) * u
            else:     # smooth S-curve from the parent's right edge to the child's left edge
                xx = x1 + NODE_W + (x2 - x1 - NODE_W) * u; yy = y1 + (y2 - y1) * (3 * u * u - 2 * u ** 3)
            rows.append(dict(layout_scope=scope_id, row_type='edge', node_id=N[p]['id'], child_node_id=N[c]['id'],
                             edge_id=f'E{k:04d}', point_order=t + 1, x=round(xx, 4), y=round(yy, 4), x_label=None, reach_keys=None))
lay = pd.DataFrame(rows)
lay['node_key'] = lay.node_id.map(nid)
lay['child_key'] = lay.child_node_id.map(lambda v: nid.get(v) if isinstance(v, str) else None).astype('Int64')
lay['edge_key'] = lay.node_id.map(lambda s: nid[s]).astype(str) + '>' + lay.child_node_id.map(lambda s: nid.get(s, -1) if isinstance(s, str) else -1).astype(str)
write(lay, 'mart_lineage_layout')

# ---------- 8. mart_job_runs ----------
j = jr.copy()
j['run_date'] = j.run_started_at.dt.date
j['start_minute_of_day'] = j.run_started_at.dt.hour * 60 + j.run_started_at.dt.minute
j['duration_min'] = (j.duration_sec / 60).round(2)
write(j, 'mart_job_runs')

# ---------- 9. mart_run_errors ----------
e = mr[mr.status == 'error'][['job_run_id', 'node_id', 'platform', 'run_started_at', 'error_category', 'error_message']].copy()
e['date'] = e.run_started_at.dt.date
write(e.sort_values('run_started_at', ascending=False), 'mart_run_errors')

# ---------- 10. mart_test_daily : one row per test per day with a non-pass result ----------
t = tr[tr.status != 'pass'].groupby(['test_id', 'test_name', 'test_type', 'node_id', 'column_name', 'severity', 'date']).agg(
    fails=('status', lambda s: int(s.isin(['fail', 'error']).sum())), warns=('status', lambda s: int((s == 'warn').sum()))).reset_index()
t['weekday'] = t.date.dt.day_name(); t['date'] = t.date.dt.date
write(t, 'mart_test_daily')

# ---------- 11. mart_recovery_episodes (MTTR) ----------
KIND = {'run': 'Model run', 'fresh': 'Source freshness', 'refresh': 'BI refresh'}
ep = pd.DataFrame([dict(node_id=N[x[0]]['id'], kind=KIND[x[1]], failed_at=x[2], recovered_at=x[3], hours_to_recover=x[4],
                        start_date=DATES[x[5]], platform_on_day=plat_at(x[0], x[5]), is_open=x[3] is None) for x in A['EP']])
write(ep, 'mart_recovery_episodes')

# ---------- 12. fct_incidents (+ dates) ----------
inc2 = inc.copy(); inc2['start_date'] = inc2.started_at.dt.date; inc2['is_open'] = inc2.resolved_at.isna()
write(inc2, 'fct_incidents')

# ---------- 13. mart_observed_access (+ cost share, registration) ----------
o = oa.copy()
cq = wc[wc.cost_type == 'consumer_query'].groupby(['principal', 'date']).est_cost_usd.sum()
share = o.groupby(['principal', 'date']).query_count.transform(lambda s: s / s.sum())
o['est_cost_usd'] = [round(cq.get((p, d), 0) * sh, 4) for p, d, sh in zip(o.principal, o.date, share)]
o['is_registered'] = o.mapped_exposure_id.notna()
o['inferred_exposure_name'] = o.inferred_exposure_id.map(lambda s: N[nid[s]]['n'] if isinstance(s, str) and s in nid else None)
o['date'] = o.date.dt.date
write(o, 'mart_observed_access')

# ---------- 14. mart_exposure_tiles.geojson : rounded tile shapes for the Health grid (map layers) ----------
# Tiles are drawn as polygons in a small lat/lon box near 0,0 so Tableau map layers can stack the tile, its status
# dot and its text in one sheet. Near the equator Web Mercator is almost linear (under 0.2% stretch here), so the
# shapes stay true. Two layouts are pre-computed: every exposure, and only the ones that need attention.
TILE_W, TILE_H, GAP_X, GAP_Y, HEAD_H, RADIUS, COLS = 1.0, 0.34, 0.06, 0.06, 0.20, 0.045, 5
GROUPS = ['BI dashboards', 'Apps, ML and notebooks', 'AI agents and data hubs', 'Unregistered, found in query history']
def rounded_rect(x0, y_top, w, h, r, k=6):
    pts = []
    corners = [(x0 + w - r, y_top - r, 90), (x0 + w - r, y_top - h + r, 0), (x0 + r, y_top - h + r, 270), (x0 + r, y_top - r, 180)]
    for cx, cy, start in corners:  # clockwise around the box, arc at each corner
        for j in range(k + 1):
            a = math.radians(start - 90 * j / k)
            pts.append([round(cx + r * math.cos(a), 6), round(cy + r * math.sin(a), 6)])
    pts.append(pts[0]); return pts
feats = []
exp_rows = [(i, N[i]) for i in EXP]
for layout, keep in (('All', lambda i: True), ('Needs attention', lambda i: A['CUR'][str(i)]['s'] >= 2)):
    y = 0.0
    for gi, gname in enumerate(GROUPS):
        members = [i for i, n in exp_rows if exp_group(n) == gname and keep(i)]
        if not members: continue
        members.sort(key=lambda i: (-A['CUR'][str(i)]['s'], N[i]['n']))
        hy = y - HEAD_H * 0.55
        feats.append(dict(type='Feature', geometry=dict(type='Polygon', coordinates=[rounded_rect(0, y, 0.02, 0.02, 0.005, 1)]),
                          properties=dict(feature_type='header', layout=layout, node_id=None, group_label=gname, group_order=gi + 1,
                                          group_count=len(members), label_lon=0.0, label_lat=round(hy, 6))))
        y -= HEAD_H
        for k, i in enumerate(members):
            row, col = divmod(k, COLS)
            x0 = col * (TILE_W + GAP_X); yt = y - row * (TILE_H + GAP_Y)
            feats.append(dict(type='Feature', geometry=dict(type='Polygon', coordinates=[rounded_rect(x0, yt, TILE_W, TILE_H, RADIUS)]),
                              properties=dict(feature_type='tile', layout=layout, node_id=N[i]['id'], group_label=gname, group_order=gi + 1,
                                              group_count=len(members), tile_row=row + 1, tile_col=col + 1,
                                              name_lon=round(x0 + 0.05, 6), name_lat=round(yt - 0.075, 6),
                                              meta_lon=round(x0 + 0.05, 6), meta_lat=round(yt - 0.165, 6),
                                              trust_lon=round(x0 + 0.05, 6), trust_lat=round(yt - TILE_H + 0.075, 6),
                                              score_lon=round(x0 + TILE_W - 0.05, 6), score_lat=round(yt - TILE_H + 0.075, 6),
                                              dot_lon=round(x0 + TILE_W - 0.06, 6), dot_lat=round(yt - 0.075, 6),
                                              label_lon=None, label_lat=None)))
        rows_used = math.ceil(len(members) / COLS)
        y -= rows_used * TILE_H + (rows_used - 1) * GAP_Y + 0.12
gj = dict(type='FeatureCollection', name='mart_exposure_tiles', features=feats)
json.dump(gj, open(os.path.join(OUT, 'mart_exposure_tiles.geojson'), 'w'))
print(f"{'mart_exposure_tiles.geojson':28s} {len(feats):>7,d} features")
print('done ->', OUT)
