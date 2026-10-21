"""Roll the Lineage Control Tower CSVs up into one compact JSON for the HTML mockup.
Every number the mockup shows is derived here from the real generated data.
Usage: python generator/aggregate.py data mockup/data/lct_agg.json
"""
import sys, json, math
import numpy as np, pandas as pd

D, OUT = sys.argv[1], sys.argv[2]
START = pd.Timestamp('2026-07-22'); END = pd.Timestamp('2026-10-19'); ND = 90
PLATS = ['snowflake', 'databricks', 'redshift']

def r(x, n=2):
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))): return None
    return round(float(x), n)

def di(ts):  # day index
    return (pd.to_datetime(ts).normalize() - START).days

nodes = pd.read_csv(f'{D}/dim_nodes.csv')
owners = pd.read_csv(f'{D}/dim_owners.csv')
edges = pd.read_csv(f'{D}/fct_lineage_edges.csv')
ups = pd.read_csv(f'{D}/fct_exposure_upstream.csv')
lay = pd.read_csv(f'{D}/fct_lineage_layout.csv')
jr = pd.read_csv(f'{D}/fct_job_runs.csv', parse_dates=['run_started_at', 'run_completed_at'])
mr = pd.read_csv(f'{D}/fct_model_runs.csv', parse_dates=['run_started_at'])
tr = pd.read_csv(f'{D}/fct_test_results.csv', parse_dates=['run_at'])
sf = pd.read_csv(f'{D}/fct_source_freshness.csv', parse_dates=['checked_at', 'max_loaded_at'])
sr = pd.read_csv(f'{D}/fct_semantic_refresh.csv', parse_dates=['refresh_started_at'])
wc = pd.read_csv(f'{D}/fct_warehouse_cost.csv', parse_dates=['date'])
co = pd.read_csv(f'{D}/fct_consumption.csv', parse_dates=['date'])
oa = pd.read_csv(f'{D}/fct_observed_access.csv', parse_dates=['date'])
inc = pd.read_csv(f'{D}/fct_incidents.csv', parse_dates=['started_at', 'resolved_at'])

# ---------- nodes ----------
nid = {n: i for i, n in enumerate(nodes.node_id)}
N = []
for _, x in nodes.iterrows():
    N.append(dict(
        id=x.node_id, n=x.display_name, rt=x.resource_type, l=x.layer, lo=int(x.layer_order),
        p=x.platform, mf=None if pd.isna(x.migrated_from_platform) else x.migrated_from_platform,
        md=None if pd.isna(x.migration_date) else x.migration_date,
        pj=x.dbt_project, mat=None if pd.isna(x.materialization) else x.materialization,
        d=x.domain, o=None if pd.isna(x.owner_name) else x.owner_name,
        t=None if pd.isna(x.owner_team) else x.owner_team, desc=bool(x.has_description),
        tc=int(x.test_count), sch=None if pd.isna(x.schema_name) else x.schema_name,
        et=None if pd.isna(x.exposure_type) else x.exposure_type,
        bi=None if pd.isna(x.bi_tool) else x.bi_tool,
        ap=None if pd.isna(x.access_path) else x.access_path,
        bm=None if pd.isna(x.build_method) else x.build_method,
        dec=bool(x.is_declared) if not pd.isna(x.is_declared) else True,
        mt=None if pd.isna(x.maturity) else x.maturity,
        sp=None if pd.isna(x.service_principal) else x.service_principal,
        ct=None if pd.isna(x.consumption_type) else x.consumption_type,
        so=None if pd.isna(x.semantic_object_type) else x.semantic_object_type,
        cn=None if pd.isna(x.connection_type) else x.connection_type,
        wa=None if pd.isna(x.warn_after_minutes) else int(x.warn_after_minutes),
        ea=None if pd.isna(x.error_after_minutes) else int(x.error_after_minutes),
        cd=x.created_date,
    ))
EXP = [i for i, x in enumerate(N) if x['rt'] == 'exposure']

def plat_at(node_id, ts):
    x = N[nid[node_id]]
    if x['mf'] and pd.Timestamp(ts) < pd.Timestamp(x['md']): return x['mf']
    return x['p']

E = [[nid[a], nid[b], bool(c)] for a, b, c in zip(edges.parent_node_id, edges.child_node_id, edges.crosses_platform)]
UP = {}
for e, u, d in zip(ups.exposure_id, ups.upstream_node_id, ups.depth):
    UP.setdefault(nid[e], []).append([nid[u], int(d)])

# layouts (node positions only; edges drawn as sigmoid curves = same shape as the 12-point paths)
LAY = {}
for scope, g in lay[lay.row_type == 'node'].groupby('layout_scope'):
    key = 'global' if scope == 'global' else str(nid[scope])
    LAY[key] = [[nid[a], r(x, 3), r(y, 3)] for a, x, y in zip(g.node_id, g.x, g.y)]

# ---------- job runs ----------
jr['jp'] = jr.platform
jobs = sorted(jr.job_name.unique())
jid = {j: i for i, j in enumerate(jobs)}
JOBS = [dict(n=j, pj=g.dbt_project.iloc[0], sch=g.schedule.iloc[0], env=g.environment.iloc[0]) for j, g in jr.groupby('job_name')]
JOBS = sorted(JOBS, key=lambda x: jid[x['n']])
SC = {'success': 0, 'error': 1, 'cancelled': 2}
t0 = START
JR = []
for x in jr.itertuples():
    JR.append([jid[x.job_name], PLATS.index(x.platform), int((x.run_started_at - t0).total_seconds() // 60),
               r(x.duration_sec, 0), SC[x.status], int(x.models_run), int(x.models_failed), int(x.models_skipped), int(x.tests_failed)])
jr_env = dict(zip(jr.job_run_id, jr.environment)); jr_plat = dict(zip(jr.job_run_id, jr.platform))

# ---------- daily platform series ----------
mr['d'] = (mr.run_started_at.dt.normalize() - START).dt.days
tr['d'] = (tr.run_at.dt.normalize() - START).dt.days
sf['d'] = (sf.checked_at.dt.normalize() - START).dt.days
sr['d'] = (sr.refresh_started_at.dt.normalize() - START).dt.days
wc['d'] = (wc.date - START).dt.days
co['d'] = (co.date - START).dt.days
oa['d'] = (oa.date - START).dt.days
tr['p'] = tr.job_run_id.map(jr_plat)
sf['p'] = [plat_at(a, b) for a, b in zip(sf.source_node_id, sf.checked_at)]

def daily(df, mask, pcol='platform'):
    out = {}
    for p in PLATS:
        s = df[mask & (df[pcol] == p)].groupby('d').size().reindex(range(ND), fill_value=0)
        out[p] = s.astype(int).tolist()
    return out

S = dict(
    runOk=daily(mr, mr.status == 'success'),
    runErr=daily(mr, mr.status == 'error'),
    runSkip=daily(mr, mr.status == 'skipped'),
    testPass=daily(tr, tr.status == 'pass', 'p'),
    testWarn=daily(tr, tr.status == 'warn', 'p'),
    testFail=daily(tr, tr.status.isin(['fail', 'error']), 'p'),
    frPass=daily(sf, sf.status == 'pass', 'p'),
    frWarn=daily(sf, sf.status == 'warn', 'p'),
    frErr=daily(sf, sf.status == 'error', 'p'),
)
S['cost'] = {p: [r(v) for v in wc[wc.platform == p].groupby('d').est_cost_usd.sum().reindex(range(ND), fill_value=0)] for p in PLATS}
S['jobOk'] = {p: jr[(jr.platform == p) & (jr.status == 'success')].assign(d=lambda z: (z.run_started_at.dt.normalize() - START).dt.days).groupby('d').size().reindex(range(ND), fill_value=0).astype(int).tolist() for p in PLATS}
S['jobTot'] = {p: jr[(jr.platform == p)].assign(d=lambda z: (z.run_started_at.dt.normalize() - START).dt.days).groupby('d').size().reindex(range(ND), fill_value=0).astype(int).tolist() for p in PLATS}
# error category by day
S['errCat'] = {c: mr[mr.error_category == c].groupby('d').size().reindex(range(ND), fill_value=0).astype(int).tolist()
               for c in ['database', 'compilation', 'permission', 'timeout', 'schema_change']}

# ---------- node-day status (worst during day) ----------
# 3 = red, 2 = amber, 1 = green, 0 = no activity
nd = np.zeros((len(N), ND), dtype=np.int8)
def bump(arr_nodes, arr_days, val):
    for a, d in zip(arr_nodes, arr_days):
        i = nid[a]
        if 0 <= d < ND and nd[i, d] < val: nd[i, d] = val
bump(mr.node_id, mr.d, 1)
bump(mr[mr.status == 'error'].node_id, mr[mr.status == 'error'].d, 3)
bump(tr[tr.status.isin(['warn', 'fail', 'error'])].node_id, tr[tr.status.isin(['warn', 'fail', 'error'])].d, 2)
bump(sf.source_node_id, sf.d, 1)
bump(sf[sf.status == 'warn'].source_node_id, sf[sf.status == 'warn'].d, 2)
bump(sf[sf.status == 'error'].source_node_id, sf[sf.status == 'error'].d, 3)
bump(sr.node_id, sr.d, 1)
bump(sr[sr.status == 'skipped_upstream'].node_id, sr[sr.status == 'skipped_upstream'].d, 2)
bump(sr[sr.status == 'failed'].node_id, sr[sr.status == 'failed'].d, 3)

# end-of-day status per node (what a user saw at close of day)
eod = np.zeros((len(N), ND), dtype=np.int8)
last_run = mr.sort_values('run_started_at').groupby(['node_id', 'd']).status.last()
for (a, d), s in last_run.items(): eod[nid[a], d] = max(eod[nid[a], d], 3 if s == 'error' else 1)
last_test = tr.sort_values('run_at').groupby(['test_id', 'd']).agg(node=('node_id', 'last'), s=('status', 'last'))
for (t, d), x in last_test.iterrows():
    if x.s != 'pass': eod[nid[x.node], d] = max(eod[nid[x.node], d], 2)
last_fr = sf.sort_values('checked_at').groupby(['source_node_id', 'd']).status.last()
for (a, d), s in last_fr.items(): eod[nid[a], d] = max(eod[nid[a], d], {'pass': 1, 'warn': 2, 'error': 3}[s])
last_sr = sr.sort_values('refresh_started_at').groupby(['node_id', 'd']).status.last()
for (a, d), s in last_sr.items(): eod[nid[a], d] = max(eod[nid[a], d], {'success': 1, 'skipped_upstream': 2, 'failed': 3}[s])

def exp_status(mat, e):
    idx = [e] + [u for u, _ in UP.get(e, [])]
    return mat[idx].max(axis=0)

EXPDAY = {}
for e in EXP:
    worst = exp_status(nd, e); end = exp_status(eod, e)
    EXPDAY[e] = dict(w=''.join(map(str, worst.tolist())), e=''.join(map(str, end.tolist())))

# ---------- current status as of END (latest observation) ----------
cur = {}
lm = mr.sort_values('run_started_at').groupby('node_id').last()
for a, x in lm.iterrows():
    cur[nid[a]] = dict(s=3 if x.status == 'error' else (2 if x.status == 'skipped' else 1), at=str(x.run_started_at)[:16],
                       rt=r(x.execution_time_sec, 1), rows=None if pd.isna(x.rows_affected) else int(x.rows_affected),
                       err=x.error_message if x.status == 'error' else None, rs=x.status)
lt = tr.sort_values('run_at').groupby('test_id').last()
tstat = {}
for t, x in lt.iterrows():
    i = nid[x.node_id]; tstat.setdefault(i, [0, 0, 0])
    tstat[i][{'pass': 0, 'warn': 1, 'fail': 2, 'error': 2}[x.status]] += 1
lfr = sf.sort_values('checked_at').groupby('source_node_id').last()
for a, x in lfr.iterrows():
    cur[nid[a]] = dict(s={'pass': 1, 'warn': 2, 'error': 3}[x.status], at=str(x.checked_at)[:16], lag=r(x.lag_minutes, 0),
                       wa=int(x.warn_after_minutes), ea=int(x.error_after_minutes))
lsr = sr.sort_values('refresh_started_at').groupby('node_id').last()
for a, x in lsr.iterrows():
    cur[nid[a]] = dict(s={'success': 1, 'skipped_upstream': 2, 'failed': 3}[x.status], at=str(x.refresh_started_at)[:16],
                       dur=r(x.duration_sec, 0), err=None if pd.isna(x.error_message) else x.error_message)
for i, v in tstat.items():
    cur.setdefault(i, dict(s=1))
    cur[i]['tp'], cur[i]['tw'], cur[i]['tf'] = v
    if v[1] + v[2] > 0: cur[i]['s'] = max(cur[i]['s'], 2)

CUR = {}
for e in EXP:
    idx = [u for u, _ in UP.get(e, [])]
    culprits = [[u, cur[u]['s']] for u in idx if u in cur and cur[u]['s'] >= 2]
    st = max([c[1] for c in culprits], default=1)
    if not idx: st = 0
    CUR[e] = dict(s=st, why=sorted(culprits, key=lambda c: -c[1]))
for i, v in cur.items():
    if N[i]['rt'] != 'exposure': CUR[i] = v

# ---------- health score per exposure per day (40 run, 30 test, 30 fresh) ----------
node_run_ok = mr[mr.status == 'success'].groupby(['node_id', 'd']).size()
node_run_tot = mr[mr.status != 'skipped'].groupby(['node_id', 'd']).size()
node_t_ok = tr[tr.status == 'pass'].groupby(['node_id', 'd']).size()
node_t_tot = tr.groupby(['node_id', 'd']).size()
node_f_ok = sf[sf.status == 'pass'].groupby(['source_node_id', 'd']).size()
node_f_tot = sf.groupby(['source_node_id', 'd']).size()
def mat_from(series):
    m = np.zeros((len(N), ND))
    for (a, d), v in series.items(): m[nid[a], d] = v
    return m
RO, RT, TO, TT, FO, FT = map(mat_from, [node_run_ok, node_run_tot, node_t_ok, node_t_tot, node_f_ok, node_f_tot])
SCORE = {}
for e in EXP:
    idx = [u for u, _ in UP.get(e, [])]
    if not idx: continue
    sc = []
    for d in range(ND):
        lo = max(0, d - 6)
        def rate(o, t):
            tt = t[idx, lo:d + 1].sum(); return (o[idx, lo:d + 1].sum() / tt) if tt else 1.0
        sc.append(r(100 * (0.4 * rate(RO, RT) + 0.3 * rate(TO, TT) + 0.3 * rate(FO, FT)), 1))
    SCORE[e] = sc

# ---------- MTTR episodes (model runs, freshness, semantic refresh) ----------
EP = []
def episodes(df, node_col, ts_col, bad, good, kind):
    for a, g in df.sort_values(ts_col).groupby(node_col):
        start = None
        for ts, s in zip(g[ts_col], g.status):
            if s in bad and start is None: start = ts
            elif s in good and start is not None:
                EP.append([nid[a], kind, str(start)[:16], str(ts)[:16], r((ts - start).total_seconds() / 3600, 2), di(start)]); start = None
        if start is not None:
            EP.append([nid[a], kind, str(start)[:16], None, None, di(start)])
episodes(mr, 'node_id', 'run_started_at', {'error'}, {'success'}, 'run')
episodes(sf, 'source_node_id', 'checked_at', {'error'}, {'pass'}, 'fresh')
episodes(sr, 'node_id', 'refresh_started_at', {'failed'}, {'success'}, 'refresh')

# ---------- errors list ----------
ERR = []
for x in mr[mr.status == 'error'].sort_values('run_started_at', ascending=False).itertuples():
    ERR.append([nid[x.node_id], str(x.run_started_at)[:16], x.error_category, x.error_message, x.job_run_id])
SKIPD = mr[mr.status == 'skipped'].groupby('d').size().reindex(range(ND), fill_value=0).astype(int).tolist()

# ---------- per node daily: runtime avg, cost, errors, test worst, freshness max lag ----------
models = [i for i, x in enumerate(N) if x['rt'] == 'model']
RTD = {}
g = mr[mr.status == 'success'].groupby(['node_id', 'd']).execution_time_sec.mean()
for (a, d), v in g.items(): RTD.setdefault(nid[a], [None] * ND)[d] = r(v, 1)
COSTD = {}
g = wc[wc.cost_type == 'build'].groupby(['node_id', 'd']).est_cost_usd.sum()
for (a, d), v in g.items(): COSTD.setdefault(nid[a], [0] * ND)[d] = r(v, 2)
ERRD = {}
g = mr[mr.status == 'error'].groupby(['node_id', 'd']).size()
for (a, d), v in g.items(): ERRD.setdefault(nid[a], [0] * ND)[d] = int(v)
RUNSD = {}
g = mr[mr.status != 'skipped'].groupby(['node_id', 'd']).size()
for (a, d), v in g.items(): RUNSD.setdefault(nid[a], [0] * ND)[d] = int(v)
# test heatmap per model: worst test outcome per day: 0 none, 1 pass, 2 warn, 3 fail
TH = {}
code = tr.status.map({'pass': 1, 'warn': 2, 'fail': 3, 'error': 3})
g = tr.assign(c=code).groupby(['node_id', 'd']).c.max()
for (a, d), v in g.items(): TH.setdefault(nid[a], [0] * ND)[d] = int(v)
TH = {k: ''.join(map(str, v)) for k, v in TH.items()}
LAGD = {}
g = sf.groupby(['source_node_id', 'd']).lag_minutes.max()
for (a, d), v in g.items(): LAGD.setdefault(nid[a], [None] * ND)[d] = r(v, 0)
ROWS = {}
g = mr[mr.rows_affected.notna()].sort_values('run_started_at').groupby('node_id').rows_affected.last()
for a, v in g.items(): ROWS[nid[a]] = int(v)

# materialisation per node per day (a model can change, e.g. table -> incremental) and the largest build
MATD = {}
g = mr.groupby(['node_id', 'd']).materialization.last()
for (a, d), v in g.items(): MATD.setdefault(nid[a], [None] * ND)[d] = {'table': 't', 'incremental': 'i', 'view': 'v'}.get(v, '?')
for k, v in MATD.items():
    last = None
    for d in range(ND):
        if v[d] is None: v[d] = last
        last = v[d]
MATD = {k: ''.join(x or '-' for x in v) for k, v in MATD.items()}
ROWSMAX = {nid[a]: int(v) for a, v in mr[mr.rows_affected.notna()].groupby('node_id').rows_affected.max().items()}
# tests: per test failing/warn days
TESTS = []
for t, g in tr.groupby('test_id'):
    bad = g[g.status != 'pass']
    TESTS.append(dict(n=g.test_name.iloc[0], node=nid[g.node_id.iloc[0]], ty=g.test_type.iloc[0], col=g.column_name.iloc[0],
                      sev=g.severity.iloc[0], runs=int(len(g)),
                      fd=bad[bad.status.isin(['fail', 'error'])].groupby('d').size().astype(int).to_dict(),
                      wd=bad[bad.status == 'warn'].groupby('d').size().astype(int).to_dict()))
for x in TESTS:
    x['fd'] = {str(k): v for k, v in x['fd'].items()}; x['wd'] = {str(k): v for k, v in x['wd'].items()}
TYPE_D = {}
for ty, g in tr[tr.status != 'pass'].groupby('test_type'):
    TYPE_D[ty] = g.groupby('d').size().reindex(range(ND), fill_value=0).astype(int).tolist()

# ---------- semantic refresh daily ----------
SEM = {}
for a, g in sr.groupby('node_id'):
    SEM[nid[a]] = dict(ok=g[g.status == 'success'].groupby('d').size().reindex(range(ND), fill_value=0).astype(int).tolist(),
                       fail=g[g.status == 'failed'].groupby('d').size().reindex(range(ND), fill_value=0).astype(int).tolist(),
                       skip=g[g.status == 'skipped_upstream'].groupby('d').size().reindex(range(ND), fill_value=0).astype(int).tolist(),
                       dur=[r(v, 0) for v in g.groupby('d').duration_sec.mean().reindex(range(ND))])

# ---------- consumption per exposure ----------
CONS = {}
for a, g in co.groupby('exposure_id'):
    g = g.set_index('d').reindex(range(ND))
    CONS[nid[a]] = dict(ev=g.events.fillna(0).astype(int).tolist(), uc=g.unique_consumers.fillna(0).astype(int).tolist(),
                        lat=[r(v, 2) for v in g.avg_latency_sec],
                        mc=[None if pd.isna(v) else int(v) for v in g.metrics_called],
                        fc=[None if pd.isna(v) else int(v) for v in g.failed_calls])
# undeclared exposures: use observed query counts as their consumption
for e in EXP:
    if not N[e]['dec']:
        g = oa[oa.inferred_exposure_id == N[e]['id']].groupby('d').query_count.sum().reindex(range(ND), fill_value=0)
        CONS[e] = dict(ev=g.astype(int).tolist(), uc=[1 if v else 0 for v in g], lat=[None] * ND, mc=[None] * ND, fc=[None] * ND, observed=True)

# ---------- cost per exposure (build cost split evenly across exposures each node feeds + direct consumer cost) ----------
feeds = {}
for e in EXP:
    for u, _ in UP.get(e, []): feeds.setdefault(u, []).append(e)
EXPCOST = {e: np.zeros(ND) for e in EXP}
for i, arr in COSTD.items():
    fs = feeds.get(i, [])
    for e in fs: EXPCOST[e] += np.array(arr) / len(fs)
prin2exp = dict(oa.dropna(subset=['inferred_exposure_id']).groupby('principal').inferred_exposure_id.first())
cq = wc[wc.cost_type == 'consumer_query']
for x in cq.itertuples():
    tgt = prin2exp.get(x.principal)
    if tgt in nid and nid[tgt] in EXPCOST: EXPCOST[nid[tgt]][x.d] += x.est_cost_usd
EXPCOST = {e: [r(v) for v in arr] for e, arr in EXPCOST.items()}

# ---------- observed access / undeclared consumers ----------
OBS = []
for (p, pt, a, m, inf), g in oa.groupby(['principal', 'principal_type', 'node_id', 'mapped_exposure_id', 'inferred_exposure_id'], dropna=False):
    s = g.groupby('d').query_count.sum().reindex(range(ND), fill_value=0)
    OBS.append(dict(p=p, pt=pt, node=nid[a], m=None if pd.isna(m) else nid.get(m), inf=None if pd.isna(inf) else nid.get(inf),
                    q=s.astype(int).tolist(), gb=r(g.bytes_scanned.sum() / 1e9, 1), first=str(g.date.min().date())))
PCOST = {p: r(v) for p, v in cq.groupby('principal').est_cost_usd.sum().items()}

INC = []
for x in inc.itertuples():
    INC.append(dict(id=x.incident_id, title=x.title, node=nid[x.root_node_id], s=str(x.started_at)[:16],
                    e=None if pd.isna(x.resolved_at) else str(x.resolved_at)[:16], sev=x.severity, n=int(x.exposures_affected), cat=x.category))

OWN = {x.owner_name: dict(t=x.owner_team, em=x.email, sl=x.slack_channel, oc=x.on_call_rotation == 'yes') for x in owners.itertuples()}

out = dict(
    meta=dict(start=str(START.date()), end=str(END.date()), nd=ND, asOf='2026-10-19 23:59', plats=PLATS,
              dates=[str((START + pd.Timedelta(days=i)).date()) for i in range(ND)],
              dow=[(START + pd.Timedelta(days=i)).dayofweek for i in range(ND)]),
    N=N, E=E, UP={str(k): v for k, v in UP.items()}, LAY=LAY, JOBS=JOBS, JR=JR, S=S, SKIPD=SKIPD,
    EXPDAY={str(k): v for k, v in EXPDAY.items()}, CUR={str(k): v for k, v in CUR.items()},
    SCORE={str(k): v for k, v in SCORE.items()}, EP=EP, ERR=ERR,
    RTD={str(k): v for k, v in RTD.items()}, COSTD={str(k): v for k, v in COSTD.items()},
    ERRD={str(k): v for k, v in ERRD.items()}, RUNSD={str(k): v for k, v in RUNSD.items()},
    TH={str(k): v for k, v in TH.items()}, LAGD={str(k): v for k, v in LAGD.items()}, ROWS={str(k): v for k, v in ROWS.items()}, MATD={str(k): v for k, v in MATD.items()}, ROWSMAX={str(k): v for k, v in ROWSMAX.items()},
    TESTS=TESTS, TYPE_D=TYPE_D, SEM={str(k): v for k, v in SEM.items()}, CONS={str(k): v for k, v in CONS.items()},
    EXPCOST={str(k): v for k, v in EXPCOST.items()}, OBS=OBS, PCOST=PCOST, INC=INC, OWN=OWN,
)
def clean(o):
    if isinstance(o, dict): return {k: clean(v) for k, v in o.items()}
    if isinstance(o, list): return [clean(v) for v in o]
    if isinstance(o, float) and (math.isnan(o) or math.isinf(o)): return None
    if isinstance(o, (np.integer,)): return int(o)
    if isinstance(o, (np.floating,)): return None if np.isnan(o) else float(o)
    if isinstance(o, (np.bool_,)): return bool(o)
    return o
s = json.dumps(clean(out), separators=(',', ':'), allow_nan=False)
open(OUT, 'w').write(s)
print(f'wrote {OUT} ({len(s):,} bytes)')
